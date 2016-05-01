########
# Copyright (c) 2015 GigaSpaces Technologies Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
#    * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    * See the License for the specific language governing permissions and
#    * limitations under the License.

# Third-party Imports
from boto.ec2.elb.healthcheck import HealthCheck
import boto.exception

# Cloudify imports
from ec2 import constants
from ec2 import connection
from ec2 import utils
from cloudify import ctx
from cloudify.decorators import operation
from cloudify.exceptions import NonRecoverableError
from cloudify.exceptions import RecoverableError


@operation
def creation_validation(**_):
    """ This checks that all user supplied info is valid """

    for property_key in constants.ELB_REQUIRED_PROPERTIES:
        utils.validate_node_property(property_key, ctx.node.properties)

    if not ctx.node.properties['resource_id']:
        elb = None
    else:
        elb = _get_existing_elb(
            ctx.node.properties['resource_id'])

    if ctx.node.properties['use_external_resource'] and not elb:
        raise NonRecoverableError(
            'External resource, but the supplied '
            'elb does not exist in the account.')

    if not ctx.node.properties['use_external_resource'] and elb:
        raise NonRecoverableError(
            'Not external resource, but the supplied '
            'elb exists.')


@operation
def create_elb(**_):

    if ctx.node.properties['use_external_resource']:
        return

    lb = _create_elb()

    health_checks = ctx.node.properties.get('health_checks')

    if health_checks:
        for health_check in health_checks:
            _add_health_check_to_elb(lb, health_check)


def _add_instance_to_elb_list_in_properties(instance_id):

    if 'instance_list' not in ctx.target.instance.runtime_properties.keys():
        ctx.target.instance.runtime_properties['instance_list'] = []

    ctx.target.instance.runtime_properties['instance_list'].append(instance_id)


def _remove_instance_from_elb_list_in_properties(instance_id):
    if instance_id in ctx.target.instance.runtime_properties['instance_list']:
        ctx.target.instance.runtime_properties['instance_list'].remove(
            instance_id)


@operation
def remove_instance_from_elb(**_):

    elb_name = \
        utils.get_external_resource_id_or_raise(
            'elb_name', ctx.target.instance)

    instance_id = \
        utils.get_external_resource_id_or_raise(
            'instance_id', ctx.source.instance)

    instance_list = [instance_id]
    lb = _get_existing_elb(elb_name)

    ctx.logger.info('Attemping to remove instance: {0} from elb {1}'
                    .format(instance_id, elb_name))

    try:
        lb.deregister_instances(instance_list)
    except (boto.exception.EC2ResponseError,
            boto.exception.BotoServerError,
            boto.exception.BotoClientError) as e:
        if instance_id in _get_instance_list():
            raise RecoverableError('Instance not removed from Load Balancer '
                                   '{0}'.format(str(e)))

    ctx.logger.info(
        'Instance {0} removed from Load Balancer {1}.'
        .format(instance_id, elb_name))
    _remove_instance_from_elb_list_in_properties(instance_id)


@operation
def add_instance_to_elb(**_):

    elb_name = \
        utils.get_external_resource_id_or_raise(
            'elb_name', ctx.target.instance)

    instance_id = \
        utils.get_external_resource_id_or_raise(
            'instance_id', ctx.source.instance)

    ctx.logger.info('Attemping to remove instance: {0} from elb {1}'
                    .format(instance_id, elb_name))

    lb = _get_existing_elb(elb_name)

    try:
        lb.register_instances(instance_id)
    except (boto.exception.EC2ResponseError,
            boto.exception.BotoServerError,
            boto.exception.BotoClientError) as e:
            raise NonRecoverableError('Instance not added to Load Balancer '
                                      '{0}'.format(str(e)))

    ctx.logger.info(
        'Instance {0} added to Load Balancer {1}.'
        .format(instance_id, elb_name))

    _add_instance_to_elb_list_in_properties(instance_id)


def _add_health_check_to_elb(elb, health_check):

    hc = _create_health_check(health_check)

    try:
        elb.configure_health_check(hc)
    except (boto.exception.EC2ResponseError,
            boto.exception.BotoServerError,
            boto.exception.BotoClientError) as e:
        raise NonRecoverableError('Health check not added to Load Balancer '
                                  '{0}'.format(str(e)))

    ctx.logger.info(
        'Health check added to Load Balancer {0}.'
        .format(elb.name))


def use_external_elb(**_):

    utils.use_external_resource(ctx.node.properties)


@operation
def delete_elb(**_):

    if ctx.node.properties['use_external_resource']:
        utils.unassign_runtime_property_from_resource(
            constants.EXTERNAL_RESOURCE_ID, ctx.instance)
        return

    ctx.logger.info('Attempting to delete Load Balancer.')

    elb_name = ctx.node.properties['elb_name']

    lb = _get_existing_elb(elb_name)

    try:
        lb.delete()
    except (boto.exception.EC2ResponseError,
            boto.exception.BotoServerError,
            boto.exception.BotoClientError) as e:
        raise NonRecoverableError('Load Balancer {0} not deleted.'
                                  .format(str(e)))

    ctx.logger.info(
        'Load Balancer {0} deleted. '
        .format(elb_name))
    if 'elb_name' in ctx.instance.runtime_properties:
        ctx.instance.runtime_properties.pop('elb_name')


def _create_health_check(user_health_check):

    health_check = {
        'interval': constants.HEALTH_CHECK_INTERVAL,
        'healthy_threshold': constants.HEALTH_CHECK_HEALTHY_THRESHOLD,
        'timeout': constants.HEALTH_CHECK_TIMEOUT,
        'unhealthy_threshold': constants.HEALTH_CHECK_UNHEALTHY_THRESHOLD
    }

    health_check.update(user_health_check)

    try:
        health_check = HealthCheck(**health_check)
    except boto.exception.BotoClientError as e:
        raise NonRecoverableError(
            'Health Check not created due to bad definition: '
            '{0}'.format(str(e)))

    return health_check


def _create_elb_params():
    params_dict = {'listeners': ctx.node.properties['listeners'],
                   'name': ctx.node.properties['elb_name'],
                   'zones': ctx.node.properties['zones']}
    if 'security_groups' in ctx.node.properties.keys():
        params_dict['security_groups'] = ctx.node.properties['security_groups']
    if 'scheme' in ctx.node.properties.keys():
        params_dict['scheme'] = ctx.node.properties['scheme']
    if 'subnets' in ctx.node.properties.keys():
        params_dict['subnets'] = ctx.node.properties['subnets']
    return params_dict


def _create_elb():

    ctx.logger.info('Attempting to Create Load Balancer.')

    params_dict = _create_elb_params()
    elb_client = connection.ELBConnectionClient().client()

    try:
        lb = elb_client.create_load_balancer(**params_dict)
    except (boto.exception.EC2ResponseError,
            boto.exception.BotoServerError,
            boto.exception.BotoClientError) as e:
        raise RecoverableError('Load Balancer not created '
                               '{0}'.format(str(e)))

    if not lb:
        raise NonRecoverableError(
            'Load Balancer not created. While the create request was completed'
            ' successfully, verifying the load balancer afterwards has failed')

    ctx.logger.info('Load Balancer Created.')

    utils.set_external_resource_id(params_dict['name'],
                                   ctx.instance,
                                   external=False)

    ctx.instance.runtime_properties['elb_name'] = params_dict['name']

    return lb


def _get_instance_list():

    ctx.logger.info('Attempting to get Load Balancer Instance List.')

    elb_name = ctx.node.properties['elb_name']
    lb = _get_existing_elb(elb_name)
    list_of_instances = lb.instances
    ctx.instance.runtime_properties[constants.EXTERNAL_RESOURCE_ID] = lb.name

    return list_of_instances


def _get_elbs_by_names(list_of_names):

    ctx.logger.info(
        'Attempting to get Load Balancers {0}.'.format(list_of_names))
    elb_client = connection.ELBConnectionClient().client()

    try:
        total_elb_list = elb_client.get_all_load_balancers()
        elb_list = elb_client.get_all_load_balancers(
            load_balancer_names=list_of_names)
    except (boto.exception.EC2ResponseError,
            boto.exception.BotoServerError,
            boto.exception.BotoClientError) as e:
        if 'LoadBalancerNotFound' in e:
            ctx.logger.info('Unable to find load balancers matching: '
                            '{0}'.format(list_of_names))
            ctx.logger.info('load balancers available: '
                            '{0}'.format(total_elb_list))
        raise NonRecoverableError('Error when accessing ELB interface '
                                  '{0}'.format(str(e)))
    return elb_list


def _get_existing_elb(elb_name):
    elbs = _get_elbs_by_names([elb_name])
    if elbs:
        if elbs[0].name == elb_name:
            return elbs[0]
    return None


@operation
def start(**_):
    """Add tags to EC2 elastic load balancer.
    """

    elb_name = ctx.node.properties['elb_name']
    lb = _get_existing_elb(elb_name)

    utils.add_tag(lb)

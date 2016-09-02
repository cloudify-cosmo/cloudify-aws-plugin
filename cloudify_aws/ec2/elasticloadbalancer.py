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
from boto import exception
from boto.ec2.elb.healthcheck import HealthCheck

# Cloudify imports
from cloudify import ctx
from cloudify.decorators import operation
from cloudify_aws import constants, connection, utils
from cloudify.exceptions import RecoverableError
from cloudify.exceptions import NonRecoverableError
from cloudify_aws.base import AwsBaseNode, AwsBaseRelationship


@operation
def creation_validation(**_):
    return Elb().creation_validation()


@operation
def create(args=None, **_):
    return Elb().created(args)


@operation
def delete(args=None, **_):
    return Elb().deleted(args)


@operation
def associate(args=None, **_):
    return ElbInstanceConnection().associated(args)


@operation
def disassociate(args=None, **_):
    return ElbInstanceConnection().disassociated(args)


class ElbInstanceConnection(AwsBaseRelationship):

    def __init__(self, client=None):
        self.client = client or connection.ELBConnectionClient().client()
        super(ElbInstanceConnection, self).__init__(client=self.client)
        self.not_found_error = 'InvalidInstanceID.NotFound.'
        self.resource_id = None
        self.source_get_all_handler = {
            'function': self.client.get_all_load_balancers,
            'argument': (
                '{0}_names'.format(constants.ELB['AWS_RESOURCE_TYPE'])
            )
        }

    def associate(self, args=None, **_):

        elb_name = self.target_resource_id

        instance_id = self.source_resource_id

        ctx.logger.info('Attemping to add instance: {0} to elb {1}'
                        .format(instance_id, elb_name))

        associate_args = dict(
            load_balancer_name=elb_name,
            instances=[instance_id])
        associate_args = utils.update_args(associate_args, args)

        try:
            self.execute(self.client.register_instances, associate_args,
                         raise_on_falsy=True)
        except (exception.EC2ResponseError,
                exception.BotoServerError,
                exception.BotoClientError) as e:
            raise NonRecoverableError('Instance not added to Load '
                                      'Balancer {0}'.format(str(e)))

        ctx.logger.info(
            'Instance {0} added to Load Balancer {1}.'
            .format(instance_id, elb_name))

        self._add_instance_to_elb_list_in_properties(instance_id)

        return True

    def disassociate(self, args=None, **_):

        disassociate_args = dict(
            load_balancer_name=self.target_resource_id,
            instances=[self.source_resource_id]
        )
        disassociate_args = utils.update_args(disassociate_args, args)

        try:
            self.execute(self.client.deregister_instances, disassociate_args)
        except (exception.EC2ResponseError,
                exception.BotoServerError,
                exception.BotoClientError) as e:
            if self.source_resource_id in self._get_instance_list():
                raise RecoverableError('Instance not removed from Load '
                                       'Balancer {0}'.format(str(e)))

        self._remove_instance_from_elb_list_in_properties(
            self.source_resource_id)

        return True

    def post_associate(self):

        ctx.logger.info(
            'Instance {0} registrated to Load Balancer {1}.'
            .format(self.source_resource_id, self.target_resource_id))

        self._add_instance_to_elb_list_in_properties(self.source_resource_id)

        return True

    def _add_instance_to_elb_list_in_properties(self, instance_id):

        if 'instance_list' not in \
                ctx.target.instance.runtime_properties.keys():
            ctx.target.instance.runtime_properties['instance_list'] = []

        ctx.target.instance.runtime_properties['instance_list'] \
            .append(instance_id)

    def _remove_instance_from_elb_list_in_properties(self, instance_id):
        if instance_id in \
                ctx.target.instance.runtime_properties['instance_list']:
            ctx.target.instance.runtime_properties['instance_list'] \
                .remove(instance_id)

    def _get_instance_list(self):

        ctx.logger.info('Attempting to get Load Balancer Instance List.')

        elb_name = ctx.node.properties['elb_name']
        lb = self.get_target_resource(elb_name)
        list_of_instances = lb.instances
        self.resource_id = \
            lb.name

        return list_of_instances

    def get_target_resource(self, elb_name=None):
        return self.filter_for_single_resource(
            self.get_all_handler['function'],
            [elb_name]
        )


class Elb(AwsBaseNode):

    def __init__(self, client=None):
        self.client = client or connection.ELBConnectionClient().client()
        super(Elb, self).__init__(
            constants.ELB['AWS_RESOURCE_TYPE'],
            constants.ELB['REQUIRED_PROPERTIES'],
            self.client,
        )
        self.not_found_error = constants.ELB['NOT_FOUND_ERROR']
        self.get_all_handler = {
            'function': self.client.get_all_load_balancers,
            'argument': '{0}_names'.format(constants.ELB['AWS_RESOURCE_TYPE'])
        }

    def create(self, args=None, **_):

        lb = self._create_elb(args)

        health_checks = ctx.node.properties.get('health_checks')

        if health_checks:
            for health_check in health_checks:
                self._add_health_check_to_elb(lb, health_check)

        return True

    def _create_elb(self, args):

        create_args = self._create_elb_params()
        create_args = utils.update_args(create_args, args)

        try:
            lb = self.execute(self.client.create_load_balancer, create_args,
                              raise_on_falsy=True)
        except (exception.EC2ResponseError,
                exception.BotoServerError,
                exception.BotoClientError) as e:
            raise RecoverableError('Load Balancer not created '
                                   '{0}'.format(str(e)))

        if not lb:
            raise NonRecoverableError(
                'Load Balancer not created. While the create '
                'request was completed'
                ' successfully, verifying the load balancer '
                'afterwards has failed')

        ctx.instance.runtime_properties['elb_name'] = create_args['name']
        self.resource_id = create_args['name']

        return lb

    def delete(self, args=None, **_):

        delete_args = dict(
            name=ctx.node.properties['elb_name']
        )
        delete_args = utils.update_args(delete_args, args)

        try:
            self.execute(self.client.delete_load_balancer, delete_args,
                         raise_on_falsy=True)
        except (exception.EC2ResponseError,
                exception.BotoServerError,
                exception.BotoClientError) as e:
            raise NonRecoverableError('Load Balancer {0} not deleted.'
                                      .format(str(e)))

        return True

    def post_delete(self):
        if 'elb_name' in ctx.instance.runtime_properties:
            ctx.instance.runtime_properties.pop('elb_name')
        return True

    def _add_health_check_to_elb(self, elb, health_check):

        hc = self._create_health_check(health_check)
        add_hc_args = dict(
            name=elb.name,
            health_check=hc
        )

        try:
            self.execute(self.client.configure_health_check, add_hc_args,
                         raise_on_falsy=True)
        except (exception.EC2ResponseError,
                exception.BotoServerError,
                exception.BotoClientError) as e:
            raise NonRecoverableError('Health check not added to Load '
                                      'Balancer {0}'.format(str(e)))

        ctx.logger.info(
            'Health check added to Load Balancer {0}.'
            .format(elb.name))

    def _create_elb_params(self):
        params_dict = {'listeners': ctx.node.properties['listeners'],
                       'name': ctx.node.properties['elb_name'],
                       'zones': ctx.node.properties['zones']}
        if 'security_groups' in ctx.node.properties.keys():
            params_dict['security_groups'] = \
                ctx.node.properties['security_groups']
        if 'scheme' in ctx.node.properties.keys():
            params_dict['scheme'] = ctx.node.properties['scheme']
        if 'subnets' in ctx.node.properties.keys():
            params_dict['subnets'] = ctx.node.properties['subnets']
        return params_dict

    def _create_health_check(self, user_health_check):

        health_check = {
            'interval': constants.HEALTH_CHECK_INTERVAL,
            'healthy_threshold': constants.HEALTH_CHECK_HEALTHY_THRESHOLD,
            'timeout': constants.HEALTH_CHECK_TIMEOUT,
            'unhealthy_threshold': constants.HEALTH_CHECK_UNHEALTHY_THRESHOLD
        }

        health_check.update(user_health_check)

        try:
            health_check = HealthCheck(**health_check)
        except exception.BotoClientError as e:
            raise NonRecoverableError(
                'Health Check not created due to bad definition: '
                '{0}'.format(str(e)))

        return health_check

    def get_resource(self):
        return self.resource_id

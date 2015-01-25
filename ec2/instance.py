########
# Copyright (c) 2014 GigaSpaces Technologies Ltd. All rights reserved
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

# Boto Imports
import boto.exception

# Cloudify imports
from cloudify import ctx
from cloudify.exceptions import NonRecoverableError, RecoverableError
from cloudify.decorators import operation
from ec2 import utils
from ec2 import connection

# run_instances should not allow more than one instance
# to be created this should be specified in the node_template
# instances, deploy = n
RUN_INSTANCES_UNSUPPORTED = {
    'min_count': 1,
    'max_count': 1
}


@operation
def run_instances(**_):
    """ Creates an EC2 Classic Instance.
        Requires:
            ctx.node.properties['image_id']
            ctx.node.properties['instance_type']
        Sets:
            ctx.instance.runtime_properties['aws_resource_id']
    """

    ec2_client = connection.EC2ConnectionClient().client()

    if ctx.node.properties.get('use_external_resource', False) is True:
        instance_id = ctx.node.properties.get('resource_id')
        instance = utils.get_instance_from_id(instance_id, ctx=ctx)
        ctx.instance.runtime_properties['aws_resource_id'] = instance.id
        ctx.logger.info('Using existing resource: {0}.'.format(instance.id))
        return

    arguments = dict()
    arguments['image_id'] = ctx.node.properties.get('image_id')
    arguments['instance_type'] = ctx.node.properties.get('instance_type')
    args_to_merge = utils.build_arg_dict(
        ctx.node.properties['parameters'].copy(), RUN_INSTANCES_UNSUPPORTED)
    arguments.update(args_to_merge)

    ctx.logger.info('Creating EC2 Instance.')
    ctx.logger.info('Attempting to create EC2 Instance.'
                    'Image id: {0}. Instance type: {1}.'
                    .format(arguments['image_id'],
                            arguments['instance_type']))
    ctx.logger.info('Sending these API parameters: {0}.'
                    .format(arguments))

    try:
        reservation = ec2_client.run_instances(**arguments)
    except (boto.exception.EC2ResponseError,
            boto.exception.BotoServerError) as e:
        raise NonRecoverableError('Error. Failed to run EC2 Instance: '
                                  'API returned: {0}.'.format(str(str(e))))

    instance_id = reservation.instances[0].id
    ctx.instance.runtime_properties['aws_resource_id'] = instance_id


@operation
def start(retry_interval, **_):
    """ Starts an EC2 Classic Instance.
        If start command has already run, this does nothing.
        Requires:
            ctx.instance.runtime_properties['aws_resource_id']
        Sets:
            ctx.instance.runtime_properties['ip']
            ctx.instance.runtime_properties['private_dns_name']
            ctx.instance.runtime_properties['public_dns_name']
            ctx.instance.runtime_properties['public_ip_address']
    """
    ec2_client = connection.EC2ConnectionClient().client()
    instance_id = ctx.instance.runtime_properties.get('aws_resource_id')

    if utils.get_instance_state(ctx=ctx) == 16:
        ctx.logger.info('Instance {0} is running.'.format(instance_id))
        return

    ctx.logger.info('Starting EC2 Instance.')
    ctx.logger.debug('Attempting to start instance: {0}.)'.format(instance_id))

    try:
        ec2_client.start_instances(instance_id)
    except (boto.exception.EC2ResponseError,
            boto.exception.BotoServerError) as e:
        raise NonRecoverableError('Error. Failed to start EC2 Instance: '
                                  'API returned: {0}.'.format(str(e)))

    if utils.get_instance_state(ctx=ctx) == 16:
        ctx.logger.info('Instance {0} is running.'.format(instance_id))
        ctx.instance.runtime_properties['private_dns_name'] = \
            utils.get_private_dns_name(retry_interval, ctx=ctx)
        ctx.instance.runtime_properties['public_dns_name'] = \
            utils.get_public_dns_name(retry_interval, ctx=ctx)
        ctx.instance.runtime_properties['ip'] = \
            utils.get_private_ip_address(retry_interval, ctx=ctx)
        ctx.instance.runtime_properties['public_ip_address'] = \
            utils.get_public_ip_address(retry_interval, ctx=ctx)
    else:
        raise RecoverableError('Waiting for server to be running'
                               ' Retrying...',
                               retry_after=retry_interval)


@operation
def stop(retry_interval, **_):
    """ Stops an existing EC2 instance.
        If already stopped, this does nothing.
        Requires:
            ctx.instance.runtime_properties['aws_resource_id']
    """
    ec2_client = connection.EC2ConnectionClient().client()

    instance_id = ctx.instance.runtime_properties.get('aws_resource_id')

    ctx.logger.info('Stopping EC2 Instance.')
    ctx.logger.debug('Attempting to stop EC2 Instance.'
                     '(Instance id: {0}.)'.format(instance_id))

    try:
        ec2_client.stop_instances(instance_id)
    except (boto.exception.EC2ResponseError,
            boto.exception.BotoServerError) as e:
        raise NonRecoverableError('Error. Failed to stop EC2 Instance: '
                                  'API returned: {0}.'.format(str(e)))
    finally:
        ctx.instance.runtime_properties.pop('private_dns_name')
        ctx.instance.runtime_properties.pop('public_dns_name')
        ctx.instance.runtime_properties.pop('public_ip_address')
        ctx.instance.runtime_properties.pop('ip')

    # get the timeout code validate state
    if utils.get_instance_state(ctx=ctx) == 80:
        ctx.logger.info('Instance {0} is stopped.'.format(instance_id))
    else:
        raise RecoverableError('Waiting for server to stop'
                               'Retrying...',
                               retry_after=retry_interval)


@operation
def terminate(retry_interval, **_):
    """ Terminates an existing EC2 instance.
        If already terminated, this does nothing.
    """
    ec2_client = connection.EC2ConnectionClient().client()

    instance_id = ctx.instance.runtime_properties.get('aws_resource_id')

    ctx.logger.info('Terminating EC2 Instance.')
    ctx.logger.debug('Attempting to terminate EC2 Instance.'
                     '(Instance id: {0}.)'.format(instance_id))

    try:
        ec2_client.terminate_instances(instance_id)
    except (boto.exception.EC2ResponseError,
            boto.exception.BotoServerError) as e:
        raise NonRecoverableError('Error. Failed to terminate '
                                  'EC2 Instance: API returned: {0}.'
                                  .format(str(e)))
    finally:
        ctx.instance.runtime_properties.pop('private_dns_name', None)
        ctx.instance.runtime_properties.pop('public_dns_name', None)
        ctx.instance.runtime_properties.pop('public_ip_address', None)
        ctx.instance.runtime_properties.pop('ip', None)
        ctx.instance.runtime_properties.pop('aws_resource_id', None)
        ctx.logger.debug('Attemped to delete the instance and its '
                         'runtime properties')


@operation
def creation_validation(**_):
    """ This checks that all user supplied info is valid """
    required_properties = ['resource_id', 'use_external_resource',
                           'image_id', 'instance_type']

    for property_key in required_properties:
        utils.validate_node_property(property_key, ctx=ctx)

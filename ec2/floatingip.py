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
from boto.exception import EC2ResponseError
from boto.exception import BotoServerError

# Cloudify imports
from cloudify import ctx
from cloudify.exceptions import NonRecoverableError
from cloudify.decorators import operation
from ec2 import connection


@operation
def create(**kwargs):
    """ Gets a floating IP from an Amazon Elastic IP.
    """
    ec2_client = connection.EC2ConnectionClient().client()
    ctx.logger.debug('Getting Elastic IP from Amazon EC2.')

    try:
        address_object = ec2_client.allocate_address()
    except (EC2ResponseError, BotoServerError) as e:
        raise NonRecoverableError('(Node: {0}): Error. Failed to get '
                                  'floating ip, returned: {1}.'
                                  .format(ctx.instance.id, e))

    ctx.logger.info('Elastic IP creation response: {0}'.format(address_object))
    ctx.instance.runtime_properties['floatingip'] = address_object.public_ip


@operation
def delete(**kwargs):
    ec2_client = connection.EC2ConnectionClient().client()
    ctx.logger.debug('Deleting a Floating IP.')
    floatingip = ctx.instance.runtime_properties['floatingip']

    try:
        ec2_client.release_address(public_ip=floatingip)
    except (EC2ResponseError, BotoServerError) as e:
        raise NonRecoverableError('(Node: {0}): Error. Failed to delete '
                                  'floating ip, returned: {1}.'
                                  .format(ctx.instance.id, e))

    ctx.logger.info('Deleted Floating IP {0}.'.format(floatingip))


@operation
def connect(**kwargs):
    """ Attaches a floating IP to a node.
    """
    ec2_client = connection.EC2ConnectionClient().client()
    ctx.logger.debug('Attaching a Floating IP to EC2 Instance.')
    floatingip = ctx.target.node.properties['floatingip']
    instance_id = ctx.source.instance.runtime_properties['instance_id']

    try:
        ec2_client.associate_address(instance_id=instance_id,
                                     public_ip=floatingip)
    except (EC2ResponseError, BotoServerError) as e:
        raise NonRecoverableError('Error. Failed to attach '
                                  'floating ip, returned: {0}.'
                                  .format(e))

    ctx.logger.info('Attached Floating IP {0} to instance {1}.'.format(
        floatingip, instance_id))


@operation
def disconnect(**kwargs):
    ec2_client = connection.EC2ConnectionClient().client()
    ctx.logger.debug('Detaching a Floating IP to EC2 Instance.')
    floatingip = ctx.target.node.properties['floatingip']

    try:
        ec2_client.disassociate_address(public_ip=floatingip)
    except (EC2ResponseError, BotoServerError) as e:
        raise NonRecoverableError('(Error. Failed to detach '
                                  'floating ip, returned: {0}.'
                                  .format(e))

    ctx.logger.info('detached Floating IP {0}.'.format(floatingip))

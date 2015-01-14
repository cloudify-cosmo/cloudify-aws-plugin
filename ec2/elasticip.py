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
    """ Provisions an Elastic IP in the connected region in the AWS account.
    """
    ec2_client = connection.EC2ConnectionClient().client()
    ctx.logger.info('Provisioning Elastic IP.')

    try:
        address_object = ec2_client.allocate_address()
    except (EC2ResponseError, BotoServerError) as e:
        raise NonRecoverableError('(Node: {0}): Error. Failed to '
                                  'provision Elastic IP. Error: {1}.'
                                  .format(ctx.instance.id, e))

    ctx.logger.info('Elastic IP Provisioned: {0}'.format(
        address_object.public_ip))
    ctx.instance.runtime_properties['elasticip'] = address_object.public_ip


@operation
def delete(**kwargs):
    """ Deletes an Elastic IP from the connected region in the AWS account.
    """
    ec2_client = connection.EC2ConnectionClient().client()
    ctx.logger.info('Deleting an Elastic IP.')

    elasticip = ctx.instance.runtime_properties['elasticip']

    try:
        ec2_client.release_address(public_ip=elasticip)
    except (EC2ResponseError, BotoServerError) as e:
        raise NonRecoverableError('(Node: {0}): Error. Failed to '
                                  'delete Elastic IP. Error: {1}.'
                                  .format(ctx.instance.id, e))

    ctx.logger.info('Deleted Elastic IP {0}.')


@operation
def connect(**kwargs):
    """ Connects an Elastic IP to an EC2 Instance.
    """
    ec2_client = connection.EC2ConnectionClient().client()
    ctx.logger.info('Attaching an Elastic IP to an EC2 Instance.')

    elasticip = ctx.target.node.properties['elasticip']
    instance_id = ctx.source.instance.runtime_properties['instance_id']

    try:
        ec2_client.associate_address(instance_id=instance_id,
                                     public_ip=elasticip)
    except (EC2ResponseError, BotoServerError) as e:
        raise NonRecoverableError('Error. Failed to '
                                  'attach Elastic IP. Error: {0}.'
                                  .format(e))

    ctx.logger.info('Connected Elastic IP to instance.')


@operation
def disconnect(**kwargs):
    """ Disconnects an Elastic IP from an EC2 Instance.
    """
    ec2_client = connection.EC2ConnectionClient().client()
    ctx.logger.info('Disconnecting Elastic IP from an EC2 Instance.')
    elasticip = ctx.target.node.properties['elasticip']

    try:
        ec2_client.disassociate_address(public_ip=elasticip)
    except (EC2ResponseError, BotoServerError) as e:
        raise NonRecoverableError('Error. Failed to detach '
                                  'Elastic IP, returned: {0}.'
                                  .format(e))

    ctx.logger.info('Disconnected Elastic IP from instance.')

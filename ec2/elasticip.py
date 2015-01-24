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
from ec2 import utils


@operation
def allocate(**_):
    """ Allocates an Elastic IP in the connected region in the AWS account.
    """
    ec2_client = connection.EC2ConnectionClient().client()
    ctx.logger.info('Allocating Elastic IP.')

    if ctx.node.properties.get('use_external_resource', False) is True:
        address = utils.get_address_by_id(
            ctx.node.properties.get('resource_id'), ctx=ctx)
        ctx.instance.runtime_properties['aws_resource_id'] = address
        ctx.logger.info('Using existing resource: {0}'.format(address))
        return

    try:
        address_object = ec2_client.allocate_address(domain=None)
    except (EC2ResponseError, BotoServerError) as e:
        raise NonRecoverableError('Failed to provision Elastic IP. Error: {0}.'
                                  .format(str(e)))

    ctx.logger.info('Elastic IP allocated: {0}'.format(
        address_object.public_ip))
    ctx.instance.runtime_properties['aws_resource_id'] = \
        address_object.public_ip
    ctx.instance.runtime_properties['allocation_id'] = \
        address_object.allocation_id


@operation
def release(**_):
    """ Releases an Elastic IP from the connected region in the AWS account.
    """
    ctx.logger.info('Releasing an Elastic IP.')

    elasticip = ctx.instance.runtime_properties.get('aws_resource_id')
    allocation_id = ctx.instance.runtime_properties.get('allocation_id')

    ctx.logger.info('{}{}'.format(elasticip, allocation_id))

    address_object = utils.get_address_object_by_id(elasticip, ctx=ctx)

    try:
        address_object.release()
    except (EC2ResponseError, BotoServerError) as e:
        raise NonRecoverableError('Error. Failed to '
                                  'delete Elastic IP. Error: {0}.'
                                  .format(e))
    finally:
        ctx.instance.runtime_properties.pop('aws_resource_id', None)
        ctx.instance.runtime_properties.pop('allocation_id', None)

    ctx.logger.info('Released Elastic IP {0}.'.format(elasticip))


@operation
def associate(**_):
    """ Associates an Elastic IP with an EC2 Instance.
    """
    ec2_client = connection.EC2ConnectionClient().client()

    instance_id = ctx.source.instance.runtime_properties.get('aws_resource_id')
    elasticip = ctx.target.instance.runtime_properties.get('aws_resource_id')
    ctx.logger.info('Associating an Elastic IP {0} '
                    'with an EC2 Instance {1}.'.format(elasticip, instance_id))

    try:
        ec2_client.associate_address(instance_id=instance_id,
                                     public_ip=elasticip)
    except (EC2ResponseError, BotoServerError) as e:
        raise NonRecoverableError('Error. Failed to '
                                  'attach Elastic IP. Error: {0}.'
                                  .format(str(e)))

    ctx.logger.info('Associated Elastic IP {0} with instance {1}.'.format(
        elasticip, instance_id))
    ctx.source.instance.runtime_properties['ip'] = elasticip


@operation
def disassociate(**_):
    """ Disassociates an Elastic IP from an EC2 Instance.
    """
    ec2_client = connection.EC2ConnectionClient().client()
    elasticip = ctx.target.instance.runtime_properties['aws_resource_id']
    ctx.logger.info('Disassociating Elastic IP {0}'.format(elasticip))

    try:
        ec2_client.disassociate_address(public_ip=elasticip)
    except (EC2ResponseError, BotoServerError) as e:
        raise NonRecoverableError('Error. Failed to detach '
                                  'Elastic IP, returned: {0}.'
                                  .format(e))
    finally:
        ctx.source.instance.runtime_properties.pop('ip')

    ctx.logger.info('Disassociated Elastic IP {0}.'.format(
        elasticip))


@operation
def creation_validation(**_):
    """ This checks that all user supplied info is valid """
    required_properties = ['resource_id']
    for property_key in required_properties:
        utils.validate_node_properties(property_key, ctx=ctx)

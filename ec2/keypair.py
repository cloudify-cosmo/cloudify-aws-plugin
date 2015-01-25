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

# Built-in Imports
import os

# Boto Imports
from boto.exception import EC2ResponseError
from boto.exception import BotoServerError
from boto.exception import BotoClientError

# Cloudify imports
from cloudify import ctx
from cloudify.exceptions import NonRecoverableError
from cloudify.decorators import operation
from ec2 import utils
from ec2 import connection


@operation
def create(**kwargs):
    """ This will create the key pair within the region you are currently
        connected to.
    """
    ec2_client = connection.EC2ConnectionClient().client()

    if ctx.node.properties.get('use_external_resource', False) is True:
        ctx.instance.runtime_properties['aws_resource_id'] = \
            utils.get_key_pair_by_id(ctx=ctx)
        if not utils.search_for_key_file(ctx=ctx):
            raise NonRecoverableError('use_external_resource was specified, '
                                      'and a name given, but the key pair was'
                                      'not located on the filesystem.')
        return

    key_pair_name = ctx.node.properties['resource_id']
    ctx.logger.info('Creating key pair.')

    try:
        kp = ec2_client.create_key_pair(key_pair_name)
    except (EC2ResponseError, BotoServerError, BotoClientError) as e:
        raise NonRecoverableError('Key pair not created. '
                                  'API returned: {0}'.format(str(e)))

    ctx.logger.info('Created key pair: {0}.'.format(kp.name))
    ctx.instance.runtime_properties['aws_resource_id'] = kp.name

    utils.save_key_pair(kp, ctx=ctx)
    path = os.path.expanduser(ctx.node.properties['private_key_path'])
    ctx.instance.runtime_properties['key_path'] = \
        os.path.join(path, '{0}{1}'.format(
            ctx.node.properties['resource_id'], '.pem'))


@operation
def delete(**kwargs):
    """ This will delete the key pair that you specified in the blueprint
        when this lifecycle operation is called.
    """
    ec2_client = connection.EC2ConnectionClient().client()
    key_pair_name = ctx.instance.runtime_properties['aws_resource_id']
    ctx.logger.info('Deleting the keypair.')

    try:
        ec2_client.delete_key_pair(key_pair_name)
    except (EC2ResponseError, BotoServerError) as e:
        raise NonRecoverableError('Error response on key pair delete. '
                                  'API returned: {0}'.format(str(e)))
    finally:
        ctx.instance.runtime_properties.pop('aws_resource_id', None)
        ctx.instance.runtime_properties.pop('key_path', None)
        ctx.logger.debug('Attempted to delete key pair from account.')

    utils.delete_key_pair(key_pair_name, ctx=ctx)
    ctx.logger.info('Deleted key pair: {0}.'.format(key_pair_name))


@operation
def creation_validation(**_):
    """ This checks that all user supplied info is valid """
    required_properties = ['resource_id', 'use_external_resource']
    for property_key in required_properties:
        utils.validate_node_property(property_key, ctx=ctx)

    if ctx.node.properties.get('use_external_resource', False) is True \
            and utils.search_for_key_file(ctx=ctx) is not True:
        raise NonRecoverableError('Use external resource is true, but the '
                                  'key file does not exist.')

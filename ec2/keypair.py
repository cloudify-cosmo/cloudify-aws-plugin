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
from ec2 import utils
from ec2 import connection


@operation
def create(**kwargs):
    """ This will create a key pair. If private_key_path is
        given, then the import method is used.
    """

    if 'private_key_path' in ctx.node.properties:
        upload(ctx=ctx)
    else:
        create(ctx=ctx)


def create_new(ctx):
    """ This will create the key pair within the region you are currently
        connected to.
    """
    ec2_client = connection.EC2ConnectionClient().client()
    key_pair_name = ctx.node.properties['name']
    ctx.logger.info('Creating key pair.')

    try:
        kp = ec2_client.create_key_pair(key_pair_name)
    except (EC2ResponseError, BotoServerError) as e:
        raise NonRecoverableError('Key pair not created. '
                                  'API returned: {0}'.format(e))

    ctx.logger.info('Created key pair.')
    ctx.instance.runtime_properties['key_pair_name'] = kp.name

    utils.save_key_pair(kp)


@operation
def delete(**kwargs):
    """ This will delete the key pair that you specified in the blueprint
        when this lifecycle operation is called.
    """
    ec2_client = connection.EC2ConnectionClient().client()
    key_pair_name = ctx.instance.runtime_properties['key_pair_name']
    ctx.logger.info('Deleting the keypair.')

    try:
        ec2_client.delete_key_pair(key_pair_name)
    except (EC2ResponseError, BotoServerError) as e:
        raise NonRecoverableError('Error response on key pair delete. '
                                  'API returned: {0}'.format(e))

    ctx.logger.info('Deleted key pair.')


@operation
def upload(ctx):
    ec2_client = connection.EC2ConnectionClient().client()
    key_pair_name = ctx.instance.runtime_properties['key_pair_name']
    ctx.logger.info('Importing key pair.')

    try:
        kp = ec2_client.create_key_pair(
            key_pair_name,
            ctx.get_resource(ctx.node.property['public_key_material']))
    except (EC2ResponseError, BotoServerError) as e:
        raise NonRecoverableError('Key pair not created. '
                                  'API returned: {0}'.format(e))

    ctx.logger.info('Created key pair.')
    utils.save_key_pair(kp)


@operation
def validate_creation(**kwargs):
    ec2_client = connection.EC2ConnectionClient().client()
    ctx.logger.info('Validating that the keypair '
                    'was created in your account.')
    key_pair_name = ctx.instance.runtime_properties['key_pair_name']

    try:
        ec2_client.get_key_pair(key_pair_name)
    except (EC2ResponseError, BotoServerError) as e:
        raise NonRecoverableError('Unable to validate that Key Pair exists. '
                                  'API returned: {0}'.format(e))

    ctx.logger.info('Validated key pair.')

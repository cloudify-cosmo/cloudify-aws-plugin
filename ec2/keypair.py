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
import boto.exception

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
        Requires:
            ctx.node.properties['resource_id']
        Sets:
            ctx.instance.runtime_properties['aws_resource_id']
            ctx.instance.runtime_properties['key_path']
    """

    ec2_client = connection.EC2ConnectionClient().client()

    if ctx.node.properties['use_external_resource']:
        key_pair_id = ctx.node.properties['resource_id']
        key_pair = utils.get_key_pair_by_id(key_pair_id)
        ctx.instance.runtime_properties['aws_resource_id'] = key_pair.name
        key_path = get_key_file_path(ctx=ctx)
        ctx.logger.debug('Path to key file: {0}.'.format(key_path))
        if not search_for_key_file(key_path):
            raise NonRecoverableError('use_external_resource was specified, '
                                      'and a name given, but the key pair was '
                                      'not located on the filesystem.')
        ctx.logger.info('Using existing key pair: {0}.'.format(key_pair.name))
        return

    key_pair_name = ctx.node.properties['resource_id']

    ctx.logger.debug('Creating key pair.')

    try:
        kp = ec2_client.create_key_pair(key_pair_name)
    except (boto.exception.EC2ResponseError,
            boto.exception.BotoServerError,
            boto.exception.BotoClientError) as e:
        raise NonRecoverableError('Key pair not created. {0}'.format(str(e)))

    ctx.instance.runtime_properties['aws_resource_id'] = kp.name
    ctx.logger.info('Created key pair: {0}.'.format(kp.name))

    save_key_pair(kp, ctx=ctx)


@operation
def delete(**kwargs):
    """ This will delete the key pair that you specified in the blueprint
        when this lifecycle operation is called.
    """
    ec2_client = connection.EC2ConnectionClient().client()

    if 'aws_resource_id' not in ctx.instance.runtime_properties:
        raise NonRecoverableError(
            'Cannot delete key pair because aws_resource_id is not assigned.')

    key_pair_name = ctx.instance.runtime_properties['aws_resource_id']

    ctx.logger.debug('Attempting to delete key pair from account.')

    try:
        ec2_client.delete_key_pair(key_pair_name)
    except (boto.exception.EC2ResponseError,
            boto.exception.BotoServerError) as e:
        raise NonRecoverableError('{0}'.format(str(e)))

    try:
        utils.get_key_pair_by_id(key_pair_name)
    except NonRecoverableError:
        ctx.logger.debug(
            'Generally NonRecoverableError indicates that an operation failed.'
            'In this case, everything worked correctly.')
        del(ctx.instance.runtime_properties['aws_resource_id'])
        del(ctx.instance.runtime_properties['key_path'])
        ctx.logger.info('Deleted key pair: {0}.'.format(key_pair_name))
        delete_key_file(ctx=ctx)
    else:
        ctx.logger.error(
            'Could not delete key pair. Try deleting manually.')


@operation
def creation_validation(**_):
    """ This checks that all user supplied info is valid """
    required_properties = ['resource_id', 'use_external_resource']
    for property_key in required_properties:
        utils.validate_node_property(property_key, ctx=ctx)

    key_path = get_key_file_path(ctx=ctx)

    if ctx.node.properties['use_external_resource']:
        if not search_for_key_file(key_path):
            raise NonRecoverableError('Use external resource is true, but the '
                                      'key file does not exist.')


def save_key_pair(key_pair_object, ctx):
    """ Saves the key pair to the file specified in the blueprint. """

    ctx.logger.debug('Attempting to save the key_pair_object.')

    if 'private_key_path' not in ctx.node.properties:
        raise NonRecoverableError(
            'Unable to save key pair, private_key_path not set.')

    try:
        key_pair_object.save(ctx.node.properties['private_key_path'])
    except (
            boto.exception.BotoClientError, OSError) as e:
        raise NonRecoverableError(
            'Unable to save key pair: {0}'.format(str(e)))

    key_path = get_key_file_path(ctx=ctx)

    if os.access(key_path, os.W_OK):
        os.chmod(key_path, 0600)
    else:
        raise NonRecoverableError(
            'Unable to save file: {0}, insufficient permissions.'
            .format(key_path))

    ctx.instance.runtime_properties['key_path'] = key_path


def get_key_file_path(ctx):
    """The key_path is an attribute that gives the full path to the key file.
    This function creates the path as a string for use by various functions in
    this module. It doesn't verify whether the path points to anything.
    """

    if 'private_key_path' not in ctx.node.properties:
        raise NonRecoverableError(
            'Unable to get key file path, private_key_path not set.')

    path = os.path.expanduser(ctx.node.properties['private_key_path'])

    key_path = os.path.join(
        path, '{0}.pem'.format(ctx.node.properties['resource_id']))
    return key_path


def delete_key_file(ctx):
    """ Deletes the key pair in the file specified in the blueprint. """

    key_path = get_key_file_path(ctx=ctx)

    if search_for_key_file(key_path):
        try:
            os.remove(key_path)
        except OSError as e:
            raise NonRecoverableError(
                'Unable to delete key pair: {0}.'.format(str(e)))


def search_for_key_file(key_path):
    """ Indicates whether the file exists locally. """

    return True if os.path.exists(key_path) else False

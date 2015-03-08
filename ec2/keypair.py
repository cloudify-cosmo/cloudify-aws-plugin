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
from ec2 import constants


@operation
def create(**kwargs):

    ec2_client = connection.EC2ConnectionClient().client()

    if create_external_keypair(ctx=ctx):
        return

    key_pair_name = ctx.node.properties['resource_id']

    ctx.logger.debug('Creating key pair.')

    try:
        kp = ec2_client.create_key_pair(key_pair_name)
    except (boto.exception.EC2ResponseError,
            boto.exception.BotoServerError,
            boto.exception.BotoClientError) as e:
        raise NonRecoverableError('Key pair not created. {0}'.format(str(e)))

    utils.set_external_resource_id(kp.name, external=False, ctx=ctx)
    save_key_pair(kp, ctx=ctx)


@operation
def delete(**kwargs):
    ec2_client = connection.EC2ConnectionClient().client()

    key_pair_name = \
        utils.get_external_resource_id_or_raise(
            'delete key pair', ctx.instance, ctx=ctx)

    if delete_external_keypair(ctx=ctx):
        return

    ctx.logger.debug('Attempting to delete key pair from account.')

    try:
        ec2_client.delete_key_pair(key_pair_name)
    except (boto.exception.EC2ResponseError,
            boto.exception.BotoServerError) as e:
        raise NonRecoverableError('{0}'.format(str(e)))

    key_pair = utils.get_key_pair_by_id(key_pair_name)

    if not key_pair:
        ctx.logger.error(
            'Could not delete key pair. Try deleting manually.')
    else:
        utils.unassign_runtime_property_from_resource(
            constants.EXTERNAL_RESOURCE_ID, ctx.instance, ctx=ctx)
        utils.unassign_runtime_property_from_resource(
            'key_path', ctx.instance, ctx=ctx)
        delete_key_file(ctx=ctx)
        ctx.logger.info('Deleted key pair: {0}.'.format(key_pair_name))


def save_key_pair(key_pair_object, ctx):

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


def create_external_keypair(ctx):
    if not ctx.node.properties['use_external_resource']:
        return False
    else:
        key_pair_id = ctx.node.properties['resource_id']
        key_pair = utils.get_key_pair_by_id(key_pair_id)
        key_path = get_key_file_path(ctx=ctx)
        ctx.logger.debug('Path to key file: {0}.'.format(key_path))
        if not search_for_key_file(key_path):
            raise NonRecoverableError(
                'External resource, but the key file does not exist.')
        utils.set_external_resource_id(key_pair.name, ctx=ctx)
        return True


def delete_external_keypair(ctx):
    if not ctx.node.properties['use_external_resource']:
        return False
    else:
        ctx.logger.info('External resource. Not deleting keypair.')
        utils.unassign_runtime_property_from_resource(
            constants.EXTERNAL_RESOURCE_ID, ctx.instance, ctx=ctx)
        utils.unassign_runtime_property_from_resource(
            'key_path', ctx.instance, ctx=ctx)
        return True


@operation
def creation_validation(**_):

    key_path = get_key_file_path(ctx=ctx)

    if ctx.node.properties['use_external_resource']:
        if not search_for_key_file(key_path):
            raise NonRecoverableError(
                'External resource, but the key file does not exist.')
        if not utils.get_key_pair_by_id(ctx.node.properties['resource_id']):
            raise NonRecoverableError(
                'External resource, but the key pair is not in the account.')

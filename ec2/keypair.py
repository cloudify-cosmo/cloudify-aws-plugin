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

# Third-party Imports
import boto.exception

# Cloudify imports
from ec2 import utils
from ec2 import constants
from ec2 import connection
from cloudify import ctx
from cloudify.exceptions import NonRecoverableError
from cloudify.decorators import operation


@operation
def creation_validation(**_):
    """ This validates all nodes before bootstrap.
    """

    key_path = _get_key_file_path(ctx.node.properties)
    key_file_exists = _search_for_key_file(key_path)
    key_pair = _get_key_pair_by_id(ctx.node.properties['resource_id'])

    if ctx.node.properties['use_external_resource']:
        if not key_file_exists:
            raise NonRecoverableError(
                'External resource, but the key file does not exist locally.')
        if not key_pair:
            raise NonRecoverableError(
                'External resource, '
                'but the key pair does not exist in the account.')

    if not ctx.node.properties['use_external_resource']:
        if key_file_exists:
            raise NonRecoverableError(
                'Not external resource, '
                'but the key file exists locally.')
        if key_pair:
            raise NonRecoverableError(
                'Not external resource, '
                'but the key pair exists in the account.')


@operation
def create(**kwargs):
    """Creates a keypair
    """

    ec2_client = connection.EC2ConnectionClient().client()

    if _create_external_keypair(ctx=ctx):
        return

    key_pair_name = ctx.node.properties['resource_id']

    ctx.logger.debug('Attempting to create key pair.')

    try:
        kp = ec2_client.create_key_pair(key_pair_name)
    except (boto.exception.EC2ResponseError,
            boto.exception.BotoServerError,
            boto.exception.BotoClientError) as e:
        raise NonRecoverableError('Key pair not created. {0}'.format(str(e)))

    utils.set_external_resource_id(kp.name, ctx.instance, external=False)
    _save_key_pair(kp, ctx=ctx)


@operation
def delete(**kwargs):
    """Deletes a keypair.
    """

    ec2_client = connection.EC2ConnectionClient().client()

    key_pair_name = utils.get_external_resource_id_or_raise(
        'delete key pair', ctx.instance)

    if _delete_external_keypair(ctx=ctx):
        return

    ctx.logger.debug('Attempting to delete key pair from account.')

    try:
        ec2_client.delete_key_pair(key_pair_name)
    except (boto.exception.EC2ResponseError,
            boto.exception.BotoServerError) as e:
        raise NonRecoverableError('{0}'.format(str(e)))

    key_pair = _get_key_pair_by_id(key_pair_name)

    if key_pair:
        ctx.logger.error(
            'Could not delete key pair. Try deleting manually.')
    else:
        utils.unassign_runtime_property_from_resource(
            constants.EXTERNAL_RESOURCE_ID, ctx.instance)
        utils.unassign_runtime_property_from_resource(
            'key_path', ctx.instance)
        _delete_key_file(ctx.node.properties)
        ctx.logger.info('Deleted key pair: {0}.'.format(key_pair_name))


def _create_external_keypair(ctx):
    """If use_external_resource is True, this will set the runtime_properties,
    and then exit.

    :param ctx: The Cloudify context.
    :returns Boolean if use_external_resource is True or not.
    :raises NonRecoverableError: If unable to locate the existing key file.
    """

    if not utils.use_external_resource(ctx.node.properties):
        return False
    else:
        key_pair_id = ctx.node.properties['resource_id']
        key_pair = _get_key_pair_by_id(key_pair_id)
        key_path = _get_key_file_path(ctx.node.properties)
        ctx.logger.debug('Path to key file: {0}.'.format(key_path))
        if not _search_for_key_file(key_path):
            raise NonRecoverableError(
                'External resource, but the key file does not exist.')
        utils.set_external_resource_id(key_pair.name, ctx.instance)
        return True


def _delete_external_keypair(ctx):
    """If use_external_resource is True, this will delete the runtime_properties,
    and then exit.

    :param ctx: The Cloudify context.
    :returns Boolean if use_external_resource is True or not.
    """

    if not utils.use_external_resource(ctx.node.properties):
        return False
    else:
        ctx.logger.info('External resource. Not deleting keypair.')
        utils.unassign_runtime_property_from_resource(
            constants.EXTERNAL_RESOURCE_ID, ctx.instance)
        utils.unassign_runtime_property_from_resource(
            'key_path', ctx.instance)
        return True


def _delete_key_file(node_properties):
    """ Deletes the key pair in the file specified in the blueprint.

    :param ctx: The Cloudify context.
    :raises NonRecoverableError: If unable to delete the local key file.
    """

    key_path = _get_key_file_path(node_properties)

    if _search_for_key_file(key_path):
        try:
            os.remove(key_path)
        except OSError as e:
            raise NonRecoverableError(
                'Unable to delete key pair: {0}.'.format(str(e)))


def _save_key_pair(key_pair_object, ctx):
    """Saves a keypair to the filesystem.

    :param key_pair_object: The key pair object as returned from create.
    :param ctx: The Cloudify Context.
    :raises NonRecoverableError: If private_key_path node property not set.
    :raises NonRecoverableError: If Unable to save key file locally.
    """

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

    key_path = _get_key_file_path(ctx.node.properties)

    if os.access(key_path, os.W_OK):
        os.chmod(key_path, 0600)
    else:
        raise NonRecoverableError(
            'Unable to save file: {0}, insufficient permissions.'
            .format(key_path))

    ctx.instance.runtime_properties['key_path'] = key_path


def _get_key_pair_by_id(key_pair_id):
    """Returns the key pair object for a given key pair id.

    :param key_pair_id: The ID of a keypair.
    :returns The boto keypair object.
    :raises NonRecoverableError: If EC2 finds no matching key pairs.
    """

    ec2_client = connection.EC2ConnectionClient().client()

    try:
        key_pair = ec2_client.get_key_pair(key_pair_id)
    except (boto.exception.EC2ResponseError,
            boto.exception.BotoServerError) as e:
        raise NonRecoverableError('{0}.'.format(str(e)))

    return key_pair


def _get_key_file_path(node_properties):
    """Gets the path to the keypair file.

    :param ctx: The Cloudify context.
    :returns key_path: Path to the keypair file.
    :raises NonRecoverableError: If private_key_path is not set.
    """

    if 'private_key_path' not in node_properties:
        raise NonRecoverableError(
            'Unable to get key file path, private_key_path not set.')

    path = os.path.expanduser(node_properties['private_key_path'])

    key_path = os.path.join(
        path, '{0}.pem'.format(node_properties['resource_id']))
    return key_path


def _search_for_key_file(key_path):
    """ Checks if the key_path exists in the local filesystem.

    :param key_path: The path to the key pair file.
    :return boolean if key_path exists (True) or not.
    """

    return True if os.path.exists(key_path) else False

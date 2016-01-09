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

KEYPAIR_AWS_TYPE = 'keypair'
RUNTIME_PROPERTIES = [constants.AWS_TYPE_PROPERTY,
                      constants.EXTERNAL_RESOURCE_ID]


@operation
def creation_validation(**_):
    """ This validates all nodes before bootstrap.
    """

    for property_key in constants.KEYPAIR_REQUIRED_PROPERTIES:
        utils.validate_node_property(property_key, ctx.node.properties)

    key_file = _get_path_to_key_file()
    key_file_in_filesystem = _search_for_key_file(key_file)

    if ctx.node.properties['use_external_resource']:
        if not key_file_in_filesystem:
            raise NonRecoverableError(
                'External resource, but the key file does not exist locally.')
        try:
            _get_key_pair_by_id(ctx.node.properties['resource_id'])
        except NonRecoverableError as e:
            raise NonRecoverableError(
                'External resource, '
                'but the key pair does not exist in the account: '
                '{0}'.format(str(e)))
    else:
        if key_file_in_filesystem:
            raise NonRecoverableError(
                'Not external resource, '
                'but the key file exists locally.')
        try:
            _get_key_pair_by_id(ctx.node.properties['resource_id'])
        except NonRecoverableError:
            pass
        else:
            raise NonRecoverableError(
                'Not external resource, '
                'but the key pair exists in the account.')


@operation
def create(**kwargs):
    """Creates a keypair."""

    ec2_client = connection.EC2ConnectionClient().client()

    if _create_external_keypair():
        return

    key_pair_name = utils.get_resource_id()

    ctx.logger.debug('Attempting to create key pair.')

    try:
        kp = ec2_client.create_key_pair(key_pair_name)
    except (boto.exception.EC2ResponseError,
            boto.exception.BotoServerError,
            boto.exception.BotoClientError) as e:
        raise NonRecoverableError('Key pair not created. {0}'.format(str(e)))

    utils.set_external_resource_id(
        kp.name, ctx.instance, external=False)
    _save_key_pair(kp)

    ctx.instance.runtime_properties[constants.AWS_TYPE_PROPERTY] = \
        KEYPAIR_AWS_TYPE


@operation
def delete(**kwargs):
    """Deletes a keypair."""

    ec2_client = connection.EC2ConnectionClient().client()

    key_pair_name = utils.get_external_resource_id_or_raise(
        'delete key pair', ctx.instance)

    if _delete_external_keypair():
        return

    ctx.logger.debug('Attempting to delete key pair from account.')

    try:
        ec2_client.delete_key_pair(key_pair_name)
    except (boto.exception.EC2ResponseError,
            boto.exception.BotoServerError) as e:
        raise NonRecoverableError('{0}'.format(str(e)))

    utils.unassign_runtime_properties_from_resource(RUNTIME_PROPERTIES,
                                                    ctx.instance)
    _delete_key_file()
    ctx.logger.info('Deleted key pair: {0}.'.format(key_pair_name))


def _create_external_keypair():
    """If use_external_resource is True, this will set the runtime_properties,
    and then exit.

    :param ctx: The Cloudify context.
    :return False: Cloudify resource. Continue operation.
    :return True: External resource. Set runtime_properties. Ignore operation.
    :raises NonRecoverableError: If unable to locate the existing key file.
    """

    if not utils.use_external_resource(ctx.node.properties):
        return False

    key_pair_name = ctx.node.properties['resource_id']
    key_pair_in_account = _get_key_pair_by_id(key_pair_name)
    key_path_in_filesystem = _get_path_to_key_file()
    ctx.logger.debug(
        'Path to key file: {0}.'.format(key_path_in_filesystem))
    if not key_pair_in_account:
        raise NonRecoverableError(
            'External resource, but the key pair is not in the account.')
    if not _search_for_key_file(key_path_in_filesystem):
        raise NonRecoverableError(
            'External resource, but the key file does not exist.')
    utils.set_external_resource_id(key_pair_name, ctx.instance)
    return True


def _delete_external_keypair():
    """If use_external_resource is True, this will delete the runtime_properties,
    and then exit.

    :param ctx: The Cloudify context.
    :return False: Cloudify resource. Continue operation.
    :return True: External resource. Unset runtime_properties.
        Ignore operation.
    """

    if not utils.use_external_resource(ctx.node.properties):
        return False

    ctx.logger.info('External resource. Not deleting keypair.')

    utils.unassign_runtime_properties_from_resource(RUNTIME_PROPERTIES,
                                                    ctx.instance)
    return True


def _delete_key_file():
    """ Deletes the key pair in the file specified in the blueprint.

    :param ctx: The Cloudify context.
    :raises NonRecoverableError: If unable to delete the local key file.
    """

    key_path = _get_path_to_key_file()

    if _search_for_key_file(key_path):
        try:
            os.remove(key_path)
        except OSError as e:
            raise NonRecoverableError(
                'Unable to delete key pair: {0}.'
                .format(str(e)))


def _save_key_pair(key_pair_object):
    """Saves a keypair to the filesystem.

    :param key_pair_object: The key pair object as returned from create.
    :param ctx: The Cloudify Context.
    :raises NonRecoverableError: If private_key_path node property not set.
    :raises NonRecoverableError: If Unable to save key file locally.
    """

    ctx.logger.debug('Attempting to save the key_pair_object.')

    if not key_pair_object.material:
        raise NonRecoverableError(
            'Cannot save key. KeyPair contains no material.')

    file_path = _get_path_to_key_file()
    if os.path.exists(file_path):
        raise NonRecoverableError(
            '{0} already exists, it will not be overwritten.'.format(
                file_path))
    fp = open(file_path, 'wb')
    fp.write(key_pair_object.material)
    fp.close()

    _set_key_file_permissions(file_path)


def _set_key_file_permissions(key_file):

    if os.access(key_file, os.W_OK):
        os.chmod(key_file, 0o600)
    else:
        ctx.logger.error(
            'Unable to set permissions key file: {0}.'.format(key_file))


def _get_key_pair_by_id(key_pair_id):
    """Returns the key pair object for a given key pair id.

    :param key_pair_id: The ID of a keypair.
    :returns The boto keypair object.
    :raises NonRecoverableError: If EC2 finds no matching key pairs.
    """

    ec2_client = connection.EC2ConnectionClient().client()

    try:
        key_pairs = ec2_client.get_all_key_pairs(keynames=key_pair_id)
    except (boto.exception.EC2ResponseError,
            boto.exception.BotoServerError) as e:
        raise NonRecoverableError('{0}'.format(str(e)))

    return key_pairs[0] if key_pairs else None


def _get_path_to_key_file():
    """Gets the path to the key file.

    :param ctx: The Cloudify context.
    :returns key_path: Path to the key file.
    :raises NonRecoverableError: If private_key_path is not set.
    """

    if 'private_key_path' not in ctx.node.properties:
        raise NonRecoverableError(
            'Unable to get key file path, private_key_path not set.')

    return os.path.expanduser(ctx.node.properties['private_key_path'])


def _search_for_key_file(path_to_key_file):
    """ Checks if the key_path exists in the local filesystem.

    :param key_path: The path to the key pair file.
    :return boolean if key_path exists (True) or not.
    """

    return True if os.path.exists(path_to_key_file) else False

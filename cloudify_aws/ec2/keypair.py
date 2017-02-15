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

# Cloudify imports
from cloudify_aws import utils, constants
from cloudify import ctx
from cloudify.exceptions import NonRecoverableError
from cloudify.decorators import operation
from cloudify_aws.base import AwsBaseNode


@operation
def creation_validation(**_):
    return KeyPair().creation_validation()


@operation
def create(args=None, **_):
    return KeyPair().created(args)


@operation
def delete(args=None, **_):
    return KeyPair().deleted(args)


class KeyPair(AwsBaseNode):

    def __init__(self):
        super(KeyPair, self).__init__(
            constants.KEYPAIR['AWS_RESOURCE_TYPE'],
            constants.KEYPAIR['REQUIRED_PROPERTIES']
        )
        self.not_found_error = constants.KEYPAIR['NOT_FOUND_ERROR']
        self.get_all_handler = {
            'function': self.client.get_all_key_pairs,
            'argument': 'keynames'
        }

    def creation_validation(self, **_):
        """ This validates all nodes before bootstrap.
        """

        for property_key in self.required_properties:
            utils.validate_node_property(property_key, ctx.node.properties)

        key_file = self._get_path_to_key_file()
        key_file_in_filesystem = self._search_for_key_file(key_file)

        if ctx.node.properties['use_external_resource']:
            if not key_file_in_filesystem:
                raise NonRecoverableError(
                    'External resource, but the key file '
                    'does not exist locally.')
            try:
                if not self.get_all_matching(
                        ctx.node.properties['resource_id']):
                    raise NonRecoverableError(self.not_found_error)
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
                self.get_all_matching(ctx.node.properties['resource_id'])
            except NonRecoverableError:
                pass
            else:
                raise NonRecoverableError(
                    'Not external resource, '
                    'but the key pair exists in the account.')

        return True

    def create(self, args=None, **_):
        """Creates a keypair."""

        create_args = {
            'key_name': utils.get_resource_id()
        }

        create_args = utils.update_args(create_args, args)

        kp = self.execute(self.client.create_key_pair,
                          create_args, raise_on_falsy=True)

        self._save_key_pair(kp)

        ctx.instance.runtime_properties[constants.AWS_TYPE_PROPERTY] = \
            constants.KEYPAIR['AWS_RESOURCE_TYPE']

        self.resource_id = kp.name

        return True

    def delete(self, args=None, **_):
        """Deletes a keypair."""

        key_pair_name = utils.get_external_resource_id_or_raise(
            'delete key pair', ctx.instance)
        delete_args = {
            'key_name': key_pair_name
        }
        delete_args = utils.update_args(delete_args, args)

        return self.execute(self.client.delete_key_pair,
                            delete_args, raise_on_falsy=True)

    def post_delete(self):

        super(KeyPair, self).post_delete()
        if not self.is_external_resource:
            self._delete_key_file()

        return True

    def _get_path_to_key_file(self):
        """Gets the path to the key file.

        :param ctx: The Cloudify context.
        :returns key_path: Path to the key file.
        :raises NonRecoverableError: If private_key_path is not set.
        """

        if 'private_key_path' not in ctx.node.properties:
            raise NonRecoverableError(
                'Unable to get key file path, private_key_path not set.')

        return os.path.expanduser(ctx.node.properties['private_key_path'])

    def _search_for_key_file(self, path_to_key_file):
        """ Checks if the key_path exists in the local filesystem.

        :param key_path: The path to the key pair file.
        :return boolean if key_path exists (True) or not.
        """

        return True if os.path.exists(path_to_key_file) else False

    def _save_key_pair(self, key_pair_object):
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

        file_path = self._get_path_to_key_file()
        if os.path.exists(file_path):
            raise NonRecoverableError(
                '{0} already exists, it will not be overwritten.'.format(
                    file_path))
        fp = open(file_path, 'wb')
        fp.write(key_pair_object.material)
        fp.close()

        self._set_key_file_permissions(file_path)

    def _set_key_file_permissions(self, key_file):

        if os.access(key_file, os.W_OK):
            os.chmod(key_file, 0o600)
        else:
            ctx.logger.error(
                'Unable to set permissions key file: {0}.'
                .format(key_file))

    def _delete_key_file(self):
        """ Deletes the key pair in the file specified in the blueprint.

        :param ctx: The Cloudify context.
        :raises NonRecoverableError: If unable to delete the local key file.
        """

        key_path = self._get_path_to_key_file()

        if self._search_for_key_file(key_path):
            try:
                os.remove(key_path)
            except OSError as e:
                raise NonRecoverableError(
                    'Unable to delete key pair: {0}.'
                    .format(str(e)))

    def use_external_resource_naively(self):
        """If use_external_resource is True, this will set the runtime_properties,
        and then exit.

        :param ctx: The Cloudify context.
        :return False: Cloudify resource. Continue operation.
        :return True: External resource. Set runtime_properties.
        Ignore operation.
        :raises NonRecoverableError: If unable to locate the existing key file.
        """

        if not self.is_external_resource:
            return False

        key_pair_in_account = self.get_resource()
        key_path_in_filesystem = self._get_path_to_key_file()
        ctx.logger.debug(
            'Path to key file: {0}.'.format(key_path_in_filesystem))
        if not key_pair_in_account:
            raise NonRecoverableError(
                'External resource, but the key pair is '
                'not in the account.')
        if not self._search_for_key_file(key_path_in_filesystem):
            raise NonRecoverableError(
                'External resource, but the key file does not exist.')
        return True

    def get_resource(self):
        return self.get_all_matching(self.resource_id)

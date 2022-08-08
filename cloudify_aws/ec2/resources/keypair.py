# Copyright (c) 2018 Cloudify Platform Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
'''
    EC2.Keypair
    ~~~~~~~~~~~~~~
    AWS EC2 Keypair interface
'''


# Cloudify
from cloudify import ctx
from cloudify.exceptions import NonRecoverableError
from cloudify.manager import get_rest_client

# Lcaol imports
from cloudify_aws.common._compat import text_type
from cloudify_aws.ec2 import EC2Base
from cloudify_aws.common import decorators, utils
from cloudify_rest_client.exceptions import CloudifyClientError

RESOURCE_TYPE = 'EC2 Keypairs'
KEYPAIRS = 'KeyPairs'
KEYNAME = 'KeyName'
KEYNAMES = 'KeyNames'
PUBLIC_KEY_MATERIAL = 'PublicKeyMaterial'


class EC2Keypair(EC2Base):
    '''
        EC2 Keypair interface
    '''
    def __init__(self, ctx_node, resource_id=None, client=None, logger=None):
        EC2Base.__init__(self, ctx_node, resource_id, client, logger)
        self.type_name = RESOURCE_TYPE
        self._describe_call = 'describe_key_pairs'
        self._ids_key = KEYNAMES
        self._type_key = KEYPAIRS
        self._id_key = KEYNAME

    @property
    def status(self):
        '''Gets the status of an external resource'''
        return None

    def create(self, params, log_response=False):
        '''
            Create AWS EC2 Instances.
        '''
        return self.make_client_call(
            'create_key_pair', params, log_response)

    def import_keypair(self, params, log_response=False):
        '''
            Create AWS EC2 Instances.
        '''
        self.logger.debug(
            'Importing {0} with parameters: {1}'.format(
                self.type_name, params))
        res = self.client.import_key_pair(**params)
        if log_response:
            self.logger.debug('Response: {0}'.format(res))
        return res

    def delete(self, params):
        '''
            Delete AWS EC2 Instances.
        '''
        self.logger.debug(
            'Deleting {0} with parameters: {1}'.format(
                self.type_name, params))
        res = self.client.delete_key_pair(**params)
        self.logger.debug('Response: {0}'.format(res))
        return res


@decorators.aws_resource(EC2Keypair, resource_type=RESOURCE_TYPE)
def prepare(ctx, iface, resource_config, **_):
    '''Prepares AWS EC2 Keypairs'''
    # Save the parameters
    ctx.instance.runtime_properties['resource_config'] = resource_config


@decorators.aws_resource(EC2Keypair, RESOURCE_TYPE)
@decorators.tag_resources
def create(ctx, iface, resource_config, **_):
    '''Creates AWS EC2 Keypairs'''

    resource_config[KEYNAME] = utils.get_resource_name(resource_config.get(
        KEYNAME))
    key_name = resource_config[KEYNAME]

    if PUBLIC_KEY_MATERIAL in resource_config:
        create_response = \
            iface.import_keypair(
                resource_config,
                log_response=ctx.node.properties['log_create_response'])
    else:
        create_response = iface.create(
            resource_config,
            log_response=ctx.node.properties['log_create_response'])

        # Allow the end user to store the key material in a secret.
        if ctx.node.properties['create_secret']:

            try:
                client = get_rest_client()
            except KeyError:  # No pun intended.
                raise NonRecoverableError(
                    'create_secret is only supported with a Cloudify Manager.')

            # This makes the line too long for flake8 if included in args.
            secret_name = ctx.node.properties.get('secret_name', key_name)
            secrets_count = len(client.secrets.list(key=secret_name))
            secret_value = create_response.get('KeyMaterial')

            try:
                if secrets_count == 0:
                    client.secrets.create(
                        key=secret_name,
                        value=secret_value)
                elif secrets_count == 1 and \
                        ctx.node.properties.get(
                            'update_existing_secret', False) is True:
                    client.secrets.update(
                        key=secret_name,
                        value=secret_value)
            except CloudifyClientError as e:
                raise NonRecoverableError(text_type(e))

    cleaned_create_response = \
        utils.JsonCleanuper(create_response).to_dict()

    # Allow the end user to opt-in to storing the key
    # material in the runtime properties.
    # Default is false
    if 'KeyMaterial' in cleaned_create_response and not \
            ctx.node.properties['store_in_runtime_properties']:
        del cleaned_create_response['KeyMaterial']
    ctx.instance.runtime_properties['create_response'] = \
        cleaned_create_response

    iface.update_resource_id(cleaned_create_response.get(KEYNAME))
    utils.update_resource_id(ctx.instance, key_name)


@decorators.aws_resource(EC2Keypair, RESOURCE_TYPE)
@decorators.untag_resources
def delete(iface, resource_config, dry_run=False, **_):
    '''Deletes AWS EC2 Keypairs'''

    key_name = resource_config.get(KEYNAME, iface.resource_id)

    iface.delete({KEYNAME: key_name, 'DryRun': dry_run})

    if ctx.node.properties['create_secret']:
        try:
            client = get_rest_client()
        except KeyError:  # No pun intended.
            raise NonRecoverableError(
                'create_secret is only supported with a Cloudify Manager.')
        secret_name = ctx.node.properties.get('secret_name', key_name)
        try:
            client.secrets.delete(key=secret_name)
        except CloudifyClientError as e:
            raise NonRecoverableError(
                'Failed to store secret: {0}.'.format(text_type(e)))

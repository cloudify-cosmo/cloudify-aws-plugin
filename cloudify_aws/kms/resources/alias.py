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
"""
    KMS.KeyAlias
    ~~~~~~~~
    AWS KMS Key Alias interface
"""
# Cloudify
from cloudify_aws.common import decorators, utils
from cloudify_aws.kms.resources.key import KMSKey
from cloudify_aws.common.constants import EXTERNAL_RESOURCE_ID

RESOURCE_TYPE = 'KMS Key Alias'
RESOURCE_NAME = 'AliasName'
TARGET_KEY_ID = 'TargetKeyId'
KEY_TYPE = 'cloudify.nodes.aws.kms.CustomerMasterKey'


class KMSKeyAlias(KMSKey):
    """
        AWS KMS Key Alias interface
    """
    def __init__(self, ctx_node, resource_id=None, client=None, logger=None):
        KMSKey.__init__(self, ctx_node, resource_id, client, logger)
        self.type_name = RESOURCE_TYPE

    @property
    def properties(self):
        return None

    @property
    def status(self):
        """Gets the status of an external resource"""
        return None

    def create(self, params):
        """
            Create a new AWS KMS Key Alias.
        """
        return self.make_client_call('create_alias', params)

    def enable(self, params):
        return None

    def disable(self, params):
        return None

    def delete(self, params=None):
        """
            Deletes an existing AWS KMS Key Alias.
        """
        self.logger.debug('Deleting %s with parameters: %s'
                          % (self.type_name, params))
        self.client.delete_alias(**params)


@decorators.aws_resource(resource_type=RESOURCE_TYPE)
def prepare(ctx, resource_config, **_):
    """Prepares an AWS KMS Key"""
    # Save the parameters
    ctx.instance.runtime_properties['resource_config'] = resource_config


@decorators.aws_resource(KMSKeyAlias, RESOURCE_TYPE)
def create(ctx, iface, resource_config, **_):
    """Creates an AWS KMS Key Alias"""
    # Create a copy of the resource config for clean manipulation.
    params = \
        dict() if not resource_config else resource_config.copy()
    resource_id = \
        utils.get_resource_id(
            ctx.node,
            ctx.instance,
            params.get(RESOURCE_NAME),
            use_instance_id=True
        )
    params[RESOURCE_NAME] = resource_id
    utils.update_resource_id(ctx.instance, resource_id)

    target_key_id = params.get(TARGET_KEY_ID)
    if not target_key_id:
        target_key = \
            utils.find_rel_by_node_type(
                ctx.instance,
                KEY_TYPE)
        target_key_id = \
            target_key.target.instance.runtime_properties[EXTERNAL_RESOURCE_ID]
        params[TARGET_KEY_ID] = target_key_id
    # Actually create the resource
    iface.create(params)


@decorators.aws_resource(KMSKeyAlias, RESOURCE_TYPE)
def delete(ctx, iface, resource_config, **_):
    """Deletes an KMS Key Alias"""

    # Create a copy of the resource config for clean manipulation.
    params = \
        dict() if not resource_config else resource_config.copy()

    alias_name = params.get(RESOURCE_NAME)
    if not alias_name:
        params[RESOURCE_NAME] = \
            ctx.instance.runtime_properties.get(
                EXTERNAL_RESOURCE_ID,
                iface.resource_id)

    # Actually delete the resource
    iface.delete(params)

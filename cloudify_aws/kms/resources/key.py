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
    KMS.Key
    ~~~~~~~~
    AWS KMS Key interface
"""
# Cloudify
from cloudify_aws.common import decorators, utils
from cloudify_aws.kms import KMSBase
from cloudify_aws.common.constants import EXTERNAL_RESOURCE_ID
# Boto
from botocore.exceptions import ClientError

RESOURCE_TYPE = 'KMS Key'
KEY_ID = 'KeyId'
KEY_META = 'KeyMetadata'
ARN = 'Arn'


class KMSKey(KMSBase):
    """
        AWS KMS Key interface
    """
    def __init__(self, ctx_node, resource_id=None, client=None, logger=None):
        KMSBase.__init__(self, ctx_node, resource_id, client, logger)
        self.type_name = RESOURCE_TYPE

    @property
    def properties(self):
        """Gets the properties of an external resource"""
        if not self.resource_id:
            return
        params = {KEY_ID: self.resource_id}
        try:
            resource = \
                self.client.describe_key(**params)
        except ClientError:
            pass
        else:
            return resource.get(KEY_META, {})
        return None

    @property
    def status(self):
        """Gets the status of an external resource"""
        return None

    def create(self, params):
        """
            Create a new AWS KMS Key.
        """
        return self.make_client_call('create_key', params)

    def enable(self, params):
        """
            Enables an AWS KMS Key.
        """
        self.logger.debug('Enabling %s with parameters: %s'
                          % (self.type_name, params))
        res = self.client.enable_key(**params)
        self.logger.debug('Response: %s' % res)
        return res

    def disable(self, params):
        """
            Disables an AWS KMS Key.
        """
        self.logger.debug('Disabling %s with parameters: %s'
                          % (self.type_name, params))
        res = self.client.disable_key(**params)
        self.logger.debug('Response: %s' % res)
        return res

    def delete(self, params=None):
        """
            Deletes an existing AWS KMS Key.
        """
        self.logger.debug('Deleting %s with parameters: %s'
                          % (self.type_name, params))
        self.client.schedule_key_deletion(**params)


@decorators.aws_resource(KMSKey, RESOURCE_TYPE)
def prepare(ctx, resource_config, **_):
    """Prepares an AWS KMS Key"""
    # Save the parameters
    ctx.instance.runtime_properties['resource_config'] = resource_config


@decorators.aws_resource(KMSKey, RESOURCE_TYPE)
def create(ctx, iface, resource_config, **_):
    """Creates an AWS KMS Key"""
    create_response = iface.create(resource_config)[KEY_META]
    utils.update_resource_arn(
        ctx.instance,
        create_response.get(ARN)
    )
    utils.update_resource_id(
        ctx.instance,
        create_response.get(KEY_ID)
    )


@decorators.aws_resource(KMSKey, RESOURCE_TYPE,
                         ignore_properties=True)
def enable(ctx, iface, resource_config, **_):
    key_id = resource_config.get(KEY_ID)
    if not key_id:
        resource_config[KEY_ID] = \
            ctx.instance.runtime_properties.get(
                EXTERNAL_RESOURCE_ID,
                iface.resource_id)
    # iface.enable(params)


@decorators.aws_resource(KMSKey, RESOURCE_TYPE,
                         ignore_properties=True)
def disable(ctx, iface, resource_config, **_):
    key_id = resource_config.get(KEY_ID)
    if not key_id:
        resource_config[KEY_ID] = \
            ctx.instance.runtime_properties.get(
                EXTERNAL_RESOURCE_ID,
                iface.resource_id)
    # iface.disable(params)


@decorators.aws_resource(KMSKey, RESOURCE_TYPE,
                         ignore_properties=True)
def delete(ctx, iface, resource_config, **_):
    """Deletes an AWS KMS Key"""
    key_id = resource_config.get(KEY_ID)
    if not key_id:
        resource_config[KEY_ID] = \
            ctx.instance.runtime_properties.get(
                EXTERNAL_RESOURCE_ID,
                iface.resource_id)

    # Actually delete the resource
    iface.delete(resource_config)

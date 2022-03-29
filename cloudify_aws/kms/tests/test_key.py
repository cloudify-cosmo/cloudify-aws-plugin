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

# Standard imports
import unittest

# Third party imports
from mock import MagicMock

# Local imports
from cloudify_aws.common.tests.test_base import CLIENT_CONFIG
from cloudify_aws.kms.tests.test_kms import TestKMS
from cloudify_aws.kms.resources import key


# Constants
KEY_TH = ['cloudify.nodes.Root',
          'cloudify.nodes.aws.kms.CustomerMasterKey']

NODE_PROPERTIES = {
    'use_external_resource': False,
    'resource_config': {
        "kwargs": {
            "Description": "An example CMK.",
            "Tags": [{
                "TagKey": "Cloudify",
                "TagValue": "Example"
            }]
        }
    },
    'client_config': CLIENT_CONFIG
}

RUNTIME_PROPERTIES = {
    'resource_config': {}
}

RUNTIME_PROPERTIES_AFTER_CREATE = {
    'aws_resource_arn': 'arn_id',
    'aws_resource_id': 'key_id',
    'resource_config': {}
}


class TestKMSKey(TestKMS):

    def test_prepare(self):
        self._prepare_check(
            type_hierarchy=KEY_TH,
            type_name='kms',
            type_class=key
        )

    def test_create_raises_UnknownServiceError(self):
        self._prepare_create_raises_UnknownServiceError(
            type_hierarchy=KEY_TH,
            type_name='kms',
            type_class=key
        )

    def test_create(self):
        _ctx = self._prepare_context(
            KEY_TH, NODE_PROPERTIES
        )

        self.fake_client.create_key = MagicMock(return_value={
            'KeyMetadata': {
                'Arn': "arn_id",
                'KeyId': 'key_id'
            }
        })

        key.create(ctx=_ctx, resource_config=None, iface=None)

        self.fake_boto.assert_called_with('kms', **CLIENT_CONFIG)

        self.fake_client.create_key.assert_called_with(
            Description='An example CMK.',
            Tags=[{'TagKey': 'Cloudify', 'TagValue': 'Example'}]
        )

        self.assertEqual(
            _ctx.instance.runtime_properties,
            RUNTIME_PROPERTIES_AFTER_CREATE
        )

    def test_enable(self):
        _ctx = self._prepare_context(
            KEY_TH, NODE_PROPERTIES, RUNTIME_PROPERTIES_AFTER_CREATE
        )

        self.fake_client.schedule_key_deletion = MagicMock(return_value={})

        key.enable(ctx=_ctx, resource_config={}, iface=None)

        self.fake_boto.assert_called_with('kms', **CLIENT_CONFIG)

        self.assertEqual(
            _ctx.instance.runtime_properties,
            RUNTIME_PROPERTIES_AFTER_CREATE
        )

    def test_disable(self):
        _ctx = self._prepare_context(
            KEY_TH, NODE_PROPERTIES, RUNTIME_PROPERTIES_AFTER_CREATE
        )

        self.fake_client.schedule_key_deletion = MagicMock(return_value={})

        key.disable(ctx=_ctx, resource_config={}, iface=None)

        self.fake_boto.assert_called_with('kms', **CLIENT_CONFIG)

        self.assertEqual(
            _ctx.instance.runtime_properties,
            RUNTIME_PROPERTIES_AFTER_CREATE
        )

    def test_delete(self):
        _ctx = self._prepare_context(
            KEY_TH, NODE_PROPERTIES, RUNTIME_PROPERTIES_AFTER_CREATE
        )

        self.fake_client.schedule_key_deletion = MagicMock(return_value={})

        key.delete(ctx=_ctx, resource_config={}, iface=None)

        self.fake_boto.assert_called_with('kms', **CLIENT_CONFIG)

        self.fake_client.schedule_key_deletion.assert_called_with(
            KeyId='key_id'
        )

        self.assertEqual(
            _ctx.instance.runtime_properties,
            RUNTIME_PROPERTIES_AFTER_CREATE
        )

    def test_KMSKey_status(self):

        test_instance = key.KMSKey("ctx_node", resource_id='queue_id',
                                   client=self.fake_client, logger=None)

        self.assertEqual(test_instance.status, None)

    def test_KMSKey_properties(self):

        test_instance = key.KMSKey("ctx_node", resource_id='queue_id',
                                   client=self.fake_client, logger=None)

        self.assertEqual(test_instance.properties, None)

    def test_KMSKey_properties_with_key(self):

        test_instance = key.KMSKey("ctx_node", resource_id='queue_id',
                                   client=self.fake_client, logger=None)

        self.fake_client.describe_key = MagicMock(
            return_value={'KeyMetadata': 'z'}
        )

        self.assertEqual(test_instance.properties, 'z')

    def test_KMSKey_enable(self):

        test_instance = key.KMSKey("ctx_node", resource_id='queue_id',
                                   client=self.fake_client, logger=None)

        self.fake_client.enable_key = MagicMock(
            return_value={'KeyMetadata': 'y'}
        )

        self.assertEqual(
            test_instance.enable({'a': 'b'}),
            {'KeyMetadata': 'y'}
        )

        self.fake_client.enable_key.assert_called_with(a='b')

    def test_KMSKey_disable(self):

        test_instance = key.KMSKey("ctx_node", resource_id='queue_id',
                                   client=self.fake_client, logger=None)

        self.fake_client.disable_key = MagicMock(
            return_value={'KeyMetadata': 'y'}
        )

        self.assertEqual(
            test_instance.disable({'a': 'b'}),
            {'KeyMetadata': 'y'}
        )

        self.fake_client.disable_key.assert_called_with(a='b')


if __name__ == '__main__':
    unittest.main()

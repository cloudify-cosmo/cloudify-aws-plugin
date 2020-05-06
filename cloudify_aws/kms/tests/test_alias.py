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
from botocore.exceptions import UnknownServiceError


# Local imports
from cloudify_aws.common._compat import text_type
from cloudify_aws.common.constants import EXTERNAL_RESOURCE_ID
from cloudify_aws.common.tests.test_base import CLIENT_CONFIG
from cloudify_aws.kms.tests.test_kms import TestKMS
from cloudify_aws.kms.resources import alias


# Constants
ALIAS_TH = ['cloudify.nodes.Root',
            'cloudify.nodes.aws.kms.Alias']

NODE_PROPERTIES = {
    'use_external_resource': False,
    'resource_config': {
        "kwargs": {
            "AliasName": "alias/test_key"
        }
    },
    'client_config': CLIENT_CONFIG
}

RUNTIME_PROPERTIES = {
    'aws_resource_id': 'aws_resource',
    'resource_config': {}
}


class TestKMSAlias(TestKMS):

    def test_prepare(self):
        self._prepare_check(
            type_hierarchy=ALIAS_TH,
            type_name='kms',
            type_class=alias
        )

    def test_create_raises_UnknownServiceError(self):
        _ctx = self._prepare_context(ALIAS_TH, NODE_PROPERTIES)

        with self.assertRaises(UnknownServiceError) as error:
            alias.create(ctx=_ctx, resource_config=None, iface=None)

        self.assertEqual(
            text_type(error.exception),
            "Unknown service: 'kms'. Valid service names are: ['rds']"
        )

        self.fake_boto.assert_called_with('kms', **CLIENT_CONFIG)

    def test_create(self):
        _ctx = self._prepare_context(ALIAS_TH, NODE_PROPERTIES)
        del _ctx.instance.runtime_properties[EXTERNAL_RESOURCE_ID]

        self.fake_client.create_alias = MagicMock(return_value={})

        alias.create(ctx=_ctx, resource_config=None, iface=None)

        self.fake_boto.assert_called_with('kms', **CLIENT_CONFIG)

        self.fake_client.create_alias.assert_called_with(
            AliasName='alias/test_key', TargetKeyId='a'
        )

        self.assertEqual(
            _ctx.instance.runtime_properties, {
                'aws_resource_id': 'alias/test_key', 'resource_config': {}
            }
        )

    def test_delete(self):
        _ctx = self._prepare_context(ALIAS_TH, NODE_PROPERTIES)

        self.fake_client.delete_alias = MagicMock(return_value={})

        alias.delete(ctx=_ctx, resource_config=None, iface=None)

        self.fake_boto.assert_called_with('kms', **CLIENT_CONFIG)

        self.fake_client.delete_alias.assert_called_with(
            AliasName='alias/test_key'
        )

        self.assertEqual(
            _ctx.instance.runtime_properties, {
                'aws_resource_id': 'aws_resource', 'resource_config': {}
            }
        )

    def test_delete_without_alias(self):
        _ctx = self._prepare_context(ALIAS_TH, {
            'use_external_resource': False,
            'resource_config': {},
            'client_config': CLIENT_CONFIG
        })

        self.fake_client.delete_alias = MagicMock(return_value={})

        alias.delete(ctx=_ctx, resource_config=None, iface=None)

        self.fake_boto.assert_called_with('kms', **CLIENT_CONFIG)

        self.fake_client.delete_alias.assert_called_with(
            AliasName='aws_resource'
        )

        self.assertEqual(
            _ctx.instance.runtime_properties, {
                'aws_resource_id': 'aws_resource', 'resource_config': {}
            }
        )

    def test_KMSKeyAlias_status(self):

        test_instance = alias.KMSKeyAlias("ctx_node", resource_id='queue_id',
                                          client=self.fake_client, logger=None)

        self.assertEqual(test_instance.status, None)

    def test_KMSKeyAlias_properties(self):

        test_instance = alias.KMSKeyAlias("ctx_node", resource_id='queue_id',
                                          client=self.fake_client, logger=None)

        self.assertEqual(test_instance.properties, None)

    def test_KMSKeyAlias_enable(self):

        test_instance = alias.KMSKeyAlias("ctx_node", resource_id='queue_id',
                                          client=self.fake_client, logger=None)

        self.assertEqual(test_instance.enable(None), None)

    def test_KMSKeyAlias_disable(self):

        test_instance = alias.KMSKeyAlias("ctx_node", resource_id='queue_id',
                                          client=self.fake_client, logger=None)

        self.assertEqual(test_instance.disable(None), None)


if __name__ == '__main__':
    unittest.main()

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

from cloudify_aws.common._compat import text_type


from cloudify_aws.common.constants import EXTERNAL_RESOURCE_ID
from cloudify_aws.common.tests.test_base import CLIENT_CONFIG
from cloudify_aws.kms.tests.test_kms import TestKMS
from cloudify_aws.kms.resources import grant


# Constants
GRANT_TH = ['cloudify.nodes.Root',
            'cloudify.nodes.aws.kms.Grant']

NODE_PROPERTIES = {
    'use_external_resource': False,
    'resource_id': 'TestGrant',
    'resource_config': {
        "kwargs": {
            "Name": "TestGrant",
            "GranteePrincipal": "ami_arn",
            "Operations": ["Encrypt", "Decrypt"]
        }
    },
    'client_config': CLIENT_CONFIG
}

RUNTIME_PROPERTIES = {
    'resource_config': {}
}

RUNTIME_PROPERTIES_AFTER_CREATE = {
    'KeyId': 'a',
    'aws_resource_id': 'grant_id',
    'resource_config': {},
    'GrantToken': 'grant_token'
}


class TestKMSGrant(TestKMS):

    def test_prepare(self):
        self._prepare_check(
            type_hierarchy=GRANT_TH,
            type_name='kms',
            type_class=grant
        )

    def test_KMSKeyGrant_status(self):

        test_instance = grant.KMSKeyGrant("ctx_node", resource_id='queue_id',
                                          client=self.fake_client, logger=None)

        self.assertEqual(test_instance.status, None)

    def test_KMSKeyGrant_properties(self):

        test_instance = grant.KMSKeyGrant("ctx_node", resource_id='queue_id',
                                          client=self.fake_client, logger=None)

        self.assertEqual(test_instance.properties, None)

    def test_create_raises_UnknownServiceError(self):
        _ctx = self._prepare_context(
            GRANT_TH, NODE_PROPERTIES
        )

        with self.assertRaises(UnknownServiceError) as error:
            grant.create(ctx=_ctx, resource_config=None, iface=None)

        self.assertEqual(
            text_type(error.exception),
            "Unknown service: 'kms'. Valid service names are: ['rds']"
        )

        self.fake_boto.assert_called_with('kms', **CLIENT_CONFIG)

    def test_create(self):
        _ctx = self._prepare_context(
            GRANT_TH, NODE_PROPERTIES
        )
        del _ctx.instance.runtime_properties[EXTERNAL_RESOURCE_ID]

        self.fake_client.create_grant = MagicMock(return_value={
            'GrantId': "grant_id",
            'GrantToken': 'grant_token'
        })

        grant.create(ctx=_ctx, resource_config=None, iface=None)
        self.fake_boto.assert_called_with('kms', **CLIENT_CONFIG)

        self.fake_client.create_grant.assert_called_with(
            GranteePrincipal='ami_arn', KeyId='a', Name='TestGrant',
            Operations=['Encrypt', 'Decrypt']
        )

        self.assertEqual(
            _ctx.instance.runtime_properties,
            RUNTIME_PROPERTIES_AFTER_CREATE
        )

    def test_delete(self):
        _ctx = self._prepare_context(
            GRANT_TH, NODE_PROPERTIES,
            runtime_prop=RUNTIME_PROPERTIES_AFTER_CREATE
        )

        self.fake_client.revoke_grant = MagicMock(return_value={})

        grant.delete(ctx=_ctx, resource_config={}, iface=None)

        self.fake_boto.assert_called_with('kms', **CLIENT_CONFIG)

        self.fake_client.revoke_grant.assert_called_with(
            GrantId='grant_id', KeyId='a'
        )

        self.assertEqual(
            _ctx.instance.runtime_properties, {
                'KeyId': 'a',
                'aws_resource_id': 'grant_id',
                'resource_config': {},
                'GrantToken': 'grant_token'
            }
        )


if __name__ == '__main__':
    unittest.main()

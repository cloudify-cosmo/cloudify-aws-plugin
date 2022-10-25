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
import datetime

# Third party imports
from mock import patch, MagicMock

from cloudify.state import current_ctx

# Local imports
from ..resources import identity_pool
from ...common.tests.test_base import TestBase, CLIENT_CONFIG
from ...common.tests.test_base import DEFAULT_RUNTIME_PROPERTIES

# Constants
IDENTITY_POOL_NAME = 'DemoIdentityPool'

IDENTITY_POOL_TH = [
    'cloudify.nodes.Root',
    'cloudify.nodes.aws.cognito.IdentityPool'
]

NODE_PROPERTIES = {
    'resource_id': 'node_resource_id',
    'use_external_resource': False,
    'resource_config': {
        "IdentityPoolName": IDENTITY_POOL_NAME,
        "AllowUnauthenticatedIdentities": True,
        "SupportedLoginProviders": {
              "www.amazon.com": 'foo',
        },
        "CognitoIdentityProviders": [
            {
                "ClientId": 'foo',
                "ProviderName": 'foo',
            }
        ]
    },
    'client_config': CLIENT_CONFIG
}

RUNTIME_PROPERTIES_AFTER_CREATE = {
    'aws_resource_id': IDENTITY_POOL_NAME,
    'resource_config': NODE_PROPERTIES.get('resource_config', {}),
}

CREATE_RESPONSE = {
    'IdentityPoolId': 'foo',
    'IdentityPoolName': IDENTITY_POOL_NAME,
    'AllowUnauthenticatedIdentities': False,
    'AllowClassicFlow': False,
    'SupportedLoginProviders': {
        'foo': 'bar',
    },
    'DeveloperProviderName': 'foo',
    'OpenIdConnectProviderARNs': ['foo'],
    'CognitoIdentityProviders': [
        {
            'ProviderName': 'foo',
            'ClientId': 'foo',
        },
    ],
    'SamlProviderARNs': ['foo'],
    'IdentityPoolTags': {
        'foo': 'bar',
    }
}

TEST_DATE = datetime.datetime(2020, 1, 1)


class TestCognitoIdentityPool(TestBase):

    def setUp(self):
        super(TestCognitoIdentityPool, self).setUp()

        self.fake_boto, self.fake_client = self.fake_boto_client(
            'cognito-identity')

        self.mock_patch = patch('boto3.client', self.fake_boto)
        self.mock_patch.start()

    def tearDown(self):
        self.mock_patch.stop()
        self.fake_boto = None
        self.fake_client = None
        super(TestCognitoIdentityPool, self).tearDown()

    def test_create(self):
        _ctx = self.get_mock_ctx(
            'test_create',
            test_properties=NODE_PROPERTIES,
            test_runtime_properties=DEFAULT_RUNTIME_PROPERTIES,
            type_hierarchy=IDENTITY_POOL_TH,
            ctx_operation_name='cloudify.interfaces.lifecycle.create',
        )
        current_ctx.set(_ctx)
        self.fake_client.create_identity_pool = MagicMock(
            return_value=CREATE_RESPONSE,
        )
        identity_pool.create(ctx=_ctx, iface=None, params=None)
        self.fake_boto.assert_called_with('cognito-identity', **CLIENT_CONFIG)
        self.fake_client.create_identity_pool.assert_called_with(
            **_ctx.node.properties['resource_config']
        )

    def test_delete(self):
        _ctx = self.get_mock_ctx(
            'test_delete',
            test_properties=NODE_PROPERTIES,
            test_runtime_properties=RUNTIME_PROPERTIES_AFTER_CREATE,
            type_hierarchy=IDENTITY_POOL_TH,
            ctx_operation_name='cloudify.interfaces.lifecycle.delete'
        )
        current_ctx.set(_ctx)
        identity_pool.delete(ctx=_ctx, resource_config=None, iface=None)
        self.fake_boto.assert_called_with('cognito-identity', **CLIENT_CONFIG)
        self.fake_client.delete_identity_pool.assert_called_with(
            IdentityPoolId=IDENTITY_POOL_NAME
        )

    def test_set(self):
        self.fake_client.get_identity_pool_roles = MagicMock(
            return_value={
                'IdentityPoolId': IDENTITY_POOL_NAME,
                'Roles': {
                    'authenticated': 'foo',
                },
            },
        )
        _source_ctx, _target_ctx, _group_rel = \
            self._create_common_relationships(
                'test_node',
                source_type_hierarchy=[
                    'cloudify.nodes.Root',
                    'cloudify.nodes.aws.iam.Role'
                ],
                target_type_hierarchy=[
                    'cloudify.nodes.Root',
                    'cloudify.nodes.aws.cognito.IdentityPool'
                ],
                source_node_id='unauthenticated',
                source_node_properties=NODE_PROPERTIES,
            )
        _source_ctx.instance.runtime_properties['aws_resource_id'] = \
            'foo'
        _source_ctx.instance.runtime_properties['aws_resource_arn'] = \
            'bar'
        _target_ctx.instance.runtime_properties['aws_resource_id'] = \
            IDENTITY_POOL_NAME
        _ctx = self.get_mock_relationship_ctx(
            'foo',
            test_source=_source_ctx,
            test_target=_target_ctx,
        )
        current_ctx.set(_ctx)
        identity_pool.set(ctx=_ctx, iface=None, params=None)

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
from ..resources import user_pool_client
from cloudify_aws.common.tests.test_base import TestBase, CLIENT_CONFIG
from cloudify_aws.common.tests.test_base import DEFAULT_RUNTIME_PROPERTIES

# Constants
USER_POOL_CLIENT_NAME = 'DemoUserPool'

USER_POOL_CLIENT_TH = [
    'cloudify.nodes.Root',
    'cloudify.nodes.aws.cognito.UserPool'
]

NODE_PROPERTIES = {
    'resource_id': 'node_resource_id',
    'use_external_resource': False,
    'resource_config': {
        "UserPoolId": "foo",
        "ClientName": USER_POOL_CLIENT_NAME,
        "GenerateSecret": True,
    },
    'client_config': CLIENT_CONFIG
}

RUNTIME_PROPERTIES_AFTER_CREATE = {
    'aws_resource_id': 'foo',
    'resource_config': NODE_PROPERTIES.get('resource_config', {}),
}

CREATE_RESPONSE = {
    'UserPoolClient': {
        'UserPoolId': 'foo',
        'ClientName': USER_POOL_CLIENT_NAME,
        'ClientId': 'foo',
        'ClientSecret': 'bar',
    }
}

TEST_DATE = datetime.datetime(2020, 1, 1)


class TestCognitoUserPool(TestBase):

    def setUp(self):
        super(TestCognitoUserPool, self).setUp()

        self.fake_boto, self.fake_client = self.fake_boto_client(
            'cognito-idp')

        self.mock_patch = patch('boto3.client', self.fake_boto)
        self.mock_patch.start()

    def tearDown(self):
        self.mock_patch.stop()
        self.fake_boto = None
        self.fake_client = None
        super(TestCognitoUserPool, self).tearDown()

    def test_create(self):
        _ctx = self.get_mock_ctx(
            'test_create',
            test_properties=NODE_PROPERTIES,
            test_runtime_properties=DEFAULT_RUNTIME_PROPERTIES,
            type_hierarchy=USER_POOL_CLIENT_TH,
            ctx_operation_name='cloudify.interfaces.lifecycle.create',
        )
        current_ctx.set(_ctx)
        self.fake_client.create_user_pool_client = MagicMock(
            return_value=CREATE_RESPONSE,
        )
        user_pool_client.create(ctx=_ctx, iface=None, params=None)
        self.fake_boto.assert_called_with('cognito-idp', **CLIENT_CONFIG)
        self.fake_client.create_user_pool_client.assert_called_with(
            **_ctx.node.properties['resource_config']
        )

    def test_delete(self):
        _ctx = self.get_mock_ctx(
            'test_delete',
            test_properties=NODE_PROPERTIES,
            test_runtime_properties=RUNTIME_PROPERTIES_AFTER_CREATE,
            type_hierarchy=USER_POOL_CLIENT_TH,
            ctx_operation_name='cloudify.interfaces.lifecycle.delete'
        )
        current_ctx.set(_ctx)
        user_pool_client.delete(ctx=_ctx, resource_config=None, iface=None)
        self.fake_boto.assert_called_with('cognito-idp', **CLIENT_CONFIG)
        self.fake_client.delete_user_pool_client.assert_called_with(
            UserPoolId='foo',
            ClientId='foo',
        )

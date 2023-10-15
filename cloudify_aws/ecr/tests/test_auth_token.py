# Copyright (c) 2023 Cloudify Platform LTD. All rights reserved
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

import mock
from datetime import datetime

from cloudify_aws.common.tests.test_base import TestBase
from cloudify_aws.ecr.resources import authorization_token as auth


def mock_aws_resource(function,
                      class_decl,
                      resource_type,
                      ignore_properties,
                      **kwargs):
    return function(**kwargs)


DEFAULT_RC = {
    'registryIds': [
        'foo',
        'bar'
    ]
}
NODE_PROPERTIES = {'resource_config': DEFAULT_RC}
DEFAULT_RUNTIME_PROPERTIES = {}
TYPE_HIERARCHY = [
    'cloudify.nodes.Root',
    'cloudify.nodes.aws.ecr.AuthenticationToken'
]


@mock.patch('cloudify_aws.common.decorators._aws_resource',
            new=mock_aws_resource)
class TestECRAuth(TestBase):

    def setUp(self, *_):
        with mock.patch('cloudify_aws_sdk.client.boto3'):
            with mock.patch('cloudify_aws_sdk.client.get_client_config'):
                self.auth = auth.ECRAuthorizationToken(
                    mock.Mock(),
                    resource_id=True,
                    logger=None
                )
        self.auth.client = mock.Mock()

    def test_prepare(self, *_):
        _ctx = self.get_mock_ctx(
            'test_prepare',
            test_properties=NODE_PROPERTIES,
            test_runtime_properties=DEFAULT_RUNTIME_PROPERTIES,
            type_hierarchy=TYPE_HIERARCHY
        )
        iface = mock.Mock()
        auth.prepare(ctx=_ctx, iface=iface, resource_config=DEFAULT_RC)
        self.assertIn('resource_config', _ctx.instance.runtime_properties)
        self.assertEqual(
            _ctx.instance.runtime_properties['resource_config'],
            DEFAULT_RC)
        iface.assert_not_called()

    def test_create(self, *_):
        _ctx = self.get_mock_ctx(
            'test_create',
            test_properties=NODE_PROPERTIES,
            test_runtime_properties=DEFAULT_RUNTIME_PROPERTIES,
            type_hierarchy=TYPE_HIERARCHY
        )
        iface = mock.Mock()
        auth.create(ctx=_ctx, iface=iface, resource_config=DEFAULT_RC)
        self.assertIn('create_response', _ctx.instance.runtime_properties)
        iface.create.assert_called_once()

    def test_class_create(self, *_):
        create_response = {
            'authorizationData': [
                {
                    'authorizationToken': 'foo',
                    'expiresAt': datetime(2015, 1, 1),
                    'proxyEndpoint': 'string'
                },
                {
                    'authorizationToken': 'bar',
                    'expiresAt': datetime(2015, 1, 1),
                    'proxyEndpoint': 'string'
                },
            ]
        }
        self.auth.client = self.make_client_function(
            'get_authorization_token', return_value=create_response)
        self.assertEqual(
            self.auth.create(DEFAULT_RC),
            create_response
        )

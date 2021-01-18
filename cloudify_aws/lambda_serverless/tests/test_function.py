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
from mock import patch, MagicMock

from cloudify.mocks import MockCloudifyContext
from cloudify_aws.common._compat import StringIO

# Local imports
from cloudify_aws.common._compat import reload_module
from cloudify_aws.lambda_serverless.resources import function
from cloudify_aws.common.tests.test_base import (
    TestBase,
    mock_decorator
)


PATCH_PREFIX = 'cloudify_aws.lambda_serverless.resources.function.'
# Constants
SUBNET_GROUP_I = ['cloudify.nodes.Root',
                  'cloudify.nodes.aws.lambda.Invoke']
SUBNET_GROUP_F = ['cloudify.nodes.Root',
                  'cloudify.nodes.aws.lambda.Function']


class TestLambdaFunction(TestBase):

    def setUp(self):
        super(TestLambdaFunction, self).setUp()
        mock1 = patch('cloudify_aws.common.decorators.aws_resource',
                      mock_decorator)
        mock2 = patch('cloudify_aws.common.decorators.wait_for_delete',
                      mock_decorator)
        mock1.start()
        mock2.start()
        reload_module(function)

    def _get_ctx(self):
        _test_name = 'test_properties'
        _test_node_properties = {
            'use_external_resource': False
        }
        _test_runtime_properties = {'resource_config': False}
        return self.get_mock_ctx(
            _test_name,
            _test_node_properties,
            _test_runtime_properties,
            None
        )

    def _mock_function_file(self):
        with open('/tmp/mock_function.txt', 'wb') as _file:
            _file.write(b'test')

    def test_class_properties(self):
        ctx = self._get_ctx()
        with patch(PATCH_PREFIX + 'LambdaBase'):
            fun = function.LambdaFunction(ctx)
            fun.resource_id = 'test_function'
            fake_client = self.make_client_function(
                'get_function',
                return_value={'Configuration':
                              {'FunctionName': 'test_function'}})
            fun.client = fake_client

            result = fun.properties
            self.assertEqual(result, {'FunctionName': 'test_function'})

            fake_client = self.make_client_function(
                'get_function',
                return_value={'Configuration': None})
            fun.client = fake_client
            result = fun.properties
            self.assertIsNone(result)

            fake_client = self.make_client_function(
                'get_function',
                side_effect=self.get_client_error_exception('get_function'))

            fun.client = fake_client
            result = fun.properties
            self.assertIsNone(result)

    def test_class_status(self):
        ctx = self._get_ctx()
        with patch(PATCH_PREFIX + 'LambdaBase'):
            fun = function.LambdaFunction(ctx)
            fun.resource_id = 'test_function'
            fake_client = self.make_client_function(
                'get_function',
                return_value={'Configuration':
                              {'FunctionName': 'test_function'}})
            fun.client = fake_client
            status = fun.status
            self.assertEqual(status, 'available')

            fake_client = self.make_client_function(
                'get_function',
                return_value={})
            fun.client = fake_client
            status = fun.status
            self.assertIsNone(status)

    def test_class_create(self):
        ctx = self._get_ctx()
        with patch(PATCH_PREFIX + 'LambdaBase'):
            fun = function.LambdaFunction(ctx)
            fun.logger = MagicMock()
            fun.resource_id = 'test_function'
            fake_client = self.make_client_function(
                'create_function',
                return_value={'FunctionArn': 'test_function_arn',
                              'FunctionName': 'test_function'})
            fun.client = fake_client
            create_response = fun.create({'param': 'params'})
            self.assertEqual(
                create_response['FunctionName'], fun.resource_id)
            self.assertEqual(
                create_response['FunctionArn'], 'test_function_arn')

    def test_class_delete(self):
        ctx = self._get_ctx()
        with patch(PATCH_PREFIX + 'LambdaBase'):
            fun = function.LambdaFunction(ctx)
            fun.logger = MagicMock()
            fun.resource_id = 'test_function'
            fake_client = self.make_client_function(
                'delete_function',
                return_value=None)
            fun.client = fake_client
            fun.delete({'param': 'params'})

    def test_class_invoke(self):
        ctx = self._get_ctx()
        with patch(PATCH_PREFIX + 'LambdaBase'):
            fun = function.LambdaFunction(ctx)
            fun.logger = MagicMock()
            fun.resource_id = 'test_function'
            fake_client = self.make_client_function(
                'invoke',
                return_value={'Payload': StringIO(u'text')})
            fun.client = fake_client
            result = fun.invoke({'param': 'params'})
            self.assertEqual(result, {'Payload': u'text'})

            fake_client = self.make_client_function(
                'invoke',
                return_value='')
            fun.client = fake_client
            result = fun.invoke({'param': 'params'})
            self.assertEqual(result, '')

            fake_client = self.make_client_function(
                'invoke',
                return_value={'Payload': StringIO(u'{"text": "test"}')})
            fun.client = fake_client
            result = fun.invoke({'param': 'params'})
            self.assertEqual(result, {'Payload': {"text": "test"}})

    def test_class_invoke_payload(self):
        ctx = self._get_ctx()
        with patch(PATCH_PREFIX + 'LambdaBase'):
            fun = function.LambdaFunction(ctx)
            fun.logger = MagicMock()
            fun.resource_id = 'test_function'
            fake_client = self.make_client_function(
                'invoke',
                side_effect=lambda FunctionName, Payload: self.assertEqual(
                    Payload, 0))
            fun.client = fake_client
            result = fun.invoke({'Payload': 0})
            self.assertEqual(result, None)

            fake_client = self.make_client_function(
                'invoke',
                side_effect=lambda FunctionName, Payload: self.assertEqual(
                    Payload, u'{"key": "value"}'))

            fun.client = fake_client
            result = fun.invoke({'Payload': {"key": "value"}})
            self.assertEqual(result, None)

            self._mock_function_file()
            fake_client = self.make_client_function(
                'invoke',
                side_effect=lambda FunctionName, Payload:
                    self.assertEqual(Payload.read(), 'test'))
            fun.client = fake_client
            result = fun.invoke({'Payload': '/tmp/mock_function.txt'})
            self.assertEqual(result, None)

    @patch(u'{0}{1}'.format(PATCH_PREFIX, '_get_iam_role_to_attach'))
    @patch(u'{0}{1}'.format(PATCH_PREFIX, '_get_security_groups_to_attach'))
    @patch(u'{0}{1}'.format(PATCH_PREFIX, '_get_subnets_to_attach'))
    def test_create(self,
                    mock_subnet_attach,
                    mock_security_groups_attach,
                    mock_iam_role_attach):
        ctx = MockCloudifyContext("test_create")
        zip_file = self._mock_function_file()
        with patch(PATCH_PREFIX + 'LambdaBase'):
            fun = function.LambdaFunction(ctx)
            fun.logger = MagicMock()
            fun.resource_id = 'test_function'
            fake_client = self.make_client_function(
                'create_function',
                return_value={
                    'FunctionArn': 'test_function_arn',
                    'FunctionName': 'test_function'
                }
            )
            fun.client = fake_client
            resource_config = {
                'VpcConfig': {
                    'SubnetIds': []
                }, 'Code': {
                    'ZipFile': zip_file
                }
            }
            mock_iam_role_attach.return_value = ['role-1']
            mock_security_groups_attach.return_value = ['sg-1']
            mock_subnet_attach.return_value = ['subnet-1']

            function.create(ctx, fun, resource_config)
            self.assertEqual(zip_file, resource_config['Code']['ZipFile'])
            self.assertEqual(
                {
                    'SubnetIds': ['subnet-1'],
                    'SecurityGroupIds': ['sg-1']
                },
                resource_config['VpcConfig']
            )

    @patch(u'{0}{1}'.format(PATCH_PREFIX, '_get_iam_role_to_attach'))
    @patch(u'{0}{1}'.format(PATCH_PREFIX, '_get_security_groups_to_attach'))
    @patch(u'{0}{1}'.format(PATCH_PREFIX, '_get_subnets_to_attach'))
    def test_create_with_download(self,
                                  mock_subnet_attach,
                                  mock_security_groups_attach,
                                  mock_iam_role_attach):
        ctx = MockCloudifyContext("test_create")
        zip_file = self._mock_function_file()
        ctx.download_resource = MagicMock(return_value=zip_file)
        with patch(PATCH_PREFIX + 'LambdaBase'):
            fun = function.LambdaFunction(ctx)
            fun.logger = MagicMock()
            fun.resource_id = 'test_function'
            fake_client = self.make_client_function(
                'create_function',
                return_value={'FunctionArn': 'test_function_arn',
                              'FunctionName': 'test_function'})
            fun.client = fake_client
            resource_config = {
                'VpcConfig': {
                    'SubnetIds': []
                }, 'Code': {
                    'ZipFile': zip_file
                }
            }
            mock_iam_role_attach.return_value = ['role-1']
            mock_security_groups_attach.return_value = ['sg-1']
            mock_subnet_attach.return_value = ['subnet-1']

            function.create(ctx, fun, resource_config)
            self.assertEqual(zip_file, resource_config['Code']['ZipFile'])
            self.assertEqual(
                {
                    'SubnetIds': ['subnet-1'],
                    'SecurityGroupIds': ['sg-1']
                },
                resource_config['VpcConfig']
            )

    def test_delete(self):
        iface = MagicMock()
        function.delete(iface, None)
        self.assertTrue(iface.delete.called)


if __name__ == '__main__':
    unittest.main()

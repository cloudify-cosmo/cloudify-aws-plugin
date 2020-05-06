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

from cloudify.manager import DirtyTrackingDict

# Local imports
from cloudify_aws.common._compat import reload_module
from cloudify_aws.lambda_serverless.resources import permission
from cloudify_aws.common.tests.test_base import (
    TestBase,
    mock_decorator
)

PATCH_PREFIX = 'cloudify_aws.lambda_serverless.resources.permission.'


class TestLambdaPermission(TestBase):

    def setUp(self):
        super(TestLambdaPermission, self).setUp()
        mock1 = patch('cloudify_aws.common.decorators.aws_resource',
                      mock_decorator)
        mock2 = patch('cloudify_aws.common.decorators.aws_relationship',
                      mock_decorator)
        mock1.start()
        mock2.start()
        reload_module(permission)

    def _get_ctx(self):
        _test_name = 'test_properties'
        _test_node_properties = {
            'use_external_resource': False
        }
        _test_runtime_properties = {'resource_config': {}}
        return self.get_mock_ctx(_test_name, _test_node_properties,
                                 _test_runtime_properties,
                                 None)

    def _get_relationship_context(self):
        _test_name = 'test_lambda'
        _test_node_properties = {
            'use_external_resource': False,
            'resource_id': 'target'
        }
        _test_runtime_properties = {'resource_config': {},
                                    '_set_changed': True}
        source = self.get_mock_ctx("source_node", _test_node_properties,
                                   DirtyTrackingDict(_test_runtime_properties),
                                   None)
        target = self.get_mock_ctx("target_node", _test_node_properties,
                                   DirtyTrackingDict(_test_runtime_properties),
                                   None)
        return self.get_mock_relationship_ctx(_test_name,
                                              _test_node_properties,
                                              _test_runtime_properties,
                                              source,
                                              target)

    def test_class_properties(self):
        ctx = self._get_ctx()
        with patch(PATCH_PREFIX + 'LambdaBase'):
            fun = permission.LambdaPermission(ctx)
            with self.assertRaises(NotImplementedError):
                fun.properties

    def test_class_status(self):
        ctx = self._get_ctx()
        with patch(PATCH_PREFIX + 'LambdaBase'):
            fun = permission.LambdaPermission(ctx)
            with self.assertRaises(NotImplementedError):
                fun.status

    def test_class_create(self):
        ctx = self._get_ctx()
        with patch(PATCH_PREFIX + 'LambdaBase'):
            fun = permission.LambdaPermission(ctx)
            fun.logger = MagicMock()
            fun.resource_id = ''
            fake_client = self.make_client_function(
                'add_permission',
                return_value={'Statement': {'Sid': 'test_id'}})
            fun.client = fake_client
            create_response = fun.create({'StatementId': 'test_id'})
            self.assertEqual(create_response['Statement']['Sid'], 'test_id')

    def test_class_delete(self):
        ctx = self._get_ctx()
        with patch(PATCH_PREFIX + 'LambdaBase'):
            fun = permission.LambdaPermission(ctx)
            fun.logger = MagicMock()
            fun.resource_id = 'test_id'
            params = {"test": "test"}
            fun.client = self.make_client_function(
                'remove_permission',
                return_value='response')
            fun.delete(params)
            self.assertIn('StatementId', params)

    def test_class_prepare(self):
        ctx = self._get_ctx()
        with patch(PATCH_PREFIX + 'utils') as utils:
            utils.get_resource_id = MagicMock(return_value=True)
            res_config = {'param': 'params'}
            permission.prepare(ctx, res_config)
            self.assertEqual(
                ctx.instance.runtime_properties['resource_config'],
                res_config
            )

        with patch(PATCH_PREFIX + 'utils') as utils:
            utils.get_resource_id = MagicMock(return_value=False)
            res_config = {'param': 'params'}
            permission.prepare(ctx, res_config)
            self.assertEqual(
                ctx.instance.runtime_properties['resource_config'],
                res_config
            )
            self.assertTrue(utils.update_resource_id.called)

        with patch(PATCH_PREFIX + 'utils') as utils:
            utils.get_resource_id = MagicMock(return_value=False)
            res_config = {'param': 'params', 'StatementId': 'test_id'}
            permission.prepare(ctx, res_config)
            self.assertEqual(
                ctx.instance.runtime_properties['resource_config'],
                res_config
            )
            self.assertTrue(utils.update_resource_id.called)
            utils.update_resource_id.assert_called_with(ctx.instance,
                                                        'test_id')

    def test_create(self):
        ctx = self._get_ctx()
        with patch(PATCH_PREFIX + 'utils') as utils:
            iface = MagicMock()
            iface.create = MagicMock(
                return_value={'Statement': {'Sid': 'res_id'}})
            iface.resource_id = 'test_id'
            permission.create(ctx, iface, {})
            self.assertEqual(1, utils.update_resource_id.call_count)
            self.assertEqual(1, utils.update_resource_arn.call_count)

        with patch(PATCH_PREFIX + 'utils') as utils:
            iface = MagicMock()
            iface.create = MagicMock(
                return_value={'Statement': {'Sid': 'res_id'}})
            iface.resource_id = None
            ctx.instance.runtime_properties['resource_config'].update(
                {'StatementId': 'test_id'})
            permission.create(ctx, iface, {})
            self.assertEqual(1, utils.update_resource_id.call_count)
            self.assertEqual(1, utils.update_resource_arn.call_count)

    def test_delete(self):
        ctx = self._get_ctx()
        iface = MagicMock()
        ctx.instance.runtime_properties['resource_config'].update(
            {'FunctionName': 'test_fun'})
        res_config = {}
        permission.delete(ctx, iface, res_config)
        self.assertTrue(iface.delete.called)
        self.assertEqual('test_fun', res_config['FunctionName'])

    def test_prepare_assoc(self):
        ctx = self._get_relationship_context()
        with patch(PATCH_PREFIX + 'utils') as utils:
            utils.get_resource_arn = MagicMock(return_value="test_arn")
            utils.is_node_type = MagicMock(return_value=True)
            iface = MagicMock()
            ctx.source.instance.runtime_properties['resource_config'].update(
                {'FunctionName': 'test_fun'})
            res_config = {}
            permission.prepare_assoc(ctx, iface, res_config)
            self.assertEqual(
                ctx.source.instance.
                runtime_properties['resource_config']['FunctionName'],
                'test_arn')

    def test_detach_from(self):
        self.assertIsNone(permission.detach_from(None, None, None))


if __name__ == '__main__':
    unittest.main()

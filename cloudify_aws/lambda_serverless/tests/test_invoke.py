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
from cloudify_aws.lambda_serverless.resources import invoke
from cloudify_aws.common.tests.test_base import (
    TestBase,
    mock_decorator
)

# Constants
SUBNET_GROUP_I = ['cloudify.nodes.Root', 'cloudify.nodes.aws.lambda.Invoke']
SUBNET_GROUP_F = ['cloudify.nodes.Root', 'cloudify.nodes.aws.lambda.Function']

LAMBDA_PATH = (
    'cloudify_aws.lambda_serverless.resources.invoke.LambdaFunction'
)
INVOKE_PATH = 'cloudify_aws.lambda_serverless.resources.invoke.'


class TestLambdaInvoke(TestBase):

    def setUp(self):
        super(TestLambdaInvoke, self).setUp()
        mock1 = patch('cloudify_aws.common.decorators.aws_resource',
                      mock_decorator)
        mock2 = patch('cloudify_aws.common.decorators.aws_relationship',
                      mock_decorator)
        mock1.start()
        mock2.start()
        reload_module(invoke)

    def _get_relationship_context(self, subnet_group):
        _test_name = 'test_lambda'
        _test_node_properties = {
            'use_external_resource': False,
            'resource_id': 'target'
        }
        _test_runtime_properties = {'resource_config': 'resource',
                                    '_set_changed': True}
        source = self.get_mock_ctx("source_node", _test_node_properties,
                                   DirtyTrackingDict(_test_runtime_properties),
                                   SUBNET_GROUP_I)
        target = self.get_mock_ctx("target_node", _test_node_properties,
                                   DirtyTrackingDict(_test_runtime_properties),
                                   subnet_group)
        return self.get_mock_relationship_ctx(_test_name,
                                              _test_node_properties,
                                              _test_runtime_properties,
                                              source,
                                              target)

    def test_configure(self):
        _test_name = 'test_configure'
        _test_node_properties = {
            'use_external_resource': False
        }
        _test_runtime_properties = {'resource_config': False}
        ctx = self.get_mock_ctx(_test_name, _test_node_properties,
                                _test_runtime_properties,
                                SUBNET_GROUP_I)
        invoke.configure(ctx=ctx, resource_config=True)
        self.assertTrue(
            ctx.instance.runtime_properties['resource_config'])

    def test_attach_to(self):
        relation_ctx = self._get_relationship_context(SUBNET_GROUP_F)
        with patch(LAMBDA_PATH) as mock, patch(INVOKE_PATH + 'utils') as utils:
            utils.is_node_type = MagicMock(return_value=True)
            invoke.attach_to(
                ctx=relation_ctx, resource_config=True)
            self.assertTrue(mock.called)
            output = relation_ctx.source.instance.runtime_properties['output']
            self.assertIsInstance(output, MagicMock)

        relation_ctx = self._get_relationship_context(SUBNET_GROUP_I)
        with patch(LAMBDA_PATH) as mock, patch(INVOKE_PATH + 'utils') as utils:
            utils.is_node_type = MagicMock(return_value=False)
            invoke.attach_to(ctx=relation_ctx, resource_config=True)
            self.assertFalse(mock.called)

    def test_detach_from(self):
        relation_ctx = self._get_relationship_context(SUBNET_GROUP_I)
        invoke.detach_from(ctx=relation_ctx, resource_config=None)


if __name__ == '__main__':
    unittest.main()

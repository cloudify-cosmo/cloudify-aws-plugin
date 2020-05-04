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
import copy

# Third party imports
from mock import patch, MagicMock

from cloudify.state import current_ctx

# Local imports
from cloudify_aws.cloudformation.resources import stack
from cloudify_aws.common.tests.test_base import TestBase, CLIENT_CONFIG
from cloudify_aws.common.tests.test_base import DELETE_RESPONSE


# Constants
STACK_TH = ['cloudify.nodes.Root',
            'cloudify.nodes.aws.cloudformation.Stack']

NODE_PROPERTIES = {
    'use_external_resource': False,
    'resource_config': {
        'kwargs': {
            'StackName': 'test-cloudformation1',
            'TemplateBody':
                {"AWSTemplateFormatVersion": "2010-09-09",
                 "Description": "A sample template"}
        }
    },
    'client_config': CLIENT_CONFIG
}

RUNTIME_PROPERTIES = {
    'aws_resource_id': None,
    'resource_config': {}
}

RUNTIMEPROP_AFTER_CREATE = {
    'aws_resource_id': 'test-cloudformation1',
    'resource_config': {}
}


class TestCloudFormationStack(TestBase):

    def setUp(self):
        super(TestCloudFormationStack, self).setUp()

        self.fake_boto, self.fake_client = \
            self.fake_boto_client('cloudformation')

        self.mock_patch = patch('boto3.client', self.fake_boto)
        self.mock_patch.start()

    def tearDown(self):
        self.mock_patch.stop()
        self.fake_boto = None
        self.fake_client = None

        super(TestCloudFormationStack, self).tearDown()

    def test_prepare(self):
        self._prepare_check(type_hierarchy=STACK_TH,
                            type_name='cloudformation',
                            type_class=stack)

    def test_create(self):
        _ctx = self.get_mock_ctx(
            'test_create', test_properties=NODE_PROPERTIES,
            test_runtime_properties=RUNTIME_PROPERTIES,
            type_hierarchy=STACK_TH,
            ctx_operation_name='cloudify.interfaces.lifecycle.configure')

        current_ctx.set(_ctx)
        self.fake_client.describe_stacks = MagicMock(return_value={
            'Stacks': [{'StackName': 'Stack',
                        'StackStatus': 'CREATE_COMPLETE'}]
        })

        self.fake_client.create_stack = MagicMock(return_value={
            'StackId': 'stack'
        })

        stack.create(ctx=_ctx, resource_config=None, iface=None)

        self.fake_boto.assert_called_with('cloudformation', **CLIENT_CONFIG)

        try:
            self.fake_client.create_stack.assert_called_with(
                StackName='test-cloudformation1',
                TemplateBody='{"AWSTemplateFormatVersion": "2010-09-09",'
                             ' "Description": "A sample template"}')
        except AssertionError:
            try:
                self.fake_client.create_stack.assert_called_with(
                    StackName='test-cloudformation1',
                    TemplateBody='{"Description": "A sample template",'
                                 ' "AWSTemplateFormatVersion": "2010-09-09"}')
            except AssertionError as e:
                raise e

        updated_runtime_prop = copy.deepcopy(RUNTIMEPROP_AFTER_CREATE)
        updated_runtime_prop['create_response'] = {
            'StackName': 'Stack',
            'StackStatus': 'CREATE_COMPLETE'
        }
        self.assertEqual(_ctx.instance.runtime_properties,
                         updated_runtime_prop)

    def test_delete(self):
        _ctx = \
            self.get_mock_ctx('test_delete',
                              test_properties=NODE_PROPERTIES,
                              test_runtime_properties=RUNTIMEPROP_AFTER_CREATE,
                              type_hierarchy=STACK_TH)

        current_ctx.set(_ctx)
        self.fake_client.describe_stacks = MagicMock(return_value={
            'Stacks': [{'StackName': 'Stack',
                        'StackStatus': 'DELETE_COMPLETE'}]
        })

        self.fake_client.delete_stack = MagicMock(return_value=DELETE_RESPONSE)

        stack.delete(ctx=_ctx, resource_config=None, iface=None)

        self.fake_boto.assert_called_with('cloudformation', **CLIENT_CONFIG)

        self.fake_client.delete_stack.\
            assert_called_with(StackName='test-cloudformation1')

        self.assertEqual(_ctx.instance.runtime_properties,
                         {'__deleted': True})

    def test_CloudFormationStackClass_properties(self):
        self.fake_client.describe_stacks = MagicMock(return_value={
            'Stacks': [{'StackName': 'Stack'}]
        })

        test_instance = stack.CloudFormationStack("ctx_node",
                                                  resource_id='Stack',
                                                  client=self.fake_client,
                                                  logger=None)

        self.assertEqual(test_instance.properties['StackName'], 'Stack')

        self.fake_client.describe_stacks.assert_called_with(StackName='Stack')

    def test_CloudFormationStackClass_properties_empty(self):
        self.fake_client.describe_stacks = MagicMock(return_value={
            'Stacks': [None]
        })

        test_instance = stack.CloudFormationStack("ctx_node",
                                                  resource_id='Stack',
                                                  client=self.fake_client,
                                                  logger=None)

        self.assertEqual(test_instance.properties, None)

        self.fake_client.describe_stacks.assert_called_with(StackName='Stack')

    def test_CloudFormationStackClass_status(self):
        self.fake_client.describe_stacks = MagicMock(return_value={
            'Stacks': [{'StackName': 'Stack',
                        'StackStatus': None}]
        })

        test_instance = stack.CloudFormationStack("ctx_node",
                                                  resource_id='Stack',
                                                  client=self.fake_client,
                                                  logger=None)

        self.assertEqual(test_instance.status, None)

        self.fake_client.describe_stacks.assert_called_with(StackName='Stack')

    def test_CloudFormationStackClass_status_empty(self):
        self.fake_client.describe_stacks = MagicMock(return_value={
            'Stacks': [None]
        })

        test_instance = stack.CloudFormationStack("ctx_node",
                                                  resource_id='Stack',
                                                  client=self.fake_client,
                                                  logger=None)

        self.assertEqual(test_instance.status, None)

        self.fake_client.describe_stacks.assert_called_with(StackName='Stack')


if __name__ == '__main__':
    unittest.main()

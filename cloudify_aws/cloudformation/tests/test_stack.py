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
from cloudify_aws.common.tests.test_base import (TestBase,
                                                 CLIENT_CONFIG,
                                                 DELETE_RESPONSE)

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

RUNTIMEPROP_AFTER_START = {
    'aws_resource_id': 'test-cloudformation1',
    'resource_config': {},
    'StackId': '1',
    'StackName': 'test-cloudformation1',
    stack.SAVED_PROPERTIES: ['StackId', 'StackName']
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
            type_hierarchy=STACK_TH)

        current_ctx.set(_ctx)
        self.fake_client.describe_stacks = MagicMock(side_effect=[
            {},
            {
                'Stacks': [{'StackName': 'test-cloudformation1',
                            'StackStatus': 'CREATE_COMPLETE'}]
            },
            {
                'Stacks': [{'StackName': 'test-cloudformation1',
                            'StackStatus': 'CREATE_COMPLETE'}]
            },
            {
                'Stacks': [{'StackName': 'test-cloudformation1',
                            'StackStatus': 'CREATE_COMPLETE'}]
            },
            {
                'Stacks': [{'StackName': 'test-cloudformation1',
                            'StackStatus': 'CREATE_COMPLETE'}]
            }
        ])

        self.fake_client.create_stack = MagicMock(return_value={
            'StackId': 'test-cloudformation1'
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
            'StackName': 'test-cloudformation1',
            'StackStatus': 'CREATE_COMPLETE'
        }

        # This is just because I'm not interested in the content
        # of remote_configuration right now.
        # If it doesn't exist, this test will fail, and that's good.
        _ctx.instance.runtime_properties.pop('remote_configuration')
        self.assertEqual(_ctx.instance.runtime_properties,
                         updated_runtime_prop)

    def test_delete(self):
        _ctx = \
            self.get_mock_ctx(
                'test_delete',
                test_properties=NODE_PROPERTIES,
                test_runtime_properties=RUNTIMEPROP_AFTER_CREATE,
                type_hierarchy=STACK_TH,
                ctx_operation_name='cloudify.interfaces.lifecycle.delete')

        current_ctx.set(_ctx)
        self.fake_client.describe_stacks = MagicMock(side_effect=[
            {
                'Stacks': [{'StackName': 'Stack',
                            'StackStatus': 'CREATE_COMPLETE'}]
            },
            {
                'Stacks': [{'StackName': 'Stack',
                            'StackStatus': 'CREATE_COMPLETE'}]
            },
            {
                'Stacks': [{'StackName': 'Stack',
                            'StackStatus': 'DELETE_COMPLETE'}]
            }
        ])

        self.fake_client.delete_stack = MagicMock(return_value=DELETE_RESPONSE)

        stack.delete(ctx=_ctx, resource_config={}, iface=None)

        self.fake_boto.assert_called_with('cloudformation', **CLIENT_CONFIG)

        self.fake_client.delete_stack. \
            assert_called_with(StackName='test-cloudformation1')

        self.assertEqual(_ctx.instance.runtime_properties,
                         {'__deleted': True})

    def test_pull(self):
        _ctx = \
            self.get_mock_ctx('test_pull',
                              test_properties=NODE_PROPERTIES,
                              test_runtime_properties=RUNTIMEPROP_AFTER_START,
                              type_hierarchy=STACK_TH,
                              ctx_operation_name='cloudify.interfaces.'
                                                 'lifecycle.pull')
        current_ctx.set(_ctx)

        # Change StackId
        self.fake_client.describe_stacks = MagicMock(return_value={
            'Stacks': [
                {'StackId': '2',
                 'StackName': 'test-cloudformation1'
                 }
            ]
        })
        self.fake_client.detect_stack_drift = MagicMock(
            return_value={'StackDriftDetectionId': 'fake-detection-id'})

        self.fake_client.describe_stack_drift_detection_status = MagicMock(
            return_value={'DetectionStatus': 'DETECTION_COMPLETE'})
        self.fake_client.list_stack_resources = MagicMock(
            return_value={})
        self.fake_client.describe_stack_resource_drifts = MagicMock(
            return_value={})
        stack.pull(ctx=_ctx)
        expected_runtime_properties = dict(RUNTIMEPROP_AFTER_START)
        expected_runtime_properties.update(
            {'StackId': '2',
             'is_drifted': False,
             stack.STACK_RESOURCES_DRIFTS: [],
             stack.STACK_RESOURCES_RUNTIME_PROP: []})

        expected_runtime_properties[stack.SAVED_PROPERTIES].append(
            stack.STACK_RESOURCES_DRIFTS)
        # Pop the list of saved properties and compare them separately due
        # to ordering issues.
        expected_saved_properties = expected_runtime_properties.pop(
            stack.SAVED_PROPERTIES)
        actual_saved_properties = _ctx.instance.runtime_properties.pop(
            stack.SAVED_PROPERTIES)
        self.assertDictEqual(_ctx.instance.runtime_properties,
                             expected_runtime_properties)
        self.assertSetEqual(set(actual_saved_properties),
                            set(expected_saved_properties))

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
            'Stacks': []
        })

        test_instance = stack.CloudFormationStack("ctx_node",
                                                  resource_id='Stack',
                                                  client=self.fake_client,
                                                  logger=None)

        self.assertEqual(test_instance.properties, {})

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
            'Stacks': []
        })

        test_instance = stack.CloudFormationStack("ctx_node",
                                                  resource_id='Stack',
                                                  client=self.fake_client,
                                                  logger=None)

        self.assertEqual(test_instance.status, None)

        self.fake_client.describe_stacks.assert_called_with(StackName='Stack')

    def test_CloudFormationStackClass_list_resources(self):
        fake_return_value = {
            'StackResourceSummaries': [
                {
                    'LogicalResourceId': 'VPC',
                    'PhysicalResourceId': 'vpc-11223344',
                    'ResourceStatus': 'CREATE_COMPLETE'
                }
            ]
        }

        self.fake_client.list_stack_resources = MagicMock(
            return_value=fake_return_value)

        test_instance = stack.CloudFormationStack('ctx_node',
                                                  resource_id='Stack',
                                                  client=self.fake_client,
                                                  logger=None)

        self.assertEqual(test_instance.list_resources(),
                         fake_return_value[stack.STACK_RESOURCES])

        self.fake_client.list_stack_resources.assert_called_with(
            StackName='Stack')

    def test_CloudFormationStackClass_list_resources_error(self):
        test_instance = stack.CloudFormationStack('ctx_node',
                                                  resource_id='Stack',
                                                  client=self.fake_client,
                                                  logger=None)

        self.assertEqual(test_instance.list_resources(), [])

    def test_CloudFormationStackClass_detect_stack_drifts(self):

        self.fake_client.detect_stack_drift = MagicMock(
            return_value={'StackDriftDetectionId': 'fake-detection-id'})

        self.fake_client.describe_stack_drift_detection_status = MagicMock(
            return_value={'DetectionStatus': 'DETECTION_COMPLETE'})
        test_instance = stack.CloudFormationStack("ctx_node",
                                                  resource_id='Stack',
                                                  client=self.fake_client,
                                                  logger=None)

        self.assertEqual(test_instance.detect_stack_drifts(),
                         'DETECTION_COMPLETE')

        self.fake_client.detect_stack_drift.assert_called_with(
            StackName='Stack')
        self.fake_client.describe_stack_drift_detection_status \
            .assert_called_with(StackDriftDetectionId='fake-detection-id')

    def test_CloudFormationStackClass_resources_drifts(self):
        fake_return_value = {'StackResourceDrifts': [
            {
                'StackId': '1234',
                'LogicalResourceId': 'vpc',
                'PhysicalResourceId': 'vpc-1234',
                'PropertyDifferences': [],
            },
        ],
        }

        self.fake_client.describe_stack_resource_drifts = MagicMock(
            return_value=fake_return_value)

        test_instance = stack.CloudFormationStack('ctx_node',
                                                  resource_id='Stack',
                                                  client=self.fake_client,
                                                  logger=None)

        self.assertEqual(test_instance.resources_drifts(),
                         fake_return_value[stack.STACK_RESOURCES_DRIFTS])

        self.fake_client.describe_stack_resource_drifts.assert_called_with(
            StackName='Stack',
            StackResourceDriftStatusFilters=['DELETED', 'MODIFIED'])

    def test_CloudFormationStackClass_resources_drifts_error(self):
        test_instance = stack.CloudFormationStack('ctx_node',
                                                  resource_id='Stack',
                                                  client=self.fake_client,
                                                  logger=None)

        self.assertEqual(test_instance.resources_drifts(), [])

        self.fake_client.describe_stack_resource_drifts.assert_called_with(
            StackName='Stack',
            StackResourceDriftStatusFilters=['DELETED', 'MODIFIED'])

    def test_delete_stack_info_runtime_properties(self):
        _ctx = self.get_mock_ctx(
            'test_delete_stack_info_runtime_properties',
            test_properties=NODE_PROPERTIES,
            test_runtime_properties=RUNTIMEPROP_AFTER_START,
            type_hierarchy=STACK_TH)

        current_ctx.set(_ctx)

        stack.delete_stack_info_runtime_properties(_ctx)
        runtime_properties_after_deletion = dict(RUNTIMEPROP_AFTER_CREATE)
        runtime_properties_after_deletion.update({stack.SAVED_PROPERTIES: []})
        self.assertEqual(_ctx.instance.runtime_properties,
                         runtime_properties_after_deletion)

    def test_update_runtime_properties_with_stack_info(self):
        _ctx = self.get_mock_ctx(
            'test_update_runtime_properties_with_stack_info',
            test_properties=NODE_PROPERTIES,
            test_runtime_properties=RUNTIMEPROP_AFTER_CREATE,
            type_hierarchy=STACK_TH)

        current_ctx.set(_ctx)
        test_instance = stack.CloudFormationStack(
            "ctx_node",
            resource_id='test-cloudformation1',
            client=self.fake_client,
            logger=None)

        self.fake_client.describe_stacks = MagicMock(return_value={
            'Stacks': [
                {'StackName': 'test-cloudformation1',
                 'StackId': '1',
                 'Outputs': [
                     {"OutputKey": "URL",
                      "OutputValue": "10.0.0.0",
                      "Description": "IP Address of Server"
                      }
                 ]
                 }
            ]
        })
        stack.update_runtime_properties_with_stack_info(_ctx, test_instance)
        expected_runtime_properties = dict(RUNTIMEPROP_AFTER_START)
        expected_runtime_properties.pop(stack.SAVED_PROPERTIES)
        expected_runtime_properties.update(
            {'outputs_items': {'URL': '10.0.0.0'}, 'Outputs': [
                {'OutputKey': 'URL', 'OutputValue': '10.0.0.0',
                 'Description': 'IP Address of Server'}], 'is_drifted': False})
        expected_saved_properties = ['StackName',
                                     'StackId',
                                     'Outputs',
                                     'outputs_items']
        # Pop the list of saved properties and compare them separately due
        # to ordering issues.
        actual_saved_properties = _ctx.instance.runtime_properties.pop(
            stack.SAVED_PROPERTIES)
        self.assertDictEqual(_ctx.instance.runtime_properties,
                             expected_runtime_properties)
        self.assertSetEqual(set(actual_saved_properties),
                            set(expected_saved_properties))


if __name__ == '__main__':
    unittest.main()

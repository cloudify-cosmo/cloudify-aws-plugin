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

from cloudify.state import current_ctx

# Local imports
from cloudify_aws.autoscaling.resources import lifecycle_hook
from cloudify_aws.common.tests.test_base import TestBase, CLIENT_CONFIG
from cloudify_aws.common.tests.test_base import DELETE_RESPONSE


# Constants
LIFECYCLE_HOOK_TH = ['cloudify.nodes.Root',
                     'cloudify.nodes.aws.autoscaling.LifecycleHook']

NODE_PROPERTIES = {
    'use_external_resource': False,
    'resource_config': {
        'kwargs': {
            'LifecycleHookName': 'test-autoscaling3',
            'LifecycleTransition': 'autoscaling:EC2_INSTANCE_LAUNCHING'
        }
    },
    'client_config': CLIENT_CONFIG
}

RUNTIME_PROPERTIES_AFTER_CREATE = {
    'AutoScalingGroupName': 'aws_id',
    'aws_resource_id': 'test-autoscaling3',
    'resource_config': {}
}


class TestAutoscalingLifecycleHook(TestBase):

    def setUp(self):
        super(TestAutoscalingLifecycleHook, self).setUp()

        self.fake_boto, self.fake_client = self.fake_boto_client('autoscaling')

        self.mock_patch = patch('boto3.client', self.fake_boto)
        self.mock_patch.start()

    def tearDown(self):
        self.mock_patch.stop()
        self.fake_boto = None
        self.fake_client = None

        super(TestAutoscalingLifecycleHook, self).tearDown()

    def test_prepare(self):
        self._prepare_check(
            type_hierarchy=LIFECYCLE_HOOK_TH,
            type_name='autoscaling',
            type_class=lifecycle_hook
        )

    def test_create_raises_UnknownServiceError(self):
        self._prepare_create_raises_UnknownServiceError(
            type_hierarchy=LIFECYCLE_HOOK_TH,
            type_name='autoscaling',
            type_class=lifecycle_hook
        )

    def _prepare_context(self, runtime_prop=None):
        mock_group = MagicMock()
        mock_group.type_hierarchy = 'cloudify.relationships.depends_on'
        mock_group.target.instance.runtime_properties = {
            'aws_resource_id': 'aws_id'
        }
        mock_group.target.node.type_hierarchy = [
            'cloudify.nodes.Root',
            'cloudify.nodes.aws.autoscaling.Group'
        ]

        _ctx = self.get_mock_ctx(
            'test_create',
            test_properties=NODE_PROPERTIES,
            test_runtime_properties=runtime_prop if runtime_prop else {
                'resource_config': {}
            },
            type_hierarchy=LIFECYCLE_HOOK_TH,
            test_relationships=[mock_group]
        )

        current_ctx.set(_ctx)
        return _ctx

    def test_create(self):
        _ctx = self._prepare_context()

        self.fake_client.put_lifecycle_hook = MagicMock(return_value={
            'AutoScalingGroupName': 'scaling_name',
            'AutoScalingGroupARN': 'scaling_arn'
        })

        lifecycle_hook.create(ctx=_ctx, resource_config=None, iface=None,
                              params=None)

        self.fake_boto.assert_called_with('autoscaling', **CLIENT_CONFIG)

        self.fake_client.put_lifecycle_hook.assert_called_with(
            AutoScalingGroupName='aws_id',
            LifecycleHookName='test-autoscaling3',
            LifecycleTransition='autoscaling:EC2_INSTANCE_LAUNCHING'
        )

        self.assertEqual(
            _ctx.instance.runtime_properties,
            RUNTIME_PROPERTIES_AFTER_CREATE
        )

    def test_delete(self):
        _ctx = self._prepare_context(RUNTIME_PROPERTIES_AFTER_CREATE)

        self.fake_client.delete_lifecycle_hook = self.mock_return(
            DELETE_RESPONSE)

        lifecycle_hook.delete(ctx=_ctx, resource_config={}, iface=None)

        self.fake_boto.assert_called_with('autoscaling', **CLIENT_CONFIG)

        self.fake_client.delete_lifecycle_hook.assert_called_with(
            AutoScalingGroupName='aws_id',
            LifecycleHookName='test-autoscaling3'
        )

        self.assertEqual(
            _ctx.instance.runtime_properties, {
                'AutoScalingGroupName': 'aws_id',
                'aws_resource_id': 'test-autoscaling3',
                'resource_config': {}
            }
        )

    def test_AutoscalingLifecycleHook_properties(self):
        test_instance = lifecycle_hook.AutoscalingLifecycleHook(
            "ctx_node", resource_id='hook_id', client=self.fake_client,
            logger=None
        )

        self.assertEqual(test_instance.properties, None)

    def test_AutoscalingLifecycleHook_properties_not_empty(self):
        test_instance = lifecycle_hook.AutoscalingLifecycleHook(
            "ctx_node", resource_id='hook_id', client=self.fake_client,
            logger=None
        )

        self.fake_client.describe_lifecycle_hooks = MagicMock(
            return_value={'LifecycleHooks': ['SomeHook']}
        )

        self.assertEqual(test_instance.properties, 'SomeHook')

        self.fake_client.describe_lifecycle_hooks.assert_called_with(
            LifecycleHookNames=['hook_id']
        )

    def test_AutoscalingLifecycleHook_status(self):
        test_instance = lifecycle_hook.AutoscalingLifecycleHook(
            "ctx_node", resource_id='hook_id', client=self.fake_client,
            logger=None
        )

        self.assertEqual(test_instance.status, None)

    def test_AutoscalingLifecycleHook_status_NotEmpty(self):
        self.fake_client.describe_lifecycle_hooks = MagicMock(
            return_value={'LifecycleHooks': ['SomeHook']}
        )

        test_instance = lifecycle_hook.AutoscalingLifecycleHook(
            "ctx_node", resource_id='hook_id', client=self.fake_client,
            logger=None
        )

        self.assertEqual(test_instance.status, None)


if __name__ == '__main__':
    unittest.main()

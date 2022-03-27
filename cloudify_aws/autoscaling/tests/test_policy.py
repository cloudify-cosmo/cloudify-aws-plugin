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
from cloudify_aws.autoscaling.resources import policy
from cloudify_aws.common.tests.test_base import TestBase, CLIENT_CONFIG
from cloudify_aws.common.tests.test_base import DELETE_RESPONSE


# Constants
POLICY_TH = ['cloudify.nodes.Root',
             'cloudify.nodes.aws.autoscaling.Policy']

NODE_PROPERTIES = {
    'use_external_resource': False,
    'resource_config': {
        'kwargs': {
            'PolicyName': 'test-autoscaling2',
            'PolicyType': 'SimpleScaling',
            'AdjustmentType': 'ExactCapacity',
            'ScalingAdjustment': '1'
        }
    },
    'client_config': CLIENT_CONFIG
}

RUNTIME_PROPERTIES_AFTER_CREATE = {
    'aws_resource_arn': 'arn_id',
    'resource_config': {},
    'aws_resource_id': 'test-autoscaling2',
    'AutoScalingGroupName': 'group_id'
}


class TestAutoscalingPolicy(TestBase):

    def setUp(self):
        super(TestAutoscalingPolicy, self).setUp()

        self.fake_boto, self.fake_client = self.fake_boto_client('autoscaling')

        self.mock_patch = patch('boto3.client', self.fake_boto)
        self.mock_patch.start()

    def tearDown(self):
        self.mock_patch.stop()
        self.fake_boto = None
        self.fake_client = None

        super(TestAutoscalingPolicy, self).tearDown()

    def _prepare_context(self, runtime_prop=None):
        mock_group = MagicMock()
        mock_group.type_hierarchy = 'cloudify.relationships.depends_on'
        mock_group.target.instance.runtime_properties = {
            'aws_resource_id': 'group_id',
            'resource_id': 'group_name_id'
        }
        mock_group.target.node.properties = {}
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
            type_hierarchy=POLICY_TH,
            test_relationships=[mock_group]
        )

        current_ctx.set(_ctx)
        return _ctx

    def test_prepare(self):
        self._prepare_check(
            type_hierarchy=POLICY_TH,
            type_name='autoscaling',
            type_class=policy
        )

    def test_create(self):
        _ctx = self._prepare_context()

        self.fake_client.put_scaling_policy = MagicMock(
            return_value={
                'PolicyARN': 'arn_id'
            }
        )

        policy.create(ctx=_ctx, resource_config=None, iface=None, params=None)

        self.fake_boto.assert_called_with('autoscaling', **CLIENT_CONFIG)

        self.fake_client.put_scaling_policy.assert_called_with(
            AdjustmentType='ExactCapacity',
            AutoScalingGroupName='group_id',
            PolicyName='test-autoscaling2',
            PolicyType='SimpleScaling',
            ScalingAdjustment='1'
        )

        self.assertEqual(
            _ctx.instance.runtime_properties,
            RUNTIME_PROPERTIES_AFTER_CREATE
        )

    def test_delete(self):
        _ctx = self._prepare_context(RUNTIME_PROPERTIES_AFTER_CREATE)

        self.fake_client.delete_policy = self.mock_return(DELETE_RESPONSE)

        policy.delete(ctx=_ctx, resource_config={}, iface=None)

        self.fake_boto.assert_called_with('autoscaling', **CLIENT_CONFIG)

        self.fake_client.delete_policy.assert_called_with(
            AutoScalingGroupName='group_id', PolicyName='test-autoscaling2'
        )

        self.assertEqual(
            _ctx.instance.runtime_properties,
            RUNTIME_PROPERTIES_AFTER_CREATE
        )

    def test_create_raises_UnknownServiceError(self):
        self._prepare_create_raises_UnknownServiceError(
            type_hierarchy=POLICY_TH,
            type_name='autoscaling',
            type_class=policy
        )

    def test_AutoscalingPolicy_properties(self):
        test_instance = policy.AutoscalingPolicy(
            "ctx_node", resource_id='policy_id', client=self.fake_client,
            logger=None
        )

        self.assertEqual(test_instance.properties, None)

    def test_AutoscalingPolicy_properties_not_empty(self):
        test_instance = policy.AutoscalingPolicy(
            "ctx_node", resource_id='policy_id', client=self.fake_client,
            logger=None
        )

        self.fake_client.describe_policies = MagicMock(
            return_value={'ScalingPolicies': ['policy']}
        )

        self.assertEqual(test_instance.properties, 'policy')

        self.fake_client.describe_policies.assert_called_with(
            PolicyNames=['policy_id']
        )

    def test_AutoscalingPolicy_status(self):
        test_instance = policy.AutoscalingPolicy(
            "ctx_node", resource_id='policy_id', client=self.fake_client,
            logger=None
        )

        self.assertEqual(test_instance.status, None)

    def test_AutoscalingPolicy_status_NotEmpty(self):
        self.fake_client.describe_policies = MagicMock(
            return_value={'ScalingPolicies': ['policy']}
        )

        test_instance = policy.AutoscalingPolicy(
            "ctx_node", resource_id='policy_id', client=self.fake_client,
            logger=None
        )

        self.assertEqual(test_instance.status, None)


if __name__ == '__main__':
    unittest.main()

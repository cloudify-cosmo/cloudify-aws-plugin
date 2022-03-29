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
from cloudify_aws.common._compat import text_type
from cloudify.exceptions import OperationRetry

# Local imports
from cloudify_aws.common.tests.test_base import TestBase, CLIENT_CONFIG
from cloudify_aws.common.tests.test_base import DELETE_RESPONSE
from cloudify_aws.autoscaling.resources import autoscaling_group


# Constants
GROUP_TH = ['cloudify.nodes.Root',
            'cloudify.nodes.aws.autoscaling.Group']

NODE_PROPERTIES = {
    'use_external_resource': False,
    'resource_config': {
        'kwargs': {
            'AutoScalingGroupName': 'test-autoscaling1',
            'MinSize': '1',
            'MaxSize': '1',
            'DefaultCooldown': '300',
            'AvailabilityZones': ['aws_region']
        }
    },
    'client_config': CLIENT_CONFIG
}

RUNTIME_PROPERTIES_AFTER_CREATE = {
    'resource_config': {},
    'aws_resource_arn': 'scaling_arn',
    'aws_resource_id': 'test-autoscaling1'
}


class TestAutoscalingGroup(TestBase):

    def setUp(self):
        super(TestAutoscalingGroup, self).setUp()

        self.fake_boto, self.fake_client = self.fake_boto_client('autoscaling')

        self.mock_patch = patch('boto3.client', self.fake_boto)
        self.mock_patch.start()

    def tearDown(self):
        self.mock_patch.stop()
        self.fake_boto = None
        self.fake_client = None

        super(TestAutoscalingGroup, self).tearDown()

    def _prepare_context(self, runtime_prop=None, ctx_operation_name=None):
        mock_subnet = MagicMock()
        mock_subnet.type_hierarchy = 'cloudify.relationships.depends_on'
        mock_subnet.target.instance.runtime_properties = {
            'aws_resource_id': 'aws_net_id'
        }
        mock_subnet.target.node.type_hierarchy = [
            'cloudify.nodes.Root',
            'cloudify.nodes.aws.ec2.Subnet'
        ]

        mock_config = MagicMock()
        mock_config.type_hierarchy = 'cloudify.relationships.depends_on'
        mock_config.target.instance.runtime_properties = {
            'aws_resource_id': 'aws_id'
        }
        mock_config.target.node.type_hierarchy = [
            'cloudify.nodes.Root',
            'cloudify.nodes.aws.autoscaling.LaunchConfiguration'
        ]

        _ctx = self.get_mock_ctx(
            'test_create',
            test_properties=NODE_PROPERTIES,
            test_runtime_properties=runtime_prop if runtime_prop else {
                'resource_config': {}
            },
            type_hierarchy=GROUP_TH,
            test_relationships=[mock_config, mock_subnet],
            ctx_operation_name=ctx_operation_name
        )

        current_ctx.set(_ctx)
        return _ctx

    def test_prepare(self):
        self._prepare_check(
            type_hierarchy=GROUP_TH,
            type_name='autoscaling',
            type_class=autoscaling_group
        )

    def test_create_raises_UnknownServiceError(self):
        self._prepare_create_raises_UnknownServiceError(
            type_hierarchy=GROUP_TH,
            type_name='autoscaling',
            type_class=autoscaling_group
        )

    def test_create(self):
        _ctx = self._prepare_context()

        self.fake_client.describe_auto_scaling_groups = MagicMock(
            return_value={
                'AutoScalingGroups': [{
                    'AutoScalingGroupName': 'test-autoscaling1',
                    'AutoScalingGroupARN': 'scaling_arn'
                }]
            }
        )

        self.fake_client.create_auto_scaling_group = MagicMock(
            return_value={
                'AutoScalingGroupName': 'test-autoscaling1',
                'AutoScalingGroupARN': 'scaling_arn'
            }
        )

        autoscaling_group.create(
            ctx=_ctx,
            resource_config=None,
            iface=None,
            params=None)

        self.fake_boto.assert_called_with('autoscaling', **CLIENT_CONFIG)

        self.fake_client.create_auto_scaling_group.assert_called_with(
            AutoScalingGroupName='test-autoscaling1',
            AvailabilityZones=['aws_region'],
            DefaultCooldown='300',
            LaunchConfigurationName='aws_id',
            MaxSize='1',
            MinSize='1',
            VPCZoneIdentifier='aws_net_id'
        )

        # This is just because I'm not interested in the content
        # of remote_configuration right now.
        # If it doesn't exist, this test will fail, and that's good.
        _ctx.instance.runtime_properties.pop('remote_configuration')
        self.assertEqual(
            _ctx.instance.runtime_properties,
            RUNTIME_PROPERTIES_AFTER_CREATE
        )

    def test_delete(self):
        _ctx = self._prepare_context(RUNTIME_PROPERTIES_AFTER_CREATE)

        self.fake_client.delete_auto_scaling_group = self.mock_return(
            DELETE_RESPONSE)

        self.fake_client.detach_instances = self.mock_return(DELETE_RESPONSE)

        self.fake_client.describe_auto_scaling_groups = self.mock_return(
            {
                'AutoScalingGroups': [{
                    'AutoScalingGroupName': 'test-autoscaling1',
                    'AutoScalingGroupARN': 'scaling_arn',
                    'Instances': [{
                        'InstanceId': 'inst_one'
                    }]
                }]
            }
        )

        autoscaling_group.delete(ctx=_ctx, resource_config={}, iface=None)

        self.fake_boto.assert_called_with('autoscaling', **CLIENT_CONFIG)

        self.fake_client.delete_auto_scaling_group.assert_called_with(
            AutoScalingGroupName='test-autoscaling1'
        )
        self.fake_client.describe_auto_scaling_groups.assert_called_with(
            AutoScalingGroupNames=['test-autoscaling1']
        )
        self.fake_client.detach_instances.assert_called_with(
            AutoScalingGroupName='test-autoscaling1',
            InstanceIds=['inst_one'],
            ShouldDecrementDesiredCapacity=False
        )

        # This is just because I'm not interested in the content
        # of remote_configuration right now.
        # If it doesn't exist, this test will fail, and that's good.
        _ctx.instance.runtime_properties.pop('remote_configuration')
        self.assertEqual(
            _ctx.instance.runtime_properties, {
                'resource_config': {},
                'aws_resource_arn': 'scaling_arn',
                'aws_resource_id': 'test-autoscaling1'
            }
        )

    def test_stop(self):
        _ctx = self._prepare_context(RUNTIME_PROPERTIES_AFTER_CREATE,
                                     'cloudify.interfaces.lifecycle.stop')

        self.fake_client.update_auto_scaling_group = self.mock_return(
            DELETE_RESPONSE)
        self.fake_client.describe_auto_scaling_groups = MagicMock(
            return_value={'AutoScalingGroups': [{'Status': 'Created',
                                                 'MinSize': 0,
                                                 'MaxSize': 0,
                                                 'DesiredCapacity': 0,
                                                 'Instances': []}]}
        )

        self.fake_client.detach_instances = self.mock_return(DELETE_RESPONSE)
        iface = MagicMock
        iface.status = self.fake_client.describe_auto_scaling_groups['AutoScalingGroups'][0]['Status']  # noqa
        # we don't have things for remove
        autoscaling_group.stop(ctx=_ctx, resource_config=None,
                               iface=None)

        self.fake_boto.assert_called_with('autoscaling', **CLIENT_CONFIG)
        self.fake_client.update_auto_scaling_group.assert_not_called()
        self.fake_client.describe_auto_scaling_groups.assert_called_with(
            AutoScalingGroupNames=['test-autoscaling1'])

        # have some alive instances
        self.fake_client.describe_auto_scaling_groups = MagicMock(
            return_value={'AutoScalingGroups': [{'Status': 'Created',
                                                 'MinSize': 0,
                                                 'MaxSize': 0,
                                                 'DesiredCapacity': 1,
                                                 'Instances': [{}]}]}
        )
        with self.assertRaises(OperationRetry) as error:
            autoscaling_group.stop(ctx=_ctx, resource_config=None,
                                   iface=None)
        self.assertEqual(
            text_type(error.exception),
            'Autoscaling Group ID# "test-autoscaling1" is deleting associated '
            'instances.'
        )

        self.fake_boto.assert_called_with('autoscaling', **CLIENT_CONFIG)
        self.fake_client.update_auto_scaling_group.assert_not_called()
        self.fake_client.describe_auto_scaling_groups.assert_called_with(
            AutoScalingGroupNames=['test-autoscaling1'])

        # we have some scale staff
        self.fake_client.describe_auto_scaling_groups = MagicMock(
            return_value={'AutoScalingGroups': [{'Status': 'Created',
                                                 'MinSize': 1,
                                                 'MaxSize': 1,
                                                 'DesiredCapacity': 1,
                                                 'Instances': [{}]}]}
        )
        with self.assertRaises(OperationRetry) as error:
            autoscaling_group.stop(ctx=_ctx, resource_config=None,
                                   iface=None)
        self.assertEqual(
            text_type(error.exception),
            'Updating Autoscaling Group ID# "test-autoscaling1" parameters '
            'before deletion.'
        )

        self.fake_boto.assert_called_with('autoscaling', **CLIENT_CONFIG)
        self.fake_client.update_auto_scaling_group.assert_called_with(
            AutoScalingGroupName='test-autoscaling1', DesiredCapacity=0,
            MaxSize=0, MinSize=0)
        self.fake_client.describe_auto_scaling_groups.assert_called_with(
            AutoScalingGroupNames=['test-autoscaling1'])

    def test_AutoscalingGroup_properties(self):
        test_instance = autoscaling_group.AutoscalingGroup(
            "ctx_node", resource_id='group_id', client=self.fake_client,
            logger=None
        )

        self.assertEqual(test_instance.properties, None)

    def test_AutoscalingGroup_properties_not_empty(self):
        test_instance = autoscaling_group.AutoscalingGroup(
            "ctx_node", resource_id='group_id', client=self.fake_client,
            logger=None
        )

        self.fake_client.describe_auto_scaling_groups = MagicMock(
            return_value={
                'AutoScalingGroups': [{
                    'AutoScalingGroupName': 'test-autoscaling1',
                    'AutoScalingGroupARN': 'scaling_arn'
                }]
            }
        )

        self.assertEqual(test_instance.properties, {
            'AutoScalingGroupName': 'test-autoscaling1',
            'AutoScalingGroupARN': 'scaling_arn'
        })

        self.fake_client.describe_auto_scaling_groups.assert_called_with(
            AutoScalingGroupNames=['group_id']
        )

    def test_AutoscalingGroup_status(self):
        test_instance = autoscaling_group.AutoscalingGroup(
            "ctx_node", resource_id='group_id', client=self.fake_client,
            logger=None
        )

        self.assertEqual(test_instance.status, None)

    def test_AutoscalingGroup_status_NotEmpty(self):
        test_instance = autoscaling_group.AutoscalingGroup(
            "ctx_node", resource_id='group_id', client=self.fake_client,
            logger=None
        )
        self.fake_client.describe_auto_scaling_groups = MagicMock(
            return_value={'AutoScalingGroups': [{'Status': 'Created'}]}
        )

        self.assertEqual(test_instance.status, 'Created')

    def test_AutoscalingGroup_remove_instances(self):
        test_instance = autoscaling_group.AutoscalingGroup(
            "ctx_node", resource_id='group_id', client=self.fake_client,
            logger=None
        )
        self.fake_client.detach_instances = self._gen_client_error(
            "detach_instances"
        )

        self.assertEqual(test_instance.remove_instances({}), None)


if __name__ == '__main__':
    unittest.main()

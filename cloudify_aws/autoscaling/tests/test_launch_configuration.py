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
from cloudify_aws.common.tests.test_base import TestBase, CLIENT_CONFIG
from cloudify_aws.common.tests.test_base import DELETE_RESPONSE
from cloudify_aws.autoscaling.resources import launch_configuration


# Constants
LAUNCH_CONFIGURATION_TH = [
    'cloudify.nodes.Root',
    'cloudify.nodes.aws.autoscaling.LaunchConfiguration'
]

NODE_PROPERTIES = {
    'use_external_resource': False,
    'resource_config': {
        'kwargs': {
            'LaunchConfigurationName': 'test-lauchconfig3'
        }
    },
    'client_config': CLIENT_CONFIG
}

RUNTIME_PROPERTIES_AFTER_CREATE = {
    'aws_resource_arn': 'arn_id',
    'resource_config': {},
    'aws_resource_id': 'test-lauchconfig3'
}

RUNTIME_PROPERTIES_AFTER_CREATE = {
    'aws_resource_arn': 'arn_id',
    'resource_config': {},
    'aws_resource_id': 'test-lauchconfig3'
}


class TestAutoscalingLaunchConfiguration(TestBase):

    def setUp(self):
        super(TestAutoscalingLaunchConfiguration, self).setUp()

        self.fake_boto, self.fake_client = self.fake_boto_client('autoscaling')

        self.mock_patch = patch('boto3.client', self.fake_boto)
        self.mock_patch.start()

    def tearDown(self):
        self.mock_patch.stop()
        self.fake_boto = None
        self.fake_client = None

        super(TestAutoscalingLaunchConfiguration, self).tearDown()

    def _prepare_context(self, runtime_prop=None):
        mock_instance = MagicMock()
        mock_instance.type_hierarchy = 'cloudify.relationships.depends_on'
        mock_instance.target.instance.runtime_properties = {
            'aws_resource_id': 'aws_id'
        }
        mock_instance.target.node.properties = {
            'instance_type': 'depricated'
        }
        mock_instance.target.node.type_hierarchy = [
            'cloudify.nodes.Root',
            'cloudify.aws.nodes.Instance'
        ]

        mock_group = MagicMock()
        mock_group.type_hierarchy = 'cloudify.relationships.depends_on'
        mock_group.target.instance.runtime_properties = {
            'aws_resource_id': 'group_id'
        }
        mock_group.target.node.properties = {}
        mock_group.target.node.type_hierarchy = [
            'cloudify.nodes.Root',
            'cloudify.aws.nodes.SecurityGroup'
        ]

        _ctx = self.get_mock_ctx(
            'test_create',
            test_properties=NODE_PROPERTIES,
            test_runtime_properties=runtime_prop if runtime_prop else {
                'resource_config': {}
            },
            type_hierarchy=LAUNCH_CONFIGURATION_TH,
            test_relationships=[mock_instance, mock_group]
        )

        current_ctx.set(_ctx)
        return _ctx

    def test_prepare(self):
        self._prepare_check(
            type_hierarchy=LAUNCH_CONFIGURATION_TH,
            type_name='autoscaling',
            type_class=launch_configuration
        )

    def test_create(self):
        _ctx = self._prepare_context()

        self.fake_client.create_launch_configuration = MagicMock(
            return_value={
                'LaunchConfigurationARN': 'arn_id'
            }
        )
        self.fake_client.describe_launch_configurations = MagicMock(
            return_value={
                'LaunchConfigurations': [{
                    'LaunchConfigurationARN': 'arn_id'
                }]
            }
        )

        launch_configuration.create(ctx=_ctx, resource_config=None,
                                    iface=None, params=None)

        self.fake_boto.assert_called_with('autoscaling', **CLIENT_CONFIG)

        self.fake_client.create_launch_configuration.assert_called_with(
            InstanceId='aws_id',
            InstanceType='depricated',
            SecurityGroups=['group_id'],
            LaunchConfigurationName='test-lauchconfig3'
        )

        # This is just because I'm not interested in the content
        # of remote_configuration right now.
        # If it doesn't exist, this test will fail, and that's good.
        _ctx.instance.runtime_properties.pop('remote_configuration')
        self.assertEqual(
            _ctx.instance.runtime_properties,
            RUNTIME_PROPERTIES_AFTER_CREATE
        )

    def test_create_raises_UnknownServiceError(self):
        self._prepare_create_raises_UnknownServiceError(
            type_hierarchy=LAUNCH_CONFIGURATION_TH,
            type_name='autoscaling',
            type_class=launch_configuration
        )

    def test_delete(self):
        _ctx = self._prepare_context(RUNTIME_PROPERTIES_AFTER_CREATE)

        self.fake_client.delete_launch_configuration = self.mock_return(
            DELETE_RESPONSE)

        launch_configuration.delete(ctx=_ctx, resource_config={},
                                    iface=None)

        self.fake_boto.assert_called_with('autoscaling', **CLIENT_CONFIG)

        self.fake_client.delete_launch_configuration.assert_called_with(
            LaunchConfigurationName='test-lauchconfig3'
        )

        self.assertEqual(
            _ctx.instance.runtime_properties,
            RUNTIME_PROPERTIES_AFTER_CREATE
        )

    def test_AutoscalingLaunchConfiguration_properties(self):
        test_instance = launch_configuration.AutoscalingLaunchConfiguration(
            "ctx_node", resource_id='launch_id', client=self.fake_client,
            logger=None
        )

        self.assertEqual(test_instance.properties, None)

    def test_AutoscalingLaunchConfiguration_properties_not_empty(self):
        test_instance = launch_configuration.AutoscalingLaunchConfiguration(
            "ctx_node", resource_id='launch_id', client=self.fake_client,
            logger=None
        )

        self.fake_client.describe_launch_configurations = MagicMock(
            return_value={'LaunchConfigurations': ['launch_configuration']}
        )

        self.assertEqual(test_instance.properties, 'launch_configuration')

        self.fake_client.describe_launch_configurations.assert_called_with(
            LaunchConfigurationNames=['launch_id']
        )

    def test_AutoscalingLaunchConfiguration_status(self):
        test_instance = launch_configuration.AutoscalingLaunchConfiguration(
            "ctx_node", resource_id='launch_id', client=self.fake_client,
            logger=None
        )

        self.assertEqual(test_instance.status, None)

    def test_AutoscalingLaunchConfiguration_status_NotEmpty(self):
        test_instance = launch_configuration.AutoscalingLaunchConfiguration(
            "ctx_node", resource_id='launch_id', client=self.fake_client,
            logger=None
        )

        self.fake_client.describe_launch_configurations = MagicMock(
            return_value={'LaunchConfigurations': ['launch_configuration']}
        )

        self.assertEqual(test_instance.status, None)


if __name__ == '__main__':
    unittest.main()

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
from cloudify_aws.cloudwatch.resources import alarm
from cloudify_aws.common.tests.test_base import TestBase, CLIENT_CONFIG
from cloudify_aws.common.tests.test_base import DELETE_RESPONSE


# Constants
ALARM_TH = ['cloudify.nodes.Root',
            'cloudify.nodes.aws.cloudwatch.Alarm']

NODE_PROPERTIES = {
    'use_external_resource': False,
    'resource_config': {
        'kwargs': {
            'AlarmName': 'test-cloudwatch1',
            'ActionsEnabled': 'true',
            'AlarmActions': [
                'arn:aws:automate:region:ec2:terminate'
            ],
            'ComparisonOperator': 'LessThanThreshold',
            'Statistic': 'Minimum',
            'MetricName': 'CPUUtilization',
            'Namespace': 'AWS/EC2',
            'Period': '60',
            'EvaluationPeriods': '5',
            'Threshold': '60'
        }
    },
    'client_config': CLIENT_CONFIG
}

RUNTIME_PROPERTIES = {
    'aws_resource_id': None,
    'resource_config': {}
}

RUNTIME_PROPERTIES_AFTER_CREATE = {
    'aws_resource_id': 'test-cloudwatch1',
    'resource_config': {}
}


class TestCloudwatchAlarm(TestBase):

    def setUp(self):
        super(TestCloudwatchAlarm, self).setUp()

        self.fake_boto, self.fake_client = self.fake_boto_client('cloudwatch')

        self.mock_patch = patch('boto3.client', self.fake_boto)
        self.mock_patch.start()

    def tearDown(self):
        self.mock_patch.stop()
        self.fake_boto = None
        self.fake_client = None

        super(TestCloudwatchAlarm, self).tearDown()

    def test_prepare(self):
        self._prepare_check(
            type_hierarchy=ALARM_TH,
            type_name='cloudwatch',
            type_class=alarm
        )

    def test_create_raises_UnknownServiceError(self):
        self._prepare_create_raises_UnknownServiceError(
            type_hierarchy=ALARM_TH,
            type_name='cloudwatch',
            type_class=alarm
        )

    def test_create(self):
        _ctx = self.get_mock_ctx(
            'test_create',
            test_properties=NODE_PROPERTIES,
            test_runtime_properties=RUNTIME_PROPERTIES,
            type_hierarchy=ALARM_TH
        )

        current_ctx.set(_ctx)

        self.fake_client.put_metric_alarm = MagicMock(return_value={
            'metric': 'alarm'
        })

        alarm.create(ctx=_ctx, resource_config=None, iface=None)

        self.fake_boto.assert_called_with('cloudwatch', **CLIENT_CONFIG)

        self.fake_client.put_metric_alarm.assert_called_with(
            ActionsEnabled='true',
            AlarmActions=['arn:aws:automate:region:ec2:terminate'],
            AlarmName='test-cloudwatch1',
            ComparisonOperator='LessThanThreshold',
            EvaluationPeriods='5',
            MetricName='CPUUtilization',
            Namespace='AWS/EC2',
            Period='60',
            Statistic='Minimum',
            Threshold='60'
        )

        self.assertEqual(
            _ctx.instance.runtime_properties,
            RUNTIME_PROPERTIES_AFTER_CREATE
        )

    def test_delete(self):
        _ctx = self.get_mock_ctx(
            'test_delete',
            test_properties=NODE_PROPERTIES,
            test_runtime_properties=RUNTIME_PROPERTIES_AFTER_CREATE,
            type_hierarchy=ALARM_TH
        )

        current_ctx.set(_ctx)

        self.fake_client.delete_alarms = self.mock_return(DELETE_RESPONSE)

        alarm.delete(ctx=_ctx, resource_config={}, iface=None)

        self.fake_boto.assert_called_with('cloudwatch', **CLIENT_CONFIG)

        self.fake_client.delete_alarms.assert_called_with(
            AlarmNames=['test-cloudwatch1']
        )

        self.assertEqual(
            _ctx.instance.runtime_properties,
            {
                'aws_resource_id': 'test-cloudwatch1',
                'resource_config': {}
            }
        )

    def test_CloudwatchAlarmClass_properties(self):
        self.fake_client.describe_alarms = MagicMock(return_value={
            'MetricAlarms': ['FirstAlarm']
        })

        test_instance = alarm.CloudwatchAlarm("ctx_node",
                                              resource_id='alarm_id',
                                              client=self.fake_client,
                                              logger=None)

        self.assertEqual(test_instance.properties, 'FirstAlarm')

        self.fake_client.describe_alarms.assert_called_with(
            AlarmNames=['alarm_id']
        )

    def test_CloudwatchAlarmClass_properties_empty(self):
        test_instance = alarm.CloudwatchAlarm("ctx_node",
                                              resource_id='alarm_id',
                                              client=self.fake_client,
                                              logger=None)

        self.assertEqual(test_instance.properties, None)

        self.fake_client.describe_alarms.assert_called_with(
            AlarmNames=['alarm_id']
        )

    def test_CloudwatchAlarmClass_status(self):
        self.fake_client.describe_alarms = MagicMock(return_value={
            'MetricAlarms': ['FirstAlarm']
        })

        test_instance = alarm.CloudwatchAlarm("ctx_node",
                                              resource_id='alarm_id',
                                              client=self.fake_client,
                                              logger=None)

        self.assertEqual(test_instance.status, None)

    def test_CloudwatchAlarmClass_status_empty(self):
        test_instance = alarm.CloudwatchAlarm("ctx_node",
                                              resource_id='alarm_id',
                                              client=self.fake_client,
                                              logger=None)

        self.assertEqual(test_instance.status, None)


if __name__ == '__main__':
    unittest.main()

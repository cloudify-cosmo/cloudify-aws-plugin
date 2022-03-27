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
from cloudify_aws.cloudwatch.resources import rule
from cloudify_aws.common.tests.test_base import TestBase, CLIENT_CONFIG
from cloudify_aws.common.tests.test_base import DELETE_RESPONSE


# Constants
RULE_TH = ['cloudify.nodes.Root',
           'cloudify.nodes.aws.cloudwatch.Rule']

EVENT_PATTERN_STR = (
    '{"detail-type": ["AWS API Call via CloudTrail"], "detail": {"eventSo' +
    'urce": ["autoscaling.amazonaws.com"]}}'
)

NODE_PROPERTIES = {
    'use_external_resource': False,
    'resource_config': {
        'kwargs': {
            'Name': 'test-cloudwatch1',
            'ScheduleExpression': 'rate(5 minutes)',
            'EventPattern': EVENT_PATTERN_STR,
            'State': 'ENABLED'
        }
    },
    'client_config': CLIENT_CONFIG
}

RUNTIME_PROPERTIES = {
    'aws_resource_id': None,
    'resource_config': {}
}

RUNTIME_PROPERTIES_AFTER_CREATE = {
    'aws_resource_arn': 'aws_rule_arn',
    'aws_resource_id': 'test-cloudwatch1',
    'resource_config': {}
}


class TestCloudwatchEventsRule(TestBase):

    def setUp(self):
        super(TestCloudwatchEventsRule, self).setUp()

        self.fake_boto, self.fake_client = self.fake_boto_client('events')

        self.mock_patch = patch('boto3.client', self.fake_boto)
        self.mock_patch.start()

    def tearDown(self):
        self.mock_patch.stop()
        self.fake_boto = None
        self.fake_client = None

        super(TestCloudwatchEventsRule, self).tearDown()

    def test_prepare(self):
        self._prepare_check(
            type_hierarchy=RULE_TH,
            type_name='events',
            type_class=rule
        )

    def test_create(self):
        _ctx = self.get_mock_ctx(
            'test_create',
            test_properties=NODE_PROPERTIES,
            test_runtime_properties=RUNTIME_PROPERTIES,
            type_hierarchy=RULE_TH
        )

        current_ctx.set(_ctx)

        self.fake_client.put_rule = MagicMock(return_value={
            'RuleArn': 'aws_rule_arn'
        })

        rule.create(ctx=_ctx, resource_config=None, iface=None)

        self.fake_boto.assert_called_with('events', **CLIENT_CONFIG)

        self.fake_client.put_rule.assert_called_with(
            EventPattern=EVENT_PATTERN_STR,
            Name='test-cloudwatch1',
            ScheduleExpression='rate(5 minutes)',
            State='ENABLED'
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
            type_hierarchy=RULE_TH
        )

        current_ctx.set(_ctx)

        self.fake_client.delete_rule = self.mock_return(DELETE_RESPONSE)

        rule.delete(ctx=_ctx, resource_config={}, iface=None)

        self.fake_boto.assert_called_with('events', **CLIENT_CONFIG)

        self.fake_client.delete_rule.assert_called_with(
            Name='test-cloudwatch1'
        )

        self.assertEqual(
            _ctx.instance.runtime_properties,
            {
                'aws_resource_arn': 'aws_rule_arn',
                'aws_resource_id': 'test-cloudwatch1',
                'resource_config': {}
            }
        )

    def test_CloudwatchEventsRuleClass_properties(self):
        self.fake_client.describe_rule = MagicMock(return_value=['Event'])

        test_instance = rule.CloudwatchEventsRule("ctx_node",
                                                  resource_id='rule_id',
                                                  client=self.fake_client,
                                                  logger=None)

        self.assertEqual(test_instance.properties, 'Event')

        self.fake_client.describe_rule.assert_called_with(
            Name=['rule_id']
        )

    def test_CloudwatchEventsRuleClass_properties_empty(self):
        test_instance = rule.CloudwatchEventsRule("ctx_node",
                                                  resource_id='rule_id',
                                                  client=self.fake_client,
                                                  logger=None)

        self.assertEqual(test_instance.properties, None)

        self.fake_client.describe_rule.assert_called_with(
            Name=['rule_id']
        )

    def test_CloudwatchEventsRuleClass_status(self):
        self.fake_client.describe_rule = MagicMock(return_value=['Event'])

        test_instance = rule.CloudwatchEventsRule("ctx_node",
                                                  resource_id='rule_id',
                                                  client=self.fake_client,
                                                  logger=None)

        self.assertEqual(test_instance.status, None)

    def test_CloudwatchEventsRuleClass_status_empty(self):
        test_instance = rule.CloudwatchEventsRule("ctx_node",
                                                  resource_id='rule_id',
                                                  client=self.fake_client,
                                                  logger=None)

        self.assertEqual(test_instance.status, None)


if __name__ == '__main__':
    unittest.main()

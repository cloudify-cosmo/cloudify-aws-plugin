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

# Local imports
from cloudify_aws.common._compat import reload_module
from cloudify_aws.common.constants import EXTERNAL_RESOURCE_ARN
from cloudify_aws.elb.resources import rule
from cloudify_aws.common.tests.test_base import (
    TestBase,
    mock_decorator
)
from cloudify_aws.elb.resources.rule import (
    ELBRule,
    LISTENER_ARN,
    RULE_ARN,
    TARGET_ARN
)

PATCH_PREFIX = 'cloudify_aws.elb.resources.rule.'


class TestELBRule(TestBase):

    def setUp(self):
        super(TestELBRule, self).setUp()
        self.rule = ELBRule("ctx_node", resource_id=True,
                            client=MagicMock(), logger=None)
        mock1 = patch('cloudify_aws.common.decorators.aws_resource',
                      mock_decorator)
        mock1.start()
        reload_module(rule)

    def test_class_properties(self):
        effect = self.get_client_error_exception(name='S3 ELB')
        self.rule.client = self.make_client_function('describe_rules',
                                                     side_effect=effect)
        res = self.rule.properties
        self.assertEqual(res, {})

        value = []
        self.rule.client = self.make_client_function('describe_rules',
                                                     return_value=value)
        res = self.rule.properties
        self.assertEqual(res, {})

        value = {'Rules': [{'RuleArn': True}]}
        self.rule.resource_id = True
        self.rule.client = self.make_client_function('describe_rules',
                                                     return_value=value)
        res = self.rule.properties
        self.assertEqual(res, {'RuleArn': True})

    def test_class_status(self):
        value = []
        self.rule.client = self.make_client_function('describe_rules',
                                                     return_value=value)
        res = self.rule.status
        self.assertEqual(res, {})

        value = {'Rules': [{'RuleArn': True, 'State': {'Code': 'ok'}}]}
        self.rule.resource_id = True
        self.rule.client = self.make_client_function('describe_rules',
                                                     return_value=value)
        res = self.rule.status
        self.assertEqual(res, {'RuleArn': True, 'State': {'Code': 'ok'}})

    def test_class_create(self):
        value = {'Rules': [{RULE_ARN: 'id'}]}
        self.rule.client = self.make_client_function('create_rule',
                                                     return_value=value)
        res = self.rule.create(value)['Rules'][0][RULE_ARN]
        self.assertEqual(res, 'id')

    def test_class_delete(self):
        params = {}
        self.rule.client = self.make_client_function('delete_rule')
        self.rule.delete(params)
        self.assertTrue(self.rule.client.delete_rule.called)

        params = {LISTENER_ARN: 'id'}
        self.rule.delete(params)
        self.assertTrue(self.rule.client.delete_rule.called)

    def test_prepare(self):
        ctx = self.get_mock_ctx("ELB")
        rule.prepare(ctx, 'config')
        self.assertEqual(ctx.instance.runtime_properties['resource_config'],
                         'config')

    def test_create(self):
        ctx = self.get_mock_ctx("ELB", {}, {'resource_config': {}})
        ctx_target = self.get_mock_relationship_ctx(
            "elb",
            test_target=self.get_mock_ctx("elb", {},
                                          {EXTERNAL_RESOURCE_ARN: 'ext_id'}))
        iface = MagicMock()
        config = {LISTENER_ARN: 'listener', 'Actions': [{TARGET_ARN: ''}]}
        with patch(PATCH_PREFIX + 'utils') as utils:
            utils.find_rel_by_node_type = self.mock_return(ctx_target)
            rule.create(ctx, iface, config)
            self.assertTrue(iface.create.called)
            self.assertEqual(
                config,
                {'Actions': [{'TargetGroupArn': ''}],
                 'ListenerArn': 'listener'})

        config = {'Actions': [{TARGET_ARN: 'elb'}]}
        with patch(PATCH_PREFIX + 'utils') as utils:
            utils.find_rels_by_node_type = self.mock_return([ctx_target])
            rule.create(ctx, iface, config)
            self.assertTrue(iface.create.called)
            self.assertEqual(config, {
                'Actions': [{'TargetGroupArn': 'ext_id'}],
                'ListenerArn': 'ext_id'})

    def test_delete(self):
        iface = MagicMock()
        rule.delete(iface, {})
        self.assertTrue(iface.delete.called)


if __name__ == '__main__':
    unittest.main()

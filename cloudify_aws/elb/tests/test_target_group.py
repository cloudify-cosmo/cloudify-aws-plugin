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

from cloudify_aws.common._compat import reload_module
from cloudify_aws.common.tests.test_base import (
    TestBase,
    mock_decorator
)

# Local imports
from cloudify_aws.elb.resources.target_group import (
    ELBTargetGroup,
    VPC_ID,
    TARGETGROUP_ARN,
    GRP_ATTR
)
from cloudify_aws.common.constants import EXTERNAL_RESOURCE_ID
from cloudify_aws.elb.resources import target_group

PATCH_PREFIX = 'cloudify_aws.elb.resources.target_group.'


class TestELBTargetGroup(TestBase):

    def setUp(self):
        super(TestELBTargetGroup, self).setUp()
        self.target_group = ELBTargetGroup("ctx_node", resource_id='test',
                                           client=MagicMock(), logger=None)
        mock1 = patch('cloudify_aws.common.decorators.aws_resource',
                      mock_decorator)
        mock2 = patch('cloudify_aws.common.decorators.wait_for_status',
                      mock_decorator)
        mock3 = patch('cloudify_aws.common.decorators.wait_for_delete',
                      mock_decorator)
        mock1.start()
        mock2.start()
        mock3.start()
        reload_module(target_group)

    def test_class_properties(self):
        effect = self.get_client_error_exception(name='S3 ELB')
        self.target_group.client = self.make_client_function(
            'describe_target_groups',
            side_effect=effect)
        res = self.target_group.properties
        self.assertIsNone(res)

        value = []
        self.target_group.client = self.make_client_function(
            'describe_target_groups',
            return_value=value)
        res = self.target_group.properties
        self.assertEqual(res, {})

        value = {'TargetGroups': [{'TargetGroupArn': 'test'}]}
        self.target_group.client = self.make_client_function(
            'describe_target_groups',
            return_value=value)
        res = self.target_group.properties
        self.assertEqual(res, {'TargetGroupArn': 'test'})

    def test_class_status(self):
        value = []
        self.target_group.client = self.make_client_function(
            'describe_target_groups',
            return_value=value)
        res = self.target_group.status
        self.assertIsNone(res)

        value = {
            'TargetGroups': [
                {'TargetGroupArn': 'test',
                 'State': {'Code': 'ok'}
                 }
            ]
        }
        self.target_group.client = self.make_client_function(
            'describe_target_groups',
            return_value=value)
        res = self.target_group.status
        self.assertEqual(res, 'ok')

    def test_class_create(self):
        value = {'TargetGroups': [{TARGETGROUP_ARN: 'arn'}]}
        self.target_group.client = self.make_client_function(
            'create_target_group',
            return_value={'TargetGroups': [{TARGETGROUP_ARN: 'arn'}]})
        arn = self.target_group.create(
            value)['TargetGroups'][0][TARGETGROUP_ARN]
        self.assertEqual(arn, 'arn')

    def test_class_delete(self):
        params = {}
        self.target_group.client = self.make_client_function(
            'delete_target_group')
        self.target_group.delete(params)
        self.assertTrue(self.target_group.client.delete_target_group.called)

    def test_class_modify_attributes(self):
        value = {GRP_ATTR: 'attr'}
        self.target_group.client = self.make_client_function(
            'modify_target_group_attributes',
            return_value=value)
        res = self.target_group.modify_attribute(value)
        self.assertEqual(res, 'attr')

    def test_prepare(self):
        ctx = self.get_mock_ctx("ELB")
        target_group.prepare(ctx, 'config')
        self.assertEqual(ctx.instance.runtime_properties['resource_config'],
                         'config')

    def test_create(self):
        ctx = self.get_mock_ctx("ELB", {}, {'resource_config': {}})
        ctx_target = self.get_mock_relationship_ctx(
            "elb",
            test_target=self.get_mock_ctx("elb", {},
                                          {EXTERNAL_RESOURCE_ID: 'ext_id'}))
        iface = MagicMock()
        config = {VPC_ID: 'vpc_id'}
        with patch(PATCH_PREFIX + 'utils') as utils:
            utils.find_rels_by_node_type = self.mock_return([ctx_target])
            target_group.create(ctx, iface, config)
            self.assertTrue(iface.create.called)

        config = {}
        with patch(PATCH_PREFIX + 'utils') as utils:
            utils.find_rels_by_node_type = self.mock_return([ctx_target])
            target_group.create(ctx, iface, config)
            self.assertTrue(iface.create.called)

    def test_delete(self):
        iface = MagicMock()
        target_group.delete(iface, {})
        self.assertTrue(iface.delete.called)

    # def test_modify(self):
        ctx = self.get_mock_ctx("ELB", {}, {'resource_config': {}})
        ctx_target = self.get_mock_relationship_ctx(
            "elb",
            test_target=self.get_mock_ctx("elb", {},
                                          {EXTERNAL_RESOURCE_ID: 'ext_id'}))
        iface = MagicMock()
        config = {TARGETGROUP_ARN: 'target_group'}
        with patch(PATCH_PREFIX + 'utils') as utils:
            utils.find_rels_by_node_type = self.mock_return([ctx_target])
            target_group.modify(ctx, iface, config)
            self.assertNotIn(
                GRP_ATTR,
                ctx.instance.runtime_properties['resource_config'])

        config = {TARGETGROUP_ARN: 'target_group', GRP_ATTR: [True]}
        with patch(PATCH_PREFIX + 'utils') as utils:
            utils.find_rels_by_node_type = self.mock_return([ctx_target])
            target_group.modify(ctx, iface, config)
            self.assertTrue(iface.modify_attribute.called)

        ctx = self.get_mock_ctx("ELB", {}, {'resource_config': {}})
        config = {GRP_ATTR: [True]}
        with patch(PATCH_PREFIX + 'utils') as utils:
            utils.find_rels_by_node_type = self.mock_return([ctx_target])
            target_group.modify(ctx, iface, config)
            self.assertTrue(iface.modify_attribute.called)


if __name__ == '__main__':
    unittest.main()

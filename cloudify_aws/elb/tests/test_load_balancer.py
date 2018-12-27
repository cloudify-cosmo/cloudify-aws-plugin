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
#    * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    * See the License for the specific language governing permissions and
#    * limitations under the License.

import unittest
from cloudify_aws.common.tests.test_base import TestBase, mock_decorator
from cloudify_aws.elb.resources.load_balancer import (ELBLoadBalancer,
                                                      LB_ARN,
                                                      RESOURCE_NAME,
                                                      LB_ATTR)
from cloudify_aws.common.constants import EXTERNAL_RESOURCE_ID
from mock import patch, MagicMock
from cloudify_aws.elb.resources import load_balancer

PATCH_PREFIX = 'cloudify_aws.elb.resources.load_balancer.'


class TestELBLoadBalancer(TestBase):

    def setUp(self):
        super(TestELBLoadBalancer, self).setUp()
        self.load_balancer = ELBLoadBalancer("ctx_node", resource_id=True,
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
        reload(load_balancer)

    def test_class_properties(self):
        effect = self.get_client_error_exception(name='S3 ELB')
        self.load_balancer.client = self.make_client_function(
            'describe_load_balancers',
            side_effect=effect)
        res = self.load_balancer.properties
        self.assertIsNone(res)

        value = []
        self.load_balancer.client = self.make_client_function(
            'describe_load_balancers',
            return_value=value)
        res = self.load_balancer.properties
        self.assertIsNone(res)

        value = {'LoadBalancers': ['test']}
        self.load_balancer.client = self.make_client_function(
            'describe_load_balancers',
            return_value=value)
        res = self.load_balancer.properties
        self.assertEqual(res, 'test')

    def test_class_status(self):
        value = []
        self.load_balancer.client = self.make_client_function(
            'describe_load_balancers',
            return_value=value)
        res = self.load_balancer.status
        self.assertIsNone(res)

        value = {'LoadBalancers': [{'State': {'Code': 'ok'}}]}
        self.load_balancer.client = self.make_client_function(
            'describe_load_balancers',
            return_value=value)
        res = self.load_balancer.status
        self.assertEqual(res, 'ok')

    def test_class_create(self):
        value = {'LoadBalancers': [{RESOURCE_NAME: 'name', LB_ARN: 'arn'}]}
        self.load_balancer.client = self.make_client_function(
            'create_load_balancer',
            return_value=value)
        output = self.load_balancer.create(value)
        self.assertEqual(output, value)

    def test_class_delete(self):
        params = {}
        self.load_balancer.client = self.make_client_function(
            'delete_load_balancer')
        self.load_balancer.delete(params)
        self.assertTrue(self.load_balancer.client.delete_load_balancer.called)

    def test_class_modify_attributes(self):
        value = {LB_ATTR: 'attr'}
        self.load_balancer.client = self.make_client_function(
            'modify_load_balancer_attributes',
            return_value=value)
        res = self.load_balancer.modify_attribute(value)
        self.assertEqual(res, 'attr')

    def test_prepare(self):
        ctx = self.get_mock_ctx("ELB")
        load_balancer.prepare(ctx, 'config')
        self.assertEqual(ctx.instance.runtime_properties['resource_config'],
                         'config')

    def test_create(self):
        ctx = self.get_mock_ctx("ELB", {}, {'resource_config': {}})
        ctx_target = self.get_mock_relationship_ctx(
            "elb",
            test_target=self.get_mock_ctx("elb", {},
                                          {EXTERNAL_RESOURCE_ID: 'ext_id'}))
        iface = MagicMock()
        config = {LB_ARN: 'load_balancer'}
        with patch(PATCH_PREFIX + 'utils') as utils:
            utils.find_rels_by_node_type = self.mock_return([ctx_target])
            load_balancer.create(ctx, iface, config)
            self.assertTrue(iface.create.called)

    def test_modify(self):
        ctx = self.get_mock_ctx("ELB", {}, {'resource_config': {}})
        ctx_target = self.get_mock_relationship_ctx(
            "elb",
            test_target=self.get_mock_ctx("elb", {},
                                          {EXTERNAL_RESOURCE_ID: 'ext_id'}))
        iface = MagicMock()
        config = {LB_ARN: 'load_balancer'}
        with patch(PATCH_PREFIX + 'utils') as utils:
            utils.find_rels_by_node_type = self.mock_return([ctx_target])
            load_balancer.modify(ctx, iface, config)
            self.assertNotIn(
                LB_ATTR,
                ctx.instance.runtime_properties['resource_config'])

        config = {}
        with patch(PATCH_PREFIX + 'utils') as utils:
            utils.find_rels_by_node_type = self.mock_return([ctx_target])
            load_balancer.modify(ctx, iface, config)
            self.assertNotIn(
                LB_ATTR,
                ctx.instance.runtime_properties['resource_config'])

        config = {LB_ATTR: 'attr'}
        with patch(PATCH_PREFIX + 'utils') as utils:
            utils.find_rels_by_node_type = self.mock_return([ctx_target])
            load_balancer.modify(ctx, iface, config)
            self.assertIn(LB_ATTR,
                          ctx.instance.runtime_properties['resource_config'])

    def test_delete(self):
        iface = MagicMock()
        load_balancer.delete(None, iface, {})
        self.assertTrue(iface.delete.called)


if __name__ == '__main__':
    unittest.main()

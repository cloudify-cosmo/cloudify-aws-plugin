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
from cloudify_aws.elb.resources.classic.load_balancer import (
    ELBClassicLoadBalancer, RESOURCE_NAME)
from cloudify_aws.common.constants import EXTERNAL_RESOURCE_ID
from mock import patch, MagicMock
from cloudify_aws.elb.resources.classic import load_balancer

from cloudify.exceptions import OperationRetry

PATCH_PREFIX = 'cloudify_aws.elb.resources.classic.load_balancer.'


class TestELBClassicLoadBalancer(TestBase):

    def setUp(self):
        super(TestELBClassicLoadBalancer, self).setUp()
        self.load_balancer = ELBClassicLoadBalancer("ctx_node",
                                                    resource_id=True,
                                                    client=MagicMock(),
                                                    logger=None)
        mock1 = patch('cloudify_aws.common.decorators.aws_resource',
                      mock_decorator)
        mock2 = patch('cloudify_aws.common.decorators.aws_relationship',
                      mock_decorator)
        mock1.start()
        mock2.start()
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

        value = {'LoadBalancerDescriptions': ['test']}
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

        value = {'LoadBalancerDescriptions': [{'State': {'Code': 'ok'}}]}
        self.load_balancer.client = self.make_client_function(
            'describe_load_balancers',
            return_value=value)
        res = self.load_balancer.status
        self.assertEqual(res, 'ok')

    def test_class_create(self):
        value = {'DNSName': 'dns'}
        self.load_balancer.client = self.make_client_function(
            'create_load_balancer',
            return_value=value)
        res = self.load_balancer.create(value)
        self.assertEqual(res['DNSName'], 'dns')

    def test_class_delete(self):
        params = {}
        self.load_balancer.client = self.make_client_function(
            'delete_load_balancer')
        self.load_balancer.delete(params)
        self.assertTrue(self.load_balancer.client.delete_load_balancer.called)

    def test_class_modify_attributes(self):
        value = 'attr'
        self.load_balancer.client = self.make_client_function(
            'modify_load_balancer_attributes',
            return_value=value)
        res = self.load_balancer.modify_attributes({})
        self.assertEqual(res, 'attr')

    def test_class_register_instances(self):
        value = 'attr'
        self.load_balancer.client = self.make_client_function(
            'register_instances_with_load_balancer', return_value=value)
        res = self.load_balancer.register_instances({})
        self.assertEqual(res, 'attr')

    def test_class_deregister_instances(self):
        value = 'attr'
        self.load_balancer.client = self.make_client_function(
            'deregister_instances_from_load_balancer', return_value=value)
        res = self.load_balancer.deregister_instances({})
        self.assertEqual(res, 'attr')

    def test_prepare(self):
        ctx = self.get_mock_ctx("ELB")
        load_balancer.prepare(ctx, 'config')
        self.assertEqual(ctx.instance.runtime_properties['resource_config'],
                         'config')

    def test_create(self):
        ctx = self.get_mock_ctx("ELB", {}, {'resource_config': {}})
        iface = MagicMock()
        config = {}
        with patch(PATCH_PREFIX + 'utils') as utils:
            utils.find_rels_by_node_type = self.mock_return('net')
            load_balancer.create(ctx, iface, config)
            self.assertTrue(iface.create.called)

        ctx = self.get_mock_ctx("ELB", {}, {'resource_config': {}})
        iface = MagicMock()
        config = {RESOURCE_NAME: 'name'}
        with patch(PATCH_PREFIX + 'utils') as utils:
            utils.find_rels_by_node_type = self.mock_return('net')
            load_balancer.create(ctx, iface, config)
            self.assertTrue(iface.create.called)

    def test_start(self):
        ctx = self.get_mock_ctx("ELB", {}, {'resource_config': {}})
        iface = MagicMock()
        config = {'Attributes': []}
        load_balancer.start(ctx, iface, config)
        self.assertTrue(iface.modify_attributes.called)

        ctx = self.get_mock_ctx("ELB", {}, {'resource_config': {}})
        iface = MagicMock()
        config = {RESOURCE_NAME: 'name'}
        load_balancer.start(ctx, iface, config)
        self.assertTrue(iface.modify_attributes.called)

    def test_delete(self):
        iface = MagicMock()
        config = {}
        load_balancer.delete(iface, config)
        self.assertTrue(iface.delete.called)

        iface = MagicMock()
        config = {RESOURCE_NAME: 'name'}
        load_balancer.delete(iface, config)
        self.assertTrue(iface.delete.called)

    def test_assoc(self):
        load_balancer_properties = {
            'Instances': [
                {'InstanceId': 'ext_id'}
            ]
        }
        mocked_elb = MagicMock()
        setattr(mocked_elb, 'properties', load_balancer_properties)

        ctx_target = self.get_mock_relationship_ctx(
            "elb",
            test_target=self.get_mock_ctx("elb", {},
                                          {EXTERNAL_RESOURCE_ID: 'ext_id'}),
            test_source=self.get_mock_ctx("elb", {},
                                          {EXTERNAL_RESOURCE_ID: 'ext_id'}))

        with patch(
                PATCH_PREFIX + 'ELBClassicLoadBalancer',
                return_value=mocked_elb):
            load_balancer.assoc(ctx_target)

    def test_assoc_raises(self):
        ctx_target = self.get_mock_relationship_ctx(
            "elb",
            test_target=self.get_mock_ctx("elb", {},
                                          {EXTERNAL_RESOURCE_ID: 'ext_id'}),
            test_source=self.get_mock_ctx("elb", {},
                                          {EXTERNAL_RESOURCE_ID: 'ext_id'}))
        with patch(PATCH_PREFIX + 'ELBClassicLoadBalancer'):
            self.assertRaises(OperationRetry, load_balancer.assoc, ctx_target)

    def test_disassoc(self):
        ctx_target = self.get_mock_relationship_ctx(
            "elb",
            test_target=self.get_mock_ctx("elb", {},
                                          {EXTERNAL_RESOURCE_ID: 'ext_id',
                                           'instances': ['ext_id']}),
            test_source=self.get_mock_ctx("elb", {},
                                          {EXTERNAL_RESOURCE_ID: 'ext_id'}))
        with patch(PATCH_PREFIX + 'ELBClassicLoadBalancer'):
            load_balancer.disassoc(ctx_target)

    def test_disassoc_raises(self):
        load_balancer_properties = {
            'Instances': [
                {'InstanceId': 'ext_id'}
            ]
        }
        mocked_elb = MagicMock()
        setattr(mocked_elb, 'properties', load_balancer_properties)
        ctx_target = self.get_mock_relationship_ctx(
            "elb",
            test_target=self.get_mock_ctx("elb", {},
                                          {EXTERNAL_RESOURCE_ID: 'ext_id',
                                           'instances': ['ext_id']}),
            test_source=self.get_mock_ctx("elb", {},
                                          {EXTERNAL_RESOURCE_ID: 'ext_id'}))
        with patch(
                PATCH_PREFIX + 'ELBClassicLoadBalancer',
                return_value=mocked_elb):
            self.assertRaises(
                OperationRetry, load_balancer.disassoc, ctx_target)


if __name__ == '__main__':
    unittest.main()

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
from cloudify.exceptions import NonRecoverableError

# Local imports
from cloudify_aws.common.constants import EXTERNAL_RESOURCE_ID
from cloudify_aws.elb.resources import load_balancer
from cloudify_aws.common.tests.test_base import TestBase, CLIENT_CONFIG
from cloudify_aws.common.tests.test_base import DEFAULT_RUNTIME_PROPERTIES
from cloudify_aws.common.tests.test_base import DELETE_RESPONSE
from cloudify_aws.elb.resources.load_balancer import (
    ELBLoadBalancer,
    LB_ARN,
    RESOURCE_NAME,
    LB_ATTR
)

# Constants
LOADBALANCER_TYPE = 'cloudify.nodes.aws.elb.LoadBalancer'
LOADBALANCER_TH = ['cloudify.nodes.Root',
                   LOADBALANCER_TYPE]

NODE_PROPERTIES = {
    'resource_id': 'CloudifyELB',
    'use_external_resource': False,
    'resource_config': {
        RESOURCE_NAME: 'loadbalancer',
        LB_ARN: 'load_balancer'},
    'client_config': CLIENT_CONFIG
}

RUNTIME_PROPERTIES_AFTER_CREATE = {
    'aws_resource_arn': 'def',
    'aws_resource_id': 'abc',
    'resource_config': {},
    'create_response': {
        'LoadBalancerName': 'abc',
        'LoadBalancerArn': 'def',
        'State': {'Code': 'active'}
    }
}


class TestELBLoadBalancer(TestBase):

    def setUp(self):
        super(TestELBLoadBalancer, self).setUp()
        self.load_balancer = ELBLoadBalancer(
            "ctx_node",
            resource_id=True,
            client=MagicMock(),
            logger=None)
        self.fake_boto, self.fake_client = self.fake_boto_client('elb')

        self.mock_patch = patch('boto3.client', self.fake_boto)
        self.mock_patch.start()

    def tearDown(self):
        self.mock_patch.stop()
        self.fake_boto = None
        self.fake_client = None
        super(TestELBLoadBalancer, self).tearDown()

    def test_class_properties(self):
        effect = self.get_client_error_exception(name='S3 ELB')
        self.load_balancer.client = self.make_client_function(
            'describe_load_balancers',
            side_effect=effect)
        res = self.load_balancer.properties
        self.assertEqual(res, {})

        value = []
        self.load_balancer.client = self.make_client_function(
            'describe_load_balancers',
            return_value=value)
        res = self.load_balancer.properties
        self.assertEqual(res, {})

        result = {'LoadBalancerName': 'True'}
        value = {'LoadBalancers': [result]}
        self.load_balancer.client = self.make_client_function(
            'describe_load_balancers',
            return_value=value)
        res = self.load_balancer.properties
        self.assertEqual(res, result)

    def test_class_status(self):
        value = []
        self.load_balancer.client = self.make_client_function(
            'describe_load_balancers',
            return_value=value)
        res = self.load_balancer.status
        self.assertIsNone(res)

        value = {'LoadBalancers': [{
            'LoadBalancerName': 'True',
            'State': {'Code': 'ok'}
        }]}
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
        _ctx = self.get_mock_ctx(
            'test_prepare',
            test_properties=NODE_PROPERTIES,
            test_runtime_properties=DEFAULT_RUNTIME_PROPERTIES,
            type_hierarchy=LOADBALANCER_TH,
            type_node=LOADBALANCER_TYPE,
        )

        current_ctx.set(_ctx)
        self.fake_client.describe_load_balancers = MagicMock(side_effect=[
            {},
            {
                'LoadBalancers': []
            },
            {
                'LoadBalancers': [{'State': {'Code': 0}}]
            }
        ])
        load_balancer.prepare(ctx=_ctx, resource_config=None, iface=None,
                              params=None)

        self.assertEqual(
            _ctx.instance.runtime_properties['resource_config'],
            {'LoadBalancerArn': 'load_balancer',
             'LoadBalancerName': 'loadbalancer'})

    def test_create_raises_UnknownServiceError(self):
        self._prepare_create_raises_UnknownServiceError(
            type_hierarchy=LOADBALANCER_TH,
            type_node=LOADBALANCER_TYPE,
            type_name='elbv2',
            type_class=load_balancer,
        )

    def test_create(self):
        _ctx = self.get_mock_ctx(
            'test_create',
            test_properties=NODE_PROPERTIES,
            test_runtime_properties=DEFAULT_RUNTIME_PROPERTIES,
            type_hierarchy=LOADBALANCER_TH,
            type_node=LOADBALANCER_TYPE,
            ctx_operation_name='cloudify.interfaces.lifecycle.create',
        )
        _ctx.instance._relationships = [
            self.get_mock_relationship_ctx(
                "elb",
                test_target=self.get_mock_ctx(
                    "elb", {},
                    {EXTERNAL_RESOURCE_ID: 'subnet_id'},
                    type_hierarchy=[load_balancer.SUBNET_TYPE],
                    type_node=load_balancer.SUBNET_TYPE)),
            self.get_mock_relationship_ctx(
                "elb",
                test_target=self.get_mock_ctx(
                    "elb", {},
                    {EXTERNAL_RESOURCE_ID: 'sec_id'},
                    type_hierarchy=[load_balancer.SECGROUP_TYPE],
                    type_node=load_balancer.SECGROUP_TYPE))
        ]

        current_ctx.set(_ctx)

        self.fake_client.create_load_balancer = self.mock_return(
            {'LoadBalancers': [{
                RESOURCE_NAME: "abc",
                LB_ARN: "def"
            }]})
        self.fake_client.describe_load_balancers = self.mock_return(
            {'LoadBalancers': [{
                RESOURCE_NAME: "abc",
                LB_ARN: "def",
                'State': {
                    'Code': 'active'
                }
            }]})

        load_balancer.create(ctx=_ctx, resource_config=None, iface=None,
                             params=None)

        self.fake_boto.assert_called_with('elbv2', **CLIENT_CONFIG)

        self.fake_client.create_load_balancer.assert_called_with(
            LoadBalancerArn='load_balancer', LoadBalancerName='loadbalancer',
            Name='aws_resource', SecurityGroups=['sec_id'],
            Subnets=['subnet_id'])
        self.fake_client.describe_load_balancers.assert_called_with(
            Names=['abc'])

        # This is just because I'm not interested in the content
        # of remote_configuration right now.
        # If it doesn't exist, this test will fail, and that's good.
        _ctx.instance.runtime_properties.pop('remote_configuration')

        self.assertEqual(
            _ctx.instance.runtime_properties,
            RUNTIME_PROPERTIES_AFTER_CREATE
        )
        # check error with no LB_ARN
        self.fake_client.create_load_balancer = self.mock_return(
            {'LoadBalancers': [{
                RESOURCE_NAME: "abc"
            }]})
        with self.assertRaises(NonRecoverableError):
            load_balancer.create(ctx=_ctx, resource_config=None, iface=None,
                                 params=None)

    def test_modify(self):
        # empty config
        _ctx = self.get_mock_ctx(
            'test_modify',
            test_properties=NODE_PROPERTIES,
            test_runtime_properties=RUNTIME_PROPERTIES_AFTER_CREATE,
            type_hierarchy=LOADBALANCER_TH,
            type_node=LOADBALANCER_TYPE,
            ctx_operation_name='cloudify.interfaces.lifecycle.start'
        )
        _ctx.instance._relationships = [
            self.get_mock_relationship_ctx(
                "elb",
                test_target=self.get_mock_ctx(
                    "elb", {},
                    {EXTERNAL_RESOURCE_ID: 'ext_id'}))
        ]

        current_ctx.set(_ctx)

        _ctx.instance.runtime_properties['resource_config'] = {}
        self.fake_client.describe_load_balancers = MagicMock(side_effect=[
            {
                'LoadBalancers': [
                    {
                        'LoadBalancerName': 'abc',
                        'State': {'Code': 'active'}
                    }]
            },
            {
                'LoadBalancers': [
                    {
                        'LoadBalancerName': 'abc',
                        'State': {'Code': 'active'}
                    }]
            },
            {
                'LoadBalancers': [
                    {
                        'LoadBalancerName': 'abc',
                        'State': {'Code': 'active'}
                    }]
            },
            {
                'LoadBalancers': [
                    {
                        'LoadBalancerName': 'abc',
                        'State': {'Code': 'active'}
                    }]
            },
            {
                'LoadBalancers': [
                    {
                        'LoadBalancerName': 'abc',
                        'State': {'Code': 'active'}
                    }]
            },
        ])

        load_balancer.modify(ctx=_ctx, resource_config=None, iface=None,
                             params=None)

        self.fake_boto.assert_called_with('elbv2', **CLIENT_CONFIG)

        self.fake_client.modify_load_balancer_attributes.assert_not_called()
        self.assertNotIn(
            LB_ATTR,
            _ctx.instance.runtime_properties['resource_config'])

        # with ARN
        _ctx = self.get_mock_ctx(
            'test_modify',
            test_properties=NODE_PROPERTIES,
            test_runtime_properties=RUNTIME_PROPERTIES_AFTER_CREATE,
            type_hierarchy=LOADBALANCER_TH,
            type_node=LOADBALANCER_TYPE,
            ctx_operation_name='cloudify.interfaces.lifecycle.start'
        )
        _ctx.instance._relationships = [
            self.get_mock_relationship_ctx(
                "elb",
                test_target=self.get_mock_ctx(
                    "elb", {},
                    {EXTERNAL_RESOURCE_ID: 'ext_id'}))
        ]

        current_ctx.set(_ctx)

        _ctx.instance.runtime_properties['resource_config'] = {
            LB_ARN: 'load_balancer'}

        load_balancer.modify(ctx=_ctx, resource_config=None, iface=None,
                             params=None)

        self.fake_boto.assert_called_with('elbv2', **CLIENT_CONFIG)

        self.fake_client.modify_load_balancer_attributes.assert_not_called()
        self.assertNotIn(
            LB_ATTR,
            _ctx.instance.runtime_properties['resource_config'])

        # with ARN and LB_ATTR
        _ctx = self.get_mock_ctx(
            'test_modify',
            test_properties=NODE_PROPERTIES,
            test_runtime_properties=RUNTIME_PROPERTIES_AFTER_CREATE,
            type_hierarchy=LOADBALANCER_TH,
            type_node=LOADBALANCER_TYPE,
            ctx_operation_name='cloudify.interfaces.lifecycle.start'
        )
        _ctx.node.properties['resource_config'] = {LB_ATTR: 'attr'}
        _ctx.instance._relationships = [
            self.get_mock_relationship_ctx(
                "elb",
                test_target=self.get_mock_ctx(
                    "elb", {},
                    {EXTERNAL_RESOURCE_ID: 'ext_id'}))
        ]

        current_ctx.set(_ctx)

        self.fake_client.modify_load_balancer_attributes = self.mock_return(
            {LB_ATTR: "attributes"})

        load_balancer.modify(ctx=_ctx, resource_config=None, iface=None,
                             params=None)

        self.fake_boto.assert_called_with('elbv2', **CLIENT_CONFIG)

        self.fake_client.modify_load_balancer_attributes.assert_called_with(
            Attributes='attr', LoadBalancerArn='def'
        )
        self.assertIn(
            LB_ATTR,
            _ctx.instance.runtime_properties['resource_config'])

    def test_delete(self):
        _ctx = self.get_mock_ctx(
            'test_delete',
            test_properties=NODE_PROPERTIES,
            test_runtime_properties=RUNTIME_PROPERTIES_AFTER_CREATE,
            type_hierarchy=LOADBALANCER_TH,
            type_node=LOADBALANCER_TYPE,
            ctx_operation_name='cloudify.interfaces.lifecycle.delete'
        )

        current_ctx.set(_ctx)

        self.fake_client.delete_load_balancer = self.mock_return(
            DELETE_RESPONSE)
        self.fake_client.describe_load_balancers = self.mock_return(
            {'LoadBalancers': [{
                RESOURCE_NAME: "abc",
                LB_ARN: "def",
                'State': {
                    'Code': ""
                }
            }]})

        load_balancer.delete(ctx=_ctx, resource_config={}, iface=None)

        self.fake_boto.assert_called_with('elbv2', **CLIENT_CONFIG)

        self.fake_client.delete_load_balancer.assert_called_with(
            LoadBalancerArn='def'
        )
        self.fake_client.describe_load_balancers.assert_called_with(
            Names=['abc'])


if __name__ == '__main__':
    unittest.main()

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
from mock import patch, Mock, MagicMock

from cloudify.state import current_ctx
from cloudify.exceptions import OperationRetry

# Local imports
from cloudify_aws.common.constants import EXTERNAL_RESOURCE_ID
from cloudify_aws.elb.resources.classic import load_balancer
from cloudify_aws.common.tests.test_base import TestBase, CLIENT_CONFIG
from cloudify_aws.common.tests.test_base import DEFAULT_RUNTIME_PROPERTIES
from cloudify_aws.common.tests.test_base import DELETE_RESPONSE
from cloudify_aws.elb.resources.classic.load_balancer import (
    ELBClassicLoadBalancer,
    RESOURCE_NAME,
    LB_ARN
)

PATCH_PREFIX = 'cloudify_aws.elb.resources.classic.load_balancer.'

# Constants
LOADBALANCER_TYPE = 'cloudify.nodes.aws.elb.Classic.LoadBalancer'
LOADBALANCER_TH = ['cloudify.nodes.Root',
                   LOADBALANCER_TYPE]

NODE_PROPERTIES = {
    'resource_id': 'CloudifyELB',
    'use_external_resource': False,
    'resource_config': {
        RESOURCE_NAME: 'loadbalancer',
        'Attributes': []},
    'client_config': CLIENT_CONFIG
}

RUNTIME_PROPERTIES_AFTER_CREATE = {
    'LoadBalancerName': 'aws_resource',
    'resource_config': {},
    'aws_resource_id': 'aws_resource',
    'DNSName': 'DNSName',
    'create_response': {
        'DNSName': 'DNSName',
        'LoadBalancers': [{
            'LoadBalancerName': 'abc',
            'LoadBalancerArn': 'def'}]}}


class TestELBClassicLoadBalancer(TestBase):

    def setUp(self):
        super(TestELBClassicLoadBalancer, self).setUp()
        self.load_balancer = ELBClassicLoadBalancer("ctx_node",
                                                    resource_id=True,
                                                    client=Mock(),
                                                    logger=None)
        self.fake_boto, self.fake_client = self.fake_boto_client('elb')

        self.mock_patch = patch('boto3.client', self.fake_boto)
        self.mock_patch.start()

    def tearDown(self):
        self.mock_patch.stop()
        self.fake_boto = None
        self.fake_client = None
        super(TestELBClassicLoadBalancer, self).tearDown()

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
        _ctx = self.get_mock_ctx(
            'test_prepare',
            test_properties=NODE_PROPERTIES,
            test_runtime_properties=DEFAULT_RUNTIME_PROPERTIES,
            type_hierarchy=LOADBALANCER_TH,
            type_node=LOADBALANCER_TYPE,
        )

        current_ctx.set(_ctx)

        self.fake_client.describe_load_balancers = Mock(
            side_effect=[
                {},
                {},
            ])

        load_balancer.prepare(ctx=_ctx, resource_config=None, iface=None,
                              params=None)

        self.assertEqual(
            _ctx.instance.runtime_properties['resource_config'],
            {'LoadBalancerName': 'loadbalancer'})

    def test_create_raises_UnknownServiceError(self):
        self._prepare_create_raises_UnknownServiceError(
            type_hierarchy=LOADBALANCER_TH,
            type_node=LOADBALANCER_TYPE,
            type_name='elb',
            type_class=load_balancer,
        )

    def test_create(self):
        _ctx = self.get_mock_ctx(
            'test_create',
            test_properties=NODE_PROPERTIES,
            test_runtime_properties=DEFAULT_RUNTIME_PROPERTIES,
            type_hierarchy=LOADBALANCER_TH,
            type_node=LOADBALANCER_TYPE,
        )
        _ctx.instance._relationships = [
            self.get_mock_relationship_ctx(
                "elb",
                test_target=self.get_mock_ctx(
                    "elb", {},
                    {EXTERNAL_RESOURCE_ID: 'ext_id'}))
        ]

        current_ctx.set(_ctx)

        self.fake_client.describe_load_balancers = Mock(
            side_effect=[
                {},
                {
                    'LoadBalancerDescriptions': [
                        {'State': {'Code': 'ok'}}
                    ]
                },
            ])
        self.fake_client.create_load_balancer = self.mock_return({
            'LoadBalancers': [{
                RESOURCE_NAME: "abc",
                LB_ARN: "def"
            }],
            'DNSName': 'DNSName'
        })

        load_balancer.create(ctx=_ctx, resource_config=None, iface=None,
                             params=None)

        self.fake_boto.assert_called_with('elb', **CLIENT_CONFIG)

        self.fake_client.create_load_balancer.assert_called_with(
            LoadBalancerName='aws_resource', SecurityGroups=[], Subnets=[])

        self.assertEqual(
            _ctx.instance.runtime_properties,
            RUNTIME_PROPERTIES_AFTER_CREATE
        )

    def test_start(self):
        _ctx = self.get_mock_ctx(
            'test_start',
            test_properties=NODE_PROPERTIES,
            test_runtime_properties=RUNTIME_PROPERTIES_AFTER_CREATE,
            type_hierarchy=LOADBALANCER_TH,
            type_node=LOADBALANCER_TYPE,
            ctx_operation_name='cloudify.interfaces.lifecycle.start'
        )

        current_ctx.set(_ctx)
        self.fake_client.describe_load_balancers = Mock(
            side_effect=[
                {},
                {},
            ])
        self.fake_client.modify_load_balancer_attributes = self.mock_return(
            DELETE_RESPONSE)

        # should be used resource config from inputs
        iface = MagicMock()
        iface.status = None
        load_balancer.start(ctx=_ctx, resource_config={'a': 'b'}, iface=iface)

        self.fake_boto.assert_called_with('elb', **CLIENT_CONFIG)

        self.fake_client.modify_load_balancer_attributes.assert_called_with(
            LoadBalancerName='aws_resource', a='b'
        )

        # start without resource configs
        _ctx = self.get_mock_ctx(
            'test_start',
            test_properties=NODE_PROPERTIES,
            test_runtime_properties=RUNTIME_PROPERTIES_AFTER_CREATE,
            type_hierarchy=LOADBALANCER_TH,
            type_node=LOADBALANCER_TYPE,
        )

        current_ctx.set(_ctx)
        self.fake_client.describe_load_balancers = Mock(
            side_effect=[
                {},
                {
                    'LoadBalancerDescriptions': [
                        {'State': {'Code': 'ok'}}
                    ]
                },
            ])
        self.fake_client.modify_load_balancer_attributes = self.mock_return(
            DELETE_RESPONSE)

        # should be used resource config from inputs
        load_balancer.start(ctx=_ctx, resource_config=None, iface=None)

        self.fake_boto.assert_called_with('elb', **CLIENT_CONFIG)

        self.fake_client.modify_load_balancer_attributes.assert_not_called()

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

        self.fake_client.describe_load_balancers = Mock(
            side_effect=[
                {},
                {},
            ])
        self.fake_client.delete_load_balancer = self.mock_return(
            DELETE_RESPONSE)

        iface = MagicMock()
        iface.status = None
        load_balancer.delete(ctx=_ctx, resource_config=None, iface=iface)

        self.fake_boto.assert_called_with('elb', **CLIENT_CONFIG)

        self.fake_client.delete_load_balancer.assert_called_with(
            LoadBalancerName='aws_resource'
        )

    def test_assoc(self):
        _ctx = self.get_mock_relationship_ctx(
            "elb",
            test_target=self.get_mock_ctx("elb", NODE_PROPERTIES,
                                          {EXTERNAL_RESOURCE_ID: 'ext_id'}),
            test_source=self.get_mock_ctx("elb", NODE_PROPERTIES,
                                          {EXTERNAL_RESOURCE_ID: 'ext_id'}))

        self.fake_client.register_instances_with_load_balancer = \
            self.mock_return(DELETE_RESPONSE)
        self.fake_client.describe_load_balancers = \
            self.mock_return({
                'LoadBalancerDescriptions': [{
                    'Instances': [{
                        'InstanceId': 'ext_id'
                    }]
                }]
            })
        _ctx._operation = Mock()
        _ctx.operation.retry_number = 0

        current_ctx.set(_ctx)

        load_balancer.assoc(ctx=_ctx)

        self.fake_boto.assert_called_with('elb', **CLIENT_CONFIG)

        self.fake_client.register_instances_with_load_balancer.\
            assert_called_with(Instances=[{'InstanceId': 'ext_id'}],
                               LoadBalancerName='ext_id')
        self.fake_client.describe_load_balancers.assert_called_with(
            LoadBalancerNames=['ext_id']
        )

    def test_assoc_raises(self):
        _ctx = self.get_mock_relationship_ctx(
            "elb",
            test_target=self.get_mock_ctx("elb", NODE_PROPERTIES,
                                          {EXTERNAL_RESOURCE_ID: 'ext_id'}),
            test_source=self.get_mock_ctx("elb", NODE_PROPERTIES,
                                          {EXTERNAL_RESOURCE_ID: 'ext_id'}))

        self.fake_client.register_instances_with_load_balancer = \
            self.mock_return(DELETE_RESPONSE)
        self.fake_client.describe_load_balancers = \
            self.mock_return({
                'LoadBalancerDescriptions': [{
                    'Instances': []
                }]
            })
        _ctx._operation = Mock()
        _ctx.operation.retry_number = 0

        current_ctx.set(_ctx)

        with self.assertRaises(OperationRetry):
            load_balancer.assoc(ctx=_ctx)

        self.fake_boto.assert_called_with('elb', **CLIENT_CONFIG)

        self.fake_client.register_instances_with_load_balancer.\
            assert_called_with(Instances=[{'InstanceId': 'ext_id'}],
                               LoadBalancerName='ext_id')
        self.fake_client.describe_load_balancers.assert_called_with(
            LoadBalancerNames=['ext_id']
        )

    def test_disassoc(self):
        _ctx = self.get_mock_relationship_ctx(
            "elb",
            test_target=self.get_mock_ctx("elb", NODE_PROPERTIES,
                                          {EXTERNAL_RESOURCE_ID: 'ext_id',
                                           'instances': ['ext_id']}),
            test_source=self.get_mock_ctx("elb", NODE_PROPERTIES,
                                          {EXTERNAL_RESOURCE_ID: 'ext_id'}))

        self.fake_client.deregister_instances_from_load_balancer = \
            self.mock_return(DELETE_RESPONSE)
        self.fake_client.describe_load_balancers = \
            self.mock_return({
                'LoadBalancerDescriptions': [{
                    'Instances': []
                }]
            })

        current_ctx.set(_ctx)

        load_balancer.disassoc(ctx=_ctx)

        self.fake_boto.assert_called_with('elb', **CLIENT_CONFIG)

        self.fake_client.deregister_instances_from_load_balancer.\
            assert_called_with(Instances=[{'InstanceId': 'ext_id'}],
                               LoadBalancerName='ext_id')
        self.fake_client.describe_load_balancers.assert_called_with(
            LoadBalancerNames=['ext_id']
        )

    def test_disassoc_raises(self):
        _ctx = self.get_mock_relationship_ctx(
            "elb",
            test_target=self.get_mock_ctx("elb", NODE_PROPERTIES,
                                          {EXTERNAL_RESOURCE_ID: 'ext_id',
                                           'instances': ['ext_id']}),
            test_source=self.get_mock_ctx("elb", NODE_PROPERTIES,
                                          {EXTERNAL_RESOURCE_ID: 'ext_id'}))

        self.fake_client.deregister_instances_from_load_balancer = \
            self.mock_return(DELETE_RESPONSE)
        self.fake_client.describe_load_balancers = \
            self.mock_return({
                'LoadBalancerDescriptions': [{
                    'Instances': [{
                        'InstanceId': 'ext_id'
                    }]
                }]
            })

        current_ctx.set(_ctx)

        with self.assertRaises(OperationRetry):
            load_balancer.disassoc(ctx=_ctx)

        self.fake_boto.assert_called_with('elb', **CLIENT_CONFIG)

        self.fake_client.deregister_instances_from_load_balancer.\
            assert_called_with(Instances=[{'InstanceId': 'ext_id'}],
                               LoadBalancerName='ext_id')
        self.fake_client.describe_load_balancers.assert_called_with(
            LoadBalancerNames=['ext_id']
        )


if __name__ == '__main__':
    unittest.main()

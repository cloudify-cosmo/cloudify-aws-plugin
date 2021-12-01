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
from cloudify_aws.common.constants import EXTERNAL_RESOURCE_ID
from cloudify_aws.elb.resources.classic import policy
from cloudify_aws.common.tests.test_base import TestBase, CLIENT_CONFIG
from cloudify_aws.common.tests.test_base import DEFAULT_RUNTIME_PROPERTIES
from cloudify_aws.common.tests.test_base import DELETE_RESPONSE
from cloudify_aws.elb.resources.classic.policy import (
    ELBClassicPolicy,
    RESOURCE_NAME,
    LB_TYPE
)

PATCH_PREFIX = 'cloudify_aws.elb.resources.classic.policy.'

# Constants
POLICY_TYPE = 'cloudify.nodes.aws.elb.Classic.Policy'
POLICY_TH = ['cloudify.nodes.Root',
             POLICY_TYPE]

POLICYSTICKY_TYPE = 'cloudify.nodes.aws.elb.Classic.Policy'
POLICYSTICKY_TH = ['cloudify.nodes.Root',
                   POLICYSTICKY_TYPE]

NODE_PROPERTIES = {
    'resource_id': 'CloudifyELB',
    'use_external_resource': False,
    'resource_config': {RESOURCE_NAME: 'policy'},
    'client_config': CLIENT_CONFIG
}

RUNTIME_PROPERTIES_AFTER_CREATE = {
    'LoadBalancerName': 'aws_resource',
    'resource_config': {},
    'aws_resource_id': 'aws_resource'
}

RUNTIME_STICKY_PROPERTIES_AFTER_CREATE = {
    'PolicyName': 'aws_resource',
    'resource_config': {},
    'aws_resource_id': 'aws_resource'
}


class TestELBClassicPolicy(TestBase):

    def setUp(self):
        super(TestELBClassicPolicy, self).setUp()
        self.policy = ELBClassicPolicy("ctx_node", resource_id=True,
                                       client=MagicMock(), logger=None)
        self.fake_boto, self.fake_client = self.fake_boto_client('elb')

        self.mock_patch = patch('boto3.client', self.fake_boto)
        self.mock_patch.start()

    def tearDown(self):
        self.mock_patch.stop()
        self.fake_boto = None
        self.fake_client = None
        super(TestELBClassicPolicy, self).tearDown()

    def test_class_properties(self):
        res = self.policy.properties
        self.assertIsNone(res)

    def test_class_status(self):
        res = self.policy.status
        self.assertIsNone(res)

    def test_class_create(self):
        self.policy.client = self.make_client_function(
            'create_load_balancer_policy', return_value='id')
        res = self.policy.create({})
        self.assertEqual(res, 'id')

    def test_class_create_sticky(self):
        self.policy.client = self.make_client_function(
            'create_lb_cookie_stickiness_policy', return_value='id')
        res = self.policy.create_sticky({})
        self.assertEqual(res, 'id')

    def test_class_start(self):
        self.policy.client = self.make_client_function(
            'set_load_balancer_policies_of_listener', return_value='id')
        res = self.policy.start({})
        self.assertEqual(res, 'id')

    def test_class_delete(self):
        self.policy.client = self.make_client_function(
            'delete_load_balancer_policy', return_value='del')
        res = self.policy.delete({})
        self.assertEqual(res, 'del')

    def test_prepare(self):
        _ctx = self.get_mock_ctx(
            'test_prepare',
            test_properties=NODE_PROPERTIES,
            test_runtime_properties=DEFAULT_RUNTIME_PROPERTIES,
            type_hierarchy=POLICY_TH,
            type_node=POLICY_TYPE,
        )

        current_ctx.set(_ctx)

        policy.prepare(ctx=_ctx, resource_config=None, iface=None,
                       params=None)

        self.assertEqual(
            _ctx.instance.runtime_properties['resource_config'],
            {'PolicyName': 'policy'})

    def test_create(self):
        _ctx = self.get_mock_ctx(
            'test_create',
            test_properties=NODE_PROPERTIES,
            test_runtime_properties=DEFAULT_RUNTIME_PROPERTIES,
            type_hierarchy=POLICY_TH,
            type_node=POLICY_TYPE,
        )
        _ctx.instance._relationships = [
            self.get_mock_relationship_ctx(
                "elb",
                test_target=self.get_mock_ctx(
                    "elb", {},
                    {EXTERNAL_RESOURCE_ID: 'ext_id'},
                    type_hierarchy=[LB_TYPE],
                    type_node=LB_TYPE))
        ]

        current_ctx.set(_ctx)

        self.fake_client.create_load_balancer_policy = self.mock_return({})

        policy.create(ctx=_ctx, resource_config=None, iface=None,
                      params=None)

        self.fake_boto.assert_called_with('elb', **CLIENT_CONFIG)

        self.fake_client.create_load_balancer_policy.assert_called_with(
            LoadBalancerName='ext_id', PolicyName='aws_resource')

    def test_create_sticky(self):
        _ctx = self.get_mock_ctx(
            'test_create',
            test_properties=NODE_PROPERTIES,
            test_runtime_properties=DEFAULT_RUNTIME_PROPERTIES,
            type_hierarchy=POLICYSTICKY_TH,
            type_node=POLICYSTICKY_TYPE,
        )
        _ctx.instance._relationships = [
            self.get_mock_relationship_ctx(
                "elb",
                test_target=self.get_mock_ctx(
                    "elb", {},
                    {EXTERNAL_RESOURCE_ID: 'ext_id'},
                    type_hierarchy=[LB_TYPE],
                    type_node=LB_TYPE))
        ]

        current_ctx.set(_ctx)

        self.fake_client.create_lb_cookie_stickiness_policy = self.mock_return(
            {})

        policy.create_sticky(ctx=_ctx, resource_config=None, iface=None,
                             params=None)

        self.fake_boto.assert_called_with('elb', **CLIENT_CONFIG)

        self.fake_client.create_lb_cookie_stickiness_policy.assert_called_with(
            LoadBalancerName='ext_id', PolicyName='policy')

    def test_start_sticky(self):
        _ctx = self.get_mock_ctx(
            'test_delete',
            test_properties=NODE_PROPERTIES,
            test_runtime_properties=RUNTIME_STICKY_PROPERTIES_AFTER_CREATE,
            type_hierarchy=POLICYSTICKY_TH,
            type_node=POLICYSTICKY_TYPE,
        )
        _ctx.instance._relationships = [
            self.get_mock_relationship_ctx(
                "elb",
                test_target=self.get_mock_ctx(
                    "elb", {},
                    {
                        EXTERNAL_RESOURCE_ID: 'ext_id',
                        'resource_config': {
                            'Listeners': [{}]
                        }
                    },
                    type_hierarchy=[LB_TYPE],
                    type_node=LB_TYPE))
        ]
        current_ctx.set(_ctx)

        self.fake_client.set_load_balancer_policies_of_listener = \
            self.mock_return(DELETE_RESPONSE)

        policy.start_sticky(ctx=_ctx, resource_config=None, iface=None)

        self.fake_boto.assert_called_with('elb', **CLIENT_CONFIG)

        self.fake_client.set_load_balancer_policies_of_listener.\
            assert_called_with(LoadBalancerName='ext_id',
                               LoadBalancerPort=None,
                               PolicyNames=['aws_resource'])

    def test_delete(self):
        _ctx = self.get_mock_ctx(
            'test_delete',
            test_properties=NODE_PROPERTIES,
            test_runtime_properties=RUNTIME_PROPERTIES_AFTER_CREATE,
            type_hierarchy=POLICY_TH,
            type_node=POLICY_TYPE,
            ctx_operation_name='cloudify.interfaces.lifecycle.delete'
        )

        current_ctx.set(_ctx)

        self.fake_client.delete_load_balancer_policy = self.mock_return(
            DELETE_RESPONSE)

        policy.delete(ctx=_ctx, resource_config=None, iface=None)

        self.fake_boto.assert_called_with('elb', **CLIENT_CONFIG)

        self.fake_client.delete_load_balancer_policy.assert_called_with(
            LoadBalancerName='aws_resource', PolicyName='policy'
        )


if __name__ == '__main__':
    unittest.main()

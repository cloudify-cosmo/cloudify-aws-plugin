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
from cloudify.exceptions import OperationRetry

# Local imports
from cloudify_aws.ec2.resources import vpc
from cloudify_aws.common._compat import reload_module
from cloudify_aws.common.tests.test_base import (
    TestBase,
    mock_decorator
)
from cloudify_aws.ec2.resources.vpc import (
    EC2Vpc,
    VPC,
    CIDR_BLOCK,
    VPC_ID
)


class TestEC2Vpc(TestBase):

    def setUp(self):
        super(TestEC2Vpc, self).setUp()
        self.vpc = EC2Vpc("ctx_node", resource_id='test_name',
                          client=True, logger=None)
        mock1 = patch('cloudify_aws.common.decorators.aws_resource',
                      mock_decorator)
        mock2 = patch('cloudify_aws.common.decorators.wait_for_status',
                      mock_decorator)
        mock1.start()
        mock2.start()
        reload_module(vpc)

    def test_class_properties(self):
        effect = self.get_client_error_exception(name='EC2 Vpc')
        self.vpc.client = self.make_client_function('describe_vpcs',
                                                    side_effect=effect)
        res = self.vpc.properties
        self.assertTrue(not res)

        value = {}
        self.vpc.client = self.make_client_function('describe_vpcs',
                                                    return_value=value)
        res = self.vpc.properties
        self.assertEqual(res, value)

        self.vpc.resource_id = 'test_name'
        value = {'Vpcs': [{VPC_ID: 'test_name'}]}
        self.vpc.client = self.make_client_function('describe_vpcs',
                                                    return_value=value)
        res = self.vpc.properties
        self.assertEqual(res[VPC_ID], 'test_name')

    def test_class_status(self):
        value = {}
        self.vpc.client = self.make_client_function('describe_vpcs',
                                                    return_value=value)
        res = self.vpc.status
        self.assertIsNone(res)

        value = {'Vpcs': [{VPC_ID: 'test_name', 'State': 'available'}]}
        self.vpc.client = self.make_client_function('describe_vpcs',
                                                    return_value=value)
        res = self.vpc.status
        self.assertEqual(res, 'available')

    def test_class_create(self):
        value = {VPC: {VPC_ID: 'test'}}
        self.vpc.client = self.make_client_function(
            'create_vpc', return_value=value)
        self.vpc.create(dict(CidrBlock='string'))
        self.assertEqual(self.vpc.resource_id, value[VPC][VPC_ID])

    def test_class_delete(self):
        params = {}
        self.vpc.client = self.make_client_function('delete_vpc')
        self.vpc.delete(params)
        self.assertTrue(self.vpc.client.delete_vpc.called)

        params = {VPC: 'vpc', CIDR_BLOCK: 'cidr_block'}
        self.vpc.delete(params)
        self.assertEqual(params[CIDR_BLOCK], 'cidr_block')

    def test_prepare(self):
        ctx = self.get_mock_ctx("Vpc")
        config = {VPC_ID: 'vpc', CIDR_BLOCK: 'cidr_block'}
        iface = MagicMock()
        iface.create = self.mock_return(config)
        vpc.prepare(ctx, iface, config)
        self.assertEqual(ctx.instance.runtime_properties['resource_config'],
                         config)

    def test_create(self):
        ctx = self.get_mock_ctx("Vpc")
        config = {VPC_ID: 'vpc', CIDR_BLOCK: 'cidr_block'}
        self.vpc.resource_id = config[VPC_ID]
        iface = MagicMock()
        iface.create = self.mock_return({VPC: config})
        vpc.create(ctx=ctx, iface=iface, resource_config=config)
        self.assertEqual(self.vpc.resource_id,
                         'vpc')

    def test_delete(self):
        ctx = self.get_mock_ctx("Vpc")
        iface = MagicMock()
        vpc.delete(ctx=ctx, iface=iface, resource_config={})
        self.assertTrue(iface.delete.called)

    def test_delete_with_cleanup(self):
        ctx = self.get_mock_ctx("Vpc")
        self.vpc.resource_id = 'test_name'
        self.vpc.cleanup_vpc = MagicMock()
        effect = self.get_client_error_exception(name='DependencyViolation')
        self.vpc.client = self.make_client_function(
            'delete_vpc', side_effect=effect)
        vpc.delete(ctx=ctx, iface=self.vpc, resource_config={})
        self.assertTrue(self.vpc.cleanup_vpc.called)

    def test_check_drift(self):
        original_value = dict(
            CidrBlock='10.11.0.0/24',
            State='available',
            VpcId='test_name',
            Tags=[
                {
                    'Key': 'Owner',
                    'Value': 'foo'
                },
            ]
        )
        next_value = {
            'Vpcs': [
                {
                    'CidrBlock': '10.11.0.0/24',
                    'State': 'available',
                    'VpcId': 'test_name',
                    'Tags': [
                        {
                            'Key': 'Owner',
                            'Value': 'baz'
                        },
                    ]
                },
            ],
        }
        ctx = self.get_mock_ctx("Vpc")
        ctx.instance.runtime_properties.update({
                'aws_resource_id': 'test_name',
                'expected_configuration': original_value,
                'previous_configuration': {},
                'create_response': original_value
            })
        current_ctx.set(ctx)
        self.vpc.client = self.make_client_function(
            'describe_vpcs', return_value=next_value)
        self.vpc.import_configuration(
            ctx.node.properties.get('resource_config', {}),
            ctx.instance.runtime_properties
        )
        expected = {
            'values_changed': {
                "root['Tags'][0]['Value']": {
                    'new_value': 'baz', 'old_value': 'foo'
                }
            }
        }
        message = 'The EC2 Vpc test_name configuration ' \
                  'has drifts: {}'.format(expected)
        with self.assertRaises(RuntimeError) as e:
            vpc.check_drift(ctx=ctx, iface=self.vpc)
            self.assertIn(message, str(e))

    def test_modify_vpc_attribute(self):
        ctx = self.get_mock_ctx("Vpc")
        iface = MagicMock()
        iface.status = 0
        self.vpc.resource_id = 'test_name'
        try:
            vpc.modify_vpc_attribute(
                ctx, iface, {VPC_ID: self.vpc.resource_id})
        except OperationRetry:
            pass
        self.assertTrue(iface.modify_vpc_attribute.called)


if __name__ == '__main__':
    unittest.main()

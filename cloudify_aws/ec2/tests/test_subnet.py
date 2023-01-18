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
from cloudify_aws.common._compat import reload_module
from cloudify_aws.ec2.resources import subnet
from cloudify_aws.common.tests.test_base import (
    TestBase,
    mock_decorator
)
from cloudify_aws.ec2.resources.subnet import (
    EC2Subnet,
    SUBNET,
    CIDR_BLOCK,
    SUBNET_ID,
    VPC_ID,
    VPC_TYPE
)


class TestEC2Subnet(TestBase):

    def setUp(self):
        super(TestEC2Subnet, self).setUp()
        self.subnet = EC2Subnet("ctx_node", resource_id='test_name',
                                client=True, logger=None)
        mock1 = patch('cloudify_aws.common.decorators.aws_resource',
                      mock_decorator)
        mock2 = patch('cloudify_aws.common.decorators.wait_for_status',
                      mock_decorator)
        mock1.start()
        mock2.start()
        reload_module(subnet)

    def test_class_properties(self):
        effect = self.get_client_error_exception(name='EC2 Subnet')
        self.subnet.client = self.make_client_function('describe_subnets',
                                                       side_effect=effect)
        res = self.subnet.properties
        self.assertEqual(res, {})

        value = {}
        self.subnet.client = self.make_client_function('describe_subnets',
                                                       return_value=value)
        res = self.subnet.properties
        self.assertEqual(res, value)

        value = {'Subnets': [{SUBNET_ID: 'test_name'}]}
        self.subnet.client = self.make_client_function('describe_subnets',
                                                       return_value=value)
        res = self.subnet.properties
        self.assertEqual(res[SUBNET_ID], 'test_name')

    def test_class_status(self):
        value = {}
        self.subnet.client = self.make_client_function('describe_subnets',
                                                       return_value=value)
        res = self.subnet.status
        self.assertIsNone(res)

        value = {'Subnets': [{SUBNET_ID: 'test_name', 'State': 'available'}]}
        self.subnet.client = self.make_client_function('describe_subnets',
                                                       return_value=value)
        res = self.subnet.status
        self.assertEqual(res, 'available')

    def test_class_create(self):
        value = {SUBNET: {SUBNET_ID: 'test'}}
        self.subnet.client = self.make_client_function('create_subnet',
                                                       return_value=value)
        self.subnet.resource_id = 'test'
        self.subnet.create(value)
        self.assertEqual(self.subnet.create_response, value)

    def test_class_delete(self):
        params = {}
        self.subnet.client = self.make_client_function('delete_subnet')
        self.subnet.delete(params)
        self.assertTrue(self.subnet.client.delete_subnet.called)

        params = {SUBNET: 'subnet', CIDR_BLOCK: 'cidr_block'}
        self.subnet.delete(params)
        self.assertEqual(params[CIDR_BLOCK], 'cidr_block')

    def test_prepare(self):
        ctx = self.get_mock_ctx("Subnet")
        config = {SUBNET_ID: 'subnet', CIDR_BLOCK: 'cidr_block'}
        # iface = MagicMock()
        # iface.create = self.mock_return(config)
        subnet.prepare(ctx, config)
        self.assertEqual(ctx.instance.runtime_properties['resource_config'],
                         config)

    def test_create(self):
        ctx = self.get_mock_ctx("Subnet", {'client_config': {
            'region_name': 'aq-testzone-1'
        }})
        config = {SUBNET_ID: 'subnet', CIDR_BLOCK: 'cidr_block',
                  VPC_ID: 'vpc'}
        self.subnet.resource_id = config[SUBNET_ID]
        iface = MagicMock()
        iface.create = self.mock_return({SUBNET: config})
        subnet.create(ctx=ctx, iface=iface, resource_config=config)
        self.assertEqual(self.subnet.resource_id,
                         'subnet')

    def test_create_with_relationships(self):
        ctx = self.get_mock_ctx("Subnet", test_properties={'client_config': {
            'region_name': 'aq-testzone-1'
        }}, type_hierarchy=[VPC_TYPE])
        config = {SUBNET_ID: 'subnet', CIDR_BLOCK: 'cidr_block'}
        self.subnet.resource_id = config[SUBNET_ID]
        iface = MagicMock()
        iface.create = self.mock_return({SUBNET: config})
        with patch('cloudify_aws.common.utils.find_rel_by_node_type'):
            subnet.create(ctx=ctx, iface=iface, resource_config=config)
            self.assertEqual(self.subnet.resource_id,
                             'subnet')

    def test_delete(self):
        ctx = self.get_mock_ctx("Subnet")
        iface = MagicMock()
        subnet.delete(ctx=ctx, iface=iface, resource_config={})
        self.assertTrue(iface.delete.called)

    def test_modify_subnet_attribute(self):
        ctx = self.get_mock_ctx("Subnet")
        iface = MagicMock()
        iface.status = 0
        self.subnet.resource_id = 'test_name'
        try:
            subnet.modify_subnet_attribute(
                ctx, iface, {SUBNET_ID: self.subnet.resource_id})
        except OperationRetry:
            pass
        self.assertTrue(iface.modify_subnet_attribute.called)

    def test_check_drift(self):
        original_value = {
            SUBNET_ID: 'baz',
            CIDR_BLOCK: '10.10.0.0/24',
            'AvailabilityZone': 'aq-testzone-1',
            VPC_ID: 'vpc',
            'TagSpecifications': [
                {
                    'ResourceType': 'subnet',
                    'Tags': [{'Key': 'Owner', 'Value': 'foo'}]
                }
            ]
        }
        next_value = {
            SUBNET_ID: 'baz',
            CIDR_BLOCK: '10.10.0.0/24',
            'AvailabilityZone': 'aq-testzone-1',
            VPC_ID: 'vpc',
            'TagSpecifications': [
                {
                    'ResourceType': 'subnet',
                    'Tags': [{'Key': 'Owner', 'Value': 'bar'}]
                }
            ]
        }
        ctx = self.get_mock_ctx(
            "Subnet",
            {
                'client_config': {
                    'region_name': 'aq-testzone-1'
                }
            }
        )
        self.subnet.resource_id = 'baz'
        ctx.instance.runtime_properties.update({
                'aws_resource_id': 'baz',
                'expected_configuration': original_value,
                'previous_configuration': {},
                'create_response': original_value
            })
        current_ctx.set(ctx)
        self.subnet.import_configuration(
            ctx.node.properties.get('resource_config', {}),
            ctx.instance.runtime_properties
        )
        self.subnet.client = self.make_client_function(
            'describe_subnets',
            return_value={'Subnets': [next_value]})
        expected = {
            'values_changed': {
                "root['TagSpecifications'][0]['Tags'][0]['Value']": {
                    'new_value': 'bar', 'old_value': 'foo'
                }
            }
        }
        message = 'The EC2 Subnet baz configuration ' \
                  'has drifts: {}'.format(expected)
        with self.assertRaises(RuntimeError) as e:
            subnet.check_drift(ctx=ctx, iface=self.subnet)
            self.assertIn(message, str(e))


if __name__ == '__main__':
    unittest.main()

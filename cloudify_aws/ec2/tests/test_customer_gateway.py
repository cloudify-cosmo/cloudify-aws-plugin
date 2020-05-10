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
from cloudify_aws.ec2.resources import customer_gateway
from cloudify_aws.common.tests.test_base import (
    TestBase,
    mock_decorator
)
from cloudify_aws.ec2.resources.customer_gateway import (
    EC2CustomerGateway,
    CUSTOMERGATEWAYS,
    CUSTOMERGATEWAY_ID,
    ELASTICIP_TYPE)


class TestEC2VPNGateway(TestBase):

    def setUp(self):
        self.customer_gateway = EC2CustomerGateway("ctx_node",
                                                   resource_id=True,
                                                   client=True, logger=None)
        mock1 = patch('cloudify_aws.common.decorators.aws_resource',
                      mock_decorator)
        mock2 = patch('cloudify_aws.common.decorators.wait_for_status',
                      mock_decorator)
        mock3 = patch('cloudify_aws.common.decorators.wait_for_delete',
                      mock_decorator)
        mock1.start()
        mock2.start()
        mock3.start()
        reload_module(customer_gateway)

    def test_class_properties(self):
        effect = self.get_client_error_exception(name='EC2 VPN '
                                                      'Gateway Bucket')
        self.customer_gateway.client = \
            self.make_client_function('describe_customer_gateways',
                                      side_effect=effect)
        res = self.customer_gateway.properties
        self.assertIsNone(res)

        value = {}
        self.customer_gateway.client = \
            self.make_client_function('describe_customer_gateways',
                                      return_value=value)
        res = self.customer_gateway.properties
        self.assertIsNone(res)

        value = {CUSTOMERGATEWAYS: [{CUSTOMERGATEWAY_ID: 'test_name'}]}
        self.customer_gateway.client = \
            self.make_client_function('describe_customer_gateways',
                                      return_value=value)
        res = self.customer_gateway.properties
        self.assertEqual(res[CUSTOMERGATEWAY_ID], 'test_name')

    def test_class_status(self):
        value = {}
        self.customer_gateway.client = \
            self.make_client_function('describe_customer_gateways',
                                      return_value=value)
        res = self.customer_gateway.status
        self.assertIsNone(res)

        value = {CUSTOMERGATEWAYS: [{CUSTOMERGATEWAY_ID: 'test_name',
                                     'State': 'available'}]}
        self.customer_gateway.client = \
            self.make_client_function('describe_customer_gateways',
                                      return_value=value)
        res = self.customer_gateway.status
        self.assertEqual(res, 'available')

    def test_class_create(self):
        value = {'CustomerGateway': 'test'}
        self.customer_gateway.client = \
            self.make_client_function('create_customer_gateway',
                                      return_value=value)
        res = self.customer_gateway.create(value)
        self.assertEqual(res['CustomerGateway'], value['CustomerGateway'])

    def test_class_delete(self):
        params = {}
        self.customer_gateway.client = \
            self.make_client_function('delete_customer_gateway')
        self.customer_gateway.delete(params)
        self.assertTrue(self.customer_gateway.client.delete_customer_gateway
                        .called)

        params = {'CustomerGateway': 'customer gateway'}
        self.customer_gateway.delete(params)
        self.assertEqual(params['CustomerGateway'], 'customer gateway')

    def test_prepare(self):
        ctx = self.get_mock_ctx("CustomerGateway")
        config = {CUSTOMERGATEWAY_ID: 'customer gateway'}
        customer_gateway.prepare(ctx, config)
        self.assertEqual(ctx.instance.runtime_properties['resource_config'],
                         config)

    def test_create(self):
        ctx = self.get_mock_ctx("CustomerGateway")
        config = {CUSTOMERGATEWAY_ID: 'customer gateway'}
        self.customer_gateway.resource_id = config[CUSTOMERGATEWAY_ID]
        iface = MagicMock()
        iface.create = self.mock_return({'CustomerGateway': config})
        customer_gateway.create(ctx=ctx, iface=iface, resource_config=config)
        self.assertEqual(self.customer_gateway.resource_id,
                         'customer gateway')

    def test_create_with_relationships(self):
        ctx = self.get_mock_ctx("CustomerGateway",
                                type_hierarchy=[ELASTICIP_TYPE])
        config = {'Type': 'type'}
        self.customer_gateway.resource_id = config['Type']
        iface = MagicMock()
        iface.create = self.mock_return({'CustomerGateway': config})
        with patch('cloudify_aws.common.utils.find_rel_by_node_type'):
            customer_gateway.create(
                ctx=ctx, iface=iface, resource_config=config)
            self.assertEqual(self.customer_gateway.resource_id,
                             'type')

    def test_delete(self):
        ctx = self.get_mock_ctx("CustomerGateway")
        iface = MagicMock()
        customer_gateway.delete(ctx=ctx, iface=iface, resource_config={})
        self.assertTrue(iface.delete.called)


if __name__ == '__main__':
    unittest.main()

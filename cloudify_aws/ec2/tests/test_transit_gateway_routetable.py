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
from cloudify_aws.common.tests.test_base import (
    TestBase,
    mock_decorator
)
from cloudify_aws.ec2.resources import transit_gateway_routetable as mod


class TestEC2RouteTable(TestBase):

    def setUp(self):
        self.routetable = mod.EC2TransitGatewayRouteTable(
            "ctx_node", resource_id=True, client=True, logger=None)
        mock1 = patch('cloudify_aws.common.decorators.aws_resource',
                      mock_decorator)
        mock2 = patch('cloudify_aws.common.decorators.wait_for_status',
                      mock_decorator)
        mock1.start()
        mock2.start()
        reload_module(mod)

    def test_class_properties(self):
        effect = self.get_client_error_exception(
            name='EC2 Transit Gateway Route Table')
        self.routetable.client = \
            self.make_client_function('describe_transit_gateway_route_tables',
                                      side_effect=effect)
        self.assertIsNone(self.routetable.properties)

        value = {}
        self.routetable.client = \
            self.make_client_function('describe_transit_gateway_route_tables',
                                      return_value=value)
        self.assertIsNone(self.routetable.properties)

        value = {mod.ROUTETABLES: [{mod.ROUTETABLE_ID: 'test_name'}]}
        self.routetable.client = \
            self.make_client_function('describe_transit_gateway_route_tables',
                                      return_value=value)
        res = self.routetable.properties
        self.assertEqual(res[mod.ROUTETABLE_ID], 'test_name')

    def test_class_create(self):
        value = {mod.ROUTETABLE: 'foo'}
        self.routetable.client = \
            self.make_client_function('create_transit_gateway_route_table',
                                      return_value=value)
        res = self.routetable.create(value)
        self.assertEqual(res[mod.ROUTETABLE], value[mod.ROUTETABLE])

    def test_class_delete(self):
        params = {}
        self.routetable.client = self.make_client_function(
            'delete_transit_gateway_route_table')
        self.routetable.delete(params)
        self.assertTrue(
            self.routetable.client.delete_transit_gateway_route_table.called)
        params = {mod.ROUTETABLE: 'foo'}
        self.routetable.delete(params)
        self.assertEqual(params[mod.ROUTETABLE], 'foo')

    def test_class_attach(self):
        value = {mod.ROUTETABLE_ID: 'foo', mod.TG_ATTACHMENT_ID: 'bar'}
        self.routetable.client = \
            self.make_client_function('associate_transit_gateway_route_table',
                                      return_value=value)
        res = self.routetable.attach(value)
        self.assertEqual(res[mod.ROUTETABLE_ID], value[mod.ROUTETABLE_ID])

    def test_class_detach(self):
        params = {}
        self.routetable.client = self.make_client_function(
            'disassociate_transit_gateway_route_table')
        self.routetable.detach(params)
        self.assertTrue(
            self.routetable.client
                .disassociate_transit_gateway_route_table.called)
        # ctx = self.get_mock_ctx("TransitGatewayRouteTable")
        params = {}
        self.routetable.detach(params)
        self.assertTrue(
            self.routetable.client
                .disassociate_transit_gateway_route_table.called)

    def test_create(self):
        ctx = self.get_mock_ctx("RouteTable")
        config = {mod.TG_ID: 'foo'}
        self.routetable.resource_id = 'foo'
        iface = MagicMock()
        iface.create = self.mock_return({mod.ROUTETABLE: config})
        mod.create(ctx=ctx, iface=iface, resource_config=config)
        self.assertEqual(self.routetable.resource_id, 'foo')

    def test_attach(self):
        ctx = self.get_mock_ctx("RouteTable")
        self.routetable.resource_id = 'foo'
        config = {mod.ROUTETABLE_ID: 'foo', mod.TG_ATTACHMENT_ID: 'bar'}
        iface = MagicMock()
        iface.attach = self.mock_return(config)
        with patch('cloudify_aws.common.utils.find_rel_by_node_type'):
            mod.attach(ctx, iface, config)
        self.assertEqual(self.routetable.resource_id,
                         'foo')

    def test_delete(self):
        ctx = self.get_mock_ctx("RouteTable")
        iface = MagicMock()
        mod.delete(ctx=ctx, iface=iface, resource_config={})
        self.assertTrue(iface.delete.called)

    def test_detach(self):
        ctx = self.get_mock_ctx("RouteTable")
        self.routetable.resource_id = 'route table'
        ctx.instance.runtime_properties['association_ids'] = ['association_id']
        iface = MagicMock()
        iface.detach = self.mock_return(ctx.instance.runtime_properties[
                                        'association_ids'])
        mod.detach(ctx, iface, {})
        self.assertEqual(self.routetable.resource_id,
                         'route table')


if __name__ == '__main__':
    unittest.main()

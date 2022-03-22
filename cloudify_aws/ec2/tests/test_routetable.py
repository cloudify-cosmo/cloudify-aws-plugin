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
from cloudify.exceptions import OperationRetry

# Local imports
from cloudify_aws.common._compat import reload_module
from cloudify_aws.ec2.resources import routetable
from cloudify_aws.common.tests.test_base import (
    TestBase,
    mock_decorator
)
from cloudify_aws.ec2.resources.routetable import (
    EC2RouteTable,
    ROUTETABLES,
    ROUTETABLE_ID,
    VPC_ID,
    VPC_TYPE,
    SUBNET_ID,
    SUBNET_TYPE,
    ASSOCIATION_ID
)


class TestEC2RouteTable(TestBase):

    def setUp(self):
        self.routetable = EC2RouteTable("ctx_node", resource_id='test_name',
                                        client=MagicMock(), logger=None)
        mock1 = patch('cloudify_aws.common.decorators.aws_resource',
                      mock_decorator)
        mock2 = patch('cloudify_aws.common.decorators.wait_for_status',
                      mock_decorator)
        mock1.start()
        mock2.start()
        reload_module(routetable)

    def test_class_properties(self):
        effect = self.get_client_error_exception(name='EC2 Route Table')
        self.routetable.client = \
            self.make_client_function('describe_route_tables',
                                      side_effect=effect)
        res = self.routetable.properties
        self.assertEqual(res, {})

        value = {}
        self.routetable.client = \
            self.make_client_function('describe_route_tables',
                                      return_value=value)
        res = self.routetable.properties
        self.assertEqual(res, {})

    def test_class_properties_not_empty(self):

        value = {ROUTETABLES: [{ROUTETABLE_ID: 'test_name'}]}
        self.routetable.client = self.make_client_function(
            'describe_route_tables', return_value=value)
        self.assertEqual(
            self.routetable.properties[ROUTETABLE_ID], 'test_name')

    def test_class_create(self):
        value = {'RouteTable': 'test'}
        self.routetable.client = \
            self.make_client_function('create_route_table',
                                      return_value=value)
        res = self.routetable.create(value)
        self.assertEqual(res['RouteTable'], value['RouteTable'])

    def test_class_delete(self):
        params = {}
        self.routetable.client = self.make_client_function('delete'
                                                           '_route_table')
        self.routetable.delete(params)
        self.assertTrue(self.routetable.client.delete_route_table
                        .called)

        params = {'RouteTable': 'route table'}
        self.routetable.delete(params)
        self.assertEqual(params['RouteTable'], 'route table')

    def test_class_attach(self):
        value = {ASSOCIATION_ID: 'test'}
        self.routetable.client = \
            self.make_client_function('associate_route_table',
                                      return_value=value)
        res = self.routetable.attach(value)
        self.assertEqual(res[ASSOCIATION_ID], value[ASSOCIATION_ID])

    def test_class_detach(self):
        params = {}
        self.routetable.client = self.make_client_function('disassociate'
                                                           '_route_table')
        self.routetable.detach(params)
        self.assertTrue(self.routetable.client.disassociate_route_table
                        .called)
        ctx = self.get_mock_ctx("RouteTable")
        ctx.instance.runtime_properties['association_ids'] = 'association_ids'
        params = {}
        self.routetable.delete(params)
        self.assertTrue(self.routetable.client.disassociate_route_table
                        .called)

    def test_prepare(self):
        ctx = self.get_mock_ctx("RouteTable")
        config = {ROUTETABLE_ID: 'route table'}
        iface = MagicMock()
        iface.prepare = self.mock_return(config)
        routetable.prepare(ctx, iface, config)
        self.assertEqual(ctx.instance.runtime_properties['resource_config'],
                         config)

    def test_create(self):
        ctx = self.get_mock_ctx("RouteTable")
        config = {ROUTETABLE_ID: 'route table', VPC_ID: 'vpc'}
        self.routetable.resource_id = config[ROUTETABLE_ID]
        iface = MagicMock()
        iface.create = self.mock_return({'RouteTable': config})
        routetable.create(ctx=ctx, iface=iface, resource_config=config)
        self.assertEqual(self.routetable.resource_id,
                         'route table')

    def test_create_with_relationships(self):
        ctx = self.get_mock_ctx("RouteTable", type_hierarchy=[VPC_TYPE])
        config = {}
        self.routetable.resource_id = 'routetable'
        iface = MagicMock()
        iface.create = self.mock_return({'RouteTable': config})
        with patch('cloudify_aws.common.utils.find_rel_by_node_type'):
            routetable.create(ctx=ctx, iface=iface, resource_config=config)
            self.assertEqual(self.routetable.resource_id,
                             'routetable')

    def test_attach(self):
        ctx = self.get_mock_ctx("RouteTable")
        self.routetable.resource_id = 'route table'
        config = {ROUTETABLE_ID: 'route table', SUBNET_ID: 'subnet'}
        iface = MagicMock()
        iface.attach = self.mock_return(config)
        routetable.attach(ctx, iface, config)
        self.assertEqual(self.routetable.resource_id,
                         'route table')

    def test_attach_with_relationships(self):
        ctx = self.get_mock_ctx("RouteTable", type_hierarchy=[SUBNET_TYPE])
        config = {}
        self.routetable.resource_id = 'route table'
        iface = MagicMock()
        iface.attach = self.mock_return(config)
        iface.resource_id = self.mock_return('route table')
        with patch('cloudify_aws.common.utils.find_rels_by_node_type'):
            routetable.attach(ctx, iface, config)
            self.assertEqual(self.routetable.resource_id,
                             'route table')

    def test_delete(self):
        ctx = self.get_mock_ctx("RouteTable")
        iface = MagicMock()
        with self.assertRaises(OperationRetry):
            routetable.delete(ctx=ctx, iface=iface, resource_config={})
        self.assertTrue(iface.delete.called)

    def test_detach(self):
        ctx = self.get_mock_ctx("RouteTable")
        self.routetable.resource_id = 'route table'
        ctx.instance.runtime_properties['association_ids'] = ['association_id']
        iface = MagicMock()
        iface.detach = self.mock_return(ctx.instance.runtime_properties[
                                        'association_ids'])
        routetable.detach(ctx, iface, {})
        self.assertEqual(self.routetable.resource_id,
                         'route table')


if __name__ == '__main__':
    unittest.main()

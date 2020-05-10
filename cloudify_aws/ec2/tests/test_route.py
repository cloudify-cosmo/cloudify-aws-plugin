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
from cloudify_aws.ec2.resources import route
from cloudify_aws.common.tests.test_base import (
    TestBase,
    mock_decorator
)
from cloudify_aws.ec2.resources.route import (
    EC2Route,
    ROUTETABLE_ID,
    ROUTETABLE_TYPE,
    GATEWAY_ID,
    INTERNETGATEWAY_TYPE
)


class TestEC2Route(TestBase):

    def setUp(self):
        self.route = EC2Route("ctx_node", resource_id=True,
                              client=True, logger=None)
        mock1 = patch('cloudify_aws.common.decorators.aws_resource',
                      mock_decorator)
        mock1.start()
        reload_module(route)

    def test_class_create(self):
        value = True
        config = {ROUTETABLE_ID: 'test'}
        self.route.client = \
            self.make_client_function('create_route',
                                      return_value=value)
        res = self.route.create(config)
        self.assertEqual(True, res)

    def test_class_delete(self):
        params = {}
        self.route.client = self.make_client_function('delete_route')
        self.route.delete(params)
        self.assertTrue(self.route.client.delete_route
                        .called)

        params = {ROUTETABLE_ID: 'route table'}
        self.route.delete(params)
        self.assertEqual(params[ROUTETABLE_ID], 'route table')

    def test_prepare(self):
        ctx = self.get_mock_ctx("RouteTable")
        config = {ROUTETABLE_ID: 'route table'}
        iface = MagicMock()
        iface.prepare = self.mock_return(config)
        route.prepare(ctx, iface, config)
        self.assertEqual(ctx.instance.runtime_properties['resource_config'],
                         config)

    def test_create(self):
        ctx = self.get_mock_ctx("RouteTable")
        config = {ROUTETABLE_ID: 'route table',
                  GATEWAY_ID: 'gateway', 'DestinationCidrBlock': '0.0.0.0/0'}
        self.route.resource_id = config[ROUTETABLE_ID]
        iface = MagicMock()
        iface.create = self.mock_return(config)
        route.create(ctx, iface, config)
        self.assertEqual(self.route.resource_id,
                         'route table')

    def test_create_with_relationships(self):
        ctx = self.get_mock_ctx("RouteTable",
                                type_hierarchy=[ROUTETABLE_TYPE,
                                                INTERNETGATEWAY_TYPE])
        config = {'DestinationCidrBlock': '0.0.0.0/0'}
        self.route.resource_id = 'routetable'
        iface = MagicMock()
        iface.create = self.mock_return(config)
        with patch('cloudify_aws.common.utils.find_rel_by_node_type'):
            route.create(ctx, iface, config)
            self.assertEqual(self.route.resource_id,
                             'routetable')

    def test_delete(self):
        ctx = self.get_mock_ctx("RouteTable")
        iface = MagicMock()
        config = {ROUTETABLE_ID: 'route table',
                  'DestinationCidrBlock': '0.0.0.0/0'}
        route.delete(ctx, iface, config)
        self.assertTrue(iface.delete.called)

    def test_delete_with_relationship(self):
        ctx = self.get_mock_ctx("RouteTable", type_hierarchy=[ROUTETABLE_TYPE])
        iface = MagicMock()
        config = {'DestinationCidrBlock': '0.0.0.0/0'}
        with patch('cloudify_aws.common.utils.find_rel_by_node_type'):
            route.delete(ctx, iface, config)
            self.assertTrue(iface.delete.called)


if __name__ == '__main__':
    unittest.main()

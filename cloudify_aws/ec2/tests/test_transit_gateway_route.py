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
from cloudify_aws.ec2.resources import transit_gateway_route as mod
from cloudify_aws.ec2.resources.transit_gateway import TG_ATTACHMENT_ID
from cloudify_aws.ec2.resources.transit_gateway_routetable import ROUTETABLE_ID


class TestEC2TransitGatewayRoute(TestBase):

    def setUp(self):
        self.route = mod.EC2TransitGatewayRoute(
            "ctx_node", resource_id=True,
            client=True, logger=None)
        mock1 = patch('cloudify_aws.common.decorators.aws_resource',
                      mock_decorator)
        mock1.start()
        reload_module(mod)

    def test_class_create(self):
        value = True
        config = {ROUTETABLE_ID: 'foo'}
        self.route.client = self.make_client_function(
            'create_transit_gateway_route', return_value=value)
        res = self.route.create(config)
        self.assertEqual(True, res)

    def test_class_delete(self):
        params = {}
        self.route.client = self.make_client_function(
            'delete_transit_gateway_route')
        self.route.delete(params)
        self.assertTrue(self.route.client.delete_transit_gateway_route.called)
        params = {ROUTETABLE_ID: 'foo'}
        self.route.delete(params)
        self.assertEqual(params[ROUTETABLE_ID], 'foo')

    def test_create(self):
        ctx = self.get_mock_ctx("RouteTable")
        config = {
            ROUTETABLE_ID: 'foo',
            TG_ATTACHMENT_ID: 'bar',
            'DestinationCidrBlock': '0.0.0.0/0'
        }
        self.route.resource_id = config[ROUTETABLE_ID]
        iface = MagicMock()
        iface.create = self.mock_return(config)
        mod.create(ctx, iface, config)
        self.assertEqual(self.route.resource_id, 'foo')

    def test_delete(self):
        ctx = self.get_mock_ctx("RouteTable")
        iface = MagicMock()
        config = {
            ROUTETABLE_ID: 'route table',
            'DestinationCidrBlock': '0.0.0.0/0'
        }
        mod.delete(ctx, iface, config)
        self.assertTrue(iface.delete.called)


if __name__ == '__main__':
    unittest.main()

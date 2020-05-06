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
from cloudify_aws.common import constants
from cloudify_aws.ec2.resources import vpn_connection_route
from cloudify_aws.ec2.resources.vpn_connection_route\
    import EC2VPNConnectionRoute
from cloudify_aws.common.tests.test_base import (
    TestBase,
    mock_decorator
)


class TestEC2VPNConnectionRoute(TestBase):

    def setUp(self):
        super(TestEC2VPNConnectionRoute, self).setUp()
        self.vpn_connection_route =\
            EC2VPNConnectionRoute("ctx_node",
                                  resource_id=True,
                                  client=True, logger=None)
        mock1 = patch('cloudify_aws.common.decorators.aws_resource',
                      mock_decorator)
        mock1.start()
        reload_module(vpn_connection_route)

    def test_class_create(self):
        params = \
            {
                'DestinationCidrBlock': 'destination_cidr_block',
                'VpnConnectionId': 'vpn_connection_id_test',
            }
        response = None

        self.vpn_connection_route.client = self.make_client_function(
            'create_vpn_connection_route', return_value=response)
        self.assertEqual(self.vpn_connection_route.create(params), None)

    def test_class_delete(self):
        params = \
            {
                'DestinationCidrBlock': 'destination_cidr_block',
                'VpnConnectionId': 'vpn_connection_id_test',
            }
        response = None

        self.vpn_connection_route.client = self.make_client_function(
            'delete_vpn_connection_route', return_value=response)
        self.assertEqual(self.vpn_connection_route.delete(params), None)

    def test_prepare(self):
        ctx = self.get_mock_ctx("EC2VPNConnectionRoute")
        vpn_connection_route.prepare(ctx, 'config')
        self.assertEqual(
            ctx.instance.runtime_properties['resource_config'],
            'config')

    def test_create(self):
        iface = MagicMock()
        ctx = self.get_mock_ctx("EC2VPNConnectionRoute")

        config = \
            {
                'DestinationCidrBlock': 'destination_cidr_block',
                'VpnConnectionId': 'vpn_connection_id_test',
            }
        response = None
        iface.create = self.mock_return(response)
        vpn_connection_route.create(ctx, iface, config)
        self.assertEqual(
            ctx.instance.runtime_properties[constants.EXTERNAL_RESOURCE_ID],
            'vpn_connection_id_test'
        )

    def test_delete(self):
        iface = MagicMock()
        ctx = self.get_mock_ctx("EC2VPNConnectionRoute")
        vpn_connection_route.delete(ctx, iface, {})
        self.assertTrue(iface.delete.called)


if __name__ == '__main__':
    unittest.main()

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
from cloudify_aws.ec2.resources import vpn_gateway
from cloudify_aws.common.tests.test_base import (
    TestBase,
    mock_decorator
)
from cloudify_aws.ec2.resources.vpn_gateway import (
    EC2VPNGateway,
    VPNGATEWAYS,
    VPNGATEWAY_ID,
    VPC_ID,
    VPC_TYPE
)


class TestEC2VPNGateway(TestBase):

    def setUp(self):
        self.vpn_gateway = EC2VPNGateway("ctx_node", resource_id='test_name',
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
        reload_module(vpn_gateway)

    def test_class_properties(self):
        effect = self.get_client_error_exception(name='EC2 VPN '
                                                      'Gateway Bucket')
        self.vpn_gateway.client = \
            self.make_client_function('describe_vpn_gateways',
                                      side_effect=effect)
        res = self.vpn_gateway.properties
        self.assertEqual(res, {})

        value = {}
        self.vpn_gateway.client = \
            self.make_client_function('describe_vpn_gateways',
                                      return_value=value)
        res = self.vpn_gateway.properties
        self.assertEqual(res, {})

        value = {VPNGATEWAYS: [{VPNGATEWAY_ID: 'test_name'}]}
        self.vpn_gateway.client = \
            self.make_client_function('describe_vpn_gateways',
                                      return_value=value)
        res = self.vpn_gateway.properties
        self.assertEqual(res[VPNGATEWAY_ID], 'test_name')

    def test_class_status(self):
        value = {}
        self.vpn_gateway.client = self.make_client_function('describe_vpn'
                                                            '_gateways',
                                                            return_value=value)
        res = self.vpn_gateway.status
        self.assertIsNone(res)

        value = {VPNGATEWAYS: [{VPNGATEWAY_ID: 'test_name',
                                'State': 'available'}]}
        self.vpn_gateway.client = self.make_client_function('describe_vpn'
                                                            '_gateways',
                                                            return_value=value)
        res = self.vpn_gateway.status
        self.assertEqual(res, 'available')

    def test_class_create(self):
        value = {'VpnGateway': 'test'}
        self.vpn_gateway.client = \
            self.make_client_function('create_vpn_gateway',
                                      return_value=value)
        res = self.vpn_gateway.create(value)
        self.assertEqual(res['VpnGateway'], value['VpnGateway'])

    def test_class_delete(self):
        params = {}
        self.vpn_gateway.client = \
            self.make_client_function('delete_vpn_gateway')
        self.vpn_gateway.delete(params)
        self.assertTrue(self.vpn_gateway.client.delete_vpn_gateway
                        .called)

        params = {'VpnGateway': 'vpn gateway'}
        self.vpn_gateway.delete(params)
        self.assertEqual(params['VpnGateway'], 'vpn gateway')

    def test_class_attach(self):
        value = {'VpcAttachment': {VPNGATEWAY_ID: 'vpn', VPC_ID: 'vpc'}}
        self.vpn_gateway.client = \
            self.make_client_function('attach_vpn_gateway',
                                      return_value=value)
        with patch('cloudify_aws.ec2.resources.vpn_gateway'
                   '.EC2VPNGateway.attach'):
            res = self.vpn_gateway.attach(value)
            self.assertEqual(res[VPC_ID], value['VpcAttachment'][VPC_ID])

    def test_class_detach(self):
        params = {}
        self.vpn_gateway.client = \
            self.make_client_function('detach_vpn_gateway')
        self.vpn_gateway.detach(params)
        self.assertTrue(self.vpn_gateway.client.detach_vpn_gateway
                        .called)
        params = {VPNGATEWAY_ID: 'vpn', VPC_ID: 'vpc'}
        self.vpn_gateway.delete(params)
        self.assertTrue(self.vpn_gateway.client.detach_vpn_gateway
                        .called)

    def test_prepare(self):
        ctx = self.get_mock_ctx("VpnGateway")
        config = {VPNGATEWAY_ID: 'vpn gateway'}
        vpn_gateway.prepare(ctx, config)
        self.assertEqual(ctx.instance.runtime_properties['resource_config'],
                         config)

    def test_create(self):
        ctx = self.get_mock_ctx("VpnGateway")
        config = {VPNGATEWAY_ID: 'vpn gateway'}
        self.vpn_gateway.resource_id = config[VPNGATEWAY_ID]
        iface = MagicMock()
        iface.create = self.mock_return({'VpnGateway': config})
        vpn_gateway.create(ctx=ctx, iface=iface, resource_config=config)
        self.assertEqual(self.vpn_gateway.resource_id,
                         'vpn gateway')

    def test_attach(self):
        ctx = self.get_mock_ctx("VpnGateway")
        self.vpn_gateway.resource_id = 'vpn gateway'
        config = {VPC_ID: 'vpc', 'Type': type}
        iface = MagicMock()
        iface.attach = self.mock_return(config)
        vpn_gateway.attach(ctx, iface, config)
        self.assertEqual(self.vpn_gateway.resource_id,
                         'vpn gateway')

    def test_attach_with_relationships(self):
        ctx = self.get_mock_ctx("VpnGateway", type_hierarchy=[VPC_TYPE])
        config = {VPNGATEWAY_ID: 'vpn gateway', 'Type': type}
        self.vpn_gateway.resource_id = config[VPNGATEWAY_ID]
        iface = MagicMock()
        iface.attach = self.mock_return(config)
        with patch('cloudify_aws.common.utils.find_rel_by_node_type'):
            vpn_gateway.attach(ctx, iface, config)
            self.assertEqual(self.vpn_gateway.resource_id,
                             'vpn gateway')

    def test_delete(self):
        ctx = self.get_mock_ctx("VpnGateway")
        iface = MagicMock()
        vpn_gateway.delete(ctx=ctx, iface=iface, resource_config={})
        self.assertTrue(iface.delete.called)

    def test_detach(self):
        ctx = self.get_mock_ctx("VpnGateway")
        self.vpn_gateway.resource_id = 'vpn gateway'
        config = {VPC_ID: 'vpc'}
        iface = MagicMock()
        iface.detach = self.mock_return(config)
        vpn_gateway.detach(ctx, iface, config)
        self.assertEqual(self.vpn_gateway.resource_id,
                         'vpn gateway')

    def test_detach_with_relationships(self):
        ctx = self.get_mock_ctx("VpnGateway", type_hierarchy=[VPC_TYPE])
        config = {VPNGATEWAY_ID: 'vpn gateway'}
        self.vpn_gateway.resource_id = config[VPNGATEWAY_ID]
        iface = MagicMock()
        iface.detach = self.mock_return(config)
        ctx.instance.runtime_properties['vpc_id'] = 'vpc'
        vpn_gateway.detach(ctx, iface, config)
        self.assertEqual(self.vpn_gateway.resource_id,
                         'vpn gateway')


if __name__ == '__main__':
    unittest.main()

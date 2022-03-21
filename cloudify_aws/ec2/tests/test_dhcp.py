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
from cloudify_aws.ec2.resources import dhcp
from cloudify_aws.common.tests.test_base import (
    TestBase,
    mock_decorator
)
from cloudify_aws.ec2.resources.dhcp import (
    EC2DHCPOptions,
    DHCPOPTIONS, DHCPOPTIONS_ID,
    VPC_ID,
    VPC_TYPE
)


class TestEC2DHCPOptions(TestBase):

    def setUp(self):
        self.dhcp = EC2DHCPOptions("ctx_node", resource_id='test_name',
                                   client=True, logger=None)
        mock1 = patch('cloudify_aws.common.decorators.aws_resource',
                      mock_decorator)
        mock1.start()
        reload_module(dhcp)

    def test_class_properties(self):
        effect = self.get_client_error_exception(name='EC2 Dhcp Options')
        self.dhcp.client = \
            self.make_client_function('describe_dhcp_options',
                                      side_effect=effect)
        res = self.dhcp.properties
        self.assertEqual(res, {})

        value = {}
        self.dhcp.client = \
            self.make_client_function('describe_dhcp_options',
                                      return_value=value)
        res = self.dhcp.properties
        self.assertEqual(res, {})

        value = {DHCPOPTIONS: [{DHCPOPTIONS_ID: 'test_name'}]}
        self.dhcp.client = \
            self.make_client_function('describe_dhcp_options',
                                      return_value=value)
        res = self.dhcp.properties
        self.assertEqual(res[DHCPOPTIONS_ID], 'test_name')

    def test_class_create(self):
        value = {DHCPOPTIONS: 'test'}
        self.dhcp.client = \
            self.make_client_function('create_dhcp_options',
                                      return_value=value)
        res = self.dhcp.create(value)
        self.assertEqual(res[DHCPOPTIONS], value[DHCPOPTIONS])

    def test_class_delete(self):
        params = {}
        self.dhcp.client = self.make_client_function('delete_dhcp_options')
        self.dhcp.delete(params)
        self.assertTrue(self.dhcp.client.delete_dhcp_options
                        .called)

        params = {DHCPOPTIONS: 'dhcp'}
        self.dhcp.delete(params)
        self.assertEqual(params[DHCPOPTIONS], 'dhcp')

    def test_class_attach(self):
        value = {'VpcAttachment': {DHCPOPTIONS_ID: 'dhcp',
                                   VPC_ID: 'vpc'}}
        self.dhcp.client = \
            self.make_client_function('associate_dhcp_options',
                                      return_value=True)
        with patch('cloudify_aws.ec2.resources.dhcp'
                   '.EC2DHCPOptions.attach'):
            res = self.dhcp.attach(value)
            self.assertEqual(True, res)

    def test_class_detach(self):
        params = {}
        self.dhcp.client = \
            self.make_client_function('associate_dhcp_options')
        self.dhcp.detach(params)
        self.assertTrue(self.dhcp.client.associate_dhcp_options
                        .called)
        params = {DHCPOPTIONS_ID: 'dhcp', VPC_ID: 'vpc'}
        self.dhcp.delete(params)
        self.assertTrue(self.dhcp.client.associate_dhcp_options
                        .called)

    def test_prepare(self):
        ctx = self.get_mock_ctx(DHCPOPTIONS)
        config = {DHCPOPTIONS_ID: 'dhcp'}
        dhcp.prepare(ctx, config)
        self.assertEqual(ctx.instance.runtime_properties['resource_config'],
                         config)

    def test_create(self):
        ctx = self.get_mock_ctx(DHCPOPTIONS)
        config = {DHCPOPTIONS_ID: 'dhcp'}
        self.dhcp.resource_id = config[DHCPOPTIONS_ID]
        iface = MagicMock()
        iface.create = self.mock_return({DHCPOPTIONS: config})
        dhcp.create(ctx, iface, config)
        self.assertEqual(self.dhcp.resource_id,
                         'dhcp')

    def test_attach(self):
        ctx = self.get_mock_ctx(DHCPOPTIONS)
        self.dhcp.resource_id = 'dhcp'
        config = {VPC_ID: 'vpc',
                  'DhcpConfigurations': {'Key': 'domain-name',
                                         'Value': ['example.com']}}
        iface = MagicMock()
        iface.attach = self.mock_return(config)
        dhcp.attach(ctx, iface, config)
        self.assertEqual(self.dhcp.resource_id,
                         'dhcp')

    def test_attach_with_relationships(self):
        ctx = self.get_mock_ctx(DHCPOPTIONS, type_hierarchy=[VPC_TYPE])
        config = {DHCPOPTIONS_ID: 'dhcp',
                  'DhcpConfigurations': {'Key': 'domain-name',
                                         'Value': ['example.com']}}
        self.dhcp.resource_id = config[DHCPOPTIONS_ID]
        iface = MagicMock()
        iface.attach = self.mock_return(config)
        with patch('cloudify_aws.common.utils.find_rel_by_node_type'):
            dhcp.attach(ctx, iface, config)
            self.assertEqual(self.dhcp.resource_id,
                             'dhcp')

    def test_delete(self):
        ctx = self.get_mock_ctx(DHCPOPTIONS)
        iface = MagicMock()
        dhcp.delete(ctx, iface, {})
        self.assertTrue(iface.delete.called)

    def test_detach(self):
        ctx = self.get_mock_ctx(DHCPOPTIONS)
        self.dhcp.resource_id = 'dhcp'
        config = {VPC_ID: 'vpc'}
        iface = MagicMock()
        iface.detach = self.mock_return(config)
        dhcp.detach(ctx, iface, config)
        self.assertEqual(self.dhcp.resource_id,
                         'dhcp')

    def test_detach_with_relationships(self):
        ctx = self.get_mock_ctx(DHCPOPTIONS, type_hierarchy=[VPC_TYPE])
        config = {DHCPOPTIONS_ID: 'dhcp'}
        self.dhcp.resource_id = config[DHCPOPTIONS_ID]
        iface = MagicMock()
        iface.detach = self.mock_return(config)
        ctx.instance.runtime_properties['vpc_id'] = None
        with patch('cloudify_aws.common.utils.find_rel_by_node_type'):
            dhcp.detach(ctx, iface, config)
            self.assertEqual(self.dhcp.resource_id,
                             'dhcp')


if __name__ == '__main__':
    unittest.main()

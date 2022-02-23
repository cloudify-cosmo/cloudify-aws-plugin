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
import copy
import unittest

# Third party imports
from mock import patch, MagicMock

# Local imports
from cloudify_aws.common._compat import reload_module
from cloudify_aws.ec2.resources import eni
from cloudify_aws.common.tests.test_base import (
    TestBase,
    mock_decorator
)
from cloudify_aws.ec2.resources.eni import (
    EC2NetworkInterface,
    NETWORKINTERFACES,
    NETWORKINTERFACE_ID,
    SUBNET_ID,
    SUBNET_TYPE,
    INSTANCE_TYPE_DEPRECATED,
    ATTACHMENT_ID,
    SEC_GROUPS, SEC_GROUP_TYPE
)


class TestEC2NetworkInterface(TestBase):

    def setUp(self):
        self.eni = EC2NetworkInterface("ctx_node", resource_id=True,
                                       client=True, logger=None)
        mock1 = patch('cloudify_aws.common.decorators.aws_resource',
                      mock_decorator)
        mock2 = patch('cloudify_aws.common.decorators.wait_for_status',
                      mock_decorator)
        mock1.start()
        mock2.start()
        reload_module(eni)

    def test_class_properties(self):
        effect = self.get_client_error_exception(name='EC2 Network Interface')
        self.eni.client = self.make_client_function(
            'describe_network_interfaces', side_effect=effect)
        res = self.eni.properties
        self.assertEqual(res, {})

        value = {}
        self.eni.client = self.make_client_function(
            'describe_network_interfaces', return_value=value)
        res = self.eni.properties
        self.assertEqual(res, {})

        self.eni.resource_id = 'test_name'
        value = {NETWORKINTERFACES: [{NETWORKINTERFACE_ID: 'test_name'}]}
        self.eni.client = self.make_client_function(
            'describe_network_interfaces', return_value=value)
        self.assertEqual(self.eni.properties[NETWORKINTERFACE_ID], 'test_name')

    def test_class_status(self):
        value = {}
        self.eni.client = \
            self.make_client_function('describe_network_interfaces',
                                      return_value=value)
        res = self.eni.status
        self.assertIsNone(res)

        value = {
            NETWORKINTERFACES: [
                {
                    NETWORKINTERFACE_ID: 'test_name',
                    'Status': 'available'
                }
            ]
        }
        self.eni.resource_id = 'test_name'
        self.eni.client = self.make_client_function(
            'describe_network_interfaces', return_value=value)
        self.assertEqual(self.eni.status, 'available')

    def test_class_create(self):
        value = {'NetworkInterface': {'NetworkInterfaceId': 'test'}}
        self.eni.client = self.make_client_function(
            'create_network_interface', return_value=value)
        self.eni.create(value)
        self.assertEqual(self.eni.create_response, value)

    def test_class_delete(self):
        params = {}
        self.eni.client = \
            self.make_client_function('delete_network_interface')
        self.eni.delete(params)
        self.assertTrue(self.eni.client.delete_network_interface
                        .called)

        params = {'NetworkInterface': 'network interface'}
        self.eni.delete(params)
        self.assertEqual(params['NetworkInterface'], 'network interface')

    def test_class_attach(self):
        value = {ATTACHMENT_ID: 'eni-attach'}
        self.eni.client = \
            self.make_client_function('attach_network_interface',
                                      return_value=value)
        with patch('cloudify_aws.ec2.resources.eni'
                   '.EC2NetworkInterface.attach'):
            res = self.eni.attach(value)
            self.assertEqual(res[ATTACHMENT_ID], value[ATTACHMENT_ID])

    def test_class_detach(self):
        params = {}
        self.eni.client = \
            self.make_client_function('detach_network_interface')
        self.eni.detach(params)
        self.assertTrue(self.eni.client.detach_network_interface
                        .called)
        params = {ATTACHMENT_ID: 'eni-attach'}
        self.eni.delete(params)
        self.assertTrue(self.eni.client.detach_network_interface
                        .called)

    def test_prepare(self):
        ctx = self.get_mock_ctx("NetworkInterface")
        config = {NETWORKINTERFACE_ID: 'eni'}
        eni.prepare(ctx, config)
        self.assertEqual(ctx.instance.runtime_properties['resource_config'],
                         config)

    def test_create(self):
        ctx = self.get_mock_ctx("NetworkInterface")
        config = {NETWORKINTERFACE_ID: 'eni', SUBNET_ID: 'subnet'}
        self.eni.resource_id = config[NETWORKINTERFACE_ID]
        iface = MagicMock()
        iface.create = self.mock_return({'NetworkInterface': config})
        eni.create(ctx=ctx, iface=iface, resource_config=config)
        self.assertEqual(self.eni.resource_id,
                         'eni')

    def test_create_with_groups(self):
        mock_rels = [MagicMock()]
        fake_target = self.get_mock_ctx(
            "SecurityGroup",
            test_runtime_properties={'aws_resource_id': 'group3'},
            type_hierarchy=SEC_GROUP_TYPE)
        setattr(mock_rels[0], 'target', fake_target)
        ctx = self.get_mock_ctx(
            "NetworkInterface", test_relationships=mock_rels)
        config = {
            SUBNET_ID: 'subnet',
            SEC_GROUPS: ['group1', 'group2']
        }
        expected = copy.deepcopy(config[SEC_GROUPS])
        expected.append('group3')
        create_response = {
            'NetworkInterface': {
                'NetworkInterfaceId': 'eni',
            }
        }
        create_response['NetworkInterface'].update(config)
        self.eni.client = self.make_client_function(
            'create_network_interface',
            return_value=create_response
        )
        eni.create(ctx=ctx, iface=self.eni, resource_config=config)
        self.assertEqual(self.eni.resource_id, 'eni')
        self.assertEqual(
            self.eni.create_response['NetworkInterface'][SEC_GROUPS], expected)

    def test_create_wth_modify(self):
        ctx = self.get_mock_ctx("NetworkInterface")
        config = {NETWORKINTERFACE_ID: 'eni', SUBNET_ID: 'subnet'}
        self.eni.resource_id = config[NETWORKINTERFACE_ID]
        iface = MagicMock()
        modify_args = {'SourceDestCheck': {'Value': True}}
        iface.create = self.mock_return({'NetworkInterface': config})
        eni.create(
            ctx=ctx, iface=iface, resource_config=config,
            modify_network_interface_attribute_args=modify_args)
        self.assertEqual(self.eni.resource_id,
                         'eni')

    def test_modify_network_interface_attribute(self):
        ctx = self.get_mock_ctx("NetworkInterface")
        config = \
            {
                NETWORKINTERFACE_ID: 'eni',
                'SourceDestCheck': {'Value': True}
            }
        self.eni.resource_id = config[NETWORKINTERFACE_ID]
        iface = MagicMock()
        iface.modify_network_interface_attribute = \
            self.mock_return(config)
        eni.modify_network_interface_attribute(ctx, iface, config)
        self.assertEqual(self.eni.resource_id,
                         'eni')

    def test_create_with_relationships(self):
        ctx = self.get_mock_ctx("NetworkInterface",
                                type_hierarchy=[SUBNET_TYPE])
        config = {NETWORKINTERFACE_ID: 'eni'}
        self.eni.resource_id = config[NETWORKINTERFACE_ID]
        iface = MagicMock()
        iface.create = self.mock_return({'NetworkInterface': config})
        with patch('cloudify_aws.common.utils.find_rel_by_node_type'):
            eni.create(ctx=ctx, iface=iface, resource_config=config)
            self.assertEqual(self.eni.resource_id,
                             'eni')

    @patch('cloudify_aws.ec2.resources.eni.get_attached_instance_id')
    def test_attach(self, *_):
        ctx = self.get_mock_ctx("NetworkInterface")
        self.eni.resource_id = 'eni'
        config = {ATTACHMENT_ID: 'eni-attach'}
        iface = MagicMock()
        iface.attach = self.mock_return(config)
        eni.attach(ctx, iface, config)
        self.assertEqual(self.eni.resource_id,
                         'eni')

    @patch('cloudify_aws.ec2.resources.eni.get_attached_instance_id')
    def test_attach_with_relationships(self, *_):
        ctx = self.get_mock_ctx("NetworkInterface",
                                type_hierarchy=[INSTANCE_TYPE_DEPRECATED])
        config = {ATTACHMENT_ID: 'eni-attach'}
        self.eni.resource_id = 'eni'
        iface = MagicMock()
        iface.attach = self.mock_return(config)
        with patch('cloudify_aws.common.utils.find_rel_by_node_type'):
            eni.attach(ctx, iface, config)
            self.assertEqual(self.eni.resource_id,
                             'eni')

    def test_delete(self):
        ctx = self.get_mock_ctx("NetworkInterface")
        iface = MagicMock()
        eni.delete(ctx=ctx, iface=iface, resource_config={})
        self.assertTrue(iface.delete.called)
        for prop in ['resource_config',
                     'aws_resource_id',
                     'device_index',
                     'create_response']:
            self.assertTrue(prop not in ctx.instance.runtime_properties)

    def test_detach(self):
        ctx = self.get_mock_ctx("NetworkInterface")
        self.eni.resource_id = 'eni'
        config = {ATTACHMENT_ID: 'eni-attach'}
        iface = MagicMock()
        iface.attachment = {'Status': 'detached', 'AttachmentId': 'foo'}
        iface.detach = self.mock_return(config)
        eni.detach(ctx, iface, config)
        self.assertEqual(self.eni.resource_id, 'eni')

    def test_detach_with_relationships(self):
        ctx = self.get_mock_ctx("NetworkInterface",
                                type_hierarchy=[INSTANCE_TYPE_DEPRECATED])
        config = {NETWORKINTERFACE_ID: 'eni'}
        self.eni.resource_id = config[NETWORKINTERFACE_ID]
        iface = MagicMock()
        iface.attachment = {'Status': 'detached', 'AttachmentId': 'foo'}
        iface.detach = self.mock_return(config)
        ctx.instance.runtime_properties['attachment_id'] = 'eni-attach'
        eni.detach(ctx, iface, config)
        self.assertEqual(self.eni.resource_id, 'eni')


if __name__ == '__main__':
    unittest.main()

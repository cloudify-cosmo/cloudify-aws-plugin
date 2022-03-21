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
from cloudify_aws.ec2.resources import networkacl
from cloudify_aws.common.tests.test_base import (
    TestBase,
    mock_decorator
)
from cloudify_aws.ec2.resources.networkacl import (
    EC2NetworkAcl,
    NETWORKACLS,
    NETWORKACL_ID,
    ASSOCIATION_SUBNET_ID,
    VPC_ID,
    VPC_TYPE,
    SUBNET_ID,
    SUBNET_TYPE,
    ASSOCIATION_ID
)


class TestEC2NetworkAcl(TestBase):

    def setUp(self):
        self.networkacl = EC2NetworkAcl("ctx_node", resource_id='test_name',
                                        client=True, logger=None)
        mock1 = patch('cloudify_aws.common.decorators.aws_resource',
                      mock_decorator)
        mock1.start()
        reload_module(networkacl)

    def test_class_properties(self):
        effect = self.get_client_error_exception(name='EC2 Network Acl')
        self.networkacl.client = \
            self.make_client_function('describe_network_acls',
                                      side_effect=effect)
        res = self.networkacl.properties
        self.assertEquals(res, {})

        value = {}
        self.networkacl.client = \
            self.make_client_function('describe_network_acls',
                                      return_value=value)
        res = self.networkacl.properties
        self.assertEquals(res, {})

        value = {NETWORKACLS: [{NETWORKACL_ID: 'test_name'}]}
        self.networkacl.client = \
            self.make_client_function('describe_network_acls',
                                      return_value=value)
        res = self.networkacl.properties
        self.assertEqual(res[NETWORKACL_ID], 'test_name')

    def test_class_properties_by_filter(self):
        effect = self.get_client_error_exception(name='EC2 Network Acl')
        self.networkacl.client = \
            self.make_client_function('describe_network_acls',
                                      side_effect=effect)
        config = {SUBNET_ID: 'subnet'}
        res = self.networkacl.get_properties_by_filter(ASSOCIATION_SUBNET_ID,
                                                       config[SUBNET_ID])
        self.assertIsNone(res)

        value = {}
        self.networkacl.client = \
            self.make_client_function('describe_network_acls',
                                      return_value=value)
        res = self.networkacl.get_properties_by_filter(ASSOCIATION_SUBNET_ID,
                                                       config[SUBNET_ID])
        self.assertIsNone(res)

        value = {NETWORKACLS: [{NETWORKACL_ID: 'test_name'}]}
        self.networkacl.client = \
            self.make_client_function('describe_network_acls',
                                      return_value=value)
        res = self.networkacl.get_properties_by_filter(ASSOCIATION_SUBNET_ID,
                                                       config[SUBNET_ID])
        self.assertEqual(res[NETWORKACL_ID], 'test_name')

    def test_class_create(self):
        value = {'NetworkAcl': 'test'}
        self.networkacl.client = \
            self.make_client_function('create_network_acl',
                                      return_value=value)
        res = self.networkacl.create(value)
        self.assertEqual(res['NetworkAcl'], value['NetworkAcl'])

    def test_class_delete(self):
        params = {}
        self.networkacl.client = self.make_client_function('delete'
                                                           '_network_acl')
        self.networkacl.delete(params)
        self.assertTrue(self.networkacl.client.delete_network_acl
                        .called)

        params = {'NetworkAcl': 'network acls'}
        self.networkacl.delete(params)
        self.assertEqual(params['NetworkAcl'], 'network acls')

    def test_class_attach(self):
        value = {ASSOCIATION_ID: 'test'}
        self.networkacl.client = \
            self.make_client_function('replace_network_acl_association',
                                      return_value=value)
        res = self.networkacl.replace(value)
        self.assertEqual(res[ASSOCIATION_ID], value[ASSOCIATION_ID])

    def test_class_detach(self):
        params = {}
        self.networkacl.client = \
            self.make_client_function('replace_network_acl_association')
        self.networkacl.replace(params)
        self.assertTrue(self.networkacl.client.replace_network_acl_association
                        .called)
        ctx = self.get_mock_ctx("NetworkAcl")
        ctx.instance.runtime_properties['association_id'] = 'association_id'
        params = {}
        self.networkacl.delete(params)
        self.assertTrue(self.networkacl.client.replace_network_acl_association
                        .called)

    def test_prepare(self):
        ctx = self.get_mock_ctx("NetworkAcl")
        config = {NETWORKACL_ID: 'network acl'}
        networkacl.prepare(ctx, config)
        self.assertEqual(ctx.instance.runtime_properties['resource_config'],
                         config)

    def test_create(self):
        ctx = self.get_mock_ctx("NetworkAcl")
        config = {NETWORKACL_ID: 'network acl', VPC_ID: 'vpc'}
        self.networkacl.resource_id = config[NETWORKACL_ID]
        iface = MagicMock()
        iface.create = self.mock_return({'NetworkAcl': config})
        networkacl.create(ctx=ctx, iface=iface, resource_config=config)
        self.assertEqual(self.networkacl.resource_id,
                         'network acl')

    def test_create_with_relationships(self):
        ctx = self.get_mock_ctx("NetworkAcl", type_hierarchy=[VPC_TYPE])
        config = {}
        self.networkacl.resource_id = 'networkacl'
        iface = MagicMock()
        iface.create = self.mock_return({'NetworkAcl': config})
        with patch('cloudify_aws.common.utils.find_rel_by_node_type'):
            networkacl.create(ctx=ctx, iface=iface, resource_config=config)
            self.assertEqual(self.networkacl.resource_id,
                             'networkacl')

    def test_attach(self):
        ctx = self.get_mock_ctx("NetworkAcl")
        self.networkacl.resource_id = 'network acl'
        config = {NETWORKACL_ID: 'network acl', SUBNET_ID: 'subnet'}
        iface = MagicMock()
        iface.attach = self.mock_return(config)
        networkacl.attach(ctx, iface, config)
        self.assertEqual(self.networkacl.resource_id,
                         'network acl')

    def test_attach_with_relationships(self):
        ctx = self.get_mock_ctx(
            "NetworkAcl",
            type_hierarchy=[SUBNET_TYPE])
        config = {'NewAssociationId': 'foo'}
        self.networkacl.resource_id = 'network acl'
        iface = MagicMock()
        iface.attach = self.mock_return(config)
        iface.resource_id = self.mock_return('network acl')
        with patch('cloudify_aws.common.utils.find_rel_by_node_type'):
            networkacl.attach(ctx, iface, config)
            self.assertEqual(self.networkacl.resource_id,
                             'network acl')

    def test_delete(self):
        ctx = self.get_mock_ctx("NetworkAcl")
        iface = MagicMock()
        networkacl.delete(ctx=ctx, iface=iface, resource_config={})
        self.assertTrue(iface.delete.called)

    def test_detach(self):
        ctx = self.get_mock_ctx("NetworkAcl")
        self.networkacl.resource_id = 'network acl'
        ctx.instance.runtime_properties['association_id'] = 'association_id'
        ctx.instance.runtime_properties['default_acl_id'] = 'default_acl_id'
        iface = MagicMock()
        iface.detach = self.mock_return('new_association_id')
        networkacl.detach(ctx, iface, {})
        self.assertEqual(self.networkacl.resource_id,
                         'network acl')


if __name__ == '__main__':
    unittest.main()

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
from cloudify_aws.ec2.resources import elasticip
from cloudify_aws.common._compat import reload_module
from cloudify_aws.common.tests.test_base import (
    TestBase,
    mock_decorator
)
from cloudify_aws.ec2.resources.elasticip import (
    EC2ElasticIP,
    ADDRESSES,
    ELASTICIP_ID,
    INSTANCE_ID,
    INSTANCE_TYPE_DEPRECATED,
    NETWORKINTERFACE_ID,
    NETWORKINTERFACE_TYPE,
    NETWORKINTERFACE_TYPE_DEPRECATED,
    ALLOCATION_ID
)


class TestElasticIp(TestBase):

    def setUp(self):
        self.elasticip = EC2ElasticIP("ctx_node", resource_id=True,
                                      client=True, logger=None)
        mock1 = patch('cloudify_aws.common.decorators.aws_resource',
                      mock_decorator)
        mock1.start()
        reload_module(elasticip)

    def test_class_properties(self):
        effect = self.get_client_error_exception(name='EC2 Ellastic IP')
        self.elasticip.client = \
            self.make_client_function('describe_addresses',
                                      side_effect=effect)
        res = self.elasticip.properties
        self.assertEqual(res, {})

        value = {}
        self.elasticip.client = \
            self.make_client_function('describe_addresses',
                                      return_value=value)
        res = self.elasticip.properties
        self.assertEqual(res, {})

        value = {ADDRESSES: [{NETWORKINTERFACE_ID: 'test_name'}]}
        self.elasticip.client = \
            self.make_client_function('describe_addresses',
                                      return_value=value)
        res = self.elasticip.properties
        self.assertEqual(res[NETWORKINTERFACE_ID], 'test_name')

    def test_class_create(self):
        value = {'PublicIp': 'test'}
        self.elasticip.client = \
            self.make_client_function('allocate_address',
                                      return_value=value)
        res = self.elasticip.create(value)
        self.assertEqual(res, value)

    def test_class_delete(self):
        params = {}
        self.elasticip.client = \
            self.make_client_function('release_address')
        self.elasticip.delete(params)
        self.assertTrue(self.elasticip.client.release_address
                        .called)

        params = {'PublicIp': 'test'}
        self.elasticip.delete(params)
        self.assertEqual(params['PublicIp'], 'test')

    def test_class_attach(self):
        value = {ALLOCATION_ID: 'elasticip-attach'}
        self.elasticip.client = \
            self.make_client_function('associate_address',
                                      return_value=value)
        with patch('cloudify_aws.ec2.resources.elasticip'
                   '.EC2ElasticIP.attach'):
            res = self.elasticip.attach(value)
            self.assertEqual(res[ALLOCATION_ID], value[ALLOCATION_ID])

    def test_class_attach_eni(self):
        value = {'AssociationId': 'elasticip-assos'}
        config = {ALLOCATION_ID: 'elasticip-attach'}
        self.elasticip.client = \
            self.make_client_function('associate_address',
                                      return_value=value)
        with patch('cloudify_aws.ec2.resources.elasticip'
                   '.EC2ElasticIP.attach'):
            res = self.elasticip.attach(config)
            self.assertEqual(res['AssociationId'], value['AssociationId'])

    def test_class_detach(self):
        params = {}
        self.elasticip.client = \
            self.make_client_function('disassociate_address')
        self.elasticip.detach(params)
        self.assertTrue(self.elasticip.client.disassociate_address
                        .called)
        params = {ALLOCATION_ID: 'elasticip-attach'}
        self.elasticip.delete(params)
        self.assertTrue(self.elasticip.client.disassociate_address
                        .called)

    def test_prepare(self):
        ctx = self.get_mock_ctx("PublicIp")
        config = {ELASTICIP_ID: 'elasticip'}
        elasticip.prepare(ctx, config)
        self.assertEqual(ctx.instance.runtime_properties['resource_config'],
                         config)

    def test_create(self):
        ctx = self.get_mock_ctx("PublicIp")
        config = {ELASTICIP_ID: 'elasticip', INSTANCE_ID: 'instance'}
        self.elasticip.resource_id = config[ELASTICIP_ID]
        iface = MagicMock()
        iface.create = self.mock_return(config)
        elasticip.create(ctx=ctx, iface=iface, resource_config=config)
        self.assertEqual(self.elasticip.resource_id,
                         'elasticip')

    def test_create_use_allocated(self):
        value = {
            ADDRESSES: [
                {
                    NETWORKINTERFACE_ID: 'test_name',
                    'AssociationId': 'test_name',
                    'AllocationId': 'test_name',
                },
                {
                    ELASTICIP_ID: 'elasticip',
                    NETWORKINTERFACE_ID: 'test_name2',
                    'AssociationId': '',
                    'AllocationId': 'test_name2'
                }
            ]
        }
        self.elasticip.client = self.make_client_function(
            'describe_addresses', return_value=value)

        test_node_props = {'use_unassociated_addresses': True}
        ctx = self.get_mock_ctx("PublicIp", test_properties=test_node_props)
        config = {ELASTICIP_ID: 'elasticip', INSTANCE_ID: 'instance'}
        self.elasticip.resource_id = config[ELASTICIP_ID]
        iface = MagicMock()
        iface.create = self.mock_return(config)
        iface.get = self.mock_return(value[ADDRESSES])
        elasticip.create(ctx=ctx, iface=iface, resource_config=config)
        self.assertEqual(self.elasticip.resource_id, 'elasticip')
        self.assertEqual(
            ctx.instance.runtime_properties.get('allocation_id'),
            'test_name2')

    def test_create_use_allocated_no_allocated(self):
        value = {
            ADDRESSES: [
                {
                    NETWORKINTERFACE_ID: 'test_name',
                    'AssociationId': 'test_name',
                    'AllocationId': 'test_name',
                },
                {
                    NETWORKINTERFACE_ID: 'test_name2',
                    'AssociationId': 'test_name2',
                    'AllocationId': 'test_name2'
                }
            ]
        }

        self.elasticip.client = self.make_client_function(
            'describe_addresses', return_value=value)

        test_node_props = {'use_unassociated_addresses': True}
        ctx = self.get_mock_ctx("PublicIp",
                                test_properties=test_node_props)
        config = {
            ELASTICIP_ID: 'elasticip',
            INSTANCE_ID: 'instance',
            'AllocationId': 'elasticip'
        }
        self.elasticip.resource_id = config[ELASTICIP_ID]
        iface = MagicMock()
        iface.create = self.mock_return(config)
        iface.list = self.mock_return(value[ADDRESSES])
        elasticip.create(ctx=ctx, iface=iface, resource_config=config)
        self.assertEqual(self.elasticip.resource_id, 'elasticip')
        self.assertEqual(
            ctx.instance.runtime_properties.get('allocation_id'),
            'elasticip')

    def test_create_with_relationships(self):
        ctx = self.get_mock_ctx("PublicIp",
                                type_hierarchy=[INSTANCE_TYPE_DEPRECATED])
        config = {ELASTICIP_ID: 'elasticip'}
        self.elasticip.resource_id = config[ELASTICIP_ID]
        iface = MagicMock()
        iface.create = self.mock_return(config)
        with patch('cloudify_aws.common.utils.find_rel_by_node_type'):
            elasticip.create(ctx=ctx, iface=iface, resource_config=config)
            self.assertEqual(self.elasticip.resource_id,
                             'elasticip')

    def test_attach(self):
        ctx = self.get_mock_ctx("PublicIp")
        self.elasticip.resource_id = 'elasticip'
        config = {ALLOCATION_ID: 'elasticip-attach'}
        iface = MagicMock()
        iface.attach = self.mock_return(config)
        elasticip.attach(ctx, iface, config)
        self.assertEqual(self.elasticip.resource_id,
                         'elasticip')
        ctx.instance.runtime_properties['allocation_id'] = 'elasticip-attach'
        iface.attach = self.mock_return(config)
        elasticip.attach(ctx, iface, config)
        self.assertEqual(self.elasticip.resource_id,
                         'elasticip')

    def test_attach_with_relationships(self):
        ctx = self.get_mock_ctx("PublicIp",
                                type_hierarchy=[INSTANCE_TYPE_DEPRECATED])
        config = {ALLOCATION_ID: 'elasticip-attach'}
        self.elasticip.resource_id = 'elasticip'
        iface = MagicMock()
        iface.attach = self.mock_return(config)
        with patch('cloudify_aws.common.utils.find_rel_by_node_type'):
            elasticip.attach(ctx, iface, config)
            self.assertEqual(self.elasticip.resource_id,
                             'elasticip')

    def test_attach_with_relationships_eni(self):
        ctx = \
            self.get_mock_ctx("PublicIp",
                              type_hierarchy=[NETWORKINTERFACE_TYPE,
                                              NETWORKINTERFACE_TYPE_DEPRECATED]
                              )
        value = {'AssociationId': 'elasticip-assos'}
        config = {ALLOCATION_ID: 'elasticip-attach', 'Domain': 'vpc'}
        ctx.instance.runtime_properties['allocation_id'] = 'elasticip-attach'
        iface = MagicMock()
        iface.attach = self.mock_return(value)
        with patch('cloudify_aws.common.utils.find_rel_by_node_type'):
            elasticip.attach(ctx, iface, config)

    def test_delete(self):
        ctx = self.get_mock_ctx("PublicIp")
        iface = MagicMock()
        elasticip.delete(ctx=ctx, iface=iface, resource_config={})
        self.assertTrue(iface.delete.called)
        ctx.instance.runtime_properties['allocation_id'] = 'elasticip-attach'
        elasticip.delete(ctx=ctx, iface=iface, resource_config={})
        self.assertTrue(iface.delete.called)

    def test_detach(self):
        ctx = self.get_mock_ctx("PublicIp")
        self.elasticip.resource_id = 'elasticip'
        config = {'AssociationId': 'elasticip-assos'}
        iface = MagicMock()
        iface.detach = self.mock_return(config)
        elasticip.detach(ctx, iface, config)
        self.assertEqual(self.elasticip.resource_id,
                         'elasticip')

    def test_detach_with_relationships(self):
        ctx = self.get_mock_ctx("PublicIp",
                                type_hierarchy=[INSTANCE_TYPE_DEPRECATED])
        config = {ELASTICIP_ID: 'elasticip'}
        self.elasticip.resource_id = config[ELASTICIP_ID]
        iface = MagicMock()
        iface.detach = self.mock_return(config)
        ctx.instance.runtime_properties['association_id'] = 'elasticip-assos'
        elasticip.detach(ctx, iface, config)
        self.assertEqual(self.elasticip.resource_id,
                         'elasticip')


if __name__ == '__main__':
    unittest.main()

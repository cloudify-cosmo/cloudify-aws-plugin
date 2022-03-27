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
from cloudify_aws.ec2.resources import internet_gateway
from cloudify_aws.common.tests.test_base import (
    TestBase,
    mock_decorator
)
from cloudify_aws.ec2.resources.internet_gateway import (
    EC2InternetGateway,
    INTERNETGATEWAYS,
    INTERNETGATEWAY_ID,
    VPC_ID,
    VPC_TYPE
)


class TestEC2InternetGateway(TestBase):

    def setUp(self):
        self.internet_gateway = EC2InternetGateway("ctx_node",
                                                   resource_id='test_name',
                                                   client=True, logger=None)
        mock1 = patch('cloudify_aws.common.decorators.aws_resource',
                      mock_decorator)
        mock2 = patch('cloudify_aws.common.decorators.wait_for_status',
                      mock_decorator)
        mock1.start()
        mock2.start()
        reload_module(internet_gateway)

    def test_class_properties(self):
        effect = self.get_client_error_exception(name='EC2 Internet '
                                                      'Gateway Bucket')
        self.internet_gateway.client = \
            self.make_client_function('describe_internet_gateways',
                                      side_effect=effect)
        res = self.internet_gateway.properties
        self.assertEqual(res, {})

        value = {}
        self.internet_gateway.client = \
            self.make_client_function('describe_internet_gateways',
                                      return_value=value)
        res = self.internet_gateway.properties
        self.assertEqual(res, {})

        value = {INTERNETGATEWAYS: [{INTERNETGATEWAY_ID: 'test_name'}]}
        self.internet_gateway.client = \
            self.make_client_function('describe_internet_gateways',
                                      return_value=value)
        res = self.internet_gateway.properties
        self.assertEqual(res[INTERNETGATEWAY_ID], 'test_name')

    def test_class_status(self):
        value = {}
        self.internet_gateway.client = \
            self.make_client_function('describe_internet_gateways',
                                      return_value=value)
        res = self.internet_gateway.status
        self.assertIsNone(res)

        value = {INTERNETGATEWAYS: [{INTERNETGATEWAY_ID: 'test_name',
                                     'Attachments': [{'State': 'available'}]}]}
        self.internet_gateway.client = \
            self.make_client_function('describe_internet_gateways',
                                      return_value=value)
        res = self.internet_gateway.status
        self.assertEqual(res, 'available')

    def test_class_create(self):
        value = {'InternetGateway': 'test'}
        self.internet_gateway.client = \
            self.make_client_function('create_internet_gateway',
                                      return_value=value)
        res = self.internet_gateway.create(value)
        self.assertEqual(res['InternetGateway'], value['InternetGateway'])

    def test_class_delete(self):
        params = {}
        self.internet_gateway.client = self.make_client_function('delete'
                                                                 '_internet'
                                                                 '_gateway')
        self.internet_gateway.delete(params)
        self.assertTrue(self.internet_gateway.client.delete_internet_gateway
                        .called)

        params = {'InternetGateway': 'internet gateway'}
        self.internet_gateway.delete(params)
        self.assertEqual(params['InternetGateway'], 'internet gateway')

    def test_class_attach(self):
        value = {'VpcAttachment': {INTERNETGATEWAY_ID: 'internet gateway',
                                   VPC_ID: 'vpc'}}
        self.internet_gateway.client = \
            self.make_client_function('attach_internet_gateway',
                                      return_value=True)
        with patch('cloudify_aws.ec2.resources.internet_gateway'
                   '.EC2InternetGateway.attach'):
            res = self.internet_gateway.attach(value)
            self.assertEqual(True, res)

    def test_class_detach(self):
        params = {}
        self.internet_gateway.client = \
            self.make_client_function('detach_internet_gateway')
        self.internet_gateway.detach(params)
        self.assertTrue(self.internet_gateway.client.detach_internet_gateway
                        .called)
        params = {INTERNETGATEWAY_ID: 'internet gateway', VPC_ID: 'vpc'}
        self.internet_gateway.delete(params)
        self.assertTrue(self.internet_gateway.client.detach_internet_gateway
                        .called)

    def test_prepare(self):
        ctx = self.get_mock_ctx("InternetGateway")
        config = {INTERNETGATEWAY_ID: 'internet gateway'}
        internet_gateway.prepare(ctx, config)
        self.assertEqual(ctx.instance.runtime_properties['resource_config'],
                         config)

    def test_create(self):
        ctx = self.get_mock_ctx("InternetGateway")
        config = {INTERNETGATEWAY_ID: 'internet gateway'}
        self.internet_gateway.resource_id = config[INTERNETGATEWAY_ID]
        iface = MagicMock()
        iface.create = self.mock_return({'InternetGateway': config})
        internet_gateway.create(ctx=ctx, iface=iface, resource_config=config)
        self.assertEqual(self.internet_gateway.resource_id,
                         'internet gateway')

    def test_attach(self):
        ctx = self.get_mock_ctx("InternetGateway")
        self.internet_gateway.resource_id = 'internet gateway'
        config = {VPC_ID: 'vpc'}
        iface = MagicMock()
        iface.attach = self.mock_return(config)
        internet_gateway.attach(ctx, iface, config)
        self.assertEqual(self.internet_gateway.resource_id,
                         'internet gateway')

    def test_attach_with_relationships(self):
        ctx = self.get_mock_ctx("InternetGateway", type_hierarchy=[VPC_TYPE])
        config = {INTERNETGATEWAY_ID: 'internet gateway'}
        self.internet_gateway.resource_id = config[INTERNETGATEWAY_ID]
        iface = MagicMock()
        iface.attach = self.mock_return(config)
        with patch('cloudify_aws.common.utils.find_rel_by_node_type'):
            internet_gateway.attach(ctx, iface, config)
            self.assertEqual(self.internet_gateway.resource_id,
                             'internet gateway')

    def test_delete(self):
        ctx = self.get_mock_ctx("InternetGateway")
        iface = MagicMock()
        internet_gateway.delete(ctx=ctx, iface=iface, resource_config={})
        self.assertTrue(iface.delete.called)

    def test_detach(self):
        ctx = self.get_mock_ctx("InternetGateway")
        self.internet_gateway.resource_id = 'internet gateway'
        config = {VPC_ID: 'vpc'}
        iface = MagicMock()
        iface.detach = self.mock_return(config)
        internet_gateway.detach(ctx, iface, config)
        self.assertEqual(self.internet_gateway.resource_id,
                         'internet gateway')

    def test_detach_with_relationships(self):
        ctx = self.get_mock_ctx("InternetGateway", type_hierarchy=[VPC_TYPE])
        config = {INTERNETGATEWAY_ID: 'internet gateway'}
        self.internet_gateway.resource_id = config[INTERNETGATEWAY_ID]
        iface = MagicMock()
        iface.detach = self.mock_return(config)
        with patch('cloudify_aws.common.utils.find_rel_by_node_type'):
            internet_gateway.detach(ctx, iface, config)
            self.assertEqual(self.internet_gateway.resource_id,
                             'internet gateway')


if __name__ == '__main__':
    unittest.main()

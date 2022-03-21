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
from cloudify_aws.ec2.resources import transit_gateway as mod
from cloudify_aws.common.tests.test_base import (
    TestBase,
    mock_decorator
)


class TestEC2TransitGateway(TestBase):

    def setUp(self):
        self.transit_gateway = mod.EC2TransitGateway(
            "ctx_node",
            resource_id='test_name',
            client=True,
            logger=None)
        mock1 = patch('cloudify_aws.common.decorators.aws_resource',
                      mock_decorator)
        mock2 = patch('cloudify_aws.common.decorators.wait_for_status',
                      mock_decorator)
        mock1.start()
        mock2.start()
        reload_module(mod)

    def test_class_properties(self):
        effect = self.get_client_error_exception(name='EC2 Transit Gateway')
        self.transit_gateway.client = self.make_client_function(
            'describe_transit_gateways', side_effect=effect)
        res = self.transit_gateway.properties
        self.assertEqual(res, {})

        value = {}
        self.transit_gateway.client = self.make_client_function(
            'describe_transit_gateways', return_value=value)
        res = self.transit_gateway.properties
        self.assertEqual(res, value)

        value = {mod.TGS: [{mod.TG_ID: 'test_name'}]}
        self.transit_gateway.client = self.make_client_function(
            'describe_transit_gateways', return_value=value)
        res = self.transit_gateway.properties
        self.assertEqual(res[mod.TG_ID], 'test_name')

    def test_class_status(self):
        value = {
            mod.TGS: [
                {mod.TG_ID: 'test_name', 'State': None}]
        }
        self.transit_gateway.client = self.make_client_function(
            'describe_transit_gateways', return_value=value)
        res = self.transit_gateway.status
        self.assertIsNone(res)

    def test_class_status_positive(self):

        value = {
            mod.TGS: [
                {mod.TG_ID: 'test_name', 'State': 'available'}]
        }
        se = [value, value, value]
        self.transit_gateway.client = self.make_client_function(
            'describe_transit_gateways', side_effect=se)
        res = self.transit_gateway.status
        self.assertEqual(res, 'available')

    def test_class_create(self):
        value = {mod.TG: 'test'}
        self.transit_gateway.client = self.make_client_function(
            'create_transit_gateway', return_value=value)
        res = self.transit_gateway.create(value)
        self.assertEqual(res[mod.TG], value[mod.TG])

    def test_class_delete(self):
        params = {}
        self.transit_gateway.client = self.make_client_function(
            'delete_transit_gateway')
        self.transit_gateway.delete(params)
        self.assertTrue(
            self.transit_gateway.client.delete_transit_gateway.called)
        params = {mod.TG: 'transit gateway'}
        self.transit_gateway.delete(params)
        self.assertEqual(params[mod.TG], 'transit gateway')

    def test_prepare(self):
        ctx = self.get_mock_ctx(mod.TG)
        config = {mod.TG_ID: 'transit gateway'}
        mod.prepare(ctx, mod.EC2TransitGateway, config)
        self.assertEqual(ctx.instance.runtime_properties['resource_config'],
                         config)

    def test_create(self):
        ctx = self.get_mock_ctx(mod.TG)
        config = {mod.TG_ID: 'transit gateway'}
        self.transit_gateway.resource_id = config[mod.TG_ID]
        iface = MagicMock()
        iface.create = self.mock_return({mod.TG: config})
        mod.create(ctx=ctx, iface=iface, resource_config=config)
        self.assertEqual(self.transit_gateway.resource_id, 'transit gateway')

    def test_delete(self):
        ctx = self.get_mock_ctx(mod.TG)
        iface = MagicMock()
        mod.delete(ctx=ctx, iface=iface, resource_config={})
        self.assertTrue(iface.delete.called)


class TestEC2TransitGatewayAttachment(TestBase):

    def setUp(self):
        self.transit_gateway_attachment = mod.EC2TransitGatewayAttachment(
            "ctx_node",
            resource_id=True,
            client=True,
            logger=None)
        mock1 = patch('cloudify_aws.common.decorators.aws_resource',
                      mock_decorator)
        mock2 = patch('cloudify_aws.common.decorators.wait_for_status',
                      mock_decorator)
        mock1.start()
        mock2.start()
        reload_module(mod)

    def test_class_properties(self):
        effect = self.get_client_error_exception(
            name='EC2 Transit Gateway Attachment')
        self.transit_gateway_attachment.client = self.make_client_function(
            'describe_transit_gateway_vpc_attachments', side_effect=effect)
        res = self.transit_gateway_attachment.properties
        self.assertIsNone(res)

        value = {}
        self.transit_gateway_attachment.client = self.make_client_function(
            'describe_transit_gateway_vpc_attachments', return_value=value)
        res = self.transit_gateway_attachment.properties
        self.assertIsNone(res)

        value = {
            mod.TG_ATTACHMENTS: [
                {mod.TG_ATTACHMENT_ID: 'test_name'}]
        }
        self.transit_gateway_attachment.client = self.make_client_function(
            'describe_transit_gateway_vpc_attachments', return_value=value)
        res = self.transit_gateway_attachment.properties
        self.assertEqual(res[mod.TG_ATTACHMENT_ID], 'test_name')

    def test_class_status(self):
        value = {}
        self.transit_gateway_attachment.client = self.make_client_function(
            'describe_transit_gateway_vpc_attachments', return_value=value)
        res = self.transit_gateway_attachment.status
        self.assertIsNone(res)

        value = {
            mod.TG_ATTACHMENTS: [
                {
                    mod.TG_ATTACHMENT_ID: 'test_name',
                    'State': 'available'
                }
            ]
        }
        self.transit_gateway_attachment.client = self.make_client_function(
            'describe_transit_gateway_vpc_attachments', return_value=value)
        res = self.transit_gateway_attachment.status
        self.assertEqual(res, 'available')

    def test_class_create(self):
        value = {mod.TG_ATTACHMENT: 'test'}
        self.transit_gateway_attachment.client = self.make_client_function(
            'create_transit_gateway_vpc_attachment', return_value=value)
        res = self.transit_gateway_attachment.create(value)
        self.assertEqual(res[mod.TG_ATTACHMENT],
                         value[mod.TG_ATTACHMENT])

    def test_class_accept(self):
        value = {mod.TG_ATTACHMENT: 'test'}
        self.transit_gateway_attachment.client = self.make_client_function(
            'accept_transit_gateway_vpc_attachment', return_value=value)
        res = self.transit_gateway_attachment.accept(value)
        self.assertEqual(res[mod.TG_ATTACHMENT],
                         value[mod.TG_ATTACHMENT])

    def test_class_delete(self):
        params = {}
        self.transit_gateway_attachment.client = self.make_client_function(
            'delete_transit_gateway_vpc_attachment')
        self.transit_gateway_attachment.delete(params)
        self.assertTrue(self.transit_gateway_attachment.
                        client.delete_transit_gateway_vpc_attachment.called)
        params = {mod.TG_ATTACHMENT_ID: 'transit gateway'}
        self.transit_gateway_attachment.delete(params)
        self.assertEqual(params[mod.TG_ATTACHMENT_ID],
                         'transit gateway')

    def test_create(self):
        source_ctx = self.get_mock_ctx(mod.TG)
        target_ctx = self.get_mock_ctx(mod.TG)
        ctx = self.get_mock_relationship_ctx(
            mod.TG_ATTACHMENT, test_source=source_ctx,
            test_target=target_ctx)
        config = {mod.TG_ATTACHMENT_ID: 'transit gateway'}
        self.transit_gateway_attachment.resource_id = \
            config[mod.TG_ATTACHMENT_ID]
        iface = MagicMock()
        iface.create = self.mock_return({mod.TG: config})
        mod.request_vpc_attachment(
            ctx=ctx,
            iface=iface,
            transit_gateway_id='transit gateway',
            vpc_id='vpc',
            subnet_ids=['subnet'])
        self.assertIn(mod.TG_ATTACHMENTS,
                      source_ctx.instance.runtime_properties)

    def test_delete(self):
        source_ctx = self.get_mock_ctx(
            mod.TG,
            test_runtime_properties={'aws_resource_id': 'transit gateway'})
        ctx = self.get_mock_relationship_ctx(
            mod.TG_ATTACHMENT, test_source=source_ctx)
        iface = MagicMock(client=MagicMock())
        with self.assertRaises(OperationRetry):
            mod.delete_vpc_attachment(
                ctx=ctx,
                iface=iface,
                transit_gateway_attachment_id='transit gateway')
            self.assertTrue(iface.delete.called)


if __name__ == '__main__':
    unittest.main()

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

from cloudify.state import current_ctx

# Local imports
from cloudify_aws.common._compat import reload_module
from cloudify_aws.common.tests.test_base import (
    TestBase,
    mock_decorator
)
from cloudify_aws.ec2.resources.keypair import (
    EC2Keypair,
    KEYPAIRS,
    KEYNAME,
    PUBLIC_KEY_MATERIAL
)

from cloudify_aws.ec2.resources import keypair


class TestEC2Keypair(TestBase):

    def setUp(self):
        self.keypair = EC2Keypair("ctx_node", resource_id='test_name',
                                  client=True, logger=None)
        mock1 = patch('cloudify_aws.common.decorators.aws_resource',
                      mock_decorator)
        mock2 = patch('cloudify_aws.common.decorators.wait_for_status',
                      mock_decorator)
        mock1.start()
        mock2.start()
        reload_module(keypair)

    def test_class_properties(self):
        effect = self.get_client_error_exception(name='EC2 Keypairs')
        self.keypair.client = \
            self.make_client_function('describe_key_pairs',
                                      side_effect=effect)
        res = self.keypair.properties
        self.assertEqual(res, {})

        value = {}
        self.keypair.client = \
            self.make_client_function('describe_key_pairs',
                                      return_value=value)
        res = self.keypair.properties
        self.assertEqual(res, {})

        value = {KEYPAIRS: [{KEYNAME: 'test_name'}]}
        self.keypair.client = \
            self.make_client_function('describe_key_pairs',
                                      return_value=value)
        res = self.keypair.properties
        self.assertEqual(res[KEYNAME], 'test_name')

    def test_class_create(self):
        value = {KEYNAME: 'test_name'}
        self.keypair.client = \
            self.make_client_function('create_key_pair',
                                      return_value=value)
        res = self.keypair.create(value)
        self.assertEqual(res, value)

    def test_class_delete(self):
        params = {KEYNAME: 'test_name'}
        self.keypair.client = \
            self.make_client_function('delete_key_pair')
        self.keypair.delete(params)
        self.assertTrue(self.keypair.client.delete_key_pair
                        .called)

        params = {KEYNAME: 'test_name'}
        self.keypair.delete(params)
        self.assertEqual(params[KEYNAME], 'test_name')

    def test_prepare(self):
        ctx = self.get_mock_ctx("EC2Keypair")
        params = {KEYNAME: 'test_name'}
        keypair.prepare(ctx, EC2Keypair, params)
        self.assertEqual(ctx.instance.runtime_properties['resource_config'],
                         params)

    def test_create(self):
        test_properties = {
            'log_create_response': False,
            'store_in_runtime_properties': True,
            'create_secret': False
        }
        ctx = self.get_mock_ctx("EC2Keypair", test_properties=test_properties)
        current_ctx.set(ctx=ctx)
        params = {KEYNAME: 'test_name'}
        self.keypair.resource_id = 'test_name'
        iface = MagicMock()
        value = {KEYNAME: 'test_name'}
        iface.create = self.mock_return(value)
        keypair.create(ctx=ctx, iface=iface, resource_config=params)
        self.assertEqual(self.keypair.resource_id,
                         'test_name')

    def test_import(self):
        test_properties = {
            'log_create_response': False,
            'store_in_runtime_properties': True,
            'create_secret': False
        }
        ctx = self.get_mock_ctx("EC2Keypair", test_properties=test_properties)
        current_ctx.set(ctx=ctx)
        params = {KEYNAME: 'test_name', PUBLIC_KEY_MATERIAL: 'test_material'}
        self.keypair.resource_id = 'test_name'
        iface = MagicMock()
        value = {KEYNAME: 'test_name'}
        iface.create = self.mock_return(value)
        keypair.create(ctx=ctx, iface=iface, resource_config=params)
        self.assertEqual(self.keypair.resource_id,
                         'test_name')

    def test_delete(self):
        test_properties = {
            'log_create_response': False,
            'store_in_runtime_properties': True,
            'create_secret': False
        }
        test_runtime_properties = {
            'create_response': {}
        }
        ctx = self.get_mock_ctx(
            "EC2Keypair",
            test_properties=test_properties,
            test_runtime_properties=test_runtime_properties)
        current_ctx.set(ctx=ctx)
        iface = MagicMock()
        keypair.delete(ctx=ctx, iface=iface, resource_config={})
        self.assertTrue(iface.delete.called)


if __name__ == '__main__':
    unittest.main()

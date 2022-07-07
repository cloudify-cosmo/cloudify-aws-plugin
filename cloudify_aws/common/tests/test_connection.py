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

import copy
import unittest
from mock import patch, MagicMock
from cloudify.state import current_ctx


from cloudify_aws.common.connection import Boto3Connection
from cloudify_aws.common.tests.test_base import TestBase, CLIENT_CONFIG


class TestConnection(TestBase):

    def setUp(self):
        super(TestConnection, self).setUp()

        self.fake_boto, self.fake_client = self.fake_boto_client('other')

        self.mock_patch = patch('boto3.client', self.fake_boto)
        self.mock_patch.start()

    def tearDown(self):
        self.mock_patch.stop()
        self.fake_boto = None
        self.fake_client = None

        super(TestConnection, self).tearDown()

    def test_client_direct_params(self):

        node = MagicMock()
        node.properties = {}
        _ctx = self.get_mock_ctx('test')
        current_ctx.set(_ctx)

        connection = Boto3Connection(node, copy.deepcopy(CLIENT_CONFIG))
        connection.client('abc')

        self.fake_boto.assert_called_with(
            'abc', **CLIENT_CONFIG
        )

    def test_client_node_params(self):

        node = MagicMock()
        node.properties = {
            'client_config': copy.deepcopy(CLIENT_CONFIG)
        }
        _ctx = self.get_mock_ctx('test')
        current_ctx.set(_ctx)

        connection = Boto3Connection(node, {'a': 'b'})
        connection.client('abc')

        self.fake_boto.assert_called_with(
            'abc', **CLIENT_CONFIG
        )

        self.assertEqual(connection.aws_config, CLIENT_CONFIG)

    def test_client_session_token(self):

        node = MagicMock()
        node.properties = {
            'client_config': {
                'aws_session_token': 'foo',
                'region_name': 'bar'
            }
        }
        _ctx = self.get_mock_ctx('test')
        current_ctx.set(_ctx)

        connection = Boto3Connection(node, {'a': 'b'})
        connection.client('abc')

        self.fake_boto.assert_called_with(
            'abc', **{
                'aws_session_token': 'foo',
                'region_name': 'bar'
            }
        )

        self.assertEqual(connection.aws_config, {
                'aws_session_token': 'foo',
                'region_name': 'bar'
            })


if __name__ == '__main__':
    unittest.main()

########
# Copyright (c) 2015 GigaSpaces Technologies Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
#    * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    * See the License for the specific language governing permissions and
#    * limitations under the License.

# Built-in Imports
import testtools

# Third Party Imports
from moto import mock_ec2
from boto.ec2 import EC2Connection

# Cloudify Imports is imported and used in operations
from ec2 import constants
from ec2 import connection
from cloudify.state import current_ctx
from cloudify.mocks import MockCloudifyContext


class TestConnection(testtools.TestCase):

    def get_mock_context(self, test_name):
        """ Creates a mock context."""

        return MockCloudifyContext(
            node_id=test_name,
            properties={
                constants.AWS_CONFIG_PROPERTY: {
                    'region': 'dark-side-of-the-moon'
                }
            }
        )

    @mock_ec2
    def test_connect(self):
        """ this tests that a the correct region endpoint
        in returned by the connect function
        """

        ctx = self.get_mock_context('test_connect')
        current_ctx.set(ctx=ctx)

        ec2_client = connection.EC2ConnectionClient().client()
        self.assertTrue(type(ec2_client), EC2Connection)
        self.assertEqual(ec2_client.DefaultRegionEndpoint,
                         'ec2.us-east-1.amazonaws.com')

    @mock_ec2
    def test_connect_bad_region(self):
        ctx = self.get_mock_context('test_connect_bad_region')
        current_ctx.set(ctx=ctx)
        ec2_client = connection.EC2ConnectionClient().client()
        self.assertEqual(
            ec2_client.DefaultRegionName,
            ec2_client.region.name)

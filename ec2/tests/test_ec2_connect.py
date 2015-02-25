########
# Copyright (c) 2014 GigaSpaces Technologies Ltd. All rights reserved
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
from boto.ec2 import EC2Connection
from moto import mock_ec2

# Cloudify Imports is imported and used in operations
from ec2 import connection


class TestConnection(testtools.TestCase):

    @mock_ec2
    def test_connect(self):
        """ this tests that a the correct region endpoint
        in returned by the connect function
        """

        ec2_client = connection.EC2ConnectionClient().client()
        self.assertTrue(type(ec2_client), EC2Connection)
        self.assertEqual(ec2_client.DefaultRegionEndpoint,
                         'ec2.us-east-1.amazonaws.com')

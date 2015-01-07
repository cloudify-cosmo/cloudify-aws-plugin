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
import unittest
import re

# Third Party Imports
from moto import mock_ec2
import httpretty

# Cloudify Imports is imported and used in operations
from ec2 import connection
from ec2 import instance
from cloudify.mocks import MockCloudifyContext
from cloudify.exceptions import NonRecoverableError

TEST_AMI_IMAGE_ID = 'ami-e214778a'
TEST_INSTANCE_TYPE = 't1.micro'


class TestPlugin(unittest.TestCase):

    def mock_ctx(self, test_name):

        test_node_id = test_name
        test_properties = {
            'image_id': TEST_AMI_IMAGE_ID,
            'instance_type': TEST_INSTANCE_TYPE,
            'attributes': {
                'security_groups': ['sg-73cd3f1e'],
                'instance_initiated_shutdown_behavior': 'stop'
            }
        }

        ctx = MockCloudifyContext(
            node_id=test_node_id,
            properties=test_properties
        )

        return ctx

    def test_no_route_to_host_stop(self):
        """ This tests that the NonRecoverableError is triggered
        when there is no route to host, i.e. the connection
        to amazonaws cannot be made
        """

        ctx = self.mock_ctx('test_no_route_to_host_stop')

        with mock_ec2():
            aws = connection.EC2Client().connect()
            reservation = aws.run_instances(
                TEST_AMI_IMAGE_ID, instance_type=TEST_INSTANCE_TYPE)
            id = reservation.instances[0].id
            httpretty.enable()
            httpretty.register_uri(httpretty.POST,
                                   re.compile(
                                       'https://ec2.us-east-1.amazonaws.com/.*'
                                   ),
                                   status=500)
            ctx.instance.runtime_properties['instance_id'] = id
            self.assertRaises(NonRecoverableError, instance.stop, ctx=ctx)
            httpretty.disable()
            httpretty.reset()

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


import unittest

# ec2 imports Imports
from boto.ec2.instance import Reservation
from ec2 import instance
from moto import mock_ec2

# ctx is imported and used in operations
from cloudify.mocks import MockCloudifyContext

TEST_AMI_IMAGE_ID = 'ami-e214778a'
TEST_INSTANCE_TYPE = 't1.micro'
RESERVATION_OBJECT_TYPE = Reservation


class TestPlugin(unittest.TestCase):

    def test_instance_create(self):

        test_name = 'test_instance_run'
        test_node_id = '{0}'.format(test_name)
        test_properties = {
            'ami_image_id': TEST_AMI_IMAGE_ID,
            'instance_type': TEST_INSTANCE_TYPE
        }

        with mock_ec2():

            ctx = MockCloudifyContext(
                node_id=test_node_id,
                properties=test_properties
            )
            self.assertTrue(instance.create(ctx=ctx))
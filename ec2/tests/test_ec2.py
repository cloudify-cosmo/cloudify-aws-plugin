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

# AWS Imports
from boto.ec2.instance import Reservation
from ec2 import instance

TEST_AMI_IMAGE_ID = 'ami-e214778a'
TEST_INSTANCE_TYPE = 't1.micro'
RESERVATION_OBJECT_TYPE = Reservation


class TestPlugin(unittest.TestCase):

    def test_instance_run(self):
        reservation = instance.run(TEST_AMI_IMAGE_ID, TEST_INSTANCE_TYPE)
        self.assertEqual(type(reservation), RESERVATION_OBJECT_TYPE)
        self.assertEqual(TEST_AMI_IMAGE_ID,
                         reservation.instances[0].image_id)
        self.assertEqual(TEST_INSTANCE_TYPE,
                         reservation.instances[0].instance_type)
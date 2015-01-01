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
from ec2 import instance
from moto import mock_ec2

# ctx is imported and used in operations
from cloudify.mocks import MockCloudifyContext

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

    def test_instance_create(self):

        ctx = self.mock_ctx('test_instance_create')

        with mock_ec2():

            instance.create(ctx=ctx)

    def test_instance_stop(self):

        ctx = self.mock_ctx('test_instance_stop')

        with mock_ec2():
            instance.create(ctx=ctx)
            instance.stop(ctx=ctx)

    def test_instance_start(self):

        ctx = self.mock_ctx('test_instance_start')

        with mock_ec2():
            instance.create(ctx=ctx)
            instance.stop(ctx=ctx)
            instance.start(ctx=ctx)

    def test_instance_terminate(self):

        ctx = self.mock_ctx('test_instance_terminate')

        with mock_ec2():
            instance.create(ctx=ctx)
            instance.stop(ctx=ctx)
            instance.terminate(ctx=ctx)

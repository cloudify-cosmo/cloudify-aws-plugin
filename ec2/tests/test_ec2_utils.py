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
from moto import mock_ec2

# Cloudify Imports is imported and used in operations
from ec2 import utils
from ec2 import securitygroup
from cloudify.mocks import MockCloudifyContext
from cloudify.exceptions import NonRecoverableError

TEST_AMI_IMAGE_ID = 'ami-e214778a'
TEST_INSTANCE_TYPE = 't1.micro'


class TestUtils(testtools.TestCase):

    def mock_ctx(self, test_name):

        test_node_id = test_name
        test_properties = {
            'use_external_resource': False,
            'resource_id': '',
            'image_id': TEST_AMI_IMAGE_ID,
            'instance_type': TEST_INSTANCE_TYPE,
            'parameters': {
                'security_group_ids': ['sg-73cd3f1e'],
                'instance_initiated_shutdown_behavior': 'stop'
            }
        }

        ctx = MockCloudifyContext(
            node_id=test_node_id,
            properties=test_properties
        )

        return ctx

    @mock_ec2
    def test_log_available_resources(self):
        ctx = self.mock_ctx('test_log_available_resources')
        groups = securitygroup._get_all_security_groups(ctx=ctx)
        utils.log_available_resources(groups, ctx=ctx)

    @mock_ec2
    def test_validate_no_ami(self):
        ctx = self.mock_ctx('test_validate_no_ami')
        ctx.node.properties.pop('image_id')
        ex = self.assertRaises(
            NonRecoverableError, utils.validate_node_property,
            'image_id', ctx=ctx)
        self.assertIn(
            'is a required input', ex.message)

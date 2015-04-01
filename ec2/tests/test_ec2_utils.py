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


# Third Party Imports
import testtools
from moto import mock_ec2

# Cloudify Imports is imported and used in operations
from ec2 import utils
from cloudify.state import current_ctx
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
            'cloudify_agent': {},
            'parameters': {
                'security_group_ids': ['sg-73cd3f1e'],
                'instance_initiated_shutdown_behavior': 'stop'
            }
        }

        provider_context = {
            'resources': {
                'agents_security_group': {
                    'id': 'agents'
                },
                'agents_keypair': {
                    'id': 'agents'
                }
            }
        }

        ctx = MockCloudifyContext(
            node_id=test_node_id,
            properties=test_properties,
            provider_context=provider_context
        )

        return ctx

    @mock_ec2
    def test_validate_no_ami(self):
        ctx = self.mock_ctx('test_validate_no_ami')
        ctx.node.properties.pop('image_id')
        ex = self.assertRaises(
            NonRecoverableError, utils.validate_node_property,
            'image_id', ctx.node.properties)
        self.assertIn(
            'is a required input', ex.message)

    def test_log_available_resources(self):
        list_of_resources = \
            ['Address:54.163.229.127', 'Address:107.22.223.114']
        ctx = self.mock_ctx('test_log_available_resources')
        current_ctx.set(ctx=ctx)
        utils.log_available_resources(list_of_resources)

    def test_get_provider_variable(self):
        ctx = self.mock_ctx('test_get_provider_variables')
        current_ctx.set(ctx=ctx)
        provider_context = \
            utils.get_provider_variables()

        self.assertEqual('agents', provider_context['agents_keypair'])
        self.assertEqual('agents', provider_context['agents_security_group'])

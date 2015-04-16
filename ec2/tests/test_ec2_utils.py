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

# Builtin Imports
import tempfile
import testtools

# Third Party Imports
from moto import mock_ec2
from boto.ec2 import EC2Connection

# Cloudify Imports is imported and used in operations
from ec2 import utils
from ec2 import constants
from cloudify.state import current_ctx
from cloudify.mocks import MockCloudifyContext
from cloudify.exceptions import NonRecoverableError

TEST_AMI_IMAGE_ID = 'ami-e214778a'
TEST_INSTANCE_TYPE = 't1.micro'


class TestUtils(testtools.TestCase):

    def mock_ctx(self, test_name):

        test_node_id = test_name
        test_properties = {
            constants.AWS_CONFIG_PROPERTY: {},
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

    @mock_ec2
    def test_log_available_resources(self):
        list_of_resources = \
            ['Address:54.163.229.127', 'Address:107.22.223.114']
        ctx = self.mock_ctx('test_log_available_resources')
        current_ctx.set(ctx=ctx)
        utils.log_available_resources(list_of_resources)

    @mock_ec2
    def test_get_provider_variable(self):
        ctx = self.mock_ctx('test_get_provider_variables')
        current_ctx.set(ctx=ctx)
        provider_context = \
            utils.get_provider_variables()

        self.assertEqual('agents', provider_context['agents_keypair'])
        self.assertEqual('agents', provider_context['agents_security_group'])

    @mock_ec2
    def test_utils_get_resource_id(self):

        ctx = self.mock_ctx(
            'test_utils_get_resource_id')
        current_ctx.set(ctx=ctx)

        ctx.node.properties['resource_id'] = \
            'test_utils_get_resource_id'

        resource_id = utils.get_resource_id()

        self.assertEquals(
            'test_utils_get_resource_id', resource_id)

    @mock_ec2
    def test_utils_get_resource_id_dynamic(self):

        ctx = self.mock_ctx(
            'test_utils_get_resource_id')
        current_ctx.set(ctx=ctx)

        ctx.node.properties['resource_id'] = ''

        resource_id = utils.get_resource_id()

        self.assertEquals('None-test_utils_get_resource_id', resource_id)

    @mock_ec2
    def test_utils_get_resource_id_from_key_path(self):

        ctx = self.mock_ctx(
            'test_utils_get_resource_id_from_key_path')
        current_ctx.set(ctx=ctx)
        private_key_path = tempfile.mkdtemp()
        ctx.node.properties['private_key_path'] = \
            '{0}/test_utils_get_resource_id_from_key_path.pem' \
            .format(private_key_path)

        resource_id = utils.get_resource_id()

        self.assertEquals(
            'test_utils_get_resource_id_from_key_path', resource_id)

    @mock_ec2
    def test_utils_validate_node_properties_missing_key(self):
        ctx = self.mock_ctx(
            'test_utils_validate_node_properties_missing_key')
        current_ctx.set(ctx=ctx)

        ex = self.assertRaises(
            NonRecoverableError, utils.validate_node_property,
            'missing_key',
            ctx.node.properties)

        self.assertIn(
            'missing_key is a required input. Unable to create.',
            ex.message)

    @mock_ec2
    def test_utils_log_available_resources(self):

        ctx = self.mock_ctx(
            'test_utils_log_available_resources')
        current_ctx.set(ctx=ctx)

        client = EC2Connection()

        key_pairs = client.get_all_key_pairs()

        utils.log_available_resources(key_pairs)

    @mock_ec2
    def test_utils_get_external_resource_id_or_raise_no_id(self):

        ctx = self.mock_ctx(
            'test_utils_get_external_resource_id_or_raise_no_id')
        current_ctx.set(ctx=ctx)

        ctx.instance.runtime_properties['prop'] = None

        ex = self.assertRaises(
            NonRecoverableError,
            utils.get_external_resource_id_or_raise,
            'test_operation', ctx.instance)

        self.assertIn(
            'Cannot test_operation because {0} is not assigned'
            .format(constants.EXTERNAL_RESOURCE_ID),
            ex.message)

    @mock_ec2
    def test_utils_get_external_resource_id_or_raise(self):

        ctx = self.mock_ctx(
            'test_utils_get_external_resource_id_or_raise')
        current_ctx.set(ctx=ctx)

        ctx.instance.runtime_properties[constants.EXTERNAL_RESOURCE_ID] = \
            'test_utils_get_external_resource_id_or_raise'

        output = utils.get_external_resource_id_or_raise(
            'test_operation', ctx.instance)

        self.assertEquals(
            'test_utils_get_external_resource_id_or_raise', output)

    @mock_ec2
    def test_utils_set_external_resource_id_cloudify(self):

        ctx = self.mock_ctx(
            'test_utils_set_external_resource_id_cloudify')
        current_ctx.set(ctx=ctx)

        utils.set_external_resource_id(
            'id-value',
            ctx.instance,
            external=False)

        self.assertEquals(
            'id-value',
            ctx.instance.runtime_properties[constants.EXTERNAL_RESOURCE_ID])

    @mock_ec2
    def test_utils_set_external_resource_id_external(self):

        ctx = self.mock_ctx(
            'test_utils_set_external_resource_id_external')
        current_ctx.set(ctx=ctx)

        utils.set_external_resource_id(
            'id-value',
            ctx.instance)

        self.assertEquals(
            'id-value',
            ctx.instance.runtime_properties[constants.EXTERNAL_RESOURCE_ID])

    @mock_ec2
    def test_utils_unassign_runtime_property_from_resource(self):

        ctx = self.mock_ctx(
            'test_utils_unassign_runtime_property_from_resource')
        current_ctx.set(ctx=ctx)

        ctx.instance.runtime_properties[constants.EXTERNAL_RESOURCE_ID] = \
            'test_utils_unassign_runtime_property_from_resource'

        utils.unassign_runtime_property_from_resource(
            constants.EXTERNAL_RESOURCE_ID,
            ctx.instance)

        self.assertNotIn(
            constants.EXTERNAL_RESOURCE_ID,
            ctx.instance.runtime_properties)

    @mock_ec2
    def test_utils_use_external_resource_not_external(self):

        ctx = self.mock_ctx(
            'test_utils_use_external_resource_not_external')
        current_ctx.set(ctx=ctx)

        self.assertEquals(
            False,
            utils.use_external_resource(ctx.node.properties))

    @mock_ec2
    def test_utils_use_external_resource_external(self):

        ctx = self.mock_ctx(
            'test_utils_use_external_resource_external')
        current_ctx.set(ctx=ctx)

        ctx.node.properties['use_external_resource'] = True
        ctx.node.properties['resource_id'] = \
            'test_utils_use_external_resource_external'

        self.assertEquals(
            True,
            utils.use_external_resource(ctx.node.properties))

    @mock_ec2
    def test_get_target_external_resource_ids(self):

        ctx = self.mock_ctx(
            'get_target_external_resource_ids')
        current_ctx.set(ctx=ctx)

        output = utils.get_target_external_resource_ids(
            'instance_connected_to_keypair',
            ctx.instance)

        self.assertEquals(0, len(output))

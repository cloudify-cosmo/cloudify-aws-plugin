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
from ec2 import connection
from ec2 import instance
from ec2 import utils
from cloudify.mocks import MockCloudifyContext
from cloudify.exceptions import NonRecoverableError

TEST_AMI_IMAGE_ID = 'ami-e214778a'
TEST_INSTANCE_TYPE = 't1.micro'
FQDN = '((?:[a-z][a-z\\.\\d\\-]+)\\.(?:[a-z][a-z\\-]+))(?![\\w\\.])'


class TestUtils(testtools.TestCase):

    def mock_ctx(self, test_name):

        test_node_id = test_name
        test_properties = {
            'use_external_resource': False,
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

    def test_get_instance_state(self):
        """ this tests that get instance state returns
        running for a running instance
        """

        ctx = self.mock_ctx('test_get_instance_state')
        with mock_ec2():
            instance.run_instances(ctx=ctx)
            instance_state = utils.get_instance_state(ctx=ctx)
            self.assertEqual(instance_state, 16)

    def test_no_instance_get_instance_from_id(self):
        """ this tests that a NonRecoverableError is thrown
        when a nonexisting instance_id is provided to the
        get_instance_from_id function
        """

        ctx = self.mock_ctx('test_no_instance_get_instance_from_id')

        with mock_ec2():

            instance_id = 'bad_id'
            ex = self.assertRaises(NonRecoverableError,
                                   utils.get_instance_from_id,
                                   instance_id, ctx=ctx)
            self.assertIn('Failed', ex.message)

    def test_get_private_dns_name(self):

        ctx = self.mock_ctx('test_get_private_dns_name')

        with mock_ec2():
            ec2_client = connection.EC2ConnectionClient().client()
            reservation = ec2_client.run_instances(
                TEST_AMI_IMAGE_ID, instance_type=TEST_INSTANCE_TYPE)
            ctx.instance.runtime_properties['aws_resource_id'] = \
                reservation.instances[0].id
            dns_name = utils.get_private_dns_name(ctx=ctx)
            self.assertRegexpMatches(dns_name, FQDN)

    def test_get_public_dns_name(self):

        ctx = self.mock_ctx('test_get_public_dns_name')

        ctx
        with mock_ec2():
            ec2_client = connection.EC2ConnectionClient().client()
            reservation = ec2_client.run_instances(
                TEST_AMI_IMAGE_ID, instance_type=TEST_INSTANCE_TYPE)
            ctx.instance.runtime_properties['aws_resource_id'] = \
                reservation.instances[0].id
            dns_name = utils.get_public_dns_name(ctx=ctx)
            self.assertRegexpMatches(dns_name, FQDN)

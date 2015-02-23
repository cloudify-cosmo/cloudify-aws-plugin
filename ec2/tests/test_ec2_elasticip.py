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
from ec2 import utils
from ec2 import elasticip
from cloudify.mocks import MockCloudifyContext
from cloudify.mocks import MockContext
from cloudify.exceptions import NonRecoverableError

TEST_AMI_IMAGE_ID = 'ami-e214778a'
TEST_INSTANCE_TYPE = 't1.micro'
FQDN = '((?:[a-z][a-z\\.\\d\\-]+)\\.(?:[a-z][a-z\\-]+))(?![\\w\\.])'


class TestElasticIP(testtools.TestCase):

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

    def mock_relationship_ctx(self, testname):

        instance_ctx = MockContext({
            'node': MockContext({
                'properties': {}
            }),
            'instance': MockContext({
                'runtime_properties': {
                    'instance_id': 'i-abc1234'
                }
            })
        })

        elasticip_ctx = MockContext({
            'node': MockContext({
                'properties': {}
            }),
            'instance': MockContext({
                'runtime_properties': {
                    'elasticip': ''
                }
            })
        })

        relationship_ctx = MockCloudifyContext(node_id=testname,
                                               source=instance_ctx,
                                               target=elasticip_ctx)

        return relationship_ctx

    def test_allocate(self):
        """ Tests that the allocate function is 100% successful.
        """
        ctx = self.mock_ctx('test_create_address')

        with mock_ec2():
            elasticip.allocate(ctx=ctx)
            self.assertIn('elasticip', ctx.instance.runtime_properties)

    def test_good_address_release(self):
        """ Tests that when an address that is in the user's
            EC2 account is provided to the release function
            no errors are raised
        """

        ctx = self.mock_ctx('test_good_address_delete')

        with mock_ec2():
            ec2_client = connection.EC2ConnectionClient().client()
            address = ec2_client.allocate_address()
            ctx.instance.runtime_properties['elasticip'] = address.public_ip
            elasticip.release(ctx=ctx)


    def test_good_address_associate(self):
        """ Tests that when an address that is in the user's
            EC2 account is provided to the attach function
            no errors are raised
        """

        ctx = self.mock_relationship_ctx('test_good_address_attach')

        with mock_ec2():
            ec2_client = connection.EC2ConnectionClient().client()
            reservation = ec2_client.run_instances(
                TEST_AMI_IMAGE_ID, instance_type=TEST_INSTANCE_TYPE)
            id = reservation.instances[0].id
            address = ec2_client.allocate_address()
            ctx.target.node.properties['elasticip'] = address.public_ip
            ctx.source.instance.runtime_properties['instance_id'] = id
            elasticip.associate(ctx=ctx)

    def test_bad_address_associate(self):
        """ Tests that NonRecoverableError: Invalid Address is
            raised when an address that is not in the user's
            EC2 account is provided to the attach function
        """

        ctx = self.mock_relationship_ctx('test_bad_address_attach')

        with mock_ec2():
            ec2_client = connection.EC2ConnectionClient().client()
            reservation = ec2_client.run_instances(
                TEST_AMI_IMAGE_ID, instance_type=TEST_INSTANCE_TYPE)
            id = reservation.instances[0].id
            ctx.target.node.properties['elasticip'] = '0.0.0.0'
            ctx.source.instance.runtime_properties['instance_id'] = id
            ex = self.assertRaises(NonRecoverableError,
                                   elasticip.associate, ctx=ctx)
            self.assertIn('InvalidAddress.NotFound', ex.message)

    def test_good_address_disassociate(self):
        """ Tests that when an address that is in the user's
            EC2 account is provided to the detach function
            no errors are raised
        """

        ctx = self.mock_relationship_ctx('test_good_address_detach')

        with mock_ec2():
            ec2_client = connection.EC2ConnectionClient().client()
            reservation = ec2_client.run_instances(
                TEST_AMI_IMAGE_ID, instance_type=TEST_INSTANCE_TYPE)
            id = reservation.instances[0].id
            address = ec2_client.allocate_address()
            ctx.target.node.properties['elasticip'] = address.public_ip
            ctx.source.instance.runtime_properties['instance_id'] = id
            elasticip.disassociate(ctx=ctx)

    def test_bad_address_disassociate(self):
        """ Tests that NonRecoverableError: Invalid Address is
            raised when an address that is not in the user's
            EC2 account is provided to the detach function
        """

        ctx = self.mock_relationship_ctx('test_bad_address_detach')

        with mock_ec2():
            ctx.target.node.properties['elasticip'] = '0.0.0.0'
            ex = self.assertRaises(NonRecoverableError,
                                   elasticip.disassociate, ctx=ctx)
            self.assertIn('InvalidAddress.NotFound', ex.message)

    def test_get_private_dns_name(self):
        """ tests that private_dns_name matches the regex for
            an FQDN
        """

        ctx = self.mock_ctx('test_get_private_dns_name')

        with mock_ec2():
            ec2_client = connection.EC2ConnectionClient().client()
            reservation = ec2_client.run_instances(
                TEST_AMI_IMAGE_ID, instance_type=TEST_INSTANCE_TYPE)
            id = reservation.instances[0].id
            instance_object = utils.get_instance_from_id(id, ctx=ctx)
            dns_name = utils.get_private_dns_name(instance_object, 6 * 30)
            self.assertRegexpMatches(dns_name, FQDN)

    def test_get_public_dns_name(self):
        """ tests that public_dns_name matches the regex for
            an FQDN
        """

        ctx = self.mock_ctx('test_get_public_dns_name')

        with mock_ec2():
            ec2_client = connection.EC2ConnectionClient().client()
            reservation = ec2_client.run_instances(
                TEST_AMI_IMAGE_ID, instance_type=TEST_INSTANCE_TYPE)
            id = reservation.instances[0].id
            instance_object = utils.get_instance_from_id(id, ctx=ctx)
            dns_name = utils.get_public_dns_name(instance_object, 6 * 30)
            self.assertRegexpMatches(dns_name, FQDN)

    def test_validate_creation(self):

        ctx = self.mock_ctx('test_validate_creation')

        with mock_ec2():
            ec2_client = connection.EC2ConnectionClient().client()
            a = ec2_client.allocate_address()
            ctx.instance.runtime_properties['elasticip'] = a.public_ip
            self.assertTrue(elasticip.creation_validation(ctx=ctx))

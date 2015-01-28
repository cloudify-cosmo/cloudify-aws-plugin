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
            'parameters': {
                'security_groups': ['sg-73cd3f1e']
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
                    'instance_id': 'i-abc1234',
                    'public_ip_address': '127.0.0.1'
                }
            })
        })

        elasticip_ctx = MockContext({
            'node': MockContext({
                'properties': {}
            }),
            'instance': MockContext({
                'runtime_properties': {
                    'aws_resource_id': ''
                }
            })
        })

        relationship_ctx = MockCloudifyContext(node_id=testname,
                                               source=instance_ctx,
                                               target=elasticip_ctx)

        return relationship_ctx

    @mock_ec2
    def test_allocate(self):
        """ Tests that the allocate function is 100% successful.
        """
        ctx = self.mock_ctx('test_create_address')

        elasticip.allocate(ctx=ctx)
        self.assertIn('aws_resource_id', ctx.instance.runtime_properties)

    @mock_ec2
    def test_good_address_release(self):
        """ Tests that when an address that is in the user's
            EC2 account is provided to the release function
            no errors are raised
        """

        ctx = self.mock_ctx('test_good_address_delete')

        ec2_client = connection.EC2ConnectionClient().client()
        address = ec2_client.allocate_address()
        ctx.instance.runtime_properties['aws_resource_id'] = \
            address.public_ip
        elasticip.release(ctx=ctx)
        self.assertNotIn('aws_resource_id',
                         ctx.instance.runtime_properties.keys())

    @mock_ec2
    def test_bad_address_release(self):
        """ Tests that when an address that is in the user's
            EC2 account is provided to the release function
            no errors are raised
        """

        ctx = self.mock_ctx('test_bad_address_release')

        ctx.instance.runtime_properties['aws_resource_id'] = \
            '127.0.0.1'
        ex = self.assertRaises(NonRecoverableError, elasticip.release, ctx=ctx)
        self.assertIn('InvalidAddress.NotFound', ex.message)

    @mock_ec2
    def test_good_address_associate(self):
        """ Tests that when an address that is in the user's
            EC2 account is provided to the attach function
            no errors are raised
        """

        ctx = self.mock_relationship_ctx('test_good_address_attach')

        ec2_client = connection.EC2ConnectionClient().client()
        reservation = ec2_client.run_instances(
            TEST_AMI_IMAGE_ID, instance_type=TEST_INSTANCE_TYPE)
        address = ec2_client.allocate_address()
        ctx.target.instance.runtime_properties['aws_resource_id'] = \
            address.public_ip
        ctx.source.instance.runtime_properties['aws_resource_id'] = \
            reservation.instances[0].id
        elasticip.associate(ctx=ctx)

    @mock_ec2
    def test_good_address_disassociate(self):
        """ Tests that when an address that is in the user's
            EC2 account is provided to the detach function
            no errors are raised
        """

        ctx = self.mock_relationship_ctx('test_good_address_detach')

        ec2_client = connection.EC2ConnectionClient().client()
        reservation = ec2_client.run_instances(
            TEST_AMI_IMAGE_ID, instance_type=TEST_INSTANCE_TYPE)
        instance_id = reservation.instances[0].id
        address = ec2_client.allocate_address()
        ctx.target.instance.runtime_properties['aws_resource_id'] = \
            address.public_ip
        ctx.source.instance.runtime_properties['instance_id'] = instance_id
        ctx.source.instance.runtime_properties['ip'] = address.public_ip
        elasticip.disassociate(ctx=ctx)

    @mock_ec2
    def test_bad_address_associate(self):
        """ Tests that when an address that is in the user's
            EC2 account is provided to the attach function
            no errors are raised
        """

        ctx = self.mock_relationship_ctx('test_bad_address_associate')

        ec2_client = connection.EC2ConnectionClient().client()
        reservation = ec2_client.run_instances(
            TEST_AMI_IMAGE_ID, instance_type=TEST_INSTANCE_TYPE)
        ctx.target.instance.runtime_properties['aws_resource_id'] = '127.0.0.1'
        ctx.source.instance.runtime_properties['aws_resource_id'] = \
            reservation.instances[0].id
        ex = self.assertRaises(NonRecoverableError, elasticip.associate,
                               ctx=ctx)
        ctx.source.instance.runtime_properties['public_ip_address'] = \
            '127.0.0.1'
        self.assertIn('InvalidAddress.NotFound', ex.message)

    @mock_ec2
    def test_bad_address_disassociate(self):
        """ Tests that NonRecoverableError: Invalid Address is
            raised when an address that is not in the user's
            EC2 account is provided to the detach function
        """

        ctx = self.mock_relationship_ctx('test_bad_address_detach')

        ctx.target.instance.runtime_properties['aws_resource_id'] = '0.0.0.0'
        ctx.source.instance.runtime_properties['public_ip_address'] = '0.0.0.0'
        ex = self.assertRaises(NonRecoverableError,
                               elasticip.disassociate, ctx=ctx)
        self.assertIn('InvalidAddress.NotFound', ex.message)

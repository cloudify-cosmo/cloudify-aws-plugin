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
            'use_external_resource': False,
            'resource_id': '',
            'image_id': TEST_AMI_IMAGE_ID,
            'instance_type': TEST_INSTANCE_TYPE,
            'parameters': {
                'security_group_ids': ['sg-73cd3f1e']
            }
        }

        ctx = MockCloudifyContext(
            node_id=test_node_id,
            properties=test_properties
        )

        return ctx

    def mock_elastic_ip_node(self, test_name):

        test_node_id = test_name
        test_properties = {
            'use_external_resource': False,
            'resource_id': ''
        }

        ctx = MockCloudifyContext(
            node_id=test_node_id,
            properties=test_properties
        )

        return ctx

    def mock_relationship_context(self, testname):

        instance_context = MockContext({
            'node': MockContext({
                'properties': {
                    'use_external_resource': False,
                    'resource_id': ''
                }
            }),
            'instance': MockContext({
                'runtime_properties': {
                    'aws_resource_id': 'i-abc1234',
                    'public_ip_address': '127.0.0.1'
                }
            })
        })

        elasticip_context = MockContext({
            'node': MockContext({
                'properties': {
                    'use_external_resource': False,
                    'resourece_id': '',
                }
            }),
            'instance': MockContext({
                'runtime_properties': {
                    'aws_resource_id': ''
                }
            })
        })

        relationship_context = MockCloudifyContext(
            node_id=testname, source=instance_context,
            target=elasticip_context)

        return relationship_context

    @mock_ec2
    def test_allocate(self):
        """ Tests that the allocate function assigns the aws_resource_id.
        """
        ctx = self.mock_ctx('test_allocate')

        elasticip.allocate(ctx=ctx)
        self.assertIn('aws_resource_id', ctx.instance.runtime_properties)

    @mock_ec2
    def test_external_resource(self):
        """ Tests that the allocate function assigns the aws_resource_id.
        """

        ec2_client = connection.EC2ConnectionClient().client()
        address = ec2_client.allocate_address(domain=None)
        ctx = self.mock_elastic_ip_node('test_allocate')
        ctx.node.properties['use_external_resource'] = True
        ctx.node.properties['resource_id'] = address.public_ip

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
        ex = self.assertRaises(
            NonRecoverableError, elasticip.release, ctx=ctx)
        self.assertIn(
            'Unable to release elasticip. Elasticip not in account.',
            ex.message)

    @mock_ec2
    def test_good_address_associate(self):
        """ Tests that when an address that is in the user's
            EC2 account is provided to the attach function
            no errors are raised
        """

        ctx = self.mock_relationship_context('test_good_address_associate')

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

        ctx = self.mock_relationship_context('test_good_address_detach')

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

        ctx = self.mock_relationship_context('test_bad_address_associate')

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

        ctx = self.mock_relationship_context('test_bad_address_detach')

        ctx.target.instance.runtime_properties['aws_resource_id'] = '0.0.0.0'
        ctx.source.instance.runtime_properties['public_ip_address'] = '0.0.0.0'
        ex = self.assertRaises(NonRecoverableError,
                               elasticip.disassociate, ctx=ctx)
        self.assertIn('InvalidAddress.NotFound', ex.message)

    @mock_ec2
    def test_validation(self):
        """ Tests that the allocate function assigns the aws_resource_id.
        """

        ctx = self.mock_elastic_ip_node('test_allocate')
        ctx.node.properties['use_external_resource'] = True
        ctx.node.properties['resource_id'] = '127.0.0.1'

        ex = self.assertRaises(
            NonRecoverableError, elasticip.creation_validation, ctx=ctx)
        self.assertIn('elasticip does not exist', ex.message)

    @mock_ec2
    def test_associate_no_instance_id(self):

        ctx = self.mock_relationship_context('test_associate_no_instance_id')
        del(ctx.source.instance.runtime_properties['aws_resource_id'])
        ex = self.assertRaises(
            NonRecoverableError, elasticip.associate, ctx=ctx)
        self.assertIn(
            'Cannot associate elasticip because aws_resource_id is not',
            ex.message)

    @mock_ec2
    def test_associate_no_elasticip_id(self):

        ctx = self.mock_relationship_context('test_associate_no_elasticip_id')
        del(ctx.target.instance.runtime_properties['aws_resource_id'])
        ex = self.assertRaises(
            NonRecoverableError, elasticip.associate, ctx=ctx)
        self.assertIn(
            'Cannot associate elasticip because aws_resource_id is not',
            ex.message)

    @mock_ec2
    def test_bad_address_external_resource(self):

        ctx = self.mock_ctx('test_bad_address_external_resource')

        ctx.node.properties['use_external_resource'] = True
        ctx.node.properties['resource_id'] = '127.0.0.1'
        ex = self.assertRaises(
            NonRecoverableError, elasticip.allocate, ctx=ctx)
        self.assertIn(
            'External elasticip was indicated',
            ex.message)

    @mock_ec2
    def test_release_existing(self):

        ctx = self.mock_ctx('test_release_existing')

        ec2_client = connection.EC2ConnectionClient().client()
        address = ec2_client.allocate_address()
        ctx.instance.runtime_properties['aws_resource_id'] = \
            address.public_ip
        ctx.node.properties['use_external_resource'] = True
        elasticip.release(ctx=ctx)
        self.assertNotIn(
            'aws_resource_id', ctx.instance.runtime_properties.keys())
        self.assertIsNotNone(ec2_client.get_all_addresses(address.public_ip))

    @mock_ec2
    def test_get_all_addresses_bad(self):

        ctx = self.mock_ctx('test_get_all_addresses_bad')
        output = elasticip._get_all_addresses(
            address='127.0.0.1', ctx=ctx)
        self.assertIsNone(output)

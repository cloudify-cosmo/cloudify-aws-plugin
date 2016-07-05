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

# Built-in Imports
import testtools

# Third Party Imports
from boto.ec2 import EC2Connection
from boto.vpc import VPCConnection
from moto import mock_ec2
from boto import exception

# Cloudify Imports is imported and used in operations
from cloudify_aws.ec2 import elasticip
from cloudify_aws import constants
from cloudify.state import current_ctx
from cloudify.mocks import MockContext
from cloudify.mocks import MockCloudifyContext
from cloudify.exceptions import NonRecoverableError

TEST_AMI_IMAGE_ID = 'ami-e214778a'
TEST_INSTANCE_TYPE = 't1.micro'
FQDN = '((?:[a-z][a-z\\.\\d\\-]+)\\.(?:[a-z][a-z\\-]+))(?![\\w\\.])'


class TestElasticIP(testtools.TestCase):

    def mock_ctx(self, test_name):

        test_node_id = test_name
        test_properties = {
            constants.AWS_CONFIG_PROPERTY: {},
            'use_external_resource': False,
            'resource_id': '',
            'image_id': TEST_AMI_IMAGE_ID,
            'instance_type': TEST_INSTANCE_TYPE,
            'parameters': {
                'security_group_ids': ['sg-73cd3f1e']
            },
            'domain': '',
        }

        ctx = MockCloudifyContext(
                node_id=test_node_id,
                properties=test_properties,
                provider_context={'resources': {}}
        )

        return ctx

    def mock_elastic_ip_node(self, test_name):

        test_node_id = test_name
        test_properties = {
            constants.AWS_CONFIG_PROPERTY: {},
            'use_external_resource': False,
            'resource_id': '',
            'domain': ''
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
                    constants.AWS_CONFIG_PROPERTY: {},
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
                    constants.AWS_CONFIG_PROPERTY: {},
                    'use_external_resource': False,
                    'resource_id': '',
                    'domain': '',
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

    def get_client(self):
        return EC2Connection()

    def create_vpc_client(self):
        return VPCConnection()

    def allocate_address(self, client):
        return client.allocate_address(domain=None)

    def run_instance(self, client):
        return client.run_instances(
                TEST_AMI_IMAGE_ID, instance_type=TEST_INSTANCE_TYPE)

    def get_address(self):
        client = self.get_client()
        address = self.allocate_address(client)
        return address

    def get_instance_id(self):
        client = self.get_client()
        reservation = self.run_instance(client)
        return reservation.instances[0].id

    def create_elasticip_for_checking(self):
        return elasticip.ElasticIP()

    def create_elasticipinstanceconnection_for_checking(self):
        return elasticip.ElasticIPInstanceConnection()

    @mock_ec2
    def test_allocate(self):
        """ This tests that allocate adds the runtime_properties."""

        ctx = self.mock_ctx('test_allocate')
        current_ctx.set(ctx=ctx)
        elasticip.ElasticIP().create(ctx=ctx)
        self.assertIn('aws_resource_id', ctx.instance.runtime_properties)
        self.assertNotIn('vpc_id', ctx.instance.runtime_properties)

    @mock_ec2
    def test_allocate_vpc(self):
        """ This tests that allocate and vpc adds the runtime_properties."""

        ctx = self.mock_ctx('test_allocate_vpc')
        vpc = self.create_vpc_client().create_vpc('10.10.10.0/16')
        ctx.provider_context['resources'] = {
            constants.VPC['AWS_RESOURCE_TYPE']: {
                'id': vpc.id,
                'external_resource': True
            }
        }
        current_ctx.set(ctx=ctx)
        elasticip.ElasticIP().create(ctx=ctx)
        self.assertIn('aws_resource_id', ctx.instance.runtime_properties)

    @mock_ec2
    def test_allocate_backward_compatibility(self):
        """ This tests that allocate adds the runtime_properties."""

        ctx = self.mock_ctx('test_allocate')
        del ctx.node.properties['domain']
        current_ctx.set(ctx=ctx)
        elasticip.ElasticIP().create(ctx=ctx)
        self.assertIn('aws_resource_id', ctx.instance.runtime_properties)

    @mock_ec2
    def test_associate_external_elasticip_or_instance(self):
        """ This tests that this function returns False
        if use_external_resource is false.
        """

        ctx = self.mock_relationship_context(
                'test_associate_external_elasticip_or_instance')
        current_ctx.set(ctx=ctx)
        test_elasticipinstanceconnection = \
            self.create_elasticipinstanceconnection_for_checking()
        ctx.source.node.properties['use_external_resource'] = False

        output = \
            test_elasticipinstanceconnection\
            ._associate_external_elasticip_or_instance('127.0.0.1')

        self.assertEqual(False, output)

    @mock_ec2
    def test_release_external_elasticip(self):
        """ This tests that this function returns False
        if use_external_resource is false.
        """

        ctx = self.mock_ctx(
                'test_release_external_elasticip')
        current_ctx.set(ctx=ctx)
        ctx.node.properties['use_external_resource'] = False
        test_elasticip = self.create_elasticip_for_checking()

        output = \
            test_elasticip.delete_external_resource_naively()

        self.assertEqual(False, output)

    @mock_ec2
    def test_external_resource(self):
        """ This tests that allocate sets the aws_resource_id
        runtime_properties
        """

        ctx = self.mock_elastic_ip_node('test_external_resource')
        current_ctx.set(ctx=ctx)
        address = self.get_address()
        ctx.node.properties['use_external_resource'] = True
        ctx.node.properties['resource_id'] = address.public_ip
        elasticip.ElasticIP().create(ctx=ctx)
        self.assertIn('aws_resource_id', ctx.instance.runtime_properties)

    @mock_ec2
    def test_allocate_external_elasticip(self):
        """ This tests that this function returns False
        if use_external_resource is false.
        """

        ctx = self.mock_ctx(
                'test_allocate_external_elasticip')
        current_ctx.set(ctx=ctx)
        ctx.node.properties['use_external_resource'] = False
        test_elasticip = self.create_elasticip_for_checking()

        output = \
            test_elasticip.use_external_resource_naively()

        self.assertEqual(False, output)

    @mock_ec2
    def test_good_address_release(self):
        """ This tests that release unsets the aws_resource_id
        runtime_properties
        """

        ctx = self.mock_ctx('test_good_address_delete')
        current_ctx.set(ctx=ctx)
        address = self.get_address()
        ctx.instance.runtime_properties['aws_resource_id'] = \
            address.public_ip
        ctx.instance.runtime_properties['allocation_id'] = 'random'
        elasticip.delete(ctx=ctx)
        self.assertNotIn('aws_resource_id',
                         ctx.instance.runtime_properties)
        self.assertNotIn('instance_id', ctx.instance.runtime_properties)

    @mock_ec2
    def test_disassociate_external_elasticip_or_instance(self):
        """ This tests that this function returns False
        if use_external_resource is false.
        """

        ctx = self.mock_relationship_context(
                'test_disassociate_external_elasticip_or_instance')
        current_ctx.set(ctx=ctx)
        ctx.source.node.properties['use_external_resource'] = False
        test_elasticipinstanceconnection = \
            self.create_elasticipinstanceconnection_for_checking()

        output = \
            test_elasticipinstanceconnection\
            ._disassociate_external_elasticip_or_instance()

        self.assertEqual(False, output)

    @mock_ec2
    def test_bad_address_release(self):
        """ tests that release raises an error when
        the address does not exist in the users account.
        """

        ctx = self.mock_ctx('test_bad_address_release')
        current_ctx.set(ctx=ctx)
        ctx.instance.runtime_properties['aws_resource_id'] = \
            '127.0.0.1'
        ex = self.assertRaises(
                NonRecoverableError, elasticip.ElasticIP().delete, ctx=ctx)
        self.assertIn(
                'Unable to release elasticip. Elasticip not in account.',
                ex.message)

    @mock_ec2
    def test_good_address_associate(self):
        """ Tests that associate runs when clean. """

        ctx = self.mock_relationship_context('test_good_address_associate')
        current_ctx.set(ctx=ctx)
        address = self.get_address()
        instance_id = self.get_instance_id()
        ctx.target.instance.runtime_properties['aws_resource_id'] = \
            address.public_ip
        ctx.source.instance.runtime_properties['aws_resource_id'] = \
            instance_id
        elasticip.ElasticIPInstanceConnection().associate(ctx=ctx)
        self.assertIn('instance_id',
                      ctx.target.instance.runtime_properties)
        self.assertEquals(instance_id,
                          ctx.target.instance.runtime_properties.get(
                                  'instance_id'))

    @mock_ec2
    def test_good_address_associate_with_new_domain_property(self):
        """ Tests that associate runs when clean. """

        ctx = self.mock_relationship_context('test_good_address_associate')
        ctx.source.node.properties['domain'] = ''
        current_ctx.set(ctx=ctx)
        address = self.get_address()
        instance_id = self.get_instance_id()
        ctx.target.instance.runtime_properties['aws_resource_id'] = \
            address.public_ip
        ctx.source.instance.runtime_properties['aws_resource_id'] = \
            instance_id
        ctx.source.instance.runtime_properties['vpc_id'] = \
            self.create_vpc_client().create_vpc('10.10.10.0/16').id
        elasticip.ElasticIPInstanceConnection().associate(ctx=ctx)
        self.assertIn('instance_id',
                      ctx.target.instance.runtime_properties)
        self.assertEquals(instance_id,
                          ctx.target.instance.runtime_properties.get(
                                  'instance_id'))
        self.assertIn('vpc_id', ctx.target.instance.runtime_properties)

    @mock_ec2
    def test_good_address_associate_vpc_elastic_ip(self):
        """ Tests that associate runs when clean. """

        ctx = self.mock_relationship_context('test_good_address_associate')
        ctx.source.node.properties['domain'] = 'vpc'
        current_ctx.set(ctx=ctx)
        address = self.get_address()
        instance_id = self.get_instance_id()
        ctx.target.instance.runtime_properties['aws_resource_id'] = \
            address.public_ip
        ctx.source.instance.runtime_properties['aws_resource_id'] = \
            instance_id
        elasticip.ElasticIPInstanceConnection().associate(ctx=ctx)

    @mock_ec2
    def test_good_address_disassociate(self):
        """ Tests that disassociate runs when clean. """

        ctx = self.mock_relationship_context('test_good_address_detach')
        current_ctx.set(ctx=ctx)
        address = self.get_address()
        instance_id = self.get_instance_id()

        ctx.target.instance.runtime_properties['aws_resource_id'] = \
            address.public_ip
        ctx.source.instance.runtime_properties['instance_id'] = instance_id
        ctx.target.instance.runtime_properties['instance_id'] = instance_id
        ctx.source.instance.runtime_properties['ip'] = address.public_ip
        elasticip.ElasticIPInstanceConnection().disassociate(ctx=ctx)

    @mock_ec2
    def test_bad_address_associate(self):
        """ Tests that when an address that is in the user's
            EC2 account is provided to the attach function
            no errors are raised
        """

        ctx = self.mock_relationship_context('test_bad_address_associate')
        current_ctx.set(ctx=ctx)
        instance_id = self.get_instance_id()
        ctx.target.instance.runtime_properties['aws_resource_id'] = '127.0.0.1'
        ctx.source.instance.runtime_properties['aws_resource_id'] = \
            instance_id
        ex = self.assertRaises(NonRecoverableError,
                               elasticip.ElasticIPInstanceConnection()
                               .associate, ctx=ctx)
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
        current_ctx.set(ctx=ctx)
        ctx.target.instance.runtime_properties['aws_resource_id'] = '0.0.0.0'
        ctx.source.instance.runtime_properties['public_ip_address'] = '0.0.0.0'
        ex = self.assertRaises(NonRecoverableError,
                               elasticip.ElasticIPInstanceConnection()
                               .disassociate, ctx=ctx)
        self.assertIn('no matching elastic ip in account', ex.message)

    @mock_ec2
    def test_validation(self):
        """ Tests that creation_validation raises an error
        the Elastic IP doesn't exist in the account and use_external_resource
        is true.
        """

        ctx = self.mock_elastic_ip_node('test_allocate')
        ctx.node.properties['use_external_resource'] = True
        ctx.node.properties['resource_id'] = '127.0.0.1'
        current_ctx.set(ctx=ctx)
        ex = self.assertRaises(
                NonRecoverableError,
                elasticip.ElasticIP().creation_validation, ctx=ctx)
        self.assertIn('elasticip does not exist', ex.message)

    @mock_ec2
    def test_validation_not_external(self):
        """ Tests that creation_validation raises an error
        the Elastic IP exist in the account and use_external_resource
        is false.
        """

        ctx = self.mock_elastic_ip_node('test_validation_not_external')
        current_ctx.set(ctx=ctx)
        address = self.get_address()
        ctx.node.properties['use_external_resource'] = False
        ctx.node.properties['resource_id'] = address.public_ip
        ex = self.assertRaises(
                NonRecoverableError,
                elasticip.ElasticIP().creation_validation, ctx=ctx)
        self.assertIn('elasticip exists', ex.message)

    @mock_ec2
    def test_associate_no_instance_id(self):
        """ Tests that associate will raise an error if aws_resource_id
        runtime property is not set.
        """

        ctx = self.mock_relationship_context('test_associate_no_instance_id')
        current_ctx.set(ctx=ctx)
        del(ctx.source.instance.runtime_properties['aws_resource_id'])
        ex = self.assertRaises(
                NonRecoverableError,
                elasticip.ElasticIPInstanceConnection().associate, ctx=ctx)
        self.assertIn(
                'Cannot associate elasticip because aws_resource_id is not',
                ex.message)

    @mock_ec2
    def test_bad_address_external_resource(self):

        ctx = self.mock_ctx('test_bad_address_external_resource')
        current_ctx.set(ctx=ctx)
        ctx.node.properties['use_external_resource'] = True
        ctx.node.properties['resource_id'] = '127.0.0.1'
        ex = self.assertRaises(
                NonRecoverableError,
                elasticip.ElasticIP().raise_forbidden_external_resource, ctx)
        self.assertIn(
                'is not in this account',
                ex.message)

    @mock_ec2
    def test_release_existing(self):
        """ Tests that release actually releases.
        """

        ctx = self.mock_ctx('test_release_existing')
        current_ctx.set(ctx=ctx)
        address = self.get_address()
        ctx.instance.runtime_properties['aws_resource_id'] = \
            address.public_ip
        ctx.node.properties['use_external_resource'] = True
        elasticip.delete(ctx=ctx)
        self.assertNotIn(
                'aws_resource_id', ctx.instance.runtime_properties)
        ec2_client = self.get_client()
        self.assertIsNotNone(ec2_client.get_all_addresses(address.public_ip))

    @mock_ec2
    def test_get_all_addresses_bad(self):
        """ tests that _get_all_addresses returns None
        for a bad address.
        """
        ctx = self.mock_ctx('test_get_all_addresses_bad')
        current_ctx.set(ctx=ctx)
        test_elasticip = self.create_elasticip_for_checking()

        output = test_elasticip._get_all_addresses(
                address='127.0.0.1')
        self.assertIsNone(output)

    @mock_ec2
    def test_existing_address_associate(self):
        """ Tests that when an address that is in the user's
            EC2 account is provided to the associate function
            no errors are raised
        """

        ctx = self.mock_relationship_context('test_existing_address_associate')
        current_ctx.set(ctx=ctx)
        address = self.get_address()
        instance_id = self.get_instance_id()
        ctx.target.node.properties['use_external_resource'] = True
        ctx.target.node.properties['resource_id'] = address.public_ip
        ctx.target.instance.runtime_properties['aws_resource_id'] = \
            address.public_ip
        ctx.source.node.properties['use_external_resource'] = True
        ctx.source.node.properties['resource_id'] = instance_id
        ctx.source.instance.runtime_properties['aws_resource_id'] = \
            instance_id
        elasticip.ElasticIPInstanceConnection().associate(ctx=ctx)
        self.assertEqual(
                address.public_ip,
                ctx.source.instance.runtime_properties['public_ip_address'])

    @mock_ec2
    def test_existing_address_disassociate(self):
        """ Tests that when an address that is in the user's
            EC2 account is provided to the disassociate function
            no errors are raised
        """

        ctx = self.mock_relationship_context(
                'test_existing_address_disassociate')
        current_ctx.set(ctx=ctx)
        address = self.get_address()
        instance_id = self.get_instance_id()
        ctx.target.node.properties['use_external_resource'] = True
        ctx.target.node.properties['resource_id'] = address.public_ip
        ctx.target.instance.runtime_properties['aws_resource_id'] = \
            address.public_ip
        ctx.source.node.properties['use_external_resource'] = True
        ctx.source.node.properties['resource_id'] = instance_id
        ctx.source.instance.runtime_properties['aws_resource_id'] = \
            instance_id
        ctx.source.instance.runtime_properties['public_ip_address'] = \
            address.public_ip
        elasticip.ElasticIPInstanceConnection().disassociate(ctx=ctx)
        self.assertNotIn(
                'public_ip_address', ctx.source.instance.runtime_properties)

    @mock_ec2
    def test_disassociate_external_elasticip(self):
        """ Tests that when an address that is in the user's
            EC2 account is provided to the disassociate function
            and use_external_resource is true
            no errors are raised
        """

        ctx = self.mock_relationship_context(
                'test_disassociate_external_elasticip')
        current_ctx.set(ctx=ctx)
        address = self.get_address()
        instance_id = self.get_instance_id()
        ctx.target.node.properties['use_external_resource'] = False
        ctx.target.node.properties['resource_id'] = address.public_ip
        ctx.source.node.properties['use_external_resource'] = False
        ctx.source.node.properties['resource_id'] = instance_id
        ctx.source.instance.runtime_properties['aws_resource_id'] = \
            instance_id
        test_elasticipinstanceconnection = \
            self.create_elasticipinstanceconnection_for_checking()

        output = \
            test_elasticipinstanceconnection\
            ._disassociate_external_elasticip_or_instance()
        self.assertEqual(False, output)

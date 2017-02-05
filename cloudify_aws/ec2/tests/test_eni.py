########
# Copyright (c) 2017 GigaSpaces Technologies Ltd. All rights reserved
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
import mock

# Third Party Imports
from moto import mock_ec2
from boto.ec2 import EC2Connection
from boto.vpc import VPCConnection

# Cloudify Imports is imported and used in operations
from cloudify_aws import constants
from .. import eni
from cloudify.state import current_ctx
from cloudify.mocks import MockContext
from cloudify.mocks import MockCloudifyContext
from cloudify.exceptions import NonRecoverableError, RecoverableError

TEST_AMI_IMAGE_ID = 'ami-e214778a'
TEST_INSTANCE_TYPE = 't1.micro'
FQDN = '((?:[a-z][a-z\\.\\d\\-]+)\\.(?:[a-z][a-z\\-]+))(?![\\w\\.])'


class TestNetworkInterface(testtools.TestCase):

    @staticmethod
    def mock_ctx(test_name):

        test_node_id = test_name
        test_properties = {
            constants.AWS_CONFIG_PROPERTY: {},
            'use_external_resource': False,
            'resource_id': '',
            'security_group_ids': ['sg-73cd3f1e']
        }

        ctx = MockCloudifyContext(
            node_id=test_node_id,
            properties=test_properties,
            provider_context={'resources': {}}
        )

        return ctx

    @staticmethod
    def mock_network_interface_node(test_name):

        test_node_id = test_name
        test_properties = {
            constants.AWS_CONFIG_PROPERTY: {},
            'use_external_resource': False,
            'resource_id': '',
            'parameters': {
                'subnet_id': 'subnet-73cd3f1e',
                'groups': ['sg-73cd3f1e']
            }
        }

        ctx = MockCloudifyContext(
            node_id=test_node_id,
            properties=test_properties
        )

        return ctx

    @staticmethod
    def mock_relationship_context(testname):

        network_interface_context = MockContext({
            'node': MockContext({
                'properties': {
                    constants.AWS_CONFIG_PROPERTY: {},
                    'use_external_resource': False,
                    'subnet_id': 'subnet-73cd3f1e',
                    'security_group_ids': ['sg-73cd3f1e']
                }
            }),
            'instance': MockContext({
                'runtime_properties': {
                    'aws_resource_id': ''
                }
            })
        })

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

        relationship_context = MockCloudifyContext(
            node_id=testname, source=network_interface_context,
            target=instance_context)

        return relationship_context

    @staticmethod
    def get_client():
        return EC2Connection()

    @staticmethod
    def create_vpc_client():
        return VPCConnection()

    @mock_ec2
    def test_create_bad_subnet_in_parameters(self):
        """ Tries to use a bad subnet id to create EIN."""

        ctx = self.mock_network_interface_node(
            'test_create_bad_subnet_in_parameters')
        current_ctx.set(ctx=ctx)
        output = self.assertRaises(
            NonRecoverableError,
            eni.create,
            ctx=ctx
        )
        self.assertIn('InvalidSubnetID.NotFound', output.message)

    @mock_ec2
    def test_create_subnet_in_relationship(self):
        """ Tries to use a good subnet ID to via a relationships."""

        vpc_client = self.create_vpc_client()
        vpc = vpc_client.create_vpc('10.10.10.0/16')
        subnet = vpc_client.create_subnet(vpc.id, '10.10.10.0/16')
        ctx = self.mock_network_interface_node(
            'test_create_subnet_in_relationship')
        ctx.node.properties['parameters']['subnet_id'] = subnet.id
        current_ctx.set(ctx=ctx)
        with mock.patch(
                'cloudify_aws.utils.get_target_external_resource_ids',
                return_value=[subnet.id]):
            eni.create(ctx=ctx)
            self.assertIn('aws_resource_id', ctx.instance.runtime_properties)

    @mock_ec2
    def test_create_subnet_in_relationship_too_many(self):
        """ Tries to use a too many subnet IDs via a relationship."""

        vpc_client = self.create_vpc_client()
        vpc = vpc_client.create_vpc('10.10.10.0/16')
        subnet = vpc_client.create_subnet(vpc.id, '10.10.10.0/16')
        ctx = self.mock_network_interface_node(
            'test_create_subnet_in_relationship_too_many')
        ctx.node.properties['parameters']['subnet_id'] = subnet.id
        current_ctx.set(ctx=ctx)
        with mock.patch(
                'cloudify_aws.utils.get_target_external_resource_ids',
                return_value=[subnet.id,
                              ctx.node.properties['parameters']['subnet_id']]):
            output = self.assertRaises(
                NonRecoverableError,
                eni.create,
                ctx=ctx
            )
            self.assertIn(
                'A network interface can only exist in one subnet.',
                output.message)

    @mock_ec2
    def test_create_with_existing_subnet_in_parameters(self):
        """ Tries to use a good subnet ID to create EIN."""

        ctx = self.mock_network_interface_node(
            'test_create_with_existing_subnet_in_parameters')
        vpc_client = self.create_vpc_client()
        vpc = vpc_client.create_vpc('10.10.10.0/16')
        subnet = vpc_client.create_subnet(vpc.id, '10.10.10.0/16')
        ctx.node.properties['parameters']['subnet_id'] = subnet.id
        current_ctx.set(ctx=ctx)
        eni.create(ctx=ctx)
        self.assertIn('aws_resource_id', ctx.instance.runtime_properties)

    @mock_ec2
    def test_create_external_resource_id_exists(self):
        """ Uses an existing EIN and tries to add it to Cloudify."""

        ctx = self.mock_network_interface_node(
            'test_create_external_resource_id_exists')
        vpc_client = self.create_vpc_client()
        vpc = vpc_client.create_vpc('10.10.10.0/16')
        subnet = vpc_client.create_subnet(vpc.id, '10.10.10.0/16')
        ec2_client = self.get_client()
        ein = ec2_client.create_network_interface(subnet.id)
        ctx.node.properties['use_external_resource'] = True
        ctx.node.properties['resource_id'] = ein.id
        current_ctx.set(ctx=ctx)
        eni.create(ctx=ctx)
        self.assertIn('aws_resource_id', ctx.instance.runtime_properties)

    @mock_ec2
    def test_create_external_resource_id_bad(self):
        """ Uses a bad existing EIN and tries to add it to Cloudify."""

        ctx = self.mock_network_interface_node(
            'test_create_external_resource_id_bad')
        vpc_client = self.create_vpc_client()
        vpc = vpc_client.create_vpc('10.10.10.0/16')
        subnet = vpc_client.create_subnet(vpc.id, '10.10.10.0/16')
        ec2_client = self.get_client()
        ein = ec2_client.create_network_interface(subnet.id)
        ein.delete()
        ctx.node.properties['use_external_resource'] = True
        ctx.node.properties['resource_id'] = ein.id
        current_ctx.set(ctx=ctx)
        output = self.assertRaises(
            NonRecoverableError,
            eni.create,
            ctx=ctx
        )
        self.assertIn('Cannot use_external_resource because', output.message)

    @mock_ec2
    def test_attach_external_interface_instance(self):
        """ Tries to attach existing interface to existing instance
        """

        ctx = self.mock_relationship_context(
            'test_attach_external_interface_instance')

        vpc_client = self.create_vpc_client()
        vpc = vpc_client.create_vpc('10.10.10.0/16')
        subnet = vpc_client.create_subnet(vpc.id, '10.10.10.0/16')
        ec2_client = self.get_client()
        ein = ec2_client.create_network_interface(subnet.id)
        reservation = ec2_client.run_instances(
            image_id=TEST_AMI_IMAGE_ID,
            instance_type=TEST_INSTANCE_TYPE)
        ctx.source.instance.runtime_properties['aws_resource_id'] = \
            ein.id
        ctx.target.instance.runtime_properties['aws_resource_id'] = \
            reservation.instances[0].id
        current_ctx.set(ctx=ctx)
        eni.InterfaceAttachment().associate(ctx=ctx)
        self.assertIn('attachment_id',
                      ctx.source.instance.runtime_properties)

    @mock_ec2
    def test_attach_external_interface_instance_failed(self):
        """ Tries to attach existing interface to existing instance
        """

        ctx = self.mock_relationship_context(
            'test_attach_external_interface_instance')

        vpc_client = self.create_vpc_client()
        vpc = vpc_client.create_vpc('10.10.10.0/16')
        subnet = vpc_client.create_subnet(vpc.id, '10.10.10.0/16')
        ec2_client = self.get_client()
        ein = ec2_client.create_network_interface(subnet.id)
        reservation = ec2_client.run_instances(
            image_id=TEST_AMI_IMAGE_ID,
            instance_type=TEST_INSTANCE_TYPE)
        ctx.source.instance.runtime_properties['aws_resource_id'] = \
            ein.id
        ctx.target.instance.runtime_properties['aws_resource_id'] = \
            reservation.instances[0].id
        current_ctx.set(ctx=ctx)
        with mock.patch(
                'cloudify_aws.base.AwsBase.execute',
                return_value=False):
            output = self.assertRaises(
                RecoverableError,
                eni.InterfaceAttachment().associate,
                ctx=ctx
            )
            self.assertIn('Failed to attach eni',
                          output.message)

    @mock_ec2
    def test_attach_external_interface_bad_instance(self):
        """ tries to attach existing interface to bad instance
        """

        ctx = self.mock_relationship_context(
            'test_attach_external_instance')

        vpc_client = self.create_vpc_client()
        vpc = vpc_client.create_vpc('10.10.10.0/16')
        subnet = vpc_client.create_subnet(vpc.id, '10.10.10.0/16')
        ec2_client = self.get_client()
        ein = ec2_client.create_network_interface(subnet.id)
        ctx.source.instance.runtime_properties['aws_resource_id'] = \
            ein.id
        ctx.target.instance.runtime_properties['aws_resource_id'] = \
            'i-73cd3f1e'
        current_ctx.set(ctx=ctx)
        output = self.assertRaises(
            NonRecoverableError,
            eni.InterfaceAttachment().associate,
            ctx=ctx
        )
        self.assertIn('InvalidInstanceID.NotFound', output.message)

    @mock_ec2
    def test_detach_external_interface_instance(self):
        """ tries to detach cleanly
        """

        ctx = self.mock_relationship_context(
            'test_attach_external_instance')

        vpc_client = self.create_vpc_client()
        vpc = vpc_client.create_vpc('10.10.10.0/16')
        subnet = vpc_client.create_subnet(vpc.id, '10.10.10.0/16')
        ec2_client = self.get_client()
        ein = ec2_client.create_network_interface(subnet.id)
        reservation = ec2_client.run_instances(
            image_id=TEST_AMI_IMAGE_ID,
            instance_type=TEST_INSTANCE_TYPE)
        ctx.source.node.properties['use_external_resource'] = True
        ctx.source.node.properties['resource_id'] = ein.id
        ctx.source.instance.runtime_properties['aws_resource_id'] = \
            ein.id
        ctx.target.node.properties['use_external_resource'] = True
        ctx.target.node.properties['resource_id'] = \
            reservation.instances[0].id
        ctx.target.instance.runtime_properties['aws_resource_id'] = \
            reservation.instances[0].id
        current_ctx.set(ctx=ctx)
        eni.associate(ctx=ctx)
        eni.disassociate(ctx=ctx)
        self.assertNotIn('attachment_id',
                         ctx.source.instance.runtime_properties)

    @mock_ec2
    def test_detach_external_interface_instance_failed(self):
        """ tries to detach and fails
        """

        ctx = self.mock_relationship_context(
            'test_attach_external_instance')

        vpc_client = self.create_vpc_client()
        vpc = vpc_client.create_vpc('10.10.10.0/16')
        subnet = vpc_client.create_subnet(vpc.id, '10.10.10.0/16')
        ec2_client = self.get_client()
        ein = ec2_client.create_network_interface(subnet.id)
        reservation = ec2_client.run_instances(
            image_id=TEST_AMI_IMAGE_ID,
            instance_type=TEST_INSTANCE_TYPE)
        ctx.source.node.properties['use_external_resource'] = True
        ctx.source.node.properties['resource_id'] = ein.id
        ctx.source.instance.runtime_properties['aws_resource_id'] = \
            ein.id
        ctx.target.node.properties['use_external_resource'] = True
        ctx.target.node.properties['resource_id'] = \
            reservation.instances[0].id
        ctx.target.instance.runtime_properties['aws_resource_id'] = \
            reservation.instances[0].id
        current_ctx.set(ctx=ctx)
        eni.InterfaceAttachment().associate(ctx=ctx)
        with mock.patch(
                'cloudify_aws.base.AwsBase.execute',
                return_value=False):
            output = self.assertRaises(
                RecoverableError,
                eni.InterfaceAttachment().disassociate,
                ctx=ctx
            )
            self.assertIn('Failed to detach network interface',
                          output.message)

    @mock_ec2
    def test_delete_with_existing_subnet_in_parameters(self):
        """ tries to delete cleanly."""

        ctx = self.mock_network_interface_node(
            'test_delete_with_existing_subnet_in_parameters')
        vpc_client = self.create_vpc_client()
        vpc = vpc_client.create_vpc('10.10.10.0/16')
        subnet = vpc_client.create_subnet(vpc.id, '10.10.10.0/16')
        ctx.node.properties['parameters']['subnet_id'] = subnet.id
        current_ctx.set(ctx=ctx)
        eni.create(ctx=ctx)
        eni.delete(ctx=ctx)
        self.assertNotIn('aws_resource_id', ctx.instance.runtime_properties)

    @mock_ec2
    def test_delete_with_existing_subnet_in_parameters_no_interface(self):
        """ tries to delete a non existing interface."""

        ctx = self.mock_network_interface_node(
            'test_delete_with_existing_subnet_in_parameters_no_interface'
        )
        vpc_client = self.create_vpc_client()
        vpc = vpc_client.create_vpc('10.10.10.0/16')
        subnet = vpc_client.create_subnet(vpc.id, '10.10.10.0/16')
        ctx.node.properties['parameters']['subnet_id'] = subnet.id
        current_ctx.set(ctx=ctx)
        eni.create(ctx=ctx)
        ec2_client = self.get_client()
        ein_id = ctx.instance.runtime_properties['aws_resource_id']
        ec2_client.delete_network_interface(network_interface_id=ein_id)
        output = self.assertRaises(
            NonRecoverableError,
            eni.delete,
            ctx=ctx
        )
        self.assertIn('Cannot use_external_resource because resource',
                      output.message)

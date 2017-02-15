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
from moto import mock_ec2
from boto.ec2 import EC2Connection

# Cloudify Imports is imported and used in operations
from cloudify_aws.ec2 import ebs
from cloudify.state import current_ctx
from cloudify.mocks import MockContext
from cloudify_aws import constants, connection
from cloudify.mocks import MockCloudifyContext
from cloudify.exceptions import NonRecoverableError

TEST_AMI_IMAGE_ID = 'ami-e214778a'
TEST_INSTANCE_TYPE = 't1.micro'
FQDN = '((?:[a-z][a-z\\.\\d\\-]+)\\.(?:[a-z][a-z\\-]+))(?![\\w\\.])'
TEST_ZONE = 'us-east-1a'
TEST_SIZE = 2
TEST_DEVICE = '/dev/null'
BAD_VOLUME_ID = 'vol-a51c05d7'
BAD_INSTANCE_ID = 'i-4339wSD9'


class TestEBS(testtools.TestCase):

    def mock_ctx(self, test_name, zone=TEST_ZONE):

        test_node_id = test_name
        test_properties = {
            constants.AWS_CONFIG_PROPERTY: {},
            'use_external_resource': False,
            'resource_id': '',
            'tags': {},
            'name': test_name,
            'size': TEST_SIZE,
            constants.ZONE: zone,
            'device': TEST_DEVICE
        }

        ctx = MockCloudifyContext(
            node_id=test_node_id,
            properties=test_properties
        )

        return ctx

    def mock_volume_node(self, test_name):

        test_node_id = test_name
        test_properties = {
            constants.AWS_CONFIG_PROPERTY: {},
            'use_external_resource': False,
            'resource_id': '',
            'tags': {},
            'name': test_name,
            constants.ZONE: '',
            'size': '',
            'device': ''
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
                    'aws_resource_id': 'i-abc1234'
                }
            })
        })

        volume_context = MockContext({
            'node': MockContext({
                'properties': {
                    constants.AWS_CONFIG_PROPERTY: {},
                    'use_external_resource': False,
                    'resource_id': '',
                    constants.ZONE: '',
                    'size': '',
                    'device': TEST_DEVICE
                }
            }),
            'instance': MockContext({
                'runtime_properties': {
                    'aws_resource_id': ''
                }
            })
        })

        relationship_context = MockCloudifyContext(
            node_id=testname, source=volume_context,
            target=instance_context)

        return relationship_context

    def get_client(self):
        return EC2Connection()

    def create_volume(self, client):
        return client.create_volume(
            size=TEST_SIZE,
            zone=TEST_ZONE)

    def run_instance(self, client):
        return client.run_instances(
            TEST_AMI_IMAGE_ID, instance_type=TEST_INSTANCE_TYPE)

    def get_volume(self):
        client = self.get_client()
        volume = self.create_volume(client)
        return volume

    def get_instance_id(self):
        client = self.get_client()
        reservation = self.run_instance(client)
        return reservation.instances[0].id

    def create_volume_for_checking(self):
        return ebs.Ebs()

    def create_volumeinstanceconn_for_checking(self):
        return ebs.VolumeInstanceConnection()

    @mock_ec2
    def test_create(self):
        """ This tests that allocate adds the runtime_properties."""

        ctx = self.mock_ctx('test_create')
        current_ctx.set(ctx=ctx)
        args = dict()
        ebs.create(args, ctx=ctx)
        self.assertIn('aws_resource_id', ctx.instance.runtime_properties)

    @mock_ec2
    def test_create_with_zone(self):
        """ This tests that allocate zone is updated with the users
        zone input."""

        zone = 'us-east-1b'
        ctx = self.mock_ctx('test_create_with_zone', zone=zone)
        current_ctx.set(ctx=ctx)
        args = {constants.ZONE: zone}
        ebs.create(args, ctx=ctx)
        self.assertIn('aws_resource_id', ctx.instance.runtime_properties)
        self.assertIn(constants.ZONE, ctx.instance.runtime_properties)
        self.assertEqual(zone, ctx.instance.runtime_properties.get(
            constants.ZONE))

    @mock_ec2
    def test_start(self):
        """This tests that start adds tags"""

        ctx = self.mock_ctx('test_start')
        current_ctx.set(ctx=ctx)

        ec2_client = connection.EC2ConnectionClient().client()
        volume = ec2_client.create_volume(TEST_SIZE, TEST_ZONE)
        volume_id = volume.id
        ctx.instance.runtime_properties['aws_resource_id'] = volume_id
        ebs.start(ctx=ctx)
        volume_list = ec2_client.get_all_volumes(volume_ids=volume_id)
        volume_object = volume_list[0]
        self.assertEquals(volume_object.tags.get('resource_id'),
                          ctx.instance.id)

    @mock_ec2
    def test_attach_external_volume_or_instance(self):
        """ This tests that this function returns False
        if use_external_resource is false.
        """

        ctx = self.mock_relationship_context(
            'test_attach_external_volume_or_instance')
        current_ctx.set(ctx=ctx)
        ctx.source.node.properties['use_external_resource'] = False
        ctx.target.node.properties['resource_id'] = BAD_INSTANCE_ID
        test_volumeinstanceconn = self.create_volumeinstanceconn_for_checking()

        output = \
            test_volumeinstanceconn.use_source_external_resource_naively()

        self.assertEqual(False, output)

    @mock_ec2
    def test_delete_external_volume(self):
        """ This tests that this function returns False
        if use_external_resource is false.
        """

        ctx = self.mock_ctx(
            'test_delete_external_volume')
        current_ctx.set(ctx=ctx)
        test_volume = self.create_volume_for_checking()

        output = \
            test_volume.delete_external_resource_naively()

        self.assertEqual(False, output)

    @mock_ec2
    def test_external_resource(self):
        """ This tests that create sets the aws_resource_id
        runtime_properties
        """

        ctx = self.mock_volume_node('test_external_resource')
        current_ctx.set(ctx=ctx)
        volume = self.get_volume()
        ctx.node.properties['use_external_resource'] = True
        ctx.node.properties['resource_id'] = volume.id
        args = dict()
        ebs.create(args)
        self.assertIn('aws_resource_id', ctx.instance.runtime_properties)

    @mock_ec2
    def test_create_external_volume(self):
        """ This tests that this function returns False
        if use_external_resource is false.
        """

        ctx = self.mock_ctx(
            'test_create_external_volume')
        current_ctx.set(ctx=ctx)
        test_volume = self.create_volume_for_checking()

        output = \
            test_volume.created()

        self.assertEqual(True, output)

    @mock_ec2
    def test_volume_delete(self):
        """ This tests that release unsets the aws_resource_id
        runtime_properties
        """

        ctx = self.mock_ctx('test_volume_delete')
        current_ctx.set(ctx=ctx)
        volume = self.get_volume()
        ctx.instance.runtime_properties['aws_resource_id'] = \
            volume.id
        ebs.delete(ctx=ctx)
        self.assertNotIn('aws_resource_id',
                         ctx.instance.runtime_properties)

    @mock_ec2
    def test_volume_delete_with_zone(self):
        """ This tests that release unsets the aws_resource_id
        and zone runtime_properties
        """

        ctx = self.mock_ctx('test_volume_delete_with_zone')
        current_ctx.set(ctx=ctx)
        volume = self.get_volume()
        ctx.instance.runtime_properties['aws_resource_id'] = \
            volume.id
        ctx.instance.runtime_properties[constants.ZONE] = \
            volume.zone
        ebs.delete(ctx=ctx)
        self.assertNotIn('aws_resource_id',
                         ctx.instance.runtime_properties)
        self.assertNotIn(constants.ZONE,
                         ctx.instance.runtime_properties)

    @mock_ec2
    def test_detach_external_volume_or_instance(self):
        """ This tests that this function returns False
        if use_external_resource is false.
        """

        ctx = self.mock_relationship_context(
            'test_detach_external_volume_or_instance')
        current_ctx.set(ctx=ctx)
        ctx.source.node.properties['use_external_resource'] = False
        test_volumeinstanceconn = self.create_volumeinstanceconn_for_checking()

        output = \
            test_volumeinstanceconn.disassociate_external_resource_naively()

        self.assertEqual(False, output)

    @mock_ec2
    def test_good_volume_attach(self):
        """ Tests that attach runs when clean. """

        ctx = self.mock_relationship_context('test_good_volume_attach')
        current_ctx.set(ctx=ctx)
        volume = self.get_volume()
        instance_id = self.get_instance_id()
        ctx.source.instance.runtime_properties['aws_resource_id'] = \
            volume.id
        ctx.target.instance.runtime_properties['placement'] = \
            TEST_ZONE
        ctx.target.instance.runtime_properties['aws_resource_id'] = \
            instance_id
        ebs.VolumeInstanceConnection().associate(ctx=ctx)

    @mock_ec2
    def test_good_volume_detach(self):
        """ Tests that detach runs when clean. """

        ctx = self.mock_relationship_context('test_good_address_detach')
        current_ctx.set(ctx=ctx)
        volume = self.get_volume()
        instance_id = self.get_instance_id()
        volume.attach(instance_id, TEST_DEVICE)
        ctx.source.instance.runtime_properties['aws_resource_id'] = \
            volume.id
        ctx.source.instance.runtime_properties['instance_id'] = \
            instance_id
        ctx.target.instance.runtime_properties['aws_resource_id'] = \
            instance_id
        args = dict(force=True)
        ebs.disassociate(args, ctx=ctx)

    @mock_ec2
    def test_validation(self):
        """ Tests that creation_validation raises an error
        the EBS volume doesn't exist in the account and use_external_resource
        is true.
        """

        ctx = self.mock_volume_node('test_allocate')
        ctx.node.properties['use_external_resource'] = True
        ctx.node.properties['resource_id'] = BAD_VOLUME_ID
        current_ctx.set(ctx=ctx)
        ex = self.assertRaises(
            NonRecoverableError, ebs.creation_validation, ctx=ctx)
        self.assertIn('External resource, but the supplied', ex.message)

    @mock_ec2
    def test_validation_not_external(self):
        """ Tests that creation_validation raises an error
        the Elastic IP exist in the account and use_external_resource
        is false.
        """

        ctx = self.mock_volume_node('test_validation_not_external')
        current_ctx.set(ctx=ctx)
        volume = self.get_volume()
        ctx.node.properties['use_external_resource'] = False
        ctx.node.properties['resource_id'] = volume.id
        ex = self.assertRaises(
            NonRecoverableError, ebs.creation_validation, ctx=ctx)
        self.assertIn('Not external resource, but the supplied', ex.message)

    @mock_ec2
    def test_attach_no_instance_id(self):
        """ Tests that attach will raise an error if aws_resource_id
        runtime property is not set.
        """

        ctx = self.mock_relationship_context('test_attach_no_instance_id')
        current_ctx.set(ctx=ctx)
        del(ctx.source.instance.runtime_properties['aws_resource_id'])
        ex = self.assertRaises(
                NonRecoverableError, ebs.associate,
                ctx=ctx)
        self.assertIn(
            'Cannot attach volume because aws_resource_id is not assigned',
            ex.message)

    @mock_ec2
    def test_bad_volume_external_resource(self):

        ctx = self.mock_ctx('test_bad_volume_external_resource')
        current_ctx.set(ctx=ctx)
        ctx.node.properties['use_external_resource'] = True
        ctx.node.properties['resource_id'] = BAD_VOLUME_ID
        args = dict()
        ex = self.assertRaises(
            NonRecoverableError, ebs.create, args, ctx=ctx)
        self.assertIn(
            'Cannot use_external_resource because resource',
            ex.message)

    @mock_ec2
    def test_delete_existing(self):
        """ Tests that delete actually deletes.
        """

        ctx = self.mock_ctx('test_delete_existing')
        current_ctx.set(ctx=ctx)
        volume = self.get_volume()
        ctx.instance.runtime_properties['aws_resource_id'] = \
            volume.id
        ctx.node.properties['use_external_resource'] = True
        ebs.delete(ctx=ctx)
        self.assertNotIn(
            'aws_resource_id', ctx.instance.runtime_properties.keys())
        ec2_client = self.get_client()
        self.assertIsNotNone(ec2_client.get_all_volumes([volume.id]))

    @mock_ec2
    def test_get_all_volumes_bad(self):
        """ tests that _get_all_addresses returns None
        for a bad address.
        """
        ctx = self.mock_ctx('test_get_all_volumes_bad')
        current_ctx.set(ctx=ctx)
        test_volume = self.create_volume_for_checking()

        output = test_volume.get_all_matching([BAD_VOLUME_ID])
        self.assertEqual([], output)

    @mock_ec2
    def test_existing_volume_attach(self):
        """ Tests that when an address that is in the user's
            EC2 account is provided to the associate function
            no errors are raised
        """

        ctx = self.mock_relationship_context('test_existing_volume_attach')
        current_ctx.set(ctx=ctx)
        volume = self.get_volume()
        instance_id = self.get_instance_id()
        ctx.source.node.properties['use_external_resource'] = True
        ctx.source.node.properties['resource_id'] = volume.id
        ctx.source.instance.runtime_properties['aws_resource_id'] = \
            volume.id
        ctx.target.instance.runtime_properties['placement'] = \
            TEST_ZONE
        ctx.target.node.properties['use_external_resource'] = True
        ctx.target.node.properties['resource_id'] = volume.id
        ctx.target.instance.runtime_properties['aws_resource_id'] = \
            instance_id
        ebs.associate(ctx=ctx)
        self.assertEqual(
            instance_id,
            ctx.source.instance.runtime_properties['instance_id'])

    @mock_ec2
    def test_existing_detach(self, *_):
        """ Tests that when an address that is in the user's
            EC2 account is provided to the disassociate function
            no errors are raised
        """

        ctx = self.mock_relationship_context(
            'test_existing_detach')
        current_ctx.set(ctx=ctx)
        volume = self.get_volume()
        instance_id = self.get_instance_id()
        ctx.source.node.properties['use_external_resource'] = True
        ctx.source.node.properties['resource_id'] = volume.id
        ctx.source.instance.runtime_properties['aws_resource_id'] = \
            volume.id
        ctx.target.instance.runtime_properties['placement'] = \
            TEST_ZONE
        ctx.target.node.properties['use_external_resource'] = True
        ctx.target.node.properties['resource_id'] = volume.id
        ctx.target.instance.runtime_properties['aws_resource_id'] = \
            instance_id
        ctx.source.instance.runtime_properties['instance_id'] = \
            instance_id
        args = dict(force=True)
        ebs.VolumeInstanceConnection().disassociated(args)
        self.assertNotIn(
            'instance_id', ctx.source.instance.runtime_properties)

    @mock_ec2
    def test_detach_external_volume(self):
        """ Tests that when an address that is in the user's
            EC2 account is provided to the disassociate function
            and use_external_resource is true
            no errors are raised
        """

        ctx = self.mock_relationship_context(
            'test_detach_external_volume')
        current_ctx.set(ctx=ctx)
        volume = self.get_volume()
        instance_id = self.get_instance_id()
        ctx.target.node.properties['use_external_resource'] = False
        ctx.target.node.properties['resource_id'] = volume.id
        ctx.source.node.properties['use_external_resource'] = False
        ctx.source.node.properties['resource_id'] = instance_id
        ctx.source.instance.runtime_properties['aws_resource_id'] = \
            instance_id
        test_volumeinstanceconn = self.create_volumeinstanceconn_for_checking()
        output = \
            test_volumeinstanceconn.disassociate_external_resource_naively()
        self.assertEqual(False, output)

    @mock_ec2
    def test_bad_volume_detach(self):
        """ Tests that NonRecoverableError: Invalid Address is
            raised when an address that is not in the user's
            EC2 account is provided to the detach function
        """

        ctx = self.mock_relationship_context('test_bad_volume_detach')
        current_ctx.set(ctx=ctx)
        ctx.source.instance.runtime_properties['aws_resource_id'] = \
            BAD_VOLUME_ID
        ctx.source.instance.runtime_properties['instance_id'] = \
            BAD_INSTANCE_ID
        args = dict(force=True)
        ex = self.assertRaises(NonRecoverableError,
                               ebs.disassociate, args, ctx=ctx)
        self.assertIn('not found in account', ex.message)

    @mock_ec2
    def test_bad_volume_attach(self):
        """ Tests that NonRecoverableError: Invalid Address is
            raised when an address that is not in the user's
            EC2 account is provided to the detach function
        """

        ctx = self.mock_relationship_context('test_bad_volume_detach')
        current_ctx.set(ctx=ctx)
        ctx.source.instance.runtime_properties['aws_resource_id'] = \
            BAD_VOLUME_ID
        ctx.source.instance.runtime_properties['instance_id'] = \
            BAD_INSTANCE_ID
        ctx.target.instance.runtime_properties['placement'] = \
            TEST_ZONE
        ex = self.assertRaises(NonRecoverableError,
                               ebs.VolumeInstanceConnection().associate,
                               ctx=ctx)
        self.assertIn('not found in account', ex.message)

    @mock_ec2
    def test_good_snapshot(self):

        ctx = self.mock_ctx('test_good_snapshot')
        current_ctx.set(ctx=ctx)
        args = dict()
        ebs.create(args, ctx=ctx)
        args = dict()
        ebs.create_snapshot(args, ctx=ctx)
        self.assertIn(
            constants.EBS['VOLUME_SNAPSHOT_ATTRIBUTE'],
            ctx.instance.runtime_properties)

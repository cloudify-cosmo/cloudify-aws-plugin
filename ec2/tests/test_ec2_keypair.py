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
import os
import tempfile

# Third Party Imports
from moto import mock_ec2

# Cloudify Imports is imported and used in operations
from ec2 import constants
from ec2 import connection
from ec2 import keypair
from cloudify.state import current_ctx
from cloudify.mocks import MockCloudifyContext
from cloudify.exceptions import NonRecoverableError


class TestKeyPair(testtools.TestCase):

    def setUp(self):
        super(TestKeyPair, self).setUp()

    def mock_ctx(self, test_name):

        private_key_path = tempfile.mkdtemp()

        test_node_id = test_name
        test_properties = {
            constants.AWS_CONFIG_PROPERTY: {},
            'use_external_resource': False,
            'resource_id': '{0}'.format(test_name),
            'private_key_path': '{0}/{1}.pem'.format(
                private_key_path,
                test_name)
        }

        ctx = MockCloudifyContext(
            node_id=test_node_id,
            properties=test_properties
        )

        return ctx

    def create_dummy_key_path(self, ctx):
        key_path = os.path.expanduser(
            ctx.node.properties['private_key_path'])
        return key_path

    @mock_ec2
    def test_create(self):
        """ This tests that the key pair name is added to the
        runtime_properties.
        """
        ctx = self.mock_ctx('test_create')
        current_ctx.set(ctx=ctx)

        key_path = self.create_dummy_key_path(ctx=ctx)
        keypair.create(ctx=ctx)
        self.addCleanup(os.remove, key_path)
        self.assertIn('aws_resource_id',
                      ctx.instance.runtime_properties.keys())
        self.assertTrue(os.path.exists(key_path))

    @mock_ec2
    def test_key_pair_exists_error_create(self):
        """ this tests that an error is raised if a
            keypair already exists in the file location
        """
        ctx = self.mock_ctx('test_key_pair_exists_error_create')
        current_ctx.set(ctx=ctx)

        key_path = self.create_dummy_key_path(ctx=ctx)
        keypair.create(ctx=ctx)
        self.addCleanup(os.remove, key_path)
        ex = self.assertRaises(NonRecoverableError, keypair.create,
                               ctx=ctx)
        self.assertIn('already exists', ex.message)

    @mock_ec2
    def test_delete(self):
        """ this tests that keypair delete removes the keypair from
            the account
        """
        ctx = self.mock_ctx('test_delete')
        current_ctx.set(ctx=ctx)

        ec2_client = connection.EC2ConnectionClient().client()
        kp = ec2_client.create_key_pair('test_delete')
        ctx.instance.runtime_properties['aws_resource_id'] = kp.name
        ctx.instance.runtime_properties['key_path'] = \
            self.create_dummy_key_path(ctx=ctx)
        keypair.delete(ctx=ctx)
        self.assertEquals(None, ec2_client.get_key_pair(kp.name))

    @mock_ec2
    def test_validation_use_external(self):
        ctx = self.mock_ctx('test_validation_use_external')
        current_ctx.set(ctx=ctx)

        ec2_client = connection.EC2ConnectionClient().client()
        kp = ec2_client.create_key_pair('test_validation_use_external')
        ctx.node.properties['use_external_resource'] = True
        ctx.node.properties['resource_id'] = kp.name
        ex = self.assertRaises(
            NonRecoverableError, keypair.creation_validation, ctx=ctx)
        self.assertIn(
            'but the key file does not exist locally.',
            ex.message)

    @mock_ec2
    def test_validation_use_external_not_in_account(self):
        """ Tests that an error is raised if you use external,
        but the key pair doesn't exist in your account.
        """

        ctx = self.mock_ctx('test_validation_use_external_not_in_account')
        current_ctx.set(ctx=ctx)

        ec2_client = connection.EC2ConnectionClient().client()
        kp = ec2_client.create_key_pair(
            'test_validation_use_external_not_in_account')
        ctx.node.properties['use_external_resource'] = True
        ctx.node.properties['resource_id'] = kp.name
        kp = ec2_client.delete_key_pair(
            'test_validation_use_external_not_in_account')
        key_path = \
            self.create_dummy_key_path(ctx=ctx)
        self.addCleanup(os.remove, key_path)
        with open(key_path, 'w') as dummy_key:
            dummy_key.write('test')
        ex = self.assertRaises(
            NonRecoverableError, keypair.creation_validation, ctx=ctx)
        self.assertIn(
            'the key pair does not exist in the account',
            ex.message)
        self.assertIn(
            'InvalidKeyPair.NotFound',
            ex.message)

    @mock_ec2
    def test_validation_file_exists(self):
        """ Tests that an error is raised if you don't use
        external, but the key does exist locally.
        """

        ctx = self.mock_ctx('test_validation_file_exists')
        current_ctx.set(ctx=ctx)

        ec2_client = connection.EC2ConnectionClient().client()
        kp = ec2_client.create_key_pair(
            'test_validation_file_exists')
        ctx.node.properties['use_external_resource'] = False
        ctx.node.properties['resource_id'] = kp.name
        kp = ec2_client.delete_key_pair(
            'test_validation_file_exists')
        key_path = \
            self.create_dummy_key_path(ctx=ctx)
        self.addCleanup(os.remove, key_path)
        with open(key_path, 'w') as dummy_key:
            dummy_key.write('test')
        ex = self.assertRaises(
            NonRecoverableError, keypair.creation_validation, ctx=ctx)
        self.assertIn(
            'but the key file exists locally',
            ex.message)

    @mock_ec2
    def test_validation_in_account(self):
        """ Tests that an error is raised if you don't use
        external, but the key does exist in your account.
        """

        ctx = self.mock_ctx('test_validation_in_account')
        current_ctx.set(ctx=ctx)

        ec2_client = connection.EC2ConnectionClient().client()
        kp = ec2_client.create_key_pair(
            'test_validation_in_account')
        ctx.node.properties['use_external_resource'] = False
        ctx.node.properties['resource_id'] = kp.name
        ex = self.assertRaises(
            NonRecoverableError, keypair.creation_validation, ctx=ctx)
        self.assertIn(
            'but the key pair exists in the account.',
            ex.message)

    @mock_ec2
    def test_save_keypair(self):
        """ This tests that the create keypair function
            adds the key_pair_name to runtime properties.
        """

        ctx = self.mock_ctx('test_save_keypair')
        current_ctx.set(ctx=ctx)

        ec2_client = connection.EC2ConnectionClient().client()
        kp = ec2_client.create_key_pair('test_save_keypair')
        ctx.node.properties['resource_id'] = kp.name
        key_path = self.create_dummy_key_path(ctx=ctx)
        self.addCleanup(os.remove, key_path)
        with open(key_path, 'w') as out:
            out.write('test_save_keypair')
        print ctx.node.properties
        ex = self.assertRaises(NonRecoverableError,
                               keypair._save_key_pair, kp)
        self.assertIn(
            'already exists, it will not be overwritten', ex.message)

    @mock_ec2
    def test_create_use_external(self):
        """ This tests that the create keypair function
            adds the key_pair_name to runtime properties.
        """

        ctx = self.mock_ctx('test_create_use_external')
        current_ctx.set(ctx=ctx)

        ec2_client = connection.EC2ConnectionClient().client()
        kp = ec2_client.create_key_pair('test_create_use_external')
        ctx.node.properties['use_external_resource'] = True
        ctx.node.properties['resource_id'] = kp.name
        ex = self.assertRaises(NonRecoverableError, keypair.create, ctx=ctx)
        self.assertIn(
            'External resource, but the key file does not exist', ex.message)

    @mock_ec2
    def test_get_key_pair_by_id(self):
        """ This tests that the _get_key_pair_by_id function
        returns the same keypair object.
        """

        ctx = self.mock_ctx('test_get_key_pair_by_id')
        current_ctx.set(ctx=ctx)

        ec2_client = connection.EC2ConnectionClient().client()
        kp = ec2_client.create_key_pair('test_get_key_pair_by_id_bad_id')
        output = keypair._get_key_pair_by_id(kp.name)
        self.assertEqual(output.name, kp.name)

    @mock_ec2
    def test_get_key_file_path_missing_property(self):
        """ This tests that a not NonRecoverableError error is
        raised by _get_path_to_key_file when the private_key_path
        property is not set.
        """

        ctx = self.mock_ctx('test_get_key_file_path_missing_property')
        current_ctx.set(ctx=ctx)
        del(ctx.node.properties['private_key_path'])
        ex = self.assertRaises(
            NonRecoverableError,
            keypair._get_path_to_key_file)
        self.assertIn(
            'Unable to get key file path, private_key_path not set',
            ex.message)

    @mock_ec2
    def test_save_key_pair_missing_property(self):
        """ This tests that _save_key_pair raises an error when
        private_key_path is not set.
        """

        ctx = self.mock_ctx('test_save_key_pair_missing_property')
        current_ctx.set(ctx=ctx)
        ec2_client = connection.EC2ConnectionClient().client()
        del(ctx.node.properties['private_key_path'])
        kp = ec2_client.create_key_pair('test_create_use_external')
        ex = self.assertRaises(
            NonRecoverableError,
            keypair._save_key_pair,
            kp)
        self.assertIn(
            'Unable to get key file path, private_key_path not set',
            ex.message)

    @mock_ec2
    def test_delete_use_external(self):
        """ This tests that delete function removes the
        runtime_properties for external resource.
        """

        ctx = self.mock_ctx('test_delete_use_external')
        current_ctx.set(ctx=ctx)

        ec2_client = connection.EC2ConnectionClient().client()
        kp = ec2_client.create_key_pair(
            'test_delete_use_external')
        ctx.node.properties['use_external_resource'] = True
        ctx.node.properties['resource_id'] = kp.name
        ctx.instance.runtime_properties['aws_resource_id'] = kp.name
        keypair.delete(ctx=ctx)
        self.assertNotIn('aws_resource_id', ctx.instance.runtime_properties)

    @mock_ec2
    def test_get_path_to_key_file(self):
        """ This tests that the expected key path is returned
        by _get_path_to_key_file.
        """

        ctx = self.mock_ctx(
            'test_get_path_to_key_file')
        current_ctx.set(ctx=ctx)

        full_key_path = os.path.expanduser(
            ctx.node.properties['private_key_path']
        )

        output = keypair._get_path_to_key_file()

        self.assertEqual(full_key_path, output)

    @mock_ec2
    def test_search_for_key_file_no_file(self):
        """ This tests that _search_for_key_file
        returns false when it can't find the file.
        """

        output = keypair._search_for_key_file(
            'test_search_for_key_file.pem')

        self.assertEquals(
            False,
            output
        )

    @mock_ec2
    def test_file_already_exists(self):
        """Tests that if a file already exists at 
        private_key_path, then an error is raised.
        """

        temp_key = tempfile.mktemp()
        self.addCleanup(os.remove, temp_key)
        with open(temp_key, 'w') as outfile:
            outfile.write('')
        ctx = self.mock_ctx('test_file_already_exists')
        ctx.node.properties['private_key_path'] = temp_key
        ctx.node.properties['resource_id'] = 'something_else'
        current_ctx.set(ctx=ctx)
        with self.assertRaisesRegexp(
                NonRecoverableError,
                '{0} already exists, it will not be overwritten'.format(
                    temp_key)):
            keypair.create(ctx=ctx)

    @mock_ec2
    def test_delete_different_resource_id_and_file_path(self):
        temp_key = tempfile.mktemp()
        ctx = self.mock_ctx(
            'test_delete_different_resource_id_and_file_path')
        ctx.node.properties['private_key_path'] = temp_key
        ctx.node.properties['resource_id'] = 'something_else'
        current_ctx.set(ctx=ctx)
        keypair.create(ctx=ctx)
        self.assertTrue(
            os.path.exists(temp_key))
        keypair.delete(ctx=ctx)
        self.assertFalse(
            os.path.exists(temp_key))

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
import os

# Third Party Imports
from moto import mock_ec2

# Cloudify Imports is imported and used in operations
from ec2 import connection
from ec2 import keypair
from cloudify.mocks import MockCloudifyContext
from cloudify.exceptions import NonRecoverableError

TEST_AMI_IMAGE_ID = 'ami-e214778a'
TEST_INSTANCE_TYPE = 't1.micro'


class TestKeyPair(testtools.TestCase):

    def mock_ctx(self, test_name):

        test_node_id = test_name
        test_properties = {
            'resource_id': 'test_ec2_keypair',
            'private_key_path': '~/.ssh'
        }

        ctx = MockCloudifyContext(
            node_id=test_node_id,
            properties=test_properties
        )

        return ctx

    @mock_ec2
    def test_create(self):
        """ This tests that the create keypair function
            adds the key_pair_name to runtime properties.
        """

        ctx = self.mock_ctx('test_create')

        path = os.path.expanduser(ctx.node.properties['private_key_path'])
        file = os.path.join(path,
                            '{0}{1}'.format(
                                ctx.node.properties['resource_id'],
                                '.pem'))
        if os.path.exists(file):
            os.remove(file)
        keypair.create(ctx=ctx)
        self.assertIn('aws_resource_id',
                      ctx.instance.runtime_properties.keys())
        os.remove(file)

    @mock_ec2
    def test_create_adds_file(self):
        """ This tests that the create keypair function
            creates the key_pair file.
        """

        ctx = self.mock_ctx('test_create_adds_file')

        path = os.path.expanduser(ctx.node.properties['private_key_path'])
        file = os.path.join(path,
                            '{0}{1}'.format(
                                ctx.node.properties['resource_id'],
                                '.pem'))
        if os.path.exists(file):
            os.remove(file)
        keypair.create(ctx=ctx)
        self.assertTrue(os.path.exists(file))
        os.remove(file)

    @mock_ec2
    def test_key_pair_exists_error_create(self):
        """ this tests that an error is raised if a
            keypair already exists in the file location
        """

        ctx = self.mock_ctx('test_create_adds_file')

        path = os.path.expanduser(ctx.node.properties['private_key_path'])
        file = os.path.join(path,
                            '{0}{1}'.format(
                                ctx.node.properties['resource_id'],
                                '.pem'))
        if os.path.exists(file):
            os.remove(file)
        keypair.create(ctx=ctx)
        ex = self.assertRaises(NonRecoverableError, keypair.create,
                               ctx=ctx)
        self.assertIn('already exists', ex.message)
        os.remove(file)

    @mock_ec2
    def test_delete(self):
        """ this tests that keypair delete removes the keypair from
            the account
        """

        ctx = self.mock_ctx('test_delete')

        ec2_client = connection.EC2ConnectionClient().client()
        kp = ec2_client.create_key_pair('test')
        ctx.instance.runtime_properties['aws_resource_id'] = kp.name
        keypair.delete(ctx=ctx)
        self.assertEquals(None, ec2_client.get_key_pair(kp.name))

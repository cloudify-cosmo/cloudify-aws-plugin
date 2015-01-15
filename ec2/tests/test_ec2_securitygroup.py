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
from ec2 import securitygroup
from cloudify.mocks import MockCloudifyContext
from cloudify.exceptions import NonRecoverableError

TEST_AMI_IMAGE_ID = 'ami-e214778a'
TEST_INSTANCE_TYPE = 't1.micro'


class TestPlugin(testtools.TestCase):

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

    def security_group_mock(self, test_name, test_properties):

        ctx = MockCloudifyContext(
            node_id=test_name,
            properties=test_properties
        )

        return ctx

    def test_good_security_group_create(self):
        """ There are many places that this could fail,
            so I am first testing that everything works given
            really good input.
        """

        test_properties = {
            'name': 'test_security_group',
            'description': 'This is a test.',
            'rules': [
                {
                    'ip_protocol': 'tcp',
                    'from_port': '22',
                    'to_port': '22',
                    'cidr_ip': '127.0.0.1/32'
                },
                {
                    'ip_protocol': 'tcp',
                    'from_port': '80',
                    'to_port': '80',
                    'cidr_ip': '127.0.0.1/32'
                }
            ]
        }

        ctx = self.security_group_mock('test_good_security_group_create',
                                       test_properties)

        with mock_ec2():
            securitygroup.create(ctx=ctx)

    def test_good_security_group_delete(self):
        """ There are many places that this could fail,
            so I am first testing that everything works given
            really good input.
        """

        test_properties = {
            'name': 'test_security_group',
            'description': 'This is a test.',
        }

        ctx = self.security_group_mock('test_good_security_group_delete',
                                       test_properties)

        with mock_ec2():
            ec2_client = connection.EC2ConnectionClient().client()
            group = ec2_client.create_security_group('test',
                                                     'this is test')
            ctx.instance.runtime_properties['group_name'] = group.name
            securitygroup.delete(ctx=ctx)

    def test_bad_security_group_delete(self):
        """ There are many places that this could fail,
            so I am first testing that everything works given
            really good input.
        """

        test_properties = {
            'name': 'test_security_group',
            'description': 'This is a test.',
        }

        ctx = self.security_group_mock('test_bad_security_group_delete',
                                       test_properties)

        with mock_ec2():
            ctx.instance.runtime_properties['group_name'] = 'no such group'
            ex = self.assertRaises(NonRecoverableError,
                                   securitygroup.delete, ctx=ctx)
            self.assertIn('InvalidGroup.NotFound', ex.message)

    def test_no_ip_authorize_security_group(self):
        """ Tests that an error is raised when a user omits
            a description in the create operation.
        """
        test_properties = {
            'name': 'test_security_group',
            'description': 'This is a test.',
            'rules': [
                {
                    'ip_protocol': 'tcp',
                    'from_port': '22',
                    'to_port': '22',
                }
            ]
        }

        ctx = self.security_group_mock('test_no_ip_authorize_security_group',
                                       test_properties)

        with mock_ec2():
            ec2_client = connection.EC2ConnectionClient().client()
            group = ec2_client.create_security_group('test',
                                                     'this is test')
            ex = self.assertRaises(KeyError, securitygroup.authorize_by_name,
                                   ec2_client, group.name,
                                   ctx)
            self.assertIn('cidr_ip', ex.message)

    def test_no_port_authorize_security_group(self):
        """ Tests that an error is raised when a user omits
            a description in the create operation.
        """
        test_properties = {
            'name': 'test_security_group',
            'description': 'This is a test.',
            'rules': [
                {
                    'ip_protocol': 'tcp',
                    'to_port': '22',
                    'cidr_ip': '127.0.0.1/32'
                }
            ]
        }

        ctx = self.security_group_mock('test_no_ip_authorize_security_group',
                                       test_properties)

        with mock_ec2():
            ec2_client = connection.EC2ConnectionClient().client()
            group = ec2_client.create_security_group('test',
                                                     'this is test')
            ex = self.assertRaises(KeyError, securitygroup.authorize_by_name,
                                   ec2_client, group.id,
                                   ctx)
            self.assertIn('from_port', ex.message)

    def test_no_group_creation_validation_security_group(self):
        """ Tests that NonRecoverableError is raised when
            an invalid group is tried for validation
        """

        test_properties = {
            'name': 'test_security_group',
            'description': 'This is a test.',
            'rules': [
                {
                    'ip_protocol': 'tcp',
                    'from_port': '22',
                    'to_port': '22',
                    'cidr_ip': '127.0.0.1/32'
                }
            ]
        }

        ctx = self.security_group_mock('test_no_group_creation_'
                                       'validation_security_group',
                                       test_properties)

        with mock_ec2():
            ex = self.assertRaises(NonRecoverableError,
                                   securitygroup.creation_validation,
                                   ctx=ctx)
            self.assertIn('No group name or group id provided',
                          ex.message)

    def test_no_group_authorize_security_group(self):
        """ Tests that NonRecoverableError is raised when
            an invalid group is tried for validation
        """

        test_properties = {
            'name': 'test_security_group',
            'description': 'This is a test.',
            'rules': [
                {
                    'ip_protocol': 'tcp',
                    'from_port': '80',
                    'to_port': '80',
                    'cidr_ip': '127.0.0.1/32'
                }
            ]
        }

        ctx = self.security_group_mock('test_no_group_'
                                       'authorize_security_group',
                                       test_properties)

        with mock_ec2():
            ex = self.assertRaises(NonRecoverableError,
                                   securitygroup.authorize,
                                   ctx=ctx)
            self.assertIn('No group name or group id provided',
                          ex.message)

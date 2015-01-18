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
from ec2 import utils
from cloudify.mocks import MockCloudifyContext
from cloudify.exceptions import NonRecoverableError

TEST_AMI_IMAGE_ID = 'ami-e214778a'
TEST_INSTANCE_TYPE = 't1.micro'


class TestSecurityGroup(testtools.TestCase):

    def security_group_mock(self, test_name, test_properties):
        """ Creates a mock context for security group tests
            with given properties
        """

        ctx = MockCloudifyContext(
            node_id=test_name,
            properties=test_properties
        )

        return ctx

    def test_create(self):
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

    def test_delete(self):
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
            ctx.node.properties['name'] = group.name
            securitygroup.delete(ctx=ctx)

    def test_bad_group_delete(self):
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

    def test_no_ip_authorize(self):
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

    def test_no_port_authorize(self):
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

    def test_no_group_creation_validation(self):
        """ Tests that NonRecoverableError is raised when
            an invalid group is tried for validation
        """

        test_properties = {
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

    def test_no_group_authorize(self):
        """ Tests that NonRecoverableError is raised when
            an invalid group is tried for validation
        """

        test_properties = {
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

    def test_group_name_authorize(self):
        """ tests that if a group name is
            provided in the node properties that
            everything runs smoothly in the validate operation
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

        ctx = self.security_group_mock('test_group_name_authorize',
                                       test_properties)

        with mock_ec2():
            ec2_client = connection.EC2ConnectionClient().client()
            name = ctx.node.properties['name']
            desc = ctx.node.properties['description']
            ec2_client.create_security_group(name, desc)
            securitygroup.authorize(ctx=ctx)

    def test_group_id_authorize(self):
        """ tests that if a resource_id is
            provided in the node properties that
            everything runs smoothly in the authorize operation
        """

        test_properties = {
            'rules': [
                {
                    'ip_protocol': 'tcp',
                    'from_port': '80',
                    'to_port': '80',
                    'cidr_ip': '127.0.0.1/32'
                }
            ]
        }

        with mock_ec2():
            ec2_client = connection.EC2ConnectionClient().client()
            group = ec2_client.create_security_group('test', 'tests')
            ctx = self.security_group_mock('test_group_id_authorize',
                                           test_properties)
            ctx.node.properties['resource_id'] = group.id
            securitygroup.authorize(ctx=ctx)

    def test_validate_group(self):
        """ Tests the validate group utililty
            which makes sure that the group exists for
            a given group id different from creation validation
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

        ctx = self.security_group_mock('test_validate_group',
                                       test_properties)
        with mock_ec2():
            group = 'sg-73cd3f1e'
            utils.validate_group(group, ctx=ctx)

    def test_group_id_validate(self):
        """ tests that if a resource_id is
            provided in the node properties that
            everything runs smoothly in the validate operation
        """

        test_properties = {
            'rules': [
                {
                    'ip_protocol': 'tcp',
                    'from_port': '80',
                    'to_port': '80',
                    'cidr_ip': '127.0.0.1/32'
                }
            ]
        }

        with mock_ec2():
            ec2_client = connection.EC2ConnectionClient().client()
            group = ec2_client.create_security_group('test', 'tests')
            ctx = self.security_group_mock('test_group_id_validate',
                                           test_properties)
            ctx.node.properties['resource_id'] = group.id
            securitygroup.creation_validation(ctx=ctx)

    def test_group_name_validate(self):
        """ tests that if a resource_id is
            provided in the node properties that
            everything runs smoothly
        """

        test_properties = {
            'rules': [
                {
                    'ip_protocol': 'tcp',
                    'from_port': '80',
                    'to_port': '80',
                    'cidr_ip': '127.0.0.1/32'
                }
            ]
        }

        with mock_ec2():
            ec2_client = connection.EC2ConnectionClient().client()
            group = ec2_client.create_security_group('group_name_validate',
                                                     'tests')
            ctx = self.security_group_mock('test_group_name_validate',
                                           test_properties)
            ctx.node.properties['name'] = group.name
            securitygroup.creation_validation(ctx=ctx)

    def test_group_object_validate(self):
        """ tests that if a resource_id is
            provided in the node properties that
            everything runs smoothly
        """

        test_properties = {
            'rules': [
                {
                    'ip_protocol': 'tcp',
                    'from_port': '80',
                    'to_port': '80',
                    'cidr_ip': '127.0.0.1/32'
                }
            ]
        }

        with mock_ec2():
            ec2_client = connection.EC2ConnectionClient().client()
            group = ec2_client.create_security_group('test', 'tests')
            ctx = self.security_group_mock('test_group_object_validate',
                                           test_properties)
            ctx.instance.runtime_properties['group_object'] = {
                'id': group.id,
                'name': group.name
            }
            securitygroup.creation_validation(ctx=ctx)

    def test_no_ip_revoke(self):
        """ Tests that an error is raised when a user omits
            an ip in the revoke operation.
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

        ctx = self.security_group_mock('test_no_ip_revoke',
                                       test_properties)

        with mock_ec2():
            ec2_client = connection.EC2ConnectionClient().client()
            group = ec2_client.create_security_group('test',
                                                     'this is test')
            ex = self.assertRaises(KeyError, securitygroup.revoke_by_name,
                                   ec2_client, group.name,
                                   ctx)
            self.assertIn('cidr_ip', ex.message)

    def test_no_port_revoke(self):
        """ Tests that an error is raised when a user omits
            a port in the revoke operation.
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

        ctx = self.security_group_mock('test_no_port_revoke',
                                       test_properties)

        with mock_ec2():
            ec2_client = connection.EC2ConnectionClient().client()
            group = ec2_client.create_security_group('test',
                                                     'this is test')
            ex = self.assertRaises(KeyError, securitygroup.revoke_by_name,
                                   ec2_client, group.id,
                                   ctx)
            self.assertIn('from_port', ex.message)

    def test_no_group_revoke(self):
        """ Tests that NonRecoverableError is raised when
            an invalid group is tried for revoke operation
        """

        test_properties = {
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
                                   securitygroup.revoke,
                                   ctx=ctx)
            self.assertIn('No group name or group id provided',
                          ex.message)

    def test_group_name_revoke(self):
        """ tests that if a group name is
            provided in the node properties that
            everything runs smoothly in the revoke operation
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

        ctx = self.security_group_mock('test_group_name_revoke',
                                       test_properties)

        with mock_ec2():
            ec2_client = connection.EC2ConnectionClient().client()
            name = ctx.node.properties['name']
            desc = ctx.node.properties['description']
            group = ec2_client.create_security_group(name, desc)
            r = ctx.node.properties['rules'][0]
            ec2_client.authorize_security_group(group_name=group.name,
                                                ip_protocol=r['ip_protocol'],
                                                from_port=r['from_port'],
                                                to_port=r['to_port'],
                                                cidr_ip=r['cidr_ip'])
            ctx.node.properties['resource_id'] = group.id
            securitygroup.revoke(ctx=ctx)

    def test_group_id_revoke(self):
        """ tests that if a resource_id is
            provided in the node properties that
            everything runs smoothly in revoke operation
        """

        test_properties = {
            'rules': [
                {
                    'ip_protocol': 'tcp',
                    'from_port': '80',
                    'to_port': '80',
                    'cidr_ip': '127.0.0.1/32'
                }
            ]
        }

        with mock_ec2():
            ec2_client = connection.EC2ConnectionClient().client()
            group = ec2_client.create_security_group('test', 'tests')
            ctx = self.security_group_mock('test_group_id_revoke',
                                           test_properties)
            r = ctx.node.properties['rules'][0]
            ec2_client.authorize_security_group(group_id=group.id,
                                                ip_protocol=r['ip_protocol'],
                                                from_port=r['from_port'],
                                                to_port=r['to_port'],
                                                cidr_ip=r['cidr_ip'])
            ctx.node.properties['resource_id'] = group.id
            securitygroup.revoke(ctx=ctx)

    def test_no_matching_rule_revoke_name(self):
        """ Tests that if there is not a matching rules
            provided then the revoke operation failes
            tests against the 'resource_id' node
        """

        test_properties = {
            'rules': [
                {
                    'ip_protocol': 'tcp',
                    'from_port': '80',
                    'to_port': '80',
                    'cidr_ip': '127.0.0.1/32'
                }
            ]
        }

        with mock_ec2():
            ec2_client = connection.EC2ConnectionClient().client()
            group = ec2_client.create_security_group('test', 'tests')
            ctx = self.security_group_mock('test_no_matching_rule_revoke_name',
                                           test_properties)
            ctx.node.properties['resource_id'] = group.id
            ex = self.assertRaises(NonRecoverableError, securitygroup.revoke,
                                   ctx=ctx)
            self.assertIn('InvalidPermission.NotFound', ex.message)

    def test_no_matching_rule_revoke_id(self):
        """ Tests that if there is not a matching rules
            provided then the revoke operation failes
            tests against the 'name' node property
        """

        test_properties = {
            'rules': [
                {
                    'ip_protocol': 'tcp',
                    'from_port': '80',
                    'to_port': '80',
                    'cidr_ip': '127.0.0.1/32'
                }
            ]
        }

        with mock_ec2():
            ec2_client = connection.EC2ConnectionClient().client()
            group = ec2_client.create_security_group('test', 'tests')
            ctx = self.security_group_mock('test_no_matching_rule_revoke_id',
                                           test_properties)
            ctx.node.properties['name'] = group.name
            ex = self.assertRaises(NonRecoverableError, securitygroup.revoke,
                                   ctx=ctx)
            self.assertIn('InvalidPermission.NotFound', ex.message)

    def test_no_matching_rule_revoke_object(self):
        """ Tests that if there is not a matching rules
            provided then the revoke operation failes
            tests against the 'group_object' runtime property
        """

        test_properties = {
            'rules': [
                {
                    'ip_protocol': 'tcp',
                    'from_port': '80',
                    'to_port': '80',
                    'cidr_ip': '127.0.0.1/32'
                }
            ]
        }

        with mock_ec2():
            ec2_client = connection.EC2ConnectionClient().client()
            group = ec2_client.create_security_group('test', 'tests')
            ctx = self.security_group_mock(
                'test_no_matching_rule_revoke_object',
                test_properties)
            ctx.instance.runtime_properties['group_object'] = group
            ex = self.assertRaises(NonRecoverableError, securitygroup.revoke,
                                   ctx=ctx)
            self.assertIn('InvalidPermission.NotFound', ex.message)

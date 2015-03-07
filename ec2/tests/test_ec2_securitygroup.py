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

    def get_mock_properties(self):

        test_properties = {
            'use_external_resource': False,
            'resource_id': 'test_security_group',
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

        return test_properties

    @mock_ec2
    def test_create(self):

        test_properties = self.get_mock_properties()
        ctx = self.security_group_mock('test_create', test_properties)
        securitygroup.create(ctx=ctx)

    @mock_ec2
    def test_delete(self):

        test_properties = self.get_mock_properties()
        ctx = self.security_group_mock('test_delete', test_properties)
        ec2_client = connection.EC2ConnectionClient().client()
        group = ec2_client.create_security_group('test',
                                                 'this is test')
        ctx.instance.runtime_properties['aws_resource_id'] = group.id
        securitygroup.delete(ctx=ctx)
        self.assertNotIn('aws_resource_id', ctx.instance.runtime_properties)

    @mock_ec2
    def test_create_duplicate(self):

        test_properties = self.get_mock_properties()
        ctx = self.security_group_mock(
            'test_create_duplicate', test_properties)
        name = ctx.node.properties.get('resource_id')
        description = ctx.node.properties.get('description')
        ec2_client = connection.EC2ConnectionClient().client()
        ec2_client.create_security_group(name, description)
        ex = self.assertRaises(
            NonRecoverableError, securitygroup.create, ctx=ctx)
        self.assertIn('InvalidGroup.Duplicate', ex.message)

    @mock_ec2
    def test_delete_deleted(self):

        test_properties = self.get_mock_properties()
        ctx = self.security_group_mock(
            'test_delete_deleted', test_properties)
        ec2_client = connection.EC2ConnectionClient().client()
        group = ec2_client.create_security_group('test_delete_deleted',
                                                 'this is test')
        ctx.instance.runtime_properties['aws_resource_id'] = group.id
        ec2_client.delete_security_group(group_id=group.id)
        ex = self.assertRaises(
            NonRecoverableError, securitygroup.delete, ctx=ctx)
        self.assertIn('InvalidGroup.NotFound', ex.message)

    @mock_ec2
    def test_use_external_not_existing(self):

        test_properties = self.get_mock_properties()
        ctx = self.security_group_mock(
            'test_creation_validation', test_properties)
        ctx.node.properties['use_external_resource'] = True
        ctx.node.properties['resource_id'] = 'sg-73cd3f1e'
        ex = self.assertRaises(
            NonRecoverableError, securitygroup.create, ctx=ctx)
        self.assertIn(
            'but the given security group or Name does not exist', ex.message)

    @mock_ec2
    def test_creation_validation_not_existing(self):

        test_properties = self.get_mock_properties()
        ctx = self.security_group_mock(
            'test_creation_validation', test_properties)
        ctx.node.properties['use_external_resource'] = True
        ctx.node.properties['resource_id'] = 'sg-73cd3f1e'
        ex = self.assertRaises(
            NonRecoverableError, securitygroup.creation_validation, ctx=ctx)
        self.assertIn('the security group does not exist.', ex.message)

    @mock_ec2
    def test_authorize_by_id(self):

        ec2_client = connection.EC2ConnectionClient().client()
        test_properties = self.get_mock_properties()
        ctx = self.security_group_mock(
            'test_authorize_by_id', test_properties)
        group = ec2_client.create_security_group('test_authorize_by_id',
                                                 'this is test')
        rules = ctx.node.properties['rules']
        securitygroup.authorize_by_id(ec2_client, group.id, rules)
        self.assertNotEqual(
            group.rules,
            ec2_client.get_all_security_groups(
                groupnames='test_authorize_by_id')[0].rules)

    @mock_ec2
    def test_authorize_external(self):
        ec2_client = connection.EC2ConnectionClient().client()
        group = ec2_client.create_security_group('test_authorize_external',
                                                 'this is test')
        test_properties = self.get_mock_properties()
        ctx = self.security_group_mock(
            'test_authorize_external', test_properties)
        ctx.node.properties['use_external_resource'] = True
        ctx.node.properties['resource_id'] = group.id
        ctx.instance.runtime_properties['aws_resource_id'] = group.id
        self.assertIsNone(securitygroup.authorize(ctx=ctx))

    @mock_ec2
    def test_authorize_not_external(self):
        ec2_client = connection.EC2ConnectionClient().client()
        group = ec2_client.create_security_group('test_authorize_not_external',
                                                 'this is test')
        test_properties = self.get_mock_properties()
        ctx = self.security_group_mock(
            'test_authorize_external', test_properties)
        ctx.node.properties['use_external_resource'] = False
        ctx.instance.runtime_properties['aws_resource_id'] = group.id
        securitygroup.authorize(ctx=ctx)

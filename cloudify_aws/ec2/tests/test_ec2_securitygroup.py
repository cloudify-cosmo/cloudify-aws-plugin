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
import uuid
import testtools
import mock

# Third Party Imports
from moto import mock_ec2

# Cloudify Imports is imported and used in operations
from cloudify.state import current_ctx
from cloudify_aws.ec2 import securitygroup
from cloudify_aws import constants, connection
from cloudify.mocks import MockCloudifyContext
from cloudify.exceptions import NonRecoverableError


class TestSecurityGroup(testtools.TestCase):

    def security_group_mock(self,
                            test_name,
                            test_properties,
                            retry_number=0,
                            operation_name='create'):
        """ Creates a mock context for security group tests
            with given properties
        """

        operation = {
            'name': operation_name,
            'retry_number': retry_number
        }

        ctx = MockCloudifyContext(
                node_id=test_name,
                properties=test_properties,
                deployment_id=str(uuid.uuid4()),
                operation=operation
        )

        return ctx

    def get_mock_properties(self):

        test_properties = {
            constants.AWS_CONFIG_PROPERTY: {},
            'use_external_resource': False,
            'resource_id': 'test_security_group',
            'tags': {},
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

        return test_properties

    def create_sg_for_checking(self):
        return securitygroup.SecurityGroup()

    @mock_ec2
    def test_create_rules_in_args(self):
        """This tests that create runs"""

        test_properties = self.get_mock_properties()
        ctx = self.security_group_mock('test_create', test_properties)
        current_ctx.set(ctx=ctx)
        rules = [
            {
                'ip_protocol': 'udp',
                'from_port': '33333',
                'to_port': '33333',
                'cidr_ip': '127.0.0.2/32'
            }
        ]
        ec2_client = connection.EC2ConnectionClient().client()
        with mock.patch(
                'cloudify_aws.ec2.securitygroup.'
                'SecurityGroup.get_resource_state'
                ) as securitygroup_state:
            securitygroup_state.return_value = 'available'
            securitygroup.create(rules=rules, ctx=ctx)
        group_id = \
            ctx.instance.runtime_properties[constants.EXTERNAL_RESOURCE_ID]
        group_list = ec2_client.get_all_security_groups(group_ids=group_id)
        group = group_list[0]
        all_rules = rules + ctx.node.properties['rules']
        self.assertEqual(len(all_rules), len(group.rules))

    @mock_ec2
    def test_update_rules(self):
        """This tests that create creates the runtime_properties"""

        test_properties = self.get_mock_properties()
        ctx = self.security_group_mock(
            'test_create_duplicate', test_properties)
        current_ctx.set(ctx=ctx)
        name = ctx.node.properties.get('resource_id')
        description = ctx.node.properties.get('description')
        ec2_client = connection.EC2ConnectionClient().client()
        group = ec2_client.create_security_group(name, description)
        ctx.node.properties['use_external_resource'] = True
        ctx.node.properties['resource_id'] = group.id
        with mock.patch(
                'cloudify_aws.ec2.securitygroup.'
                'SecurityGroup.get_resource_state'
                ) as securitygroup_state:
            securitygroup_state.return_value = 'available'
            securitygroup.create(ctx=ctx)
        rules = [
            {
                'ip_protocol': 'udp',
                'from_port': '33333',
                'to_port': '33333',
                'cidr_ip': '127.0.0.2/32'
            }
        ]
        securitygroup.update_rules(rules=rules, ctx=ctx)
        group_id = \
            ctx.instance.runtime_properties[constants.EXTERNAL_RESOURCE_ID]
        group_list = ec2_client.get_all_security_groups(group_ids=group_id)
        group = group_list[0]
        all_rules = rules + ctx.node.properties['rules']
        self.assertEqual(len(all_rules), len(group.rules))

    @mock_ec2
    def test_create(self):
        """This tests that create runs"""

        test_properties = self.get_mock_properties()
        ctx = self.security_group_mock('test_create', test_properties)
        current_ctx.set(ctx=ctx)
        with mock.patch(
                'cloudify_aws.ec2.securitygroup.'
                'SecurityGroup.get_resource_state'
                ) as securitygroup_state:
            securitygroup_state.return_value = 'available'
            securitygroup.create(ctx=ctx)

    @mock_ec2
    def test_create_retry(self):
        """This tests that create retry works"""

        test_properties = self.get_mock_properties()
        ctx = self.security_group_mock('test_create_retry', test_properties,
                                       retry_number=1)
        current_ctx.set(ctx=ctx)
        name = ctx.node.properties.get('resource_id')
        description = ctx.node.properties.get('description')
        ec2_client = connection.EC2ConnectionClient().client()
        group = ec2_client.create_security_group(name, description)
        ctx.instance.runtime_properties[constants.EXTERNAL_RESOURCE_ID] = \
            group.id
        with mock.patch(
                'cloudify_aws.ec2.securitygroup.'
                'SecurityGroup.get_resource_state'
                ) as securitygroup_state:
            securitygroup_state.return_value = 'available'
            securitygroup.create(ctx=ctx)

    @mock_ec2
    def test_create_existing(self):
        """This tests that create creates the runtime_properties"""

        test_properties = self.get_mock_properties()
        ctx = self.security_group_mock(
                'test_create_duplicate', test_properties)
        current_ctx.set(ctx=ctx)
        name = ctx.node.properties.get('resource_id')
        description = ctx.node.properties.get('description')
        ec2_client = connection.EC2ConnectionClient().client()
        group = ec2_client.create_security_group(name, description)
        ctx.node.properties['use_external_resource'] = True
        ctx.node.properties['resource_id'] = group.id
        with mock.patch(
                'cloudify_aws.ec2.securitygroup.'
                'SecurityGroup.get_resource_state'
                ) as securitygroup_state:
            securitygroup_state.return_value = 'available'
            securitygroup.create(ctx=ctx)
            self.assertEqual(
                    ctx.instance.runtime_properties['aws_resource_id'],
                    group.id)

    @mock_ec2
    def test_start(self):
        """This tests that start adds tags"""

        test_properties = self.get_mock_properties()
        ctx = self.security_group_mock(
                'test_start', test_properties, operation_name='start')
        current_ctx.set(ctx=ctx)

        ec2_client = connection.EC2ConnectionClient().client()
        group = ec2_client.create_security_group('test_start', 'this is test')
        group_id = group.id
        ctx.instance.runtime_properties['aws_resource_id'] = group_id
        securitygroup.start(ctx=ctx)
        group_list = ec2_client.get_all_security_groups(group_ids=group_id)
        group_object = group_list[0]
        self.assertEquals(group_object.tags.get('resource_id'),
                          ctx.instance.id)
        self.assertEquals(group_object.tags.get('deployment_id'),
                          ctx.deployment.id)

    @mock_ec2
    def test_delete(self):
        """This tests that delete removes the runtime_properties"""

        test_properties = self.get_mock_properties()
        ctx = self.security_group_mock('test_delete',
                                       test_properties,
                                       operation_name='delete')
        current_ctx.set(ctx=ctx)
        ec2_client = connection.EC2ConnectionClient().client()
        group = ec2_client.create_security_group('test',
                                                 'this is test')
        ctx.instance.runtime_properties['aws_resource_id'] = group.id
        with mock.patch('cloudify_aws.base.AwsBaseNode.get_resource',
                        return_value=[]):
            securitygroup.SecurityGroup().delete_helper()
            self.assertNotIn('aws_resource_id',
                             ctx.instance.runtime_properties)

    @mock_ec2
    def test_create_duplicate(self):
        """This tests that when you give a name of an existing
        resource, a NonRecoverableError is raised.
        """

        test_properties = self.get_mock_properties()
        ctx = self.security_group_mock(
                'test_create_duplicate', test_properties)
        current_ctx.set(ctx=ctx)
        name = ctx.node.properties.get('resource_id')
        description = ctx.node.properties.get('description')
        ec2_client = connection.EC2ConnectionClient().client()
        ec2_client.create_security_group(name, description)
        ex = self.assertRaises(
                NonRecoverableError, securitygroup.create, ctx=ctx)
        self.assertIn('InvalidGroup.Duplicate', ex.message)

    @mock_ec2
    def test_delete_deleted(self):
        """This tests that security group delete raises an
        error when the group is already deleted.
        """

        test_properties = self.get_mock_properties()
        test_properties['use_external_resource'] = True
        ctx = self.security_group_mock(
                'test_delete_deleted',
                test_properties,
                operation_name='delete')
        current_ctx.set(ctx=ctx)
        ec2_client = connection.EC2ConnectionClient().client()
        group = ec2_client.create_security_group('test_delete_deleted',
                                                 'this is test')
        ctx.instance.runtime_properties['aws_resource_id'] = group.id
        ec2_client.delete_security_group(group_id=group.id)
        with mock.patch('cloudify_aws.base.AwsBaseNode.get_resource',
                        return_value=None):
            out = securitygroup.delete()
            self.assertEquals(True, out)

    @mock_ec2
    def test_delete_existing(self):
        """This tests that security group delete removed the
        runtime_properties
        """
        test_properties = self.get_mock_properties()
        ctx = self.security_group_mock(
                'test_delete_existing',
                test_properties,
                operation_name='delete')
        current_ctx.set(ctx=ctx)
        ec2_client = connection.EC2ConnectionClient().client()
        group = ec2_client.create_security_group('test_delete_existing',
                                                 'this is test')
        ctx.node.properties['use_external_resource'] = True
        ctx.node.properties['resource_id'] = group.id
        ctx.instance.runtime_properties['aws_resource_id'] = group.id
        with mock.patch('cloudify_aws.base.AwsBaseNode.get_resource',
                        return_value=[]):
            securitygroup.delete(ctx=ctx)
            self.assertNotIn(
                    'aws_resource_id',
                    ctx.instance.runtime_properties)

    @mock_ec2
    def test_use_external_not_existing(self):
        """This tests that when use_external_resource is true
        if such a security group not exists an error is raised.
        """

        test_properties = self.get_mock_properties()
        ctx = self.security_group_mock(
                'test_use_external_not_existing', test_properties)
        current_ctx.set(ctx=ctx)
        ctx.node.properties['use_external_resource'] = True
        ctx.node.properties['resource_id'] = 'sg-73cd3f1e'
        ex = self.assertRaises(
                NonRecoverableError, securitygroup.create, ctx=ctx)
        self.assertIn(
                'is not in this account', ex.message)

    @mock_ec2
    def test_creation_validation_existing(self):
        """This tests that when use_external_resource is true
        if such a security group not exists an error is raised.
        """

        test_properties = self.get_mock_properties()
        ctx = self.security_group_mock(
                'test_creation_validation_existing', test_properties)
        current_ctx.set(ctx=ctx)
        ctx.node.properties['use_external_resource'] = True
        ctx.node.properties['resource_id'] = 'sg-73cd3f1e'
        ex = self.assertRaises(
                NonRecoverableError, securitygroup.creation_validation,
                ctx=ctx)
        self.assertIn(
                'External resource, but the supplied group', ex.message)

    @mock_ec2
    def test_creation_validation_not_existing(self):
        """This tests that when use_external_resource is false
        if such a security group exists an error is raised.
        """

        test_properties = self.get_mock_properties()
        ctx = self.security_group_mock(
                'test_creation_validation_not_existing', test_properties)
        current_ctx.set(ctx=ctx)
        ctx.node.properties['use_external_resource'] = False
        ec2_client = connection.EC2ConnectionClient().client()
        group = ec2_client.create_security_group(
                'test_creation_validation_not_existing',
                'this is a test')
        ctx.node.properties['resource_id'] = group.id
        ex = self.assertRaises(
                NonRecoverableError, securitygroup.creation_validation,
                ctx=ctx)
        self.assertIn(
                'Not external resource, but the supplied group',
                ex.message)

    @mock_ec2
    def test_create_group_rules(self):
        """ This tests that _create_group_rules creates
        the rules and that they match on the way out
        to what when in.
        """

        test_properties = self.get_mock_properties()
        ctx = self.security_group_mock(
                'test_create_group_rules', test_properties)
        current_ctx.set(ctx=ctx)
        test_securitygroup = self.create_sg_for_checking()

        ec2_client = connection.EC2ConnectionClient().client()
        group = ec2_client.create_security_group('test_create_group_rules',
                                                 'this is test')
        test_securitygroup._create_group_rules(group)
        self.assertEqual(
                str(group.rules),
                str(ec2_client.get_all_security_groups(
                        groupnames='test_create_group_rules')[0].rules))

    @mock_ec2
    def test_create_group_rules_no_src_group_id_or_cidr(self):
        """ This tests that either src_group_id or cidr_ip is
        error is raised when both are given.
        """

        ec2_client = connection.EC2ConnectionClient().client()
        test_properties = self.get_mock_properties()
        ctx = self.security_group_mock(
                'test_create_group_rules_no_src_group_id_or_cidr',
                test_properties)
        current_ctx.set(ctx=ctx)
        test_securitygroup = self.create_sg_for_checking()

        del ctx.node.properties['rules'][0]['cidr_ip']
        group = ec2_client.create_security_group(
                'test_create_group_rules_no_src_group_id_or_cidr',
                'this is test')
        ex = self.assertRaises(
                NonRecoverableError,
                test_securitygroup._create_group_rules,
                group)
        self.assertIn(
                'You need to pass either src_group_id OR cidr_ip.',
                ex.message)

    @mock_ec2
    def test_create_group_rules_both_src_group_id_cidr(self):
        """ This tests that either src_group_id or cidr_ip is
        error is raised when neither is given.
        """

        ec2_client = connection.EC2ConnectionClient().client()
        group = ec2_client.create_security_group(
                'test_create_group_rules_both_src_group_id_or_cidr',
                'this is test')
        test_properties = self.get_mock_properties()
        ctx = self.security_group_mock(
                'test_create_group_rules_both_src_group_id_or_cidr',
                test_properties)
        current_ctx.set(ctx=ctx)
        test_securitygroup = self.create_sg_for_checking()

        group_object = ec2_client.create_security_group(
                'dummy',
                'this is test')
        ctx.node.properties['rules'][0]['src_group_id'] = group_object
        ex = self.assertRaises(
                NonRecoverableError,
                test_securitygroup._create_group_rules,
                group)
        self.assertIn(
                'You need to pass either src_group_id OR cidr_ip.',
                ex.message)

    @mock_ec2
    def test_create_group_rules_src_group(self):
        """ This tests that _create_group_rules creates
        the rules and that they match on the way out
        to what when in.
        """

        ec2_client = connection.EC2ConnectionClient().client()
        test_properties = self.get_mock_properties()
        ctx = self.security_group_mock(
                'test_create_group_rules_src_group', test_properties)
        group_object = ec2_client.create_security_group(
                'dummy',
                'this is test')
        ctx.node.properties['rules'][0]['src_group_id'] = group_object.id
        del ctx.node.properties['rules'][0]['cidr_ip']
        current_ctx.set(ctx=ctx)
        with mock.patch(
                'cloudify_aws.ec2.securitygroup.'
                'SecurityGroup.get_resource_state'
                ) as securitygroup_state:
            securitygroup_state.return_value = 'available'
            securitygroup.create(ctx=ctx)
        group = ec2_client.get_all_security_groups(
            group_ids=ctx.instance.runtime_properties[
                constants.EXTERNAL_RESOURCE_ID]
        )
        self.assertIn('test_security_group-111122223333',
                      str(group[0].rules[0].grants[0]))

    @mock_ec2
    def test_create_external_securitygroup_not_external(self):
        """ This checks that _create_external_securitygroup
        returns false when use_external_resource is false.
        """

        test_properties = self.get_mock_properties()
        ctx = self.security_group_mock(
                'test_create_external_securitygroup_not_external',
                test_properties)
        current_ctx.set(ctx=ctx)
        test_securitygroup = self.create_sg_for_checking()

        ctx.node.properties['use_external_resource'] = False

        output = test_securitygroup.use_external_resource_naively()
        self.assertEqual(False, output)

    @mock_ec2
    def test_delete_external_securitygroup_not_external(self):
        """ This checks that _delete_external_securitygroup
        returns false when use_external_resource is false.
        """

        test_properties = self.get_mock_properties()
        ctx = self.security_group_mock(
                'test_delete_external_securitygroup_not_external',
                test_properties)
        current_ctx.set(ctx=ctx)
        test_securitygroup = self.create_sg_for_checking()

        ctx.node.properties['use_external_resource'] = False

        output = test_securitygroup.delete_external_resource_naively()
        self.assertEqual(False, output)

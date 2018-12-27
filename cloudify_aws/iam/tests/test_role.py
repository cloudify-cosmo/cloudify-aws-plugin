# Copyright (c) 2018 Cloudify Platform Ltd. All rights reserved
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
from mock import patch, MagicMock
import unittest
from cloudify.state import current_ctx
from cloudify_aws.common.tests.test_base import TestBase, CLIENT_CONFIG
from cloudify_aws.common.tests.test_base import DELETE_RESPONSE
from cloudify_aws.common.tests.test_base import DEFAULT_RUNTIME_PROPERTIES
from cloudify_aws.iam.resources import role


# Constants
ROLE_TH = ['cloudify.nodes.Root',
           'cloudify.nodes.aws.iam.Role']

NODE_PROPERTIES = {
    'resource_id': 'CloudifyLambdaEC2Role',
    'use_external_resource': False,
    'resource_config': {
        'kwargs': {
            'Path': '/service-role/',
            'AssumeRolePolicyDocument': {
                'Version': '2012-10-17',
                'Statement': [{
                    'Effect': 'Allow',
                    'Principal': {
                        'Service': 'lambda.amazonaws.com'
                    },
                    'Action': 'sts:AssumeRole'
                }]
            }
        }
    },
    'client_config': CLIENT_CONFIG
}

ASSUME_STR = (
    '{"Version": "2012-10-17", "Statement": [{"Action": "sts:AssumeRole", ' +
    '"Effect": "Allow", "Principal": {"Service": "lambda.amazonaws.com"}}]}'
)

NODE_PROPERTIES_ASSUME_STR = {
    'resource_id': 'CloudifyLambdaEC2Role',
    'use_external_resource': False,
    'resource_config': {
        'kwargs': {
            'Path': '/service-role/',
            'AssumeRolePolicyDocument': ASSUME_STR
        }
    },
    'client_config': CLIENT_CONFIG
}

RUNTIME_PROPERTIES_AFTER_CREATE = {
    'aws_resource_arn': 'arn_id',
    'aws_resource_id': 'role_name_id',
    'resource_config': {}
}


class TestIAMRole(TestBase):

    def setUp(self):
        super(TestIAMRole, self).setUp()

        self.fake_boto, self.fake_client = self.fake_boto_client('iam')

        self.mock_patch = patch('boto3.client', self.fake_boto)
        self.mock_patch.start()

    def tearDown(self):
        self.mock_patch.stop()
        self.fake_boto = None
        self.fake_client = None

        super(TestIAMRole, self).tearDown()

    def test_create_raises_UnknownServiceError(self):
        self._prepare_create_raises_UnknownServiceError(
            type_hierarchy=ROLE_TH,
            type_name='iam',
            type_class=role
        )

    def test_create(self):
        _ctx = self.get_mock_ctx(
            'test_create',
            test_properties=NODE_PROPERTIES,
            test_runtime_properties=DEFAULT_RUNTIME_PROPERTIES,
            type_hierarchy=ROLE_TH
        )

        current_ctx.set(_ctx)

        self.fake_client.create_role = MagicMock(return_value={
            'Role': {
                'RoleName': "role_name_id",
                'Arn': "arn_id"
            }
        })

        role.create(ctx=_ctx, resource_config=None, iface=None)

        self.fake_boto.assert_called_with('iam', **CLIENT_CONFIG)

        self.assertEqual(
            _ctx.instance.runtime_properties,
            RUNTIME_PROPERTIES_AFTER_CREATE
        )

    def test_create_assume_str(self):
        _ctx = self.get_mock_ctx(
            'test_create',
            test_properties=NODE_PROPERTIES_ASSUME_STR,
            test_runtime_properties=DEFAULT_RUNTIME_PROPERTIES,
            type_hierarchy=ROLE_TH
        )

        current_ctx.set(_ctx)

        self.fake_client.create_role = MagicMock(return_value={
            'Role': {
                'RoleName': "role_name_id",
                'Arn': "arn_id"
            }
        })

        role.create(ctx=_ctx, resource_config=None, iface=None)

        self.fake_boto.assert_called_with('iam', **CLIENT_CONFIG)

        self.fake_client.create_role.assert_called_with(
            AssumeRolePolicyDocument=ASSUME_STR,
            Path='/service-role/',
            RoleName='aws_resource'
        )

        self.assertEqual(
            _ctx.instance.runtime_properties,
            RUNTIME_PROPERTIES_AFTER_CREATE
        )

    def test_delete(self):
        _ctx = self.get_mock_ctx(
            'test_delete',
            test_properties=NODE_PROPERTIES,
            test_runtime_properties=RUNTIME_PROPERTIES_AFTER_CREATE,
            type_hierarchy=ROLE_TH
        )

        current_ctx.set(_ctx)

        self.fake_client.delete_role = MagicMock(
            return_value=DELETE_RESPONSE
        )

        role.delete(ctx=_ctx, resource_config=None, iface=None)

        self.fake_boto.assert_called_with('iam', **CLIENT_CONFIG)

        self.fake_client.delete_role.assert_called_with(
            RoleName='role_name_id'
        )

        self.assertEqual(
            _ctx.instance.runtime_properties,
            {
                '__deleted': True,
            }
        )

    def test_IAMRoleClass_properties(self):
        self.fake_client.get_role = MagicMock(return_value={
            'Role': {
                'RoleName': "role_name_id",
                'Arn': "arn_id"
            }
        })

        test_instance = role.IAMRole("ctx_node", resource_id='role_id',
                                     client=self.fake_client, logger=None)

        self.assertEqual(test_instance.properties, {
            'RoleName': "role_name_id",
            'Arn': "arn_id"
        })

        self.fake_client.get_role.assert_called_with(
            RoleName='role_id'
        )

    def test_IAMRoleClass_status(self):
        self.fake_client.get_role = MagicMock(return_value={
            'Role': {
                'RoleName': "role_name_id",
                'Arn': "arn_id"
            }
        })

        test_instance = role.IAMRole("ctx_node", resource_id='role_id',
                                     client=self.fake_client, logger=None)

        self.assertEqual(test_instance.status, 'available')

        self.fake_client.get_role.assert_called_with(
            RoleName='role_id'
        )

    def test_attach_to(self):
        _source_ctx, _target_ctx, _ctx = self._create_common_relationships(
            'test_attach_to',
            ROLE_TH,
            ['cloudify.nodes.Root', 'cloudify.nodes.aws.iam.Policy']
        )
        current_ctx.set(_ctx)

        self.fake_client.attach_role_policy = MagicMock(return_value={})

        role.attach_to(
            ctx=_ctx, resource_config=None, iface=None
        )

        self.fake_client.attach_role_policy.assert_called_with(
            PolicyArn='aws_resource_mock_arn',
            RoleName='aws_resource_mock_id'
        )

        self.assertEqual(
            _source_ctx.instance.runtime_properties, {
                '_set_changed': True,
                'aws_resource_id': 'aws_resource_mock_id',
                'resource_config': {},
                'resource_id': 'prepare_attach_source'
            }
        )

    def test_detach_from(self):
        _source_ctx, _target_ctx, _ctx = self._create_common_relationships(
            'test_detach_from',
            ROLE_TH,
            ['cloudify.nodes.Root', 'cloudify.nodes.aws.iam.Policy']
        )
        current_ctx.set(_ctx)

        self.fake_client.detach_role_policy = MagicMock(return_value={})

        role.detach_from(
            ctx=_ctx, resource_config=None, iface=None
        )

        self.fake_client.detach_role_policy.assert_called_with(
            PolicyArn='aws_resource_mock_arn',
            RoleName='aws_resource_mock_id'
        )

        self.assertEqual(
            _source_ctx.instance.runtime_properties, {
                '_set_changed': True,
                'aws_resource_id': 'aws_resource_mock_id',
                'resource_config': {},
                'resource_id': 'prepare_attach_source'
            }
        )


if __name__ == '__main__':
    unittest.main()

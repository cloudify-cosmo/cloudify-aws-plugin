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
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# Standard imports
import unittest
import collections

# Third party imports
from mock import patch, MagicMock

from cloudify.state import current_ctx

# Local imports
from cloudify_aws.iam.resources import role_policy
from cloudify_aws.common.constants import EXTERNAL_RESOURCE_ID
from cloudify_aws.common.tests.test_base import TestBase, CLIENT_CONFIG
from cloudify_aws.common.tests.test_base import DEFAULT_RUNTIME_PROPERTIES


# Constants
ROLEPOLICY_TYPE = 'cloudify.nodes.aws.iam.RolePolicy'
ROLEPOLICY_TH = ['cloudify.nodes.Root',
                 ROLEPOLICY_TYPE]

NODE_PROPERTIES = {
    "PolicyName": "pmcfy_iam_role_policy",
    "resource_config": {
        "PolicyDocument": collections.OrderedDict([
            ("Version", "2012-10-17"),
            ("Statement", collections.OrderedDict([
                ("Effect", "Allow"),
                ("Resource", "*"),
                ("Action", "sts:AssumeRole")
            ]))
        ])
    },
    'client_config': CLIENT_CONFIG
}
ctx_node = MagicMock(
    properties=NODE_PROPERTIES,
    plugin=MagicMock(properties={})
)

RUNTIME_PROPERTIES_AFTER_CREATE = {
    'aws_resource_id': 'aws_resource',
    'resource_config': {}
}


@patch('cloudify_common_sdk.utils.ctx_from_import')
@patch('cloudify_aws.common.connection.Boto3Connection.get_account_id')
class TestIAMRolePolicy(TestBase):

    def setUp(self):
        super(TestIAMRolePolicy, self).setUp()

        self.fake_boto, self.fake_client = self.fake_boto_client('iam')

        self.mock_patch = patch('boto3.client', self.fake_boto)
        self.mock_patch.start()

    def tearDown(self):
        self.mock_patch.stop()
        self.fake_boto = None
        self.fake_client = None

        super(TestIAMRolePolicy, self).tearDown()

    def test_IAMRolePolicyClass_properties(self, *_):
        test_instance = role_policy.IAMRolePolicy(
            ctx_node, resource_id='role_id',
            client=self.fake_client, logger=None)

        self.assertIsNone(test_instance.properties)

    def test_IAMRolePolicyClass_status(self, *_):
        test_instance = role_policy.IAMRolePolicy(
            ctx_node, resource_id='role_id',
            client=self.fake_client, logger=None)

        self.assertIsNone(test_instance.status)

    def test_IAMRolePolicyClass_create(self, *_):
        test_instance = role_policy.IAMRolePolicy(
            ctx_node, resource_id='role_id',
            client=self.fake_client, logger=None)
        self.fake_client.put_role_policy = self.mock_return({"c": "d"})
        self.assertEqual(test_instance.create({"a": "b"}), {"c": "d"})
        self.fake_client.put_role_policy.assert_called_with(a='b')

    def test_IAMRolePolicyClass_delete(self, *_):
        test_instance = role_policy.IAMRolePolicy(
            ctx_node, resource_id='role_id',
            client=self.fake_client, logger=None)
        self.fake_client.delete_role_policy = self.mock_return({"c": "d"})
        self.assertEqual(test_instance.delete({"a": "b"}), {"c": "d"})
        self.fake_client.delete_role_policy.assert_called_with(a='b')

    def test_create_raises_UnknownServiceError(self, *_):
        fake_boto = self._prepare_create_raises_UnknownServiceError(
            type_hierarchy=ROLEPOLICY_TH,
            type_name='iam',
            type_class=role_policy
        )
        fake_boto.assert_called_with(
            'iam',
            aws_access_key_id='xxx',
            aws_secret_access_key='yyy',
            region_name='aq-testzone-1')

    def test_create(self, *_):
        _ctx = self.get_mock_ctx(
            'test_create',
            test_properties=NODE_PROPERTIES,
            test_runtime_properties=DEFAULT_RUNTIME_PROPERTIES,
            type_hierarchy=ROLEPOLICY_TH,
            type_node=ROLEPOLICY_TYPE,
        )
        _ctx.instance._relationships = [
            self.get_mock_relationship_ctx(
                "iam",
                test_target=self.get_mock_ctx(
                    "iam", {},
                    {EXTERNAL_RESOURCE_ID: 'subnet_id'},
                    type_hierarchy=[role_policy.ROLE_TYPE],
                    type_node=role_policy.ROLE_TYPE))
        ]

        current_ctx.set(_ctx)

        self.fake_client.put_role_policy = self.mock_return({})

        role_policy.create(ctx=_ctx, resource_config=None, iface=None,
                           params=None)

        self.fake_boto.assert_called_with(
            'iam',
            aws_access_key_id='xxx',
            aws_secret_access_key='yyy',
            region_name='aq-testzone-1')

        self.fake_client.put_role_policy.assert_called_with(
            PolicyName='aws_resource', RoleName='subnet_id',
            PolicyDocument='{"Version": "2012-10-17", "Statement": {"Effect": '
                           '"Allow", "Resource": "*", "Action": "sts:AssumeRol'
                           'e"}}')
        self.assertEqual(
            _ctx.instance.runtime_properties,
            RUNTIME_PROPERTIES_AFTER_CREATE
        )

    def test_delete(self, *_):
        _ctx = self.get_mock_ctx(
            'test_create',
            test_properties=NODE_PROPERTIES,
            test_runtime_properties=RUNTIME_PROPERTIES_AFTER_CREATE,
            type_hierarchy=ROLEPOLICY_TH,
            type_node=ROLEPOLICY_TYPE,
            ctx_operation_name='cloudify.interfaces.lifecycle.delete'
        )
        _ctx.instance._relationships = [
            self.get_mock_relationship_ctx(
                "iam",
                test_target=self.get_mock_ctx(
                    "iam", {},
                    {EXTERNAL_RESOURCE_ID: 'subnet_id'},
                    type_hierarchy=[role_policy.ROLE_TYPE],
                    type_node=role_policy.ROLE_TYPE))
        ]

        current_ctx.set(_ctx)

        self.fake_client.delete_role_policy = self.mock_return({})

        role_policy.delete(ctx=_ctx, resource_config={}, iface=None,
                           params=None)

        self.fake_boto.assert_called_with(
            'iam',
            aws_access_key_id='xxx',
            aws_secret_access_key='yyy',
            region_name='aq-testzone-1')

        self.fake_client.delete_role_policy.assert_called_with(
            PolicyName='aws_resource', RoleName='subnet_id')
        self.assertEqual(
            _ctx.instance.runtime_properties, {}
        )


if __name__ == '__main__':
    unittest.main()

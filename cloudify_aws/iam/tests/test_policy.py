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

# Third party imports
from mock import patch, MagicMock

from cloudify.state import current_ctx

# Local imports
from cloudify_aws.iam.resources import policy
from cloudify_aws.common.tests.test_base import TestBase, CLIENT_CONFIG
from cloudify_aws.common.tests.test_base import DELETE_RESPONSE
from cloudify_aws.common.tests.test_base import DEFAULT_RUNTIME_PROPERTIES


# Constants
POLICY_TH = ['cloudify.nodes.Root',
             'cloudify.nodes.aws.iam.Policy']

NODE_PROPERTIES = {
    'resource_id': 'CloudifyVPCAccessPolicy',
    'use_external_resource': False,
    'resource_config': {
        'kwargs': {
            'Description': 'Grants access to EC2 network components',
            'Path': '/service-role/',
            'PolicyDocument': {
                'Version': '2012-10-17',
                'Statement': [{
                    'Effect': 'Allow',
                    'Action': [
                        'ec2:CreateNetworkInterface',
                        'ec2:DeleteNetworkInterface',
                        'ec2:DescribeNetworkInterfaces'
                    ],
                    'Resource': '*'
                }]
            }
        }
    },
    'client_config': CLIENT_CONFIG
}

POLICY_STR = (
    '{"Version": "2012-10-17", "Statement": [{"Action": ["ec2:CreateNetworkI' +
    'nterface", "ec2:DeleteNetworkInterface", "ec2:DescribeNetworkInterfaces' +
    '"], "Resource": "*", "Effect": "Allow"}]}'
)

NODE_PROPERTIES_POLICY_STR = {
    'resource_id': 'CloudifyVPCAccessPolicy',
    'use_external_resource': False,
    'resource_config': {
        'kwargs': {
            'Description': 'Grants access to EC2 network components',
            'Path': '/service-role/',
            'PolicyDocument': POLICY_STR
        }
    },
    'client_config': CLIENT_CONFIG
}

RUNTIME_PROPERTIES_AFTER_CREATE = {
    'aws_resource_arn': 'arn_id',
    'aws_resource_id': 'policy_name_id',
    'resource_config': {}
}
ctx_node = MagicMock(
    properties=NODE_PROPERTIES,
    plugin=MagicMock(properties={})
)


@patch('cloudify_common_sdk.utils.ctx_from_import')
@patch('cloudify_aws.common.connection.Boto3Connection.get_account_id')
class TestIAMPolicy(TestBase):

    def setUp(self):
        super(TestIAMPolicy, self).setUp()

        self.fake_boto, self.fake_client = self.fake_boto_client('iam')

        self.mock_patch = patch('boto3.client', self.fake_boto)
        self.mock_patch.start()

    def tearDown(self):
        self.mock_patch.stop()
        self.fake_boto = None
        self.fake_client = None

        super(TestIAMPolicy, self).tearDown()

    def test_create_raises_UnknownServiceError(self, *_):
        fake_boto = self._prepare_create_raises_UnknownServiceError(
            type_hierarchy=POLICY_TH,
            type_name='iam',
            type_class=policy
        )
        fake_boto.assert_called_with(
            'iam',
            aws_access_key_id='xxx',
            aws_secret_access_key='yyy',
            region_name='aq-testzone-1'
        )

    def test_create(self, *_):
        _ctx = self.get_mock_ctx(
            'test_create',
            test_properties=NODE_PROPERTIES,
            test_runtime_properties=DEFAULT_RUNTIME_PROPERTIES,
            type_hierarchy=POLICY_TH
        )

        current_ctx.set(_ctx)

        self.fake_client.create_policy = MagicMock(return_value={
            'Policy': {
                'PolicyName': 'policy_name_id',
                'Arn': 'arn_id'
            }
        })

        policy.create(ctx=_ctx, resource_config=None, iface=None)

        self.fake_boto.assert_called_with(
            'iam',
            aws_access_key_id='xxx',
            aws_secret_access_key='yyy',
            region_name='aq-testzone-1')

        self.assertEqual(
            _ctx.instance.runtime_properties,
            RUNTIME_PROPERTIES_AFTER_CREATE
        )

    def test_create_policy_str(self, *_):
        _ctx = self.get_mock_ctx(
            'test_create',
            test_properties=NODE_PROPERTIES_POLICY_STR,
            test_runtime_properties=DEFAULT_RUNTIME_PROPERTIES,
            type_hierarchy=POLICY_TH
        )

        current_ctx.set(_ctx)

        self.fake_client.create_policy = MagicMock(return_value={
            'Policy': {
                'PolicyName': 'policy_name_id',
                'Arn': 'arn_id'
            }
        })

        policy.create(ctx=_ctx, resource_config=None, iface=None)

        self.fake_boto.assert_called_with(
            'iam',
            aws_access_key_id='xxx',
            aws_secret_access_key='yyy',
            region_name='aq-testzone-1')

        self.fake_client.create_policy.assert_called_with(
            Description='Grants access to EC2 network components',
            Path='/service-role/',
            PolicyDocument=POLICY_STR,
            PolicyName='aws_resource'
        )

        self.assertEqual(
            _ctx.instance.runtime_properties,
            RUNTIME_PROPERTIES_AFTER_CREATE
        )

    def test_delete(self, _, mock_import_ctx, *__):

        _ctx = self.get_mock_ctx(
            'test_delete',
            test_properties=NODE_PROPERTIES,
            test_runtime_properties=RUNTIME_PROPERTIES_AFTER_CREATE,
            type_hierarchy=POLICY_TH,
            ctx_operation_name='cloudify.interfaces.lifecycle.delete'
        )

        current_ctx.set(_ctx)
        mock_import_ctx.node = _ctx.node
        mock_import_ctx.instance = _ctx.instance
        mock_import_ctx.operation = _ctx.operation

        self.fake_client.delete_policy = self.mock_return(DELETE_RESPONSE)

        policy.delete(ctx=_ctx, resource_config=None, iface=None)

        self.fake_boto.assert_called_with(
            'iam',
            aws_access_key_id='xxx',
            aws_secret_access_key='yyy',
            region_name='aq-testzone-1')

        self.fake_client.delete_policy.assert_called_with(
            PolicyArn='arn_id'
        )

        self.assertEqual(
            _ctx.instance.runtime_properties,
            {
                '__deleted': True
            }
        )

    def test_IAMPolicyClass_properties(self, *_):
        self.fake_client.get_policy = MagicMock(return_value={
            'Policy': {
                'PolicyName': 'policy_name_id',
                'Arn': 'arn_id'
            }
        })

        test_instance = policy.IAMPolicy(ctx_node,
                                         resource_id='queue_id',
                                         client=self.fake_client,
                                         logger=None)

        self.assertEqual(test_instance.properties, {
            'PolicyName': 'policy_name_id',
            'Arn': 'arn_id'
        })

        self.fake_client.get_policy.assert_called_with(
            PolicyArn='queue_id'
        )

    def test_IAMPolicyClass_status(self, *_):
        self.fake_client.get_policy = MagicMock(return_value={
            'Policy': {
                'PolicyName': 'policy_name_id',
                'Arn': 'arn_id'
            }
        })

        test_instance = policy.IAMPolicy(ctx_node,
                                         resource_id='queue_id',
                                         client=self.fake_client,
                                         logger=None)

        self.assertEqual(test_instance.status, 'available')

        self.fake_client.get_policy.assert_called_with(
            PolicyArn='queue_id'
        )


if __name__ == '__main__':
    unittest.main()

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
from botocore.exceptions import UnknownServiceError, ClientError

from cloudify.state import current_ctx
from cloudify.exceptions import OperationRetry

# Local imports
from cloudify_aws.common._compat import text_type
from cloudify_aws.rds.resources import option_group
from cloudify_aws.common.tests.test_base import TestBase, CLIENT_CONFIG

# Constants
OPTION_GROUP_TH = ['cloudify.nodes.Root',
                   'cloudify.nodes.aws.rds.OptionGroup']

RUNTIME_PROPERTIES_AFTER_CREATE = {
    'aws_resource_arn': 'OptionGroupArn',
    'aws_resource_id': 'dev-db-option-group',
    'resource_config': {}
}

NODE_PROPERTIES = {
    'use_external_resource': False,
    'resource_id': 'dev-db-option-group',
    'resource_config': {
        'kwargs': {
            'EngineName': 'mysql',
            'MajorEngineVersion': '5.7',
            'OptionGroupDescription': 'MySQL5.7 Option Group for Dev'
        }
    },
    'client_config': CLIENT_CONFIG
}


class TestRDSOptionGroup(TestBase):

    def setUp(self):
        super(TestRDSOptionGroup, self).setUp()

        self.fake_boto, self.fake_client = self.fake_boto_client('rds')

        self.mock_patch = patch('boto3.client', self.fake_boto)
        self.mock_patch.start()

    def tearDown(self):
        self.mock_patch.stop()
        self.fake_boto = None
        self.fake_client = None

        super(TestRDSOptionGroup, self).tearDown()

    def test_create_raises_UnknownServiceError(self):
        _test_name = 'test_create_UnknownServiceError'
        _test_node_properties = {
            'use_external_resource': False,
            'client_config': CLIENT_CONFIG
        }
        _test_runtime_properties = {
            'resource_config': {}
        }
        _ctx = self.get_mock_ctx(
            _test_name,
            test_properties=_test_node_properties,
            test_runtime_properties=_test_runtime_properties,
            type_hierarchy=OPTION_GROUP_TH
        )
        current_ctx.set(_ctx)

        with self.assertRaises(UnknownServiceError) as error:
            option_group.create(
                ctx=_ctx, resource_config=None, iface=None
            )

        self.assertEqual(
            text_type(error.exception),
            "Unknown service: 'rds'. Valid service names are: ['rds']"
        )

        self.fake_boto.assert_called_with('rds', aws_access_key_id='xxx',
                                          aws_secret_access_key='yyy',
                                          region_name='aq-testzone-1')

    def test_create(self):
        _test_name = 'test_create'
        _test_runtime_properties = {
            'resource_config': {}
        }
        _ctx = self.get_mock_ctx(
            _test_name,
            test_properties=NODE_PROPERTIES,
            test_runtime_properties=_test_runtime_properties,
            type_hierarchy=OPTION_GROUP_TH
        )
        current_ctx.set(_ctx)

        self.fake_client.create_option_group = MagicMock(return_value={
            'OptionGroup': {
                'OptionGroupName': 'dev-db-option-group',
                'OptionGroupArn': 'OptionGroupArn'
            }
        })
        option_group.create(
            ctx=_ctx, resource_config=None, iface=None
        )
        self.fake_boto.assert_called_with(
            'rds', **CLIENT_CONFIG
        )
        self.fake_client.create_option_group.assert_called_with(
            EngineName='mysql',
            MajorEngineVersion='5.7',
            OptionGroupDescription='MySQL5.7 Option Group for Dev',
            OptionGroupName='dev-db-option-group'
        )

        self.assertEqual(
            _ctx.instance.runtime_properties,
            RUNTIME_PROPERTIES_AFTER_CREATE
        )

    def test_delete(self):
        _test_name = 'test_delete'
        _ctx = self.get_mock_ctx(
            _test_name,
            test_properties=NODE_PROPERTIES,
            test_runtime_properties=RUNTIME_PROPERTIES_AFTER_CREATE,
            type_hierarchy=OPTION_GROUP_TH,
            ctx_operation_name='cloudify.interfaces.lifecycle.delete'
        )
        current_ctx.set(_ctx)

        self.fake_client.delete_option_group = MagicMock(
            return_value={}
        )
        iface = MagicMock()
        iface.status = None
        option_group.delete(
            ctx=_ctx, resource_config=None, iface=iface
        )
        self.fake_boto.assert_called_with(
            'rds', **CLIENT_CONFIG
        )
        self.fake_client.delete_option_group.assert_called_with(
            OptionGroupName='dev-db-option-group'
        )

        self.assertEqual(
            _ctx.instance.runtime_properties, {
                '__deleted': True,
            }
        )

    def test_immortal_delete(self):
        _test_name = 'test_delete'
        _ctx = self.get_mock_ctx(
            _test_name,
            test_properties=NODE_PROPERTIES,
            test_runtime_properties=RUNTIME_PROPERTIES_AFTER_CREATE,
            type_hierarchy=OPTION_GROUP_TH,
            ctx_operation_name='cloudify.interfaces.lifecycle.delete'
        )
        current_ctx.set(_ctx)

        self.fake_client.delete_option_group = MagicMock(
            return_value={}
        )

        self.fake_client.describe_option_groups = MagicMock(
            return_value={
                'OptionGroupsList': [{
                    'OptionGroupName': 'dev-db-option-group',
                    'OptionGroupArn': 'OptionGroupArn'
                }]
            }
        )
        with self.assertRaises(OperationRetry) as error:
            option_group.delete(
                ctx=_ctx, resource_config=None, iface=None
            )

        self.assertEqual(
            text_type(error.exception),
            (
                'RDS Option Group ID# "dev-db-option-group" is still ' +
                'in a pending state.'
            )
        )

    def test_delete_client_error(self):
        _test_name = 'test_delete'
        _ctx = self.get_mock_ctx(
            _test_name,
            test_properties=NODE_PROPERTIES,
            test_runtime_properties=RUNTIME_PROPERTIES_AFTER_CREATE,
            type_hierarchy=OPTION_GROUP_TH,
            ctx_operation_name='cloudify.interfaces.lifecycle.delete'
        )
        current_ctx.set(_ctx)

        self.fake_client.delete_option_group = self._gen_client_error(
            'test_delete', message='SomeMessage'
        )

        with self.assertRaises(OperationRetry) as error:
            option_group.delete(
                ctx=_ctx, resource_config=None, iface=None
            )

        self.assertEqual(
            text_type(error.exception), 'SomeMessage'
        )

    def test_delete_unexpected_client_error(self):
        _test_name = 'test_delete'
        _ctx = self.get_mock_ctx(
            _test_name,
            test_properties=NODE_PROPERTIES,
            test_runtime_properties=RUNTIME_PROPERTIES_AFTER_CREATE,
            type_hierarchy=OPTION_GROUP_TH,
            ctx_operation_name='cloudify.interfaces.lifecycle.delete'
        )
        current_ctx.set(_ctx)

        self.fake_client.delete_option_group = self._gen_client_error(
            'test_delete', message='SomeMessage', code='InvalidFault'
        )

        with self.assertRaises(ClientError) as error:
            option_group.delete(
                ctx=_ctx, resource_config=None, iface=None
            )

        self.assertEqual(
            text_type(error.exception), (
                'An error occurred (InvalidFault) when calling the ' +
                'client_error_test_delete operation: SomeMessage'
            )
        )

    def test_attach_to(self):
        _source_ctx, _target_ctx, _ctx = self._create_common_relationships(
            'test_attach_to',
            source_type_hierarchy=OPTION_GROUP_TH,
            target_type_hierarchy=['cloudify.nodes.Root',
                                   'cloudify.nodes.aws.rds.Option']
        )
        current_ctx.set(_ctx)

        self.fake_client.modify_option_group = MagicMock(
            return_value={
                'OptionGroup': 'abc'
            }
        )
        option_group.attach_to(
            ctx=_ctx, resource_config=None, iface=None
        )
        self.assertEqual(_target_ctx.instance.runtime_properties, {
            'resource_id': 'prepare_attach_target',
            'aws_resource_id': 'aws_target_mock_id',
            'aws_resource_arn': 'aws_resource_mock_arn'
        })
        self.fake_client.modify_option_group.assert_called_with(
            ApplyImmediately=True,
            OptionGroupName='aws_resource_mock_id',
            OptionsToInclude=[{'OptionName': 'aws_target_mock_id'}]
        )

    def test_detach_from(self):
        _source_ctx, _target_ctx, _ctx = self._create_common_relationships(
            'test_detach_from',
            source_type_hierarchy=OPTION_GROUP_TH,
            target_type_hierarchy=['cloudify.nodes.Root',
                                   'cloudify.nodes.aws.rds.Option']
        )
        current_ctx.set(_ctx)

        self.fake_client.modify_option_group = MagicMock(
            return_value={
                'OptionGroup': 'abc'
            }
        )
        option_group.detach_from(
            ctx=_ctx, resource_config=None, iface=None
        )
        self.assertEqual(_target_ctx.instance.runtime_properties, {
            'resource_id': 'prepare_attach_target',
            'aws_resource_id': 'aws_target_mock_id',
            'aws_resource_arn': 'aws_resource_mock_arn'
        })
        self.fake_client.modify_option_group.assert_called_with(
            ApplyImmediately=True,
            OptionGroupName='aws_resource_mock_id',
            OptionsToRemove=['aws_target_mock_id']
        )


if __name__ == '__main__':
    unittest.main()

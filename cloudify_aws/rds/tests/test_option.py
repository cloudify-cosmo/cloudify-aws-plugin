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
from cloudify_aws.rds.resources import option
from cloudify_aws.common.tests.test_base import TestBase, CLIENT_CONFIG

# Constants
PARAMETER_OPTION_TH = ['cloudify.nodes.Root',
                       'cloudify.nodes.aws.rds.Option']


class TestRDSOption(TestBase):

    def setUp(self):
        super(TestRDSOption, self).setUp()

        self.fake_boto, self.fake_client = self.fake_boto_client('rds')

        self.mock_patch = patch('boto3.client', self.fake_boto)
        self.mock_patch.start()

    def tearDown(self):
        self.mock_patch.stop()
        self.fake_boto = None
        self.fake_client = None

        super(TestRDSOption, self).tearDown()

    def test_configure(self):
        _test_name = 'test_create_UnknownServiceError'
        _test_node_properties = {
            'use_external_resource': False,
            "resource_id": "dev-db-option-group",
            "resource_config": {
                "kwargs": {
                    "Port": 21212
                }
            },
            'client_config': CLIENT_CONFIG
        }

        _ctx = self.get_mock_ctx(
            _test_name,
            test_properties=_test_node_properties,
            test_runtime_properties={},
            type_hierarchy=PARAMETER_OPTION_TH
        )
        current_ctx.set(_ctx)

        option.configure(ctx=_ctx, resource_config=None, iface=None)

        self.fake_boto.assert_not_called()

        self.assertEqual(
            _ctx.instance.runtime_properties, {
                'resource_config': {
                    "Port": 21212
                }
            }
        )

    def test_configure_without_resource_id(self):
        _test_name = 'test_create_UnknownServiceError'
        _test_node_properties = {
            'use_external_resource': False,
            "resource_config": {
                'OptionName': 'OptionName',
                "kwargs": {
                    "Port": 21212
                }
            },
            'client_config': CLIENT_CONFIG
        }

        _ctx = self.get_mock_ctx(
            _test_name,
            test_properties=_test_node_properties,
            test_runtime_properties={},
            type_hierarchy=PARAMETER_OPTION_TH
        )
        current_ctx.set(_ctx)

        option.configure(ctx=_ctx, resource_config=None, iface=None)

        self.assertEqual(
            _ctx.instance.runtime_properties, {
                'aws_resource_id': 'OptionName',
                'resource_config': {
                    'OptionName': 'OptionName',
                    "Port": 21212
                }
            }
        )

    def _create_option_relationships(self, node_id, type_hierarchy):
        _source_ctx = self.get_mock_ctx(
            'test_attach_source',
            test_properties={},
            test_runtime_properties={
                'resource_id': 'prepare_attach_source',
                'aws_resource_id': 'aws_resource_mock_id',
                '_set_changed': True,
                'resource_config': {}
            },
            type_hierarchy=PARAMETER_OPTION_TH,
            ctx_operation_name="cloudify.interfaces.lifecycle.configure"
        )

        _target_ctx = self.get_mock_ctx(
            'test_attach_target',
            test_properties={
                'client_config': CLIENT_CONFIG
            },
            test_runtime_properties={
                'resource_id': 'prepare_attach_target',
                'aws_resource_id': 'aws_target_mock_id',
            },
            type_hierarchy=type_hierarchy,
            ctx_operation_name="cloudify.interfaces.lifecycle.configure"
        )

        _ctx = self.get_mock_relationship_ctx(
            node_id,
            test_properties={},
            test_runtime_properties={},
            test_source=_source_ctx,
            test_target=_target_ctx,
            # ctx_operation_name="cloudify.interfaces.lifecycle.configure"
        )

        return _source_ctx, _target_ctx, _ctx

    def test_attach_to(self):
        _source_ctx, _target_ctx, _ctx = self._create_option_relationships(
            'test_attach_to',
            ['cloudify.nodes.Root', 'cloudify.nodes.aws.rds.OptionGroup']
        )
        current_ctx.set(_ctx)

        self.fake_client.modify_option_group = MagicMock(
            return_value={
                'OptionGroup': 'abc'
            }
        )
        option.attach_to(
            ctx=_ctx, resource_config=None, iface=None
        )
        self.assertEqual(
            _source_ctx.instance.runtime_properties, {
                '_set_changed': True,
                'aws_resource_id': 'aws_resource_mock_id',
                'resource_config': {},
                'resource_id': 'prepare_attach_source'
            }
        )
        self.fake_client.modify_option_group.assert_called_with(
            ApplyImmediately=True,
            OptionGroupName='aws_target_mock_id',
            OptionsToInclude=[{'OptionName': 'aws_target_mock_id'}]
        )

    def test_attach_to_security_group(self):
        _source_ctx, _target_ctx, _ctx = self._create_option_relationships(
            'test_attach_to',
            ['cloudify.nodes.Root', 'cloudify.nodes.aws.ec2.SecurityGroup']
        )
        current_ctx.set(_ctx)

        option.attach_to(
            ctx=_ctx, resource_config=None, iface=None
        )
        self.assertEqual(
            _source_ctx.instance.runtime_properties, {
                '_set_changed': True,
                'aws_resource_id': 'aws_resource_mock_id',
                'resource_config': {
                    'VpcSecurityGroupMemberships': ['aws_target_mock_id']
                },
                'resource_id': 'prepare_attach_source'
            }
        )

    def test_detach_from(self):
        _source_ctx, _target_ctx, _ctx = self._create_option_relationships(
            'test_attach_to',
            ['cloudify.nodes.Root', 'cloudify.nodes.aws.rds.OptionGroup']
        )
        current_ctx.set(_ctx)

        self.fake_client.modify_option_group = MagicMock(
            return_value={
                'OptionGroup': 'abc'
            }
        )
        option.detach_from(
            ctx=_ctx, resource_config=None, iface=None
        )
        self.assertEqual(
            _source_ctx.instance.runtime_properties, {
                '_set_changed': True,
                'resource_config': {},
                'aws_resource_id': 'aws_resource_mock_id',
                'resource_id': 'prepare_attach_source'
            }
        )
        self.fake_client.modify_option_group.assert_called_with(
            ApplyImmediately=True,
            OptionGroupName='aws_target_mock_id',
            OptionsToRemove=[{'OptionName': 'aws_target_mock_id'}]
        )


if __name__ == '__main__':
    unittest.main()

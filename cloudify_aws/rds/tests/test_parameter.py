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
from cloudify_aws.rds.resources import parameter
from cloudify_aws.common.tests.test_base import TestBase, CLIENT_CONFIG

# Constants
PARAMETER_TH = ['cloudify.nodes.Root',
                'cloudify.nodes.aws.rds.Parameter']


class TestRDSParameter(TestBase):

    def setUp(self):
        super(TestRDSParameter, self).setUp()

        self.fake_boto, self.fake_client = self.fake_boto_client('rds')

        self.mock_patch = patch('boto3.client', self.fake_boto)
        self.mock_patch.start()

    def tearDown(self):
        self.mock_patch.stop()
        self.fake_boto = None
        self.fake_client = None

        super(TestRDSParameter, self).tearDown()

    def test_configure(self):
        _test_name = 'test_create_UnknownServiceError'
        _test_node_properties = {
            'use_external_resource': False,
            "resource_id": "dev-db-option-group",
            "resource_config": {
                "kwargs": {
                    "ParameterName": "log_timestamps",
                    "ParameterValue": "UTC",
                    "ApplyMethod": "immediate"
                }
            },
            'client_config': CLIENT_CONFIG
        }

        _ctx = self.get_mock_ctx(
            _test_name,
            test_properties=_test_node_properties,
            test_runtime_properties={},
            type_hierarchy=PARAMETER_TH
        )
        current_ctx.set(_ctx)

        parameter.configure(ctx=_ctx, resource_config=None, iface=None)

        self.fake_boto.assert_not_called()

        self.assertEqual(
            _ctx.instance.runtime_properties, {
                'resource_config': {
                    'ParameterName': 'log_timestamps',
                    'ParameterValue': 'UTC',
                    'ApplyMethod': 'immediate'
                }
            }
        )

    def test_configure_without_resource_id(self):
        _test_name = 'test_create_UnknownServiceError'
        _test_node_properties = {
            'use_external_resource': False,
            "resource_config": {
                'ParameterName': 'ParameterName',
                "kwargs": {
                    "ParameterName": "log_timestamps",
                    "ParameterValue": "UTC",
                    "ApplyMethod": "immediate"
                }
            },
            'client_config': CLIENT_CONFIG
        }

        _ctx = self.get_mock_ctx(
            _test_name,
            test_properties=_test_node_properties,
            test_runtime_properties={},
            type_hierarchy=PARAMETER_TH
        )
        current_ctx.set(_ctx)

        parameter.configure(ctx=_ctx, resource_config=None, iface=None)

        self.assertEqual(
            _ctx.instance.runtime_properties, {
                'aws_resource_id': 'log_timestamps',
                'resource_config': {
                    'ParameterName': 'log_timestamps',
                    'ParameterValue': 'UTC',
                    'ApplyMethod': 'immediate'
                }
            }
        )

    def _create_parameter_relationships(self, node_id):
        _source_ctx = self.get_mock_ctx(
            'test_attach_source',
            test_properties={},
            test_runtime_properties={
                'resource_config': {}
            },
            type_hierarchy=PARAMETER_TH
        )

        _target_ctx = self.get_mock_ctx(
            'test_attach_target',
            test_properties={
                'client_config': CLIENT_CONFIG
            },
            test_runtime_properties={
                'resource_id': 'prepare_attach_resource',
                'aws_resource_id': 'aws_resource_mock_id',
                '_set_changed': True
            },
            type_hierarchy=['cloudify.nodes.Root',
                            'cloudify.nodes.aws.rds.ParameterGroup']
        )

        _ctx = self.get_mock_relationship_ctx(
            node_id,
            test_properties={},
            test_runtime_properties={},
            test_source=_source_ctx,
            test_target=_target_ctx
        )

        return _source_ctx, _target_ctx, _ctx

    def test_attach_to(self):
        _source_ctx, _target_ctx, _ctx = self._create_parameter_relationships(
            'test_attach_to'
        )
        current_ctx.set(_ctx)

        self.fake_client.modify_db_parameter_group = MagicMock(
            return_value={
                'DBParameterGroupName': 'abc'
            }
        )
        parameter.attach_to(
            ctx=_ctx, resource_config=None, iface=None
        )
        self.assertEqual(_target_ctx.instance.runtime_properties, {
            '_set_changed': True,
            'aws_resource_id': 'aws_resource_mock_id',
            'resource_id': 'prepare_attach_resource'
        })
        self.fake_client.modify_db_parameter_group.assert_called_with(
            DBParameterGroupName='aws_resource_mock_id',
            Parameters=[{'ParameterName': 'aws_resource_mock_id'}]
        )

    def test_detach_from(self):
        _source_ctx, _target_ctx, _ctx = self._create_parameter_relationships(
            'test_detach_from'
        )
        current_ctx.set(_ctx)

        parameter.detach_from(
            ctx=_ctx, resource_config=None, iface=None
        )
        self.assertEqual(_target_ctx.instance.runtime_properties, {
            '_set_changed': True,
            'aws_resource_id': 'aws_resource_mock_id',
            'resource_id': 'prepare_attach_resource'
        })


if __name__ == '__main__':
    unittest.main()

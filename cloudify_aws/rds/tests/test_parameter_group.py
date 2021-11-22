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
from botocore.exceptions import UnknownServiceError

from cloudify.exceptions import OperationRetry
from cloudify.state import current_ctx

# Local imports
from cloudify_aws.common._compat import text_type
from cloudify_aws.rds.resources import parameter_group
from cloudify_aws.common.tests.test_base import TestBase, CLIENT_CONFIG

# Constants
PARAMETER_GROUP_TH = ['cloudify.nodes.Root',
                      'cloudify.nodes.aws.rds.ParameterGroup']

NODE_PROPERTIES = {
    'resource_id': 'dev-db-param-group',
    'use_external_resource': False,
    'resource_config': {
        'kwargs': {
            'DBParameterGroupFamily': 'mysql5.7',
            'Description': 'MySQL5.7 Parameter Group for Dev'
        }
    },
    'client_config': CLIENT_CONFIG
}

RUNTIME_PROPERTIES_AFTER_CREATE = {
    'aws_resource_arn': 'DBParameterGroupArn',
    'aws_resource_id': 'dev-db-param-group',
    'resource_config': {}
}


class TestRDSParameterGroup(TestBase):

    def setUp(self):
        super(TestRDSParameterGroup, self).setUp()

        self.fake_boto, self.fake_client = self.fake_boto_client('rds')

        self.mock_patch = patch('boto3.client', self.fake_boto)
        self.mock_patch.start()

    def tearDown(self):
        self.mock_patch.stop()
        self.fake_boto = None
        self.fake_client = None

        super(TestRDSParameterGroup, self).tearDown()

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
            type_hierarchy=PARAMETER_GROUP_TH
        )
        current_ctx.set(_ctx)

        with self.assertRaises(UnknownServiceError) as error:
            parameter_group.create(
                ctx=_ctx, resource_config=None, iface=None
            )

        self.assertEqual(
            text_type(error.exception),
            "Unknown service: 'rds'. Valid service names are: ['rds']"
        )

        self.fake_boto.assert_called_with('rds', aws_access_key_id='xxx',
                                          aws_secret_access_key='yyy',
                                          region_name='aq-testzone-1')

    def test_configure_empty(self):
        _test_name = 'test_configure'
        _ctx = self.get_mock_ctx(
            _test_name,
            test_properties=NODE_PROPERTIES,
            test_runtime_properties=RUNTIME_PROPERTIES_AFTER_CREATE,
            type_hierarchy=PARAMETER_GROUP_TH
        )
        current_ctx.set(_ctx)

        parameter_group.configure(
            ctx=_ctx, resource_config=None, iface=None
        )

        self.assertEqual(
            _ctx.instance.runtime_properties,
            RUNTIME_PROPERTIES_AFTER_CREATE
        )

    def test_configure(self):
        _test_name = 'test_configure'
        _ctx = self.get_mock_ctx(
            _test_name,
            test_properties=NODE_PROPERTIES,
            test_runtime_properties=RUNTIME_PROPERTIES_AFTER_CREATE,
            type_hierarchy=PARAMETER_GROUP_TH
        )
        current_ctx.set(_ctx)

        self.fake_client.modify_db_parameter_group = MagicMock(
            return_value={'DBParameterGroupName': 'abc'}
        )
        parameter_group.configure(
            ctx=_ctx, resource_config={
                "Parameters": [
                    {
                        "ParameterName": "time_zone",
                        "ParameterValue": "US/Eastern",
                        "ApplyMethod": "immediate"
                    }, {
                        "ParameterName": "lc_time_names",
                        "ParameterValue": "en_US",
                        "ApplyMethod": "immediate"
                    }
                ]
            }, iface=None
        )

        self.fake_client.modify_db_parameter_group.assert_called_with(
            DBParameterGroupName='dev-db-param-group',
            Parameters=[{
                'ParameterName': 'time_zone',
                'ParameterValue': 'US/Eastern',
                'ApplyMethod': 'immediate'
            }, {
                'ParameterName': 'lc_time_names',
                'ParameterValue': 'en_US',
                'ApplyMethod': 'immediate'
            }]
        )

        self.assertEqual(
            _ctx.instance.runtime_properties,
            RUNTIME_PROPERTIES_AFTER_CREATE
        )

    def test_create(self):
        _test_name = 'test_create_UnknownServiceError'
        _test_runtime_properties = {
            'resource_config': {}
        }
        _ctx = self.get_mock_ctx(
            _test_name,
            test_properties=NODE_PROPERTIES,
            test_runtime_properties=_test_runtime_properties,
            type_hierarchy=PARAMETER_GROUP_TH
        )
        current_ctx.set(_ctx)

        self.fake_client.create_db_parameter_group = MagicMock(
            return_value={
                'DBParameterGroup': {
                    'DBParameterGroupName': 'dev-db-param-group',
                    'DBParameterGroupArn': 'DBParameterGroupArn'
                }
            }
        )
        parameter_group.create(
            ctx=_ctx, resource_config=None, iface=None
        )

        self.fake_client.create_db_parameter_group.assert_called_with(
            DBParameterGroupFamily='mysql5.7',
            DBParameterGroupName='dev-db-param-group',
            Description='MySQL5.7 Parameter Group for Dev'
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
            type_hierarchy=PARAMETER_GROUP_TH,
            ctx_operation_name='cloudify.interfaces.lifecycle.delete'
        )
        current_ctx.set(_ctx)

        self.fake_client.delete_db_parameter_group = MagicMock(
            return_value={}
        )
        parameter_group.delete(
            ctx=_ctx, resource_config=None, iface=None
        )

        self.fake_client.delete_db_parameter_group.assert_called_with(
            DBParameterGroupName='dev-db-param-group'
        )

        self.assertEqual(
            _ctx.instance.runtime_properties, {
                '__deleted': True,
            }
        )

    def test_immortal_delete(self):
        _test_name = 'test_immortal_delete'
        _ctx = self.get_mock_ctx(
            _test_name,
            test_properties=NODE_PROPERTIES,
            test_runtime_properties=RUNTIME_PROPERTIES_AFTER_CREATE,
            type_hierarchy=PARAMETER_GROUP_TH,
            ctx_operation_name='cloudify.interfaces.lifecycle.delete'
        )
        current_ctx.set(_ctx)

        self.fake_client.delete_db_parameter_group = MagicMock(
            return_value={}
        )
        self.fake_client.describe_db_parameter_groups = MagicMock(
            return_value={
                'DBParameterGroups': [{
                    'DBParameterGroupName': 'dev-db-param-group',
                    'DBParameterGroupArn': 'DBParameterGroupArn'
                }]
            }
        )
        iface = MagicMock()
        iface.status = None
        with self.assertRaises(OperationRetry) as error:
            parameter_group.delete(
                ctx=_ctx, resource_config=None, iface=iface
            )

        self.assertEqual(
            text_type(error.exception),
            (
                'RDS Parameter Group ID# "dev-db-param-group"' +
                ' is still in a pending state.'
            )
        )

    def _create_parameter_relationships(self, node_id):
        _source_ctx = self.get_mock_ctx(
            'test_attach_source',
            test_properties={
                'client_config': CLIENT_CONFIG
            },
            test_runtime_properties={
                'resource_id': 'prepare_attach_source',
                'aws_resource_id': 'aws_resource_mock_id',
                '_set_changed': True
            },
            type_hierarchy=PARAMETER_GROUP_TH
        )

        _target_ctx = self.get_mock_ctx(
            'test_attach_target',
            test_properties={},
            test_runtime_properties={
                'resource_id': 'prepare_attach_target',
                'aws_resource_id': 'aws_target_mock_id',
            },
            type_hierarchy=['cloudify.nodes.Root',
                            'cloudify.nodes.aws.rds.Parameter']
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
        parameter_group.attach_to(
            ctx=_ctx, resource_config=None, iface=None
        )
        self.assertEqual(_target_ctx.instance.runtime_properties, {
            'aws_resource_id': 'aws_target_mock_id',
            'resource_id': 'prepare_attach_target'
        })
        self.fake_client.modify_db_parameter_group.assert_called_with(
            DBParameterGroupName='aws_resource_mock_id',
            Parameters=[{'ParameterName': 'aws_target_mock_id'}]
        )

    def test_detach_from(self):
        _source_ctx, _target_ctx, _ctx = self._create_parameter_relationships(
            'test_detach_from'
        )
        current_ctx.set(_ctx)

        parameter_group.detach_from(
            ctx=_ctx, resource_config=None, iface=None
        )
        self.assertEqual(_target_ctx.instance.runtime_properties, {
            'aws_resource_id': 'aws_target_mock_id',
            'resource_id': 'prepare_attach_target'
        })


if __name__ == '__main__':
    unittest.main()

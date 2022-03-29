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
import copy

# Third party imports
from mock import patch, MagicMock

from cloudify.state import current_ctx

# Local imports
from cloudify_aws.dynamodb.resources import table
from cloudify_aws.common.tests.test_base import TestBase, CLIENT_CONFIG
from cloudify_aws.common.tests.test_base import DELETE_RESPONSE
from cloudify_aws.common.tests.test_base import DEFAULT_RUNTIME_PROPERTIES

# Constants
TABLE_TH = ['cloudify.nodes.Root',
            'cloudify.nodes.aws.dynamodb.Table']

NODE_PROPERTIES = {
    'resource_id': 'node_resource_id',
    'use_external_resource': False,
    'resource_config': {},
    'client_config': CLIENT_CONFIG
}

RUNTIME_PROPERTIES_AFTER_CREATE = {
    'aws_resource_id': 'aws_table_name',
    'resource_config': {},
    'aws_resource_arn': 'aws_table_arn'
}


class TestDynamoDBTable(TestBase):

    def setUp(self):
        super(TestDynamoDBTable, self).setUp()

        self.fake_boto, self.fake_client = self.fake_boto_client('dynamodb')

        self.mock_patch = patch('boto3.client', self.fake_boto)
        self.mock_patch.start()

    def tearDown(self):
        self.mock_patch.stop()
        self.fake_boto = None
        self.fake_client = None

        super(TestDynamoDBTable, self).tearDown()

    def test_create_raises_UnknownServiceError(self):
        self._prepare_create_raises_UnknownServiceError(
            type_hierarchy=TABLE_TH,
            type_name='dynamodb',
            type_class=table,
            operation_name='cloudify.interfaces.lifecycle.create'
        )

    def test_create(self):
        _ctx = self.get_mock_ctx(
            'test_create',
            test_properties=NODE_PROPERTIES,
            test_runtime_properties=DEFAULT_RUNTIME_PROPERTIES,
            type_hierarchy=TABLE_TH,
            ctx_operation_name='cloudify.interfaces.lifecycle.create',
        )

        current_ctx.set(_ctx)

        self.fake_client.create_table = MagicMock(return_value={
            'TableDescription': {
                'TableName': 'aws_table_name',
                'TableArn': 'aws_table_arn'
            }
        })

        self.fake_client.describe_table = MagicMock(return_value={
            'Table': {
                'TableStatus': 'ACTIVE'
            }
        })

        table.create(
            ctx=_ctx, resource_config={
                "AttributeDefinitions": [{
                    "AttributeName": "RandomKeyUUID",
                    "AttributeType": "S"
                }],
                "KeySchema": [{
                    "AttributeName": "RandomKeyUUID",
                    "KeyType": "HASH"
                }],
                "ProvisionedThroughput": {
                    "ReadCapacityUnits": "5",
                    "WriteCapacityUnits": "5"
                }
            }, iface=None, params=None
        )

        self.fake_boto.assert_called_with('dynamodb', **CLIENT_CONFIG)

        self.fake_client.create_table.assert_called_with(
            AttributeDefinitions=[{
                'AttributeName': 'RandomKeyUUID', 'AttributeType': 'S'
            }],
            KeySchema=[{
                'KeyType': 'HASH',
                'AttributeName': 'RandomKeyUUID'
            }],
            ProvisionedThroughput={
                'ReadCapacityUnits': '5',
                'WriteCapacityUnits': '5'
            },
            TableName='aws_resource'
        )

        self.fake_client.describe_table.assert_called_with(
            TableName='aws_table_name'
        )

        updated_runtime_prop = copy.deepcopy(RUNTIME_PROPERTIES_AFTER_CREATE)
        updated_runtime_prop['create_response'] = {'TableStatus': 'ACTIVE'}

        # This is just because I'm not interested in the content
        # of remote_configuration right now.
        # If it doesn't exist, this test will fail, and that's good.
        _ctx.instance.runtime_properties.pop('remote_configuration')
        self.assertEqual(_ctx.instance.runtime_properties,
                         updated_runtime_prop)

    def test_delete(self):
        _ctx = self.get_mock_ctx(
            'test_delete',
            test_properties=NODE_PROPERTIES,
            test_runtime_properties=RUNTIME_PROPERTIES_AFTER_CREATE,
            type_hierarchy=TABLE_TH,
            ctx_operation_name='cloudify.interfaces.lifecycle.delete'
        )

        current_ctx.set(_ctx)

        self.fake_client.delete_table = self.mock_return(DELETE_RESPONSE)

        table.delete(ctx=_ctx, resource_config={}, iface=None)

        self.fake_boto.assert_called_with('dynamodb', **CLIENT_CONFIG)

        self.fake_client.delete_table.assert_called_with(
            TableName='aws_table_name'
        )

        self.assertEqual(
            _ctx.instance.runtime_properties,
            {
                '__deleted': True,
            }
        )


if __name__ == '__main__':
    unittest.main()

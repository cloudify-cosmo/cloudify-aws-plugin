########
# Copyright (c) 2016 GigaSpaces Technologies Ltd. All rights reserved
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

from copy import copy
import os

from cosmo_tester.framework.testenv import TestCase
from cloudify.workflows import local
from cloudify_cli import constants as cli_constants

from cloudify_aws.boto3_connection import connection


class DynamoDBTest(TestCase):
    def setUp(self):
        super(DynamoDBTest, self).setUp()

        access_key = self.env.cloudify_config['aws_access_key_id']
        secret_key = self.env.cloudify_config['aws_secret_access_key']

        self.boto3_session = connection(self.env.cloudify_config)

        self.dynamo_client = self.boto3_session.client('dynamodb')
        self.dynamo_resource = self.boto3_session.resource('dynamodb')

        self.ext_inputs = {
            'aws_access_key_id': access_key,
            'aws_secret_access_key': secret_key,
        }

        blueprints_path = os.path.split(os.path.abspath(__file__))[0]
        blueprints_path = os.path.split(blueprints_path)[0]
        self.blueprints_path = os.path.join(
            blueprints_path,
            'resources',
            'dynamodb'
        )

    def test_table(self):
        blueprint = os.path.join(
            self.blueprints_path,
            'table-blueprint.yaml'
        )

        if self.env.install_plugins:
            self.logger.info('installing required plugins')
            self.cfy.install_plugins_locally(
                blueprint_path=blueprint)

        self.logger.info('Creating a new DynamoDB table')

        inputs = copy(self.ext_inputs)

        self.table_env = local.init_env(
            blueprint,
            inputs=inputs,
            name=self._testMethodName,
            ignored_modules=cli_constants.IGNORED_LOCAL_WORKFLOW_MODULES)
        self.table_env.execute(
            'install',
            task_retries=10,
            task_retry_interval=3,
        )

        self.addCleanup(self.cleanup_table)

        outputs = self.table_env.outputs()

        self.assertIn(
                outputs['table_name'],
                [t for t in self.dynamo_client.list_tables()['TableNames']])

        table = self.dynamo_client.describe_table(
                TableName=outputs['table_name'])['Table']

        self.assertEqual(
                [{u'AttributeName': u'name', u'KeyType': u'HASH'}],
                table['KeySchema'])

        table = self.dynamo_resource.Table(outputs['table_name'])

        table.put_item(Item={'name': 'Matt', 'height': 'One million'})
        table.put_item(Item={'name': 'Sandy', 'depth': 'deep'})

        # There is a `table.item_count`, but according to the docs this is
        # updated about every 6 hours.
        self.assertEqual(2, table.scan()['Count'])

    def cleanup_table(self):
        self.table_env.execute(
            'uninstall',
            task_retries=10,
            task_retry_interval=3,
        )

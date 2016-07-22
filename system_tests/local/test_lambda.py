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
import json
import os

from cosmo_tester.framework.testenv import TestCase
from cloudify.workflows import local
from cloudify_cli import constants as cli_constants

from cloudify_aws.boto3_connection import connection


class LambdaTest(TestCase):
    def setUp(self):
        super(LambdaTest, self).setUp()

        access_key = self.env.cloudify_config['aws_access_key_id']
        secret_key = self.env.cloudify_config['aws_secret_access_key']

        self.boto3_session = connection(self.env.cloudify_config)

        self.lambda_client = self.boto3_session.client('lambda')

        self.ext_inputs = {
            'aws_access_key_id': access_key,
            'aws_secret_access_key': secret_key,
        }

        blueprints_path = os.path.split(os.path.abspath(__file__))[0]
        blueprints_path = os.path.split(blueprints_path)[0]
        self.blueprints_path = os.path.join(
            blueprints_path,
            'resources',
            'Lambda'
        )

    def test_echo(self):
        blueprint = os.path.join(
            self.blueprints_path,
            'echo-blueprint.yaml'
        )

        if self.env.install_plugins:
            self.logger.info('installing required plugins')
            self.cfy.install_plugins_locally(
                blueprint_path=blueprint)

        self.logger.info('Creating a lambda function')

        inputs = copy(self.ext_inputs)

        self.echo_env = local.init_env(
            blueprint,
            inputs=inputs,
            name=self._testMethodName,
            ignored_modules=cli_constants.IGNORED_LOCAL_WORKFLOW_MODULES)
        self.echo_env.execute(
            'install',
            task_retries=10,
            task_retry_interval=3,
        )

        outputs = self.echo_env.outputs()

        self.addCleanup(self.cleanup_echo)

        self.assertIn(
                outputs['function_name'],
                [l['FunctionName']
                 for l
                 in self.lambda_client.list_functions()['Functions']])

        execution_output = self.lambda_client.invoke(
            FunctionName=outputs['function_name'],
            Payload=json.dumps({"a": "dictionary"}),
            )['Payload'].read()

        self.assertEqual('{"input": {"a": "dictionary"}}', execution_output)

    def cleanup_echo(self):
        self.echo_env.execute(
            'uninstall',
            task_retries=10,
            task_retry_interval=3,
        )

########
# Copyright (c) 2015 GigaSpaces Technologies Ltd. All rights reserved
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

import os
import time

from cosmo_tester.framework.testenv import TestCase
from cloudify.workflows import local
from cloudify_cli import constants as cli_constants
import requests
from requests.exceptions import ConnectionError


class ECSTest(TestCase):
    def setUp(self):
        super(ECSTest, self).setUp()

        self.access_key = self.env.cloudify_config['aws_access_key_id']
        self.secret_key = self.env.cloudify_config['aws_secret_access_key']

        self.ext_inputs = {
            'aws_access_key_id': self.access_key,
            'aws_secret_access_key': self.secret_key,
            'name_prefix': 'system-tests',
        }

        blueprints_path = os.path.split(os.path.abspath(__file__))[0]
        blueprints_path = os.path.split(blueprints_path)[0]
        self.blueprints_path = os.path.join(
            blueprints_path,
            'resources',
            'ecs'
        )

    def test_basic(self):
        blueprint = os.path.join(
            self.blueprints_path,
            'basic-blueprint.yaml'
        )

        if self.env.install_plugins:
            self.logger.info('installing required plugins')
            self.cfy.install_plugins_locally(
                blueprint_path=blueprint)

        self.logger.info('Deploying ECS test site behind ELB')

        self.basic_env = local.init_env(
            blueprint,
            inputs=self.ext_inputs,
            name=self._testMethodName,
            ignored_modules=cli_constants.IGNORED_LOCAL_WORKFLOW_MODULES)
        self.basic_env.execute(
            'install',
            task_retries=50,
            task_retry_interval=5,
        )

        self.addCleanup(self.cleanup_basic)

        base_url = 'http://' + self.basic_env.outputs()['endpoint']

        attempt = 0
        retries = 50
        retry_interval = 5
        successful = False
        while not successful:
            try:
                testsite = requests.get(base_url)
                assert testsite.status_code == 200
                assert 'Welcome to nginx!' in testsite.text, (
                    'Nginx not visible yet, retrying. Saw {result}'.format(
                        result=testsite.text,
                    )
                )
                successful = True
            except (AssertionError, ConnectionError):
                # ConnectionError occurs when AWS takes its time setting up
                # DNS for the ELB
                # Then we just have to wait for the containers to actually
                # present the website via the load balancer
                if attempt < retries:
                    self.logger.info(
                        'Waiting for nginx to be on load balancer. '
                        'Attempt {attempt}. Retrying in {delay}'.format(
                            attempt=attempt,
                            delay=retry_interval,
                        )
                    )
                    time.sleep(retry_interval)
                    attempt += 1
                else:
                    raise

        self.logger.info('Nginx default page retrieved successfully.')

    def cleanup_basic(self):
        self.basic_env.execute(
            'uninstall',
            task_retries=50,
            task_retry_interval=5,
        )

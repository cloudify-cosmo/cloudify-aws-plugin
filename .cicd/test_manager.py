# #######
# Copyright (c) 2019 Cloudify Platform Ltd. All rights reserved
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

import os
from random import random

from integration_tests.tests.test_cases import PluginsTest

DEVELOPMENT_ROOT = os.environ.get(
    'REPO_BASE',
    os.path.join(os.path.expanduser('~'), 'dev/repos'))
PLUGIN_NAME = 'cloudify-aws-plugin'
TEST_KEY_PATH = '/tmp/foo.rsa'
TEST_PUB_PATH = '/tmp/foo.rsa.pub'


class AWSPluginTestCase(PluginsTest):

    base_path = os.path.dirname(os.path.realpath(__file__))

    @property
    def plugin_root_directory(self):
        return os.path.abspath(os.path.join(self.base_path, '..'))

    @property
    def inputs(self):
        return {
            'aws_region_name': os.getenv('aws_region_name'),
        }

    def create_secrets(self):
        secrets = {
            'agent_key_private': os.getenv('agent_key_private',
                                           open(TEST_KEY_PATH).read()),
            'agent_key_public': os.getenv('agent_key_public',
                                          open(TEST_PUB_PATH).read()),
            'aws_access_key_id': os.getenv('aws_access_key_id'),
            'aws_secret_access_key': os.getenv(
                'aws_secret_access_key',
                'ec2.eu-central-1.amazonaws.com'),
            'aws_region_name': os.getenv('aws_region_name',
                                         'eu-central-1'),
            'aws_availability_zone': os.getenv('aws_availability_zone',
                                               'eu-central-1b'),
            'ec2_region_endpoint': os.getenv('ec2_region_endpoint'),
        }
        self._create_secrets(secrets)

    def upload_plugins(self):
        self.upload_mock_plugin(
            PLUGIN_NAME,
            os.path.join(DEVELOPMENT_ROOT, PLUGIN_NAME))
        self.upload_mock_plugin(
            'cloudify-utilities-plugin',
            os.path.join(DEVELOPMENT_ROOT, 'cloudify-utilities-plugin'))
        self.upload_mock_plugin(
            'cloudify-ansible-plugin',
            os.path.join(DEVELOPMENT_ROOT, 'cloudify-ansible-plugin'))

    def test_blueprints(self):
        self.upload_plugins()
        self.create_secrets()
        self.check_hello_world_blueprint('aws', self.inputs, 400)
        self.check_db_lb_app_blueprint('aws', 800)

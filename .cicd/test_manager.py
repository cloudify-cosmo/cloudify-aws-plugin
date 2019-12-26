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
from integration_tests.tests import utils as test_utils

PLUGIN_NAME = 'cloudify-aws-plugin'

test_id = '{0}{1}'.format(
    os.getenv('CIRCLE_JOB', 'cfy'),
    os.getenv('CIRCLE_BUILD_NUM', str(random())[-4:-1])
)


class AWSPluginTestCase(PluginsTest):

    base_path = os.path.dirname(os.path.realpath(__file__))

    @property
    def plugin_root_directory(self):
        return os.path.abspath(os.path.join(self.base_path, '..'))

    @property
    def inputs(self):
        return {
            'aws_access_key_id': os.getenv('aws_access_key_id'),
            'aws_secret_access_key': os.getenv('aws_secret_access_key'),
            'aws_region_name': os.getenv('aws_region_name'),
        }

    def check_main_blueprint(self):
        blueprint_id = 'aws_blueprint'
        self.addCleanup(self.undeploy_application, blueprint_id)
        dep, ex_id = self.deploy_application(
            test_utils.get_resource(
                os.path.join(
                    self.plugin_root_directory,
                    '.cicd/blueprint.yaml')),
            timeout_seconds=400,
            blueprint_id=blueprint_id,
            deployment_id=blueprint_id,
            inputs=self.inputs)
        self.undeploy_application(dep.id)

    def test_blueprints(self):
        self.upload_mock_plugin(PLUGIN_NAME, self.plugin_root_directory)
        self.check_main_blueprint()

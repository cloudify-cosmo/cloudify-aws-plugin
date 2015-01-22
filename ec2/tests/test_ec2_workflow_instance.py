########
# Copyright (c) 2014 GigaSpaces Technologies Ltd. All rights reserved
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

# Built-in Imports
import os
import testtools

# Third-party Imports
from moto import mock_ec2

# Cloudify Imports
from cloudify.workflows import local

IGNORED_LOCAL_WORKFLOW_MODULES = (
    'worker_installer.tasks',
    'plugin_installer.tasks'
)


class TestWorkflowInstance(testtools.TestCase):

    def setUp(self):
        super(TestWorkflowInstance, self).setUp()
        # build blueprint path
        blueprint_path = os.path.join(os.path.dirname(__file__),
                                      'blueprint', 'blueprint.yaml')

        inputs = {
            'test_security_group_name': 'test_group',
            'test_security_group_desc': 'testing group desc',
            'test_key_name': 'test_key',
            'test_key_path': '~/.ssh',
            'test_ami_image_id': 'ami-e214778a',
            'test_instance_type': 't1.micro'
        }

        # setup local workflow execution environment
        self.env = local.init_env(
            blueprint_path, name=self._testMethodName, inputs=inputs,
            ignored_modules=IGNORED_LOCAL_WORKFLOW_MODULES)

    @testtools.skip
    @mock_ec2
    def test_install_workflow(self):
        """ Tests the install workflow using the built in
            workflows.
        """
        path = os.path.expanduser('~/.ssh')
        file = os.path.join(path, '{0}{1}'.format('test_key', '.pem'))
        if os.path.exists(file):
            os.remove(file)

        # execute install workflow
        self.env.execute('install', task_retries=0)

    @testtools.skip
    def test_uninstall_workflow(self):
        """ Tests the uninstall workflow using the built in
            workflows.
        """

        # execute install workflow
        self.env.execute('uninstall', task_retries=0)

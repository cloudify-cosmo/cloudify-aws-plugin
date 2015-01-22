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

IP_REGEX = '^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$'


class TestWorkflowSG(testtools.TestCase):

    def setUp(self):
        super(TestWorkflowSG, self).setUp()
        # build blueprint path
        blueprint_path = os.path.join(os.path.dirname(__file__),
                                      'blueprint', 'test_sg.yaml')

        inputs = {
            'test_name': 'test_name',
            'test_description': '~/.ssh'
        }

        # setup local workflow execution environment
        self.env = local.init_env(blueprint_path,
                                  name=self._testMethodName,
                                  inputs=inputs)

    @testtools.skip
    @mock_ec2
    def test_install_workflow(self):
        """ This tests the install workflow using Cloudify local workflows
            It creates a security group and ensures that the group exists
            using the boto API call to get security groups by name.
        """

        # execute install workflow
        self.env.execute('install', task_retries=0)

    @testtools.skip
    @mock_ec2
    def test_uninstall_workflow(self):
        """ This tests the uninstall workflow using Cloudify local workflows
            It deletes a security group and ensures that the group does not
            exist using the boto API call to get security groups by name.
        """

        self.env.execute('install', task_retries=0)
        self.env.execute('uninstall', task_retries=0)

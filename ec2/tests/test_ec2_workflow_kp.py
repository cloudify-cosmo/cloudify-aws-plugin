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
import unittest

# Third-party Imports
from moto import mock_ec2

# Cloudify Imports
from ec2 import connection
from cloudify.workflows import local

IP_REGEX = '^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$'


class TestWorkflowKP(unittest.TestCase):

    def setUp(self):
        # build blueprint path
        blueprint_path = os.path.join(os.path.dirname(__file__),
                                      'blueprint', 'test_kp.yaml')

        inputs = {
            'test_kp_name': 'test_name',
            'test_private_key_path': '~/.ssh'
        }

        # setup local workflow execution environment
        self.env = local.init_env(blueprint_path,
                                  name=self._testMethodName,
                                  inputs=inputs)

    @mock_ec2
    def test_install_workflow(self):
        """ This tests the install workflow using Cloudify local workflows
            It creates a key pair and ensures that the keypair exists
            using the boto API call to get keypair by name.
        """
        ec2_client = connection.EC2ConnectionClient().client()

        path = os.path.expanduser('~/.ssh')
        file = os.path.join(path, '{0}{1}'.format('test_name', '.pem'))
        if os.path.exists(file):
            os.remove(file)

        # execute install workflow
        self.env.execute('install', task_retries=0)

        # assert runtime properties is properly set in node instance
        kp = ec2_client.get_key_pair('test_name')
        self.assertEquals(kp.name, 'test_name')
        os.remove(file)

    @mock_ec2
    def test_uninstall_workflow(self):
        """ This tests the uninstall workflow using Cloudify local workflows
            It deletes a key pair and ensures that the keypair does not exist
            using the boto API call to get keypair by name.
        """
        ec2_client = connection.EC2ConnectionClient().client()

        path = os.path.expanduser('~/.ssh')
        file = os.path.join(path, '{0}{1}'.format('test_name', '.pem'))
        if os.path.exists(file):
            os.remove(file)

        self.env.execute('install', task_retries=0)
        self.env.execute('uninstall', task_retries=0)

        kp = ec2_client.get_key_pair('test_name')
        self.assertEquals(None, kp)
        os.remove(file)

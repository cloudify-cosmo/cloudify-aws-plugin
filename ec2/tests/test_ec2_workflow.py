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

# Built-in Imports
import os
import testtools
import tempfile

# Third-party Imports
from moto import mock_ec2
from boto.ec2 import EC2Connection

# Cloudify Imports
from cloudify.workflows import local
import test_utils

IGNORED_LOCAL_WORKFLOW_MODULES = (
    'worker_installer.tasks',
    'plugin_installer.tasks'
)

TEST_KEY_FOLDER = tempfile.mkdtemp()


class TestWorkflowClean(testtools.TestCase):

    def setUp(self):
        super(TestWorkflowClean, self).setUp()
        # build blueprint path
        blueprint_path = os.path.join(os.path.dirname(__file__),
                                      'blueprint', 'blueprint.yaml')

        inputs = {
            'agent_server_name': 'test_instance',
            'image_id': 'ami-e214778a',
            'flavor_id': 't1.micro',
            'use_existing_agent_group': False,
            'agent_security_group_name': 'test_group',
            'use_existing_agent_keypair': False,
            'agent_keypair_name': 'test_key',
            'path_to_key_file': '{0}/test_key.pem'.format(TEST_KEY_FOLDER)

        }

        # setup local workflow execution environment
        self.env = local.init_env(
            blueprint_path, name=self._testMethodName, inputs=inputs,
            ignored_modules=IGNORED_LOCAL_WORKFLOW_MODULES)

    @mock_ec2
    def test_install_workflow(self):
        """ Tests the install workflow using the built in
            workflows.
        """

        # execute install workflow
        self.env.execute('install', task_retries=0)

        self.assertEquals(4, len(test_utils.get_instances(self.env.storage)))

        self.assertIsNotNone(
            test_utils.get_instance_node_id(
                'agent_security_group', self.env.storage))
        self.assertIsNotNone(
            test_utils.get_instance_node_id('agent_keypair', self.env.storage))
        self.assertIsNotNone(
            test_utils.get_instance_node_id('agent_server', self.env.storage))
        self.assertIsNotNone(
            test_utils.get_instance_node_id('agent_ip', self.env.storage))

    @mock_ec2
    def test_uninstall_workflow(self):
        """ Tests the uninstall workflow using the built in
            workflows.
        """

        path = os.path.expanduser(TEST_KEY_FOLDER)
        file = os.path.join(path, '{0}{1}'.format('test_key', '.pem'))
        self.addCleanup(os.remove, file)

        # execute install workflow
        self.env.execute('uninstall', task_retries=0)


class TestWorkflowExternalResources(testtools.TestCase):

    def setUp(self):
        super(TestWorkflowExternalResources, self).setUp()
        # build blueprint path
        blueprint_path = os.path.join(os.path.dirname(__file__),
                                      'blueprint', 'blueprint.yaml')

        inputs = {
            'agent_server_name': 'test_instance',
            'image_id': 'ami-e214778a',
            'flavor_id': 't1.micro',
            'use_existing_agent_group': True,
            'agent_security_group_name': 'test_group2',
            'use_existing_agent_keypair': True,
            'agent_keypair_name': 'test_key2',
            'path_to_key_file': '{0}/test_key2.pem'.format(TEST_KEY_FOLDER)
        }

        # setup local workflow execution environment
        self.env = local.init_env(
            blueprint_path, name=self._testMethodName, inputs=inputs,
            ignored_modules=IGNORED_LOCAL_WORKFLOW_MODULES)

    @mock_ec2
    def test_install_workflow(self):
        """ Tests the install workflow using the built in
            workflows.
        """
        ec2_client = EC2Connection()
        ec2_client.create_security_group('test_group2',
                                         'so hard to describe')

        kp = ec2_client.create_key_pair('test_key2')
        kp.save(TEST_KEY_FOLDER)

        # execute install workflow
        self.env.execute('install', task_retries=0)

    @mock_ec2
    def test_uninstall_workflow(self):
        """ Tests the uninstall workflow using the built in
            workflows.
        """

        def clean_up_keys():
            path = os.path.expanduser(TEST_KEY_FOLDER)
            files = ['test_key', 'test_key2']
            for names in files:
                file = os.path.join(path, '{0}{1}'.format(names, '.pem'))
                if os.path.exists(file):
                    os.remove(file)

        self.addCleanup(clean_up_keys)
        # execute install workflow
        self.env.execute('uninstall', task_retries=0)

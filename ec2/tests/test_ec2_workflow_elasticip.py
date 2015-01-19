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
from boto.exception import EC2ResponseError

# Cloudify Imports
from ec2 import connection
from cloudify.workflows import local

IP_REGEX = '^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$'


class TestWorkflowElasticIP(testtools.TestCase):

    def setUp(self):
        super(TestWorkflowElasticIP, self).setUp()
        # build blueprint path
        blueprint_path = os.path.join(os.path.dirname(__file__),
                                      'blueprint', 'test_elasticip.yaml')

        # setup local workflow execution environment
        self.env = local.init_env(blueprint_path,
                                  name=self._testMethodName)

    @mock_ec2
    def test_install_workflow(self):
        """ Tests the install workflow using the built in
            workflows. Uses the get_all_addresses method from
            boto to make sure that the address exists
        """
        ec2_client = connection.EC2ConnectionClient().client()

        # execute install workflow
        self.env.execute('install', task_retries=0)

        # extract single node instance
        instance = self.env.storage.get_node_instances()[0]
        elasticip = instance.runtime_properties['elasticip']

        # assert runtime properties is properly set in node instance
        self.assertRegexpMatches(elasticip, IP_REGEX)
        ip = ec2_client.get_all_addresses(elasticip)
        self.assertFalse(None, ip)

    @mock_ec2
    def test_uninstall_workflow(self):
        """ Tests the uninstall workflow using the built in
            workflows. Uses the get_all_addresses method from
            boto to make sure that the address no longer exists
        """
        ec2_client = connection.EC2ConnectionClient().client()

        # execute install workflow
        self.env.execute('install', task_retries=0)
        # extract single node instance
        instance = self.env.storage.get_node_instances()[0]
        elasticip = instance.runtime_properties['elasticip']

        # execute uninstall workflow
        self.env.execute('uninstall', task_retries=0)

        # assert runtime properties is properly set in node instance
        ex = self.assertRaises(EC2ResponseError,
                               ec2_client.get_all_addresses, elasticip)
        self.assertIn('InvalidAddress.NotFound', ex.code)

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
from cloudify.workflows import local

IP_REGEX = '^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$'


class TestWorkflowElasticIP(unittest.TestCase):

    def setUp(self):
        # build blueprint path
        blueprint_path = os.path.join(os.path.dirname(__file__),
                                      'blueprint', 'test_elasticip.yaml')

        # setup local workflow execution environment
        self.env = local.init_env(blueprint_path,
                                  name=self._testMethodName)

    @mock_ec2
    def test_elastic_ip(self):

        # execute install workflow
        self.env.execute('install', task_retries=0)

        # extract single node instance
        instance = self.env.storage.get_node_instances()[0]

        # assert runtime properties is properly set in node instance
        self.assertRegexpMatches(instance.runtime_properties['elasticip'],
                                 IP_REGEX)

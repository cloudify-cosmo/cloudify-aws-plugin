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

# Third party Imports
from boto.ec2 import EC2Connection

# Cloudify Imports
from cloudify.workflows import local

IGNORED_LOCAL_WORKFLOW_MODULES = (
    'worker_installer.tasks',
    'plugin_installer.tasks'
)

TEST_AMI = 'ami-3cf8b154'
TEST_SIZE = 'm3.medium'
INSTANCE_TO_IP = 'instance_connected_to_elastic_ip'
INSTANCE_TO_SG = 'instance_connected_to_security_group'
EXTERNAL_RESOURCE_ID = 'aws_resource_id'
SIMPLE_IP = 'simple_elastic_ip'
SIMPLE_SG = 'simple_security_group'
SIMPLE_KP = 'simple_key_pair'
SIMPLE_VM = 'simple_instance'
PAIR_A_IP = 'pair_a_connected_elastic_ip'
PAIR_A_VM = 'pair_a_connected_instance'
PAIR_B_SG = 'pair_b_connected_security_group'
PAIR_B_VM = 'pair_b_connected_instance'


class EC2LocalTestUtils(testtools.TestCase):

    def setUp(self):
        super(EC2LocalTestUtils, self).setUp()
        self._set_up()

    def tearDown(self):
        super(EC2LocalTestUtils, self).tearDown()

    def _set_up(self,
                inputs=None,
                directory='resources',
                filename='blueprint.yaml'):

        blueprint_path = os.path.join(
            os.path.dirname(
                os.path.dirname(__file__)), directory, filename)

        if not inputs:
            inputs = self._get_inputs(TEST_AMI, TEST_SIZE)

        # setup local workflow execution environment
        self.env = local.init_env(
            blueprint_path,
            name=self._testMethodName,
            inputs=inputs,
            ignored_modules=IGNORED_LOCAL_WORKFLOW_MODULES)

    def _get_inputs(self,
                    ami_image_id,
                    instance_type,
                    test_name='vanilla_test'):

        return {
            'image': ami_image_id,
            'size': instance_type,
            'key_path': '~/.ssh/{0}.pem'.format(test_name)
        }

    def _get_instances(self, storage):
        return storage.get_node_instances()

    def _get_instance_node(self, node_name, storage):
        for instance in self._get_instances(storage):
            if node_name in instance.node_id:
                return instance

    def _get_instance_node_id(self, node_name, storage):
        instance_node = self._get_instance_node(node_name, storage)
        return instance_node.node_id

    def _get_ec2_client(self):
        return EC2Connection()

    def _create_security_group(self, ec2_client, name, description):
        new_group = ec2_client.create_security_group(name, description)
        return new_group

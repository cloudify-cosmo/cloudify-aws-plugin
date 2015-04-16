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

# Third party Imports
from boto.ec2 import EC2Connection

# Cloudify Imports
from ec2 import constants
from cloudify.workflows import local
from cloudify.mocks import MockContext
from cloudify.mocks import MockCloudifyContext
from cosmo_tester.framework.testenv import TestCase

IGNORED_LOCAL_WORKFLOW_MODULES = (
    'worker_installer.tasks',
    'plugin_installer.tasks'
)

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


class EC2LocalTestUtils(TestCase):

    def setUp(self):
        super(EC2LocalTestUtils, self).setUp()
        self._set_up()

    def tearDown(self):
        super(EC2LocalTestUtils, self).tearDown()

    def _set_up(self,
                inputs=None,
                directory='resources',
                filename='simple-blueprint.yaml'):

        blueprint_path = os.path.join(
            os.path.dirname(
                os.path.dirname(__file__)), directory, filename)

        if not inputs:
            inputs = self._get_inputs()

        # setup local workflow execution environment
        self.localenv = local.init_env(
            blueprint_path,
            name=self._testMethodName,
            inputs=inputs,
            ignored_modules=IGNORED_LOCAL_WORKFLOW_MODULES)

    def _get_inputs(self,
                    resource_id_ip='', resource_id_kp='',
                    resource_id_sg='', resource_id_vm='',
                    external_ip=False, external_kp=False,
                    external_sg=False, external_vm=False,
                    test_name='vanilla_test'):

        return {
            'image': self.env.ubuntu_trusty_image_id,
            'size': self.env.medium_instance_type,
            'key_path': '~/.ssh/{0}.pem'.format(test_name),
            'resource_id_ip': resource_id_ip,
            'resource_id_kp': resource_id_kp,
            'resource_id_sg': resource_id_sg,
            'resource_id_vm': resource_id_vm,
            'external_ip': external_ip,
            'external_kp': external_kp,
            'external_sg': external_sg,
            'external_vm': external_vm
        }

    def mock_cloudify_context(self, test_name, external_vm=False,
                              resource_id_vm='', resource_id_sg='',
                              resource_id_kp=''):
        """ Creates a mock context for the instance
            tests
        """

        test_node_id = test_name
        test_properties = {
            constants.AWS_CONFIG_PROPERTY: {},
            'use_external_resource': external_vm,
            'resource_id': resource_id_vm,
            'image_id': self.env.ubuntu_trusty_image_id,
            'instance_type': self.env.medium_instance_type,
            'cloudify_agent': {},
            'parameters': {
                'security_group_ids': [resource_id_sg],
                'key_name': resource_id_kp
            }
        }

        operation = {
            'retry_number': 0
        }

        ctx = MockCloudifyContext(
            node_id=test_node_id,
            properties=test_properties,
            operation=operation
        )

        ctx.instance.relationships = \
            [self.mock_relationship_context(test_name)]

        return ctx

    def mock_relationship_context(self, testname):

        instance_context = MockContext({
            'node': MockContext({
                'properties': {
                    constants.AWS_CONFIG_PROPERTY: {},
                    'use_external_resource': False,
                    'resource_id': ''
                }
            }),
            'instance': MockContext({
                'runtime_properties': {
                    'aws_resource_id': 'i-abc1234',
                    'public_ip_address': '127.0.0.1'
                }
            })
        })

        elasticip_context = MockContext({
            'node': MockContext({
                'properties': {
                    constants.AWS_CONFIG_PROPERTY: {},
                    'use_external_resource': False,
                    'resource_id': '',
                }
            }),
            'instance': MockContext({
                'runtime_properties': {
                    'aws_resource_id': ''
                }
            })
        })

        relationship_context = MockCloudifyContext(
            node_id=testname, source=instance_context,
            target=elasticip_context)

        return relationship_context

    def _get_instances(self, storage):
        return storage.get_node_instances()

    def _get_instance_node(self, node_name, storage):
        for instance in self._get_instances(storage):
            if node_name in instance.node_id:
                return instance

    def _get_instance_node_id(self, node_name, storage):
        instance_node = self._get_instance_node(node_name, storage)
        return instance_node.node_id

    def _get_aws_config(self):

        return {
            'aws_access_key_id': self.env.aws_access_key_id,
            'aws_secret_access_key': self.env.aws_secret_access_key
        }

    def _get_ec2_client(self):
        aws_config = self._get_aws_config()
        return EC2Connection(**aws_config)

    def _create_elastic_ip(self, ec2_client):
        new_address = ec2_client.allocate_address(domain=None)
        return new_address

    def _create_key_pair(self, ec2_client, name):
        new_key_pair = ec2_client.create_key_pair(name)
        new_key_pair.save(os.path.expanduser('~/.ssh'))
        return new_key_pair

    def _create_security_group(self, ec2_client, name, description):
        new_group = ec2_client.create_security_group(name, description)
        return new_group

    def _create_instance(self, ec2_client):
        new_reservation = ec2_client.run_instances(
            image_id=self.env.ubuntu_trusty_image_id,
            instance_type=self.env.medium_instance_type)
        return new_reservation.instances[0]

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
import tempfile

# Third party Imports
from boto.ec2 import get_region
from boto.ec2 import EC2Connection
from boto.ec2.elb import connect_to_region as connect_to_elb_region

# Cloudify Imports
from ec2 import constants
from cloudify.workflows import local
from cloudify.mocks import MockContext
from cloudify.mocks import MockCloudifyContext
from cosmo_tester.framework.testenv import TestCase

IGNORED_LOCAL_WORKFLOW_MODULES = (
    'worker_installer.tasks',
    'plugin_installer.tasks',
    'cloudify_agent.operations',
    'cloudify_agent.installer.operations',
)

INSTANCE_TO_IP = 'instance_connected_to_elastic_ip'
INSTANCE_TO_SG = 'instance_connected_to_security_group'
EXTERNAL_RESOURCE_ID = 'aws_resource_id'
SIMPLE_IP = 'simple_elastic_ip'
SIMPLE_SG = 'simple_security_group'
SIMPLE_KP = 'simple_key_pair'
SIMPLE_VM = 'simple_instance'
SIMPLE_LB = 'simple_load_balancer'
SIMPLE_VOL = 'simple_volume'
PAIR_A_IP = 'pair_a_connected_elastic_ip'
PAIR_A_VM = 'pair_a_connected_instance'
PAIR_B_SG = 'pair_b_connected_security_group'
PAIR_B_VM = 'pair_b_connected_instance'
PAIR_C_LB = 'pair_c_connected_elb'
DEFAULT_LISTENER = [[80, 8080, 'http']]
DEFAULT_EXTERNAL_ELB_NAME = 'myelb'
DEFAULT_ZONES = ['us-east-1b']
DEFAULT_HEALTH_CHECK = [{'target': 'HTTP:8080/health'}]
PAIR_C_VOL = 'pair_c_connected_volume'
PAIR_C_VM = 'pair_c_connected_instance'
TEST_SIZE = 2
TEST_DEVICE = '/dev/xvdf'


class EC2LocalTestUtils(TestCase):
    def setUp(self):
        super(EC2LocalTestUtils, self).setUp()
        self._set_up()

    def tearDown(self):
        super(EC2LocalTestUtils, self).tearDown()

    def _set_up(self,
                inputs=None,
                directory='manager/resources',
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
                    resource_id_vol='', external_vol=False,
                    test_name='vanilla_test'):

        private_key_path = tempfile.mkdtemp()

        return {
            'image': self.env.ubuntu_trusty_image_id,
            'size': self.env.micro_instance_type,
            'key_path': '{0}/{1}.pem'.format(
                private_key_path,
                test_name),
            'vol_size': TEST_SIZE,
            'vol_zone': self.env.availability_zone,
            'vol_device': TEST_DEVICE,
            'resource_id_ip': resource_id_ip,
            'resource_id_kp': resource_id_kp,
            'resource_id_sg': resource_id_sg,
            'resource_id_vm': resource_id_vm,
            'resource_id_vol': resource_id_vol,
            'external_ip': external_ip,
            'external_kp': external_kp,
            'external_sg': external_sg,
            'external_vm': external_vm,
            'elb_name': DEFAULT_EXTERNAL_ELB_NAME,
            'zones': [self.env.availability_zone],
            'listeners': DEFAULT_LISTENER,
            'health_checks': DEFAULT_HEALTH_CHECK,
            'external_vol': external_vol,
            constants.AWS_CONFIG_PROPERTY:
                self._get_aws_config()
        }

    def mock_cloudify_context(self, test_name,
                              external_vm=False,
                              resource_id_vm='',
                              resource_id_sg='',
                              resource_id_kp=''):
        """ Creates a mock context for the instance
            tests
        """

        test_node_id = test_name
        test_properties = {
            constants.AWS_CONFIG_PROPERTY:
                self._get_aws_config(),
            'use_external_resource': external_vm,
            'resource_id': resource_id_vm,
            'image_id': self.env.ubuntu_trusty_image_id,
            'instance_type': self.env.micro_instance_type,
            'cloudify_agent': {},
            'parameters': {'security_group_ids': [resource_id_sg],
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

        if 'volume' in test_node_id:
            ctx.instance.relationships = \
                [self.mock_volume_relationship_context(test_name)]
        else:
            ctx.instance.relationships = \
                [self.mock_relationship_context(test_name)]

        return ctx

    def mock_relationship_context(self, testname):

        instance_context = MockContext({
            'node': MockContext({
                'properties': {
                    constants.AWS_CONFIG_PROPERTY:
                        self._get_aws_config(),
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
                    constants.AWS_CONFIG_PROPERTY:
                        self._get_aws_config(),
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

    def mock_elb_relationship_context(self, testname):
        instance_context = MockContext({
            'node': MockContext({
                'properties': {
                    constants.AWS_CONFIG_PROPERTY:
                        self._get_aws_config(),
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

        elb_context = MockContext({
            'node': MockContext({
                'properties': {
                    constants.AWS_CONFIG_PROPERTY:
                        self._get_aws_config(),
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
            target=elb_context)

        return relationship_context

    def mock_volume_relationship_context(self, testname):

        instance_context = MockContext({
            'node': MockContext({
                'properties': {
                    constants.AWS_CONFIG_PROPERTY:
                        self._get_aws_config(),
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

        volume_context = MockContext({
            'node': MockContext({
                'properties': {
                    constants.AWS_CONFIG_PROPERTY:
                        self._get_aws_config(),
                    'use_external_resource': False,
                    'resource_id': '',
                    'zone': self.env.availability_zone,
                    'size': TEST_SIZE,
                    'device': TEST_DEVICE,
                }
            }),
            'instance': MockContext({
                'runtime_properties': {
                    'aws_resource_id': ''
                }
            })
        })

        relationship_context = MockCloudifyContext(
            node_id=testname, source=volume_context,
            target=instance_context)

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
            'aws_secret_access_key': self.env.aws_secret_access_key,
            'ec2_region_name': self.env.ec2_region_name,
            'elb_region_name': self.env.ec2_region_name
        }

    def _get_ec2_client(self):
        aws_config = self._get_aws_config()
        aws_config.pop('ec2_region_name')
        aws_config.pop('elb_region_name')
        aws_config['region'] = get_region(self.env.ec2_region_name)
        return EC2Connection(**aws_config)

    def _get_elb_client(self):
        aws_config = self._get_aws_config()
        aws_config.pop('ec2_region_name')
        aws_config.pop('elb_region_name')
        elb_region = self.env.ec2_region_name
        return connect_to_elb_region(elb_region, **aws_config)

    def _create_elastic_ip(self, ec2_client):
        new_address = ec2_client.allocate_address(domain=None)
        return new_address

    def _create_key_pair(self, ec2_client, name):
        private_key_path = tempfile.mkdtemp()
        new_key_pair = ec2_client.create_key_pair(name)
        new_key_pair.save(private_key_path)
        return new_key_pair

    def _create_security_group(self, ec2_client, name, description):
        new_group = ec2_client.create_security_group(name, description)
        return new_group

    def _create_instance(self, ec2_client):
        new_reservation = ec2_client.run_instances(
            image_id=self.env.ubuntu_trusty_image_id,
            instance_type=self.env.micro_instance_type)
        return new_reservation.instances[0]

    def _create_volume(self, ec2_client,
                       size=TEST_SIZE,
                       zone=None):
        if not zone:
            zone = self.env.availability_zone
        new_volume = ec2_client.create_volume(size, zone)
        return new_volume

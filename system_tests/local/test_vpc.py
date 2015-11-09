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

# Built in Imports
from copy import deepcopy
from time import sleep

# Third Party Imports
from fabric import api as fabric_api

# Cloudify Imports
from vpc import constants
from .vpc_test_utils import TestVpcBase
from cloudify.workflows import local

IGNORED_LOCAL_WORKFLOW_MODULES = (
    'worker_installer.tasks',
    'plugin_installer.tasks',
    'cloudify_agent.operations',
    'cloudify_agent.installer.operations',
)

EC2_RESOURCES = [
    'cloudify.aws.nodes.SecurityGroup',
    'cloudify.aws.nodes.KeyPair',
    'cloudify.aws.nodes.ElasticIP',
    'cloudify.aws.nodes.Instance'
]


class TestVpc(TestVpcBase):

    def test_install_workflow(self):
        vpc_client = self.vpc_client()
        dumb_vpc = vpc_client.create_vpc('11.0.0.0/16')
        self.addCleanup(vpc_client.delete_vpc, dumb_vpc.id)
        override_inputs = dict(
            vpc_id=dumb_vpc.id,
            vpc_two_create_new_resource=True
        )
        cfy_local = local.init_env(
            self.get_blueprint_path(),
            name='test_install_workflow',
            inputs=self.get_inputs(override_inputs=override_inputs),
            ignored_modules=IGNORED_LOCAL_WORKFLOW_MODULES)
        cfy_local.execute('install', task_retries=10)
        self.addCleanup(cfy_local.execute, 'uninstall', task_retries=10)
        node_instances = cfy_local.storage.get_node_instances()
        current_resources = self.get_current_list_of_used_resources(vpc_client)
        for node_instance in node_instances:
            node = cfy_local.storage.get_node(node_instance.node_id)
            if node.type in EC2_RESOURCES:
                continue
            actual_resource_id = \
                node_instance.runtime_properties['aws_resource_id']
            expected_resource_ids = \
                [resource.id for resource in current_resources[node.type]]
            self.assertIn(actual_resource_id, expected_resource_ids)

        cloudify_aws_vpc = \
            cfy_local.storage.get_node_instances(node_id='vpc_one')
        cloudify_aws_vpc_id = \
            cloudify_aws_vpc[0].runtime_properties['aws_resource_id']
        vpc = self.vpc_client().get_all_vpcs(vpc_ids=[cloudify_aws_vpc_id])
        cloudify_aws_dhcp = \
            cfy_local.storage.get_node_instances(
                node_id='dhcp_options_one')
        cloudify_aws_dhcp_options_id = \
            cloudify_aws_dhcp[0].runtime_properties['aws_resource_id']
        dhcp_options_sets = \
            self.vpc_client().get_all_dhcp_options(
                dhcp_options_ids=[cloudify_aws_dhcp_options_id])

        self.assertIn(vpc[0].dhcp_options_id, dhcp_options_sets[0].id)
        self.assertIn('10.0.0.0/16', vpc[0].cidr_block)

        key_node = cfy_local.storage.get_node('key_one')
        elastic_ip_node = \
            cfy_local.storage.get_node_instances(node_id='elastic_ip_one')
        ec2_instance_two = \
            cfy_local.storage.get_node_instances(node_id='ec2_instance_two')
        connection = dict(
            user='ubuntu',
            key_filename=key_node.properties['private_key_path'],
            host_string=elastic_ip_node[0].runtime_properties[
                'aws_resource_id'],
            connection_attempts=10,
            command_timeout=30
        )

        with fabric_api.settings(**connection):
            instance_one_assertion = fabric_api.run('uname -a')

        try:
            with fabric_api.settings(**connection):
                fabric_api.put(
                    key_node.properties['private_key_path'],
                    '~/.ssh/key.pem'
                )
                fabric_api.run('chmod 600 ~/.ssh/key.pem')
                instance_two_assertion = \
                    fabric_api.run(
                        'ssh -o "StrictHostKeyChecking no" '
                        '-i ~/.ssh/key.pem ubuntu@{0} /bin/uname -a'
                        .format(ec2_instance_two[0].runtime_properties['ip']))
        except SystemExit:
            sleep(10)
            with fabric_api.settings(**connection):
                fabric_api.put(
                    key_node.properties['private_key_path'],
                    '~/.ssh/key.pem'
                )
                fabric_api.run('chmod 600 ~/.ssh/key.pem')
                instance_two_assertion = \
                    fabric_api.run(
                        'ssh -o "StrictHostKeyChecking no" '
                        '-i ~/.ssh/key.pem ubuntu@{0} /bin/uname -a'
                        .format(ec2_instance_two[0].runtime_properties['ip']))

        self.assertIn('Ubuntu', instance_one_assertion)
        self.assertIn('Ubuntu', instance_two_assertion)

    def test_uninstall_workflow(self):
        cfy_local = local.init_env(
            self.get_blueprint_path(),
            name='test_uninstall_workflow',
            inputs=self.get_inputs(),
            ignored_modules=IGNORED_LOCAL_WORKFLOW_MODULES)
        cfy_local.execute('install', task_retries=10)
        node_instances = cfy_local.storage.get_node_instances()
        copy_node_instances = deepcopy(node_instances)
        cfy_local.execute('uninstall', task_retries=10)
        vpc_client = self.vpc_client()
        current_resources = self.get_current_list_of_used_resources(vpc_client)
        for node_instance in copy_node_instances:
            node = cfy_local.storage.get_node(node_instance.node_id)
            if node.type in EC2_RESOURCES:
                continue
            actual_resource_id = \
                node_instance.runtime_properties['aws_resource_id']
            expected_resource_ids = \
                [resource.id for resource in current_resources[node.type]]
            if node.type in constants.CUSTOMER_GATEWAY['CLOUDIFY_NODE_TYPE']:
                customer_gateway = \
                    vpc_client.get_all_customer_gateways(
                        customer_gateway_ids=actual_resource_id)
                self.assertIn(customer_gateway[0].state,
                              ['detached', 'deleted'])
            elif node.type in constants.VPN_GATEWAY['CLOUDIFY_NODE_TYPE']:
                vpn_gateway = vpc_client.get_all_vpn_gateways(
                    vpn_gateway_ids=actual_resource_id)
                self.assertIn(vpn_gateway[0].state, ['detached', 'deleted'])
            else:
                self.assertNotIn(actual_resource_id, expected_resource_ids)

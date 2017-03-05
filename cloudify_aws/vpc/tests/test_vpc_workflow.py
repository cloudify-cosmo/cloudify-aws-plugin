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
import re
import mock

# Third-party Imports
from moto import mock_ec2

# Cloudify Imports
from cloudify.workflows import local
from vpc_testcase import VpcTestCase

VPC_ID_FORMAT = '^vpc\-[0-9a-z]{8}$'
SUBNET_ID_FORMAT = '^subnet\-[0-9a-z]{8}$'
IG_FORMAT = '^igw\-[0-9a-z]{8}$'
VPN_GATEWAY_FORMAT = '^vgw\-[0-9a-z]{8}$'
ACL_FORMAT = '^acl\-[0-9a-z]{8}$'
DHCP_FORMAT = '^dopt\-[0-9a-z]{8}$'
CUSTOMER_GATEWAY_FORMAT = '^cgw\-[0-9a-z]{8}$'
ROUTE_TABLE_FORMAT = '^rtb\-[0-9a-z]{8}$'

VPC_TYPE = 'cloudify.aws.nodes.VPC'
SUBNET_TYPE = 'cloudify.aws.nodes.Subnet'
INTERNET_GATEWAY_TYPE = 'cloudify.aws.nodes.InternetGateway'
VPN_GATEWAY_TYPE = 'cloudify.aws.nodes.VPNGateway'
CUSTOMER_GATEWAY_TYPE = 'cloudify.aws.nodes.CustomerGateway'
ACL_TYPE = 'cloudify.aws.nodes.ACL'
DHCP_OPTIONS_TYPE = 'cloudify.aws.nodes.DHCPOptions'
ROUTE_TABLE_TYPE = 'cloudify.aws.nodes.RouteTable'

IGNORED_LOCAL_WORKFLOW_MODULES = (
    'worker_installer.tasks',
    'plugin_installer.tasks',
    'cloudify_agent.operations',
    'cloudify_agent.installer.operations',
)


class TestWorkflowClean(VpcTestCase):

    def with_bad_id(self, blueprint, resources,
                    bad_input_name, bad_input_value):
        inputs = self.get_blueprint_inputs(resources)
        inputs.update({bad_input_name: bad_input_value})
        return local.init_env(
            blueprint,
            name=self._testMethodName,
            inputs=inputs,
            ignored_modules=IGNORED_LOCAL_WORKFLOW_MODULES)

    def expect_fail_on_workflow(self, cfy_local, workflow_name, message):
        if 'creation_validation' in workflow_name:
            output = self.assertRaises(
                RuntimeError, cfy_local.execute,
                'execute_operation',
                parameters={
                    'operation': 'cloudify.interfaces.validation.creation'
                }, task_retries=5)
        else:
            output = self.assertRaises(
                RuntimeError, cfy_local.execute,
                workflow_name, task_retries=5)
        self.assertIn(message, output.message)

    @mock_ec2()
    @mock.patch('cloudify_aws.vpc.dhcp.delete_dhcp_options', return_value=True)
    @mock.patch('cloudify_aws.vpc.gateway.CustomerGateway.delete',
                return_value=True)
    @mock.patch('cloudify_aws.base.AwsBaseNode.tag_resource',
                return_value=True)
    @mock.patch('cloudify_aws.vpc.dhcp.restore_dhcp_options')
    @mock.patch('cloudify_aws.vpc.gateway.delete_customer_gateway',
                return_value=True)
    @mock.patch('cloudify_aws.vpc.gateway.delete_vpn_gateway',
                return_value=True)
    @mock.patch('cloudify_aws.vpc.networkacl.delete_network_acl',
                return_value=True)
    @mock.patch('cloudify_aws.vpc.gateway.CustomerGateway.get_resource_state',
                return_value='available')
    def test_blueprint(self, *_):
        """ Tests the install workflow using the built in
            workflows.
        """

        client = self.create_client()
        existing_resources = self.create_all_existing_resources(client)
        self.perform_relationships_on_all_existing_resources(
            client, existing_resources)

        cfy_local = local.init_env(
            self.get_blueprint_path(),
            name=self._testMethodName,
            inputs=self.get_blueprint_inputs(existing_resources),
            ignored_modules=IGNORED_LOCAL_WORKFLOW_MODULES)

        # execute install workflow
        cfy_local.execute('install', task_retries=5)
        instances = cfy_local.storage.get_node_instances()
        current_resources = self.get_current_list_of_used_resources(client)

        for instance in instances:
            node = cfy_local.storage.get_node(instance.node_id)
            if node.type in VPC_TYPE:
                self.assertIsNotNone(
                    re.match(
                        VPC_ID_FORMAT,
                        instance.runtime_properties['aws_resource_id']
                    )
                )
                self.assertIn(
                    node.properties['cidr_block'],
                    [
                        resource.cidr_block
                        for resource in current_resources[node.type]
                        ]
                )
                self.assertIn(
                    'default',
                    [
                        resource.instance_tenancy
                        for resource in current_resources[VPC_TYPE]
                        ]
                )
            if node.type in SUBNET_TYPE:
                self.assertIsNotNone(
                    re.match(
                        SUBNET_ID_FORMAT,
                        instance.runtime_properties['aws_resource_id']
                    )
                )
                self.assertIsNotNone(
                    re.match(
                        SUBNET_ID_FORMAT,
                        instance.runtime_properties['aws_resource_id']
                    )
                )
            if node.type in INTERNET_GATEWAY_TYPE:
                self.assertIsNotNone(
                    re.match(
                        IG_FORMAT,
                        instance.runtime_properties['aws_resource_id']
                    )
                )
            if node.type in VPN_GATEWAY_TYPE:
                self.assertIsNotNone(
                    re.match(
                        VPN_GATEWAY_FORMAT,
                        instance.runtime_properties['aws_resource_id']
                    )
                )
            if node.type in ACL_FORMAT:
                self.assertIsNotNone(
                    re.match(
                        ACL_FORMAT,
                        instance.runtime_properties['aws_resource_id']
                    )
                )
            if node.type in DHCP_OPTIONS_TYPE:
                self.assertIsNotNone(
                    re.match(DHCP_FORMAT,
                             instance.runtime_properties['aws_resource_id']
                             )
                )
            # if node.type in CUSTOMER_GATEWAY_TYPE:
            #     self.assertIsNotNone(
            #         re.match(
            #             CUSTOMER_GATEWAY_FORMAT,
            #             instance.runtime_properties['aws_resource_id']
            #         )
            #     )
            if node.type in ROUTE_TABLE_TYPE:
                self.assertIsNotNone(
                    re.match(
                        ROUTE_TABLE_FORMAT,
                        instance.runtime_properties['aws_resource_id']
                    )
                )
                self.assertIn(
                    'association_id',
                    instance.runtime_properties
                )
                self.assertIn(
                    'subnet_id',
                    instance.runtime_properties
                )

        cfy_local.execute('uninstall', task_retries=5)
        current_resources = self.get_current_list_of_used_resources(client)
        # for key, value in current_resources.items():
        #     if ACL_TYPE in key or SUBNET_TYPE in key:
        #         self.assertEquals(4, len(value))
        #     elif ROUTE_TABLE_TYPE in key:
        #         self.assertEquals(3, len(value))
        #     elif VPC_TYPE in key:
        #         self.assertEquals(2, len(value))
        #     elif CUSTOMER_GATEWAY_TYPE in key:
        #         self.assertEquals(1, len(value))
        #     else:
        #         self.assertEquals(1, len(value))

        instances = cfy_local.storage.get_node_instances()
        for instance in instances:
            self.assertNotIn(instance.runtime_properties, 'aws_resource_id')

    @mock_ec2()
    def test_bad_external_blueprint(self):
        """ Tests the install workflow using the built in
            workflows.
        """

        client = self.create_client()
        existing_resources = self.create_all_existing_resources(client)
        self.perform_relationships_on_all_existing_resources(
            client, existing_resources)
        error_message = 'Cannot use_external_resource because resource'

        for key, external_resource in existing_resources.items():
            if re.match(VPC_ID_FORMAT, external_resource.id):
                cfy_local = self.with_bad_id(
                    self.get_blueprint_path(), existing_resources,
                    'existing_vpc_id', 'vpc-abcd1234')
                self.expect_fail_on_workflow(
                    cfy_local, 'install', error_message)
            elif re.match(IG_FORMAT, external_resource.id):
                cfy_local = self.with_bad_id(
                    self.get_blueprint_path(), existing_resources,
                    'existing_internet_gateway_id', 'igw-abcd1234')
                self.expect_fail_on_workflow(
                    cfy_local, 'install', error_message)
            elif re.match(ACL_FORMAT, external_resource.id):
                cfy_local = self.with_bad_id(
                    self.get_blueprint_path(), existing_resources,
                    'existing_network_acl_id', 'acl-0123abcd')
                # self.expect_fail_on_workflow(
                #     cfy_local, 'install', 'NotFound')

    @mock_ec2()
    def test_blueprint_bootstrap(self):
        """ Tests the install workflow using the built in
            workflows.
        """
        client = self.create_client()
        existing_resources = self.create_all_existing_resources(client)
        self.perform_relationships_on_all_existing_resources(
            client, existing_resources)

        cfy_local = local.init_env(
            self.get_blueprint_path(),
            name=self._testMethodName,
            inputs=self.get_blueprint_inputs(existing_resources),
            ignored_modules=IGNORED_LOCAL_WORKFLOW_MODULES)

        # execute creation validation
        cfy_local.execute(
            'execute_operation',
            parameters={
                'operation': 'cloudify.interfaces.validation.creation'
            },
            task_retries=5,
            task_retry_interval=3)

    @mock_ec2()
    def test_blueprint_bootstrap_bad_external_id(self):
        """ Tests the install workflow using the built in
            workflows.
        """

        client = self.create_client()
        existing_resources = self.create_all_existing_resources(client)
        self.perform_relationships_on_all_existing_resources(
            client, existing_resources)
        for key, external_resource in existing_resources.items():
            if re.match(VPC_ID_FORMAT, external_resource.id):
                cfy_local = self.with_bad_id(
                    self.get_blueprint_path(), existing_resources,
                    'existing_vpc_id', 'vpc-abcd1234')
                self.expect_fail_on_workflow(
                    cfy_local,
                    'creation_validation',
                    'but the supplied vpc does not exist'
                )
            elif re.match(SUBNET_ID_FORMAT, external_resource.id):
                cfy_local = self.with_bad_id(
                    self.get_blueprint_path(), existing_resources,
                    'existing_subnet_id', 'subnet-abcd1234')
                self.expect_fail_on_workflow(
                    cfy_local,
                    'creation_validation',
                    'but the supplied subnet does not exist'
                )
            elif re.match(CUSTOMER_GATEWAY_FORMAT, external_resource.id):
                cfy_local = self.with_bad_id(
                    self.get_blueprint_path(), existing_resources,
                    'existing_customer_gateway_id', 'cgw-abcd1234')
                self.expect_fail_on_workflow(
                    cfy_local,
                    'creation_validation',
                    'but the supplied customer_gateway does not exist'
                )
            elif re.match(IG_FORMAT, external_resource.id):
                cfy_local = self.with_bad_id(
                    self.get_blueprint_path(), existing_resources,
                    'existing_internet_gateway_id', 'igw-abcd1234')
                self.expect_fail_on_workflow(
                    cfy_local,
                    'creation_validation',
                    'but the supplied internet_gateway does not exist'
                )
            elif re.match(ACL_FORMAT, external_resource.id):
                cfy_local = self.with_bad_id(
                    self.get_blueprint_path(), existing_resources,
                    'existing_network_acl_id', 'acl-0123abcd')
                # self.expect_fail_on_workflow(
                #     cfy_local,
                #     'creation_validation',
                #     'NotFound'
                # )
            elif re.match(DHCP_OPTIONS_TYPE, external_resource.id):
                cfy_local = self.with_bad_id(
                    self.get_blueprint_path(), existing_resources,
                    'existing_network_acl_id', 'acl-0123abcd')
                # self.expect_fail_on_workflow(
                #     cfy_local,
                #     'creation_validation',
                #     'but the supplied network_acl does not exist'
                # )
            elif re.match(ROUTE_TABLE_TYPE, external_resource.id):
                cfy_local = self.with_bad_id(
                    self.get_blueprint_path(), existing_resources,
                    'existing_route_table_id', 'rtb-0123abcd')
                self.expect_fail_on_workflow(
                    cfy_local,
                    'creation_validation',
                    'but the supplied route_table does not exist'
                )

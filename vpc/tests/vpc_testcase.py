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

# Third-party Imports
from boto.vpc import VPCConnection
from vpc import constants
from cloudify.mocks import MockCloudifyContext

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


class VpcTestCase(testtools.TestCase):

    def setUp(self):
        super(VpcTestCase, self).setUp()

    def tearDown(self):
        super(VpcTestCase, self).tearDown()

    def get_blueprint_path(self):

        if 'vpc' not in os.getcwd():
            blueprint_path = os.path.join(
                'vpc/tests/blueprint', 'blueprint.yaml')
        else:
            blueprint_path = os.path.join('blueprint', 'blueprint.yaml')

        return blueprint_path

    def get_blueprint_inputs(self, resources):

        inputs = {
            'existing_vpc_id':
                resources[VPC_TYPE].id,
            'existing_subnet_id':
                resources[SUBNET_TYPE].id,
            'existing_internet_gateway_id':
                resources[INTERNET_GATEWAY_TYPE].id,
            'existing_vpn_gateway_id':
                resources[VPN_GATEWAY_TYPE].id,
            'existing_network_acl_id':
                resources[ACL_TYPE].id,
            'existing_dhcp_options_id':
                resources[DHCP_OPTIONS_TYPE].id,
            'existing_customer_gateway_id':
                resources[CUSTOMER_GATEWAY_TYPE].id,
            'existing_route_table_id':
                resources[ROUTE_TABLE_TYPE].id
        }
        return inputs

    def create_client(self):
        return VPCConnection()

    def create_vpc(self, vpc_client, args=None):
        args = dict(cidr_block='11.0.0.0/24') if not args else args
        vpc = vpc_client.create_vpc(**args)
        return vpc

    def create_subnet(self, vpc_client, vpc, args=None):
        actual_args = dict(vpc_id=vpc.id, cidr_block='11.0.0.0/25')
        if args:
            actual_args.update(args)
        subnet = vpc_client.create_subnet(**actual_args)
        return subnet

    def create_internet_gateway(self, vpc_client):
        internet_gateway = vpc_client.create_internet_gateway()
        return internet_gateway

    def create_vpn_gateway(self, vpc_client, args=None):
        args = dict(type='ipsec.1') if not args else args
        vpn_gateway = vpc_client.create_vpn_gateway(**args)
        return vpn_gateway

    def create_network_acl(self, vpc_client, vpc, args=None):
        actual_args = dict(vpc_id=vpc.id)
        if args:
            actual_args.update(args)
        network_acl = vpc_client.create_network_acl(**actual_args)
        return network_acl

    def create_dhcp_options(self, vpc_client, args=None):
        if not args:
            args = dict(
                netbios_name_servers=['biosserver-b.com', 'biosserver-a.com'],
                netbios_node_type=2
            )
        dhcp_options = vpc_client.create_dhcp_options(**args)
        return dhcp_options

    def create_customer_gateway(self, vpc_client, args=None):
        args = dict(
            type='ipsec.1', ip_address='11.0.0.7', bgp_asn=65000
        ) if not args else args
        customer_gateway = vpc_client.create_customer_gateway(**args)
        return customer_gateway

    def create_route_table(self, vpc_client, existing_vpc):
        args = dict(vpc_id=existing_vpc.id)
        return vpc_client.create_route_table(**args)

    def gateway_connected_to_vpc(self, vpc_client, source, target):

        if source.get(INTERNET_GATEWAY_TYPE):
            return vpc_client.attach_internet_gateway(
                source.get(INTERNET_GATEWAY_TYPE).id, target.id)
        elif source.get(VPN_GATEWAY_TYPE):
            return vpc_client.attach_vpn_gateway(
                source.get(VPN_GATEWAY_TYPE).id, target.id)

    def customer_gateway_connected_to_vpn_gateway(self,
                                                  vpc_client,
                                                  source,
                                                  target):
        return vpc_client.create_vpn_connection(
            'ipsec.1', source.id, target.id)

    def network_acl_associated_with_subnet(self, vpc_client, source, target):
        return vpc_client.associate_network_acl(source.id, target.id)

    def dhcp_options_associated_with_vpc(self, vpc_client, source, target):
        return vpc_client.associate_dhcp_options(source.id, target.id)

    def route_table_associated_with_subnet(self, vpc_client, source, target):
        return vpc_client.associate_route_table(source.id, target.id)

    def route_to_gateway(self, vpc_client, source, target):
        actual_args = dict(
            route_table_id=source.id,
            destination_cidr_block='0.0.0.0/0',
            gateway_id=target.id
        )
        return vpc_client.create_route(**actual_args)

    def perform_relationships_on_all_existing_resources(self,
                                                        vpc_client,
                                                        existing):

        relationships = [
            self.gateway_connected_to_vpc(
                vpc_client,
                {
                    INTERNET_GATEWAY_TYPE: existing[INTERNET_GATEWAY_TYPE]
                },
                existing[VPC_TYPE]),
            self.gateway_connected_to_vpc(
                vpc_client,
                {
                    VPN_GATEWAY_TYPE: existing[VPN_GATEWAY_TYPE]
                },
                existing[VPC_TYPE]),
            self.customer_gateway_connected_to_vpn_gateway(
                vpc_client,
                existing[CUSTOMER_GATEWAY_TYPE],
                existing[VPN_GATEWAY_TYPE]),
            self.network_acl_associated_with_subnet(
                vpc_client,
                existing[ACL_TYPE],
                existing[SUBNET_TYPE]),
            self.dhcp_options_associated_with_vpc(
                vpc_client,
                existing[DHCP_OPTIONS_TYPE],
                existing[VPC_TYPE]),
            self.route_table_associated_with_subnet(
                vpc_client,
                existing[ROUTE_TABLE_TYPE],
                existing[SUBNET_TYPE]),
            self.route_to_gateway(
                vpc_client,
                existing[ROUTE_TABLE_TYPE],
                existing[INTERNET_GATEWAY_TYPE]
            )
        ]

        return relationships

    def create_all_existing_resources(self, vpc_client):

        existing_vpc = self.create_vpc(vpc_client)
        existing_subnet = self.create_subnet(vpc_client, existing_vpc)
        existing_internet_gateway = self.create_internet_gateway(vpc_client)
        existing_vpn_gateway = self.create_vpn_gateway(vpc_client)
        existing_acl = self.create_network_acl(vpc_client, existing_vpc)
        existing_dhcp_options = self.create_dhcp_options(vpc_client)
        existing_customer_gateway = self.create_customer_gateway(vpc_client)
        existing_route_table = \
            self.create_route_table(vpc_client, existing_vpc)

        resources = {
            VPC_TYPE: existing_vpc,
            SUBNET_TYPE: existing_subnet,
            INTERNET_GATEWAY_TYPE: existing_internet_gateway,
            VPN_GATEWAY_TYPE: existing_vpn_gateway,
            ACL_TYPE: existing_acl,
            DHCP_OPTIONS_TYPE: existing_dhcp_options,
            CUSTOMER_GATEWAY_TYPE: existing_customer_gateway,
            ROUTE_TABLE_TYPE: existing_route_table
        }

        return resources

    def get_current_list_of_used_resources(self, vpc_client):

        resources = {
            VPC_TYPE: vpc_client.get_all_vpcs(),
            SUBNET_TYPE: vpc_client.get_all_subnets(),
            INTERNET_GATEWAY_TYPE: vpc_client.get_all_internet_gateways(),
            VPN_GATEWAY_TYPE: vpc_client.get_all_vpn_gateways(),
            ACL_TYPE: vpc_client.get_all_network_acls(),
            DHCP_OPTIONS_TYPE: vpc_client.get_all_dhcp_options(),
            CUSTOMER_GATEWAY_TYPE: vpc_client.get_all_customer_gateways(),
            ROUTE_TABLE_TYPE: vpc_client.get_all_route_tables()
        }

        return resources

    def mock_node_context(self, test_name,
                          node_properties=None, relationships=None):

        ctx = MockCloudifyContext(
            node_id=test_name,
            properties=node_properties,
            deployment_id='d1'
        )

        ctx.instance.relationships = [] if not relationships else relationships

        return ctx

    def get_mock_node_properties(self, node_template_properties=None):

        test_properties = {
            constants.AWS_CONFIG_PROPERTY: {},
            'use_external_resource': False,
            'resource_id': 'test_security_group',
        }

        if node_template_properties:
            test_properties.update(node_template_properties)

        return test_properties

    def vpc_node_template_properties(self, inputs):

        return {
            'cidr_block':
                inputs.get('cidr_block')
                if 'cidr_block' in inputs.keys() else '10.0.0.0/24',
            'instance_tenancy':
                inputs.get('instance_tenancy')
                if 'instance_tenancy' in inputs.keys() else 'default',
            'enable_vpc_classic_link':
                inputs.get('enable_vpc_classic_link')
                if 'enable_vpc_classic_link' in inputs.keys() else False
        }

    def subnet_node_template_properties(self, inputs):

        return {
            'cidr_block':
                inputs.get('cidr_block')
                if 'cidr_block' in inputs.keys() else '10.0.0.0/25',
            'availability_zone':
                inputs.get('availability_zone')
                if 'availability_zone' in inputs.keys() else ''
        }

    def network_acl_node_template_properties(self, inputs):

        return {
            'acl_network_entries':
                [entry for entry in inputs.get('entries')]
                if 'entries' in inputs.keys() else []
        }

    def vpn_gateway_node_template_properties(self, inputs):

        return {
            'type': 'ipsec.1',
            'availability_zone':
                inputs.get('availability_zone')
                if 'availability_zone' in inputs.keys() else ''
        }

    def customer_gateway_node_template_properties(self, inputs):

        return {
            'type': 'ipsec.1',
            'ip_address':
                inputs.get('ip_address')
                if 'ip_address' in inputs.keys() else '10.0.0.7',
            'bgp_asn': '35000'
        }

    def dhcp_options_node_template_properties(self, inputs):

        return {
            'domain_name':
                inputs.get('domain_name')
                if 'domain_name' in inputs.keys() else 'example.com',
            'domain_name_servers':
                [dns for dns in inputs.get('domain_name_servers')]
                if 'domain_name_servers' in inputs.keys() else [],
            'ntp_servers':
                [ntp for ntp in inputs.get('ntp_servers')]
                if 'ntp_servers' in inputs.keys() else [],
            'netbios_name_servers':
                [nbns for nbns in inputs.get('netbios_name_servers')]
                if 'netbios_name_servers' in inputs.keys() else [],
            'netbios_node_type': 2
        }

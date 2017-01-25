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
import mock

# Third-party Imports
from moto import mock_ec2

# Cloudify Imports
from cloudify_aws import constants
from cloudify_aws.vpc import vpc, subnet, routetable, dhcp
from vpc_testcase import VpcTestCase
from cloudify.state import current_ctx
from cloudify.exceptions import NonRecoverableError

VPC_TYPE = 'cloudify.aws.nodes.VPC'
SUBNET_TYPE = 'cloudify.aws.nodes.Subnet'
DHCP_OPTIONS_TYPE = 'cloudify.aws.nodes.DHCPOptions'
ROUTE_TABLE_TYPE = 'cloudify.aws.nodes.RouteTable'
TEST_VPC_CIDR = '10.10.10.0/16'
TEST_SUBNET_CIDR = '10.10.10.0/24'


class TestVpcModule(VpcTestCase):

    def get_mock_vpc_node_instance_context(self, test_name):

        inputs = dict()

        node_context = self.mock_node_context(
            test_name,
            self.get_mock_node_properties(
                self.vpc_node_template_properties(inputs)
            )
        )

        node_context.node.type = VPC_TYPE
        node_context.node.type_hierarchy = \
            [node_context.node.type, 'cloudify.nodes.Root']

        current_ctx.set(ctx=node_context)

        return node_context

    @mock_ec2
    def test_start_vpc(self, *_):

        ctx = self.get_mock_vpc_node_instance_context('test_start_vpc')
        ctx.node.properties['name'] = 'test_start_vpc'
        current_ctx.set(ctx=ctx)

        vpc_client = self.create_client()
        new_vpc = vpc_client.create_vpc(TEST_VPC_CIDR)
        vpc_id = new_vpc.id
        ctx.instance.runtime_properties['aws_resource_id'] = vpc_id
        vpc.start(ctx=ctx)
        vpc_list = vpc_client.get_all_vpcs(vpc_id)
        vpc_object = vpc_list[0]
        self.assertEquals(vpc_object.tags.get('resource_id'),
                          ctx.instance.id)
        self.assertEquals(vpc_object.tags.get('deployment_id'),
                          ctx.deployment.id)

    @mock_ec2
    def test_delete_invalid_vpc_id(self):
        ctx = self.get_mock_vpc_node_instance_context(
            'test_delete_invalid_vpc_id')
        ctx.instance.runtime_properties['aws_resource_id'] = 'vpc-0123abcd'
        error = self.assertRaises(NonRecoverableError, vpc.delete, ctx=ctx)
        self.assertIn(
            'Cannot use_external_resource because resource '
            'vpc-0123abcd is not in this account',
            error.message)


class TestSubnetModule(VpcTestCase):

    class Vpc(object):
        def __init__(self):
            self.id = 'vpc-0123abcd'

    def get_mock_subnet_node_instance_context(self, test_name, inputs=None):

        inputs = dict() if not inputs else inputs

        node_context = self.mock_node_context(
            test_name,
            self.get_mock_node_properties(
                self.subnet_node_template_properties(inputs)
            )
        )

        node_context.node.type = SUBNET_TYPE
        node_context.node.type_hierarchy = \
            [node_context.node.type, 'cloudify.nodes.Root']

        current_ctx.set(ctx=node_context)

        return node_context

    @mock_ec2
    def test_delete_invalid_subnet_id(self):
        ctx = self.get_mock_subnet_node_instance_context(
            'test_delete_invalid_subnet_id')
        ctx.instance.runtime_properties['aws_resource_id'] = 'subnet-0123abcd'
        error = self.assertRaises(NonRecoverableError, subnet.delete_subnet,
                                  ctx=ctx)
        self.assertIn(
            'Cannot use_external_resource because resource '
            'subnet-0123abcd is not in this account',
            error.message)

    @mock_ec2
    @mock.patch(
        'cloudify_aws.base.AwsBase.get_target_ids_of_relationship_type',
        return_value=[Vpc(), Vpc()])
    def test_create(self, *_):
        ctx = self.get_mock_subnet_node_instance_context('test_create')
        ctx.operation._operation_context['retry_number'] = 0
        error = self.assertRaises(NonRecoverableError, subnet.create_subnet,
                                  args=None, ctx=ctx)
        self.assertIn('subnet can only be connected to one vpc', error.message)

    @mock_ec2
    def test_start_subnet(self, *_):
        ctx = self.get_mock_subnet_node_instance_context('test_start_subnet')
        ctx.node.properties['name'] = 'test_start_subnet'
        current_ctx.set(ctx=ctx)

        vpc_client = self.create_client()
        vpc = vpc_client.create_vpc(TEST_VPC_CIDR)
        new_subnet = vpc_client.create_subnet(
            vpc.id, TEST_SUBNET_CIDR)
        subnet_id = new_subnet.id
        ctx.instance.runtime_properties['aws_resource_id'] = subnet_id
        subnet.start_subnet(ctx=ctx)
        subnet_list = vpc_client.get_all_subnets(subnet_id)
        subnet_object = subnet_list[0]
        self.assertEquals(subnet_object.tags.get('resource_id'),
                          ctx.instance.id)
        self.assertEquals(subnet_object.tags.get('deployment_id'),
                          ctx.deployment.id)


class TestRouteTableModule(VpcTestCase):

    class RouteTable(object):
        def __init__(self):
            self.id = 'rtb-0123abcd'

    class Vpc(object):
        def __init__(self):
            self.id = 'vpc-0123abcd'
            self.cidr_block = '10.0.0.0/24'

    def get_routes(self):
        route = {
            'destination_cidr_block': '10.0.0.0/24'
        }
        return [route]

    def get_mock_route_table_node_instance_context(self, test_name, vpc=None):

        node_context = self.mock_node_context(
            test_name,
            self.get_mock_node_properties(),
            self.create_route_table_in_vpc_relationship(vpc)
        )

        node_context.node.type = ROUTE_TABLE_TYPE
        node_context.node.type_hierarchy = \
            [node_context.node.type, 'cloudify.nodes.Root']

        current_ctx.set(ctx=node_context)

        return node_context

    def create_route_table_in_vpc_relationship(self, vpc):
        return {
            'type': constants.ROUTE_TABLE_VPC_RELATIONSHIP,
            'target': self.Vpc() if not vpc else vpc.id
        }

    @mock_ec2
    def test_start_route_table(self, *_):

        ctx = self.get_mock_route_table_node_instance_context(
            'test_start_route_table')
        ctx.node.properties['name'] = 'test_start_route_table'
        current_ctx.set(ctx=ctx)

        vpc_client = self.create_client()
        vpc = vpc_client.create_vpc(TEST_VPC_CIDR)
        new_route_table = vpc_client.create_route_table(vpc.id)
        route_table_id = new_route_table.id
        ctx.instance.runtime_properties['aws_resource_id'] = route_table_id
        routetable.start_route_table(ctx=ctx)
        route_table_route = vpc_client.get_all_route_tables(route_table_id)
        route_table_object = route_table_route[0]
        self.assertEquals(route_table_object.tags.get('resource_id'),
                          ctx.instance.id)
        self.assertEquals(route_table_object.tags.get('deployment_id'),
                          ctx.deployment.id)

    @mock_ec2
    def test_delete_route_table(self, *_):
        client = self.create_client()
        vpc = self.create_vpc(client)
        route_table = self.create_route_table(client, vpc)
        ctx = \
            self.get_mock_route_table_node_instance_context(
                'test_delete_route_table', vpc)
        ctx.instance.runtime_properties[
            constants.EXTERNAL_RESOURCE_ID] = route_table.id
        client.create_route(route_table_id=route_table.id,
                            destination_cidr_block='10.0.0.0/24')
        ctx.instance.runtime_properties['routes'] = self.get_routes()
        routetable.delete_route_table(ctx=ctx)
        self.assertNotIn(ctx.instance.runtime_properties,
                         constants.EXTERNAL_RESOURCE_ID)


class TestDhcpModule(VpcTestCase):

    def get_mock_dhcp_node_instance_context(self, test_name):

        node_context = self.mock_node_context(
            test_name,
            self.get_mock_node_properties()
        )

        node_context.node.type = DHCP_OPTIONS_TYPE
        node_context.node.type_hierarchy = \
            [node_context.node.type, 'cloudify.nodes.Root']

        current_ctx.set(ctx=node_context)

        return node_context

    @mock_ec2
    def test_start_dhcp_options(self, *_):

        ctx = self.get_mock_dhcp_node_instance_context(
            'test_start_dhcp_options')
        ctx.node.properties['name'] = 'test_start_dhcp_options'
        current_ctx.set(ctx=ctx)

        vpc_client = self.create_client()
        new_dhcp = vpc_client.create_dhcp_options()
        dhcp_id = new_dhcp.id
        ctx.instance.runtime_properties['aws_resource_id'] = dhcp_id
        dhcp.start_dhcp_options(ctx=ctx)
        dhcp_list = vpc_client.get_all_dhcp_options(dhcp_id)
        dhcp_object = dhcp_list[0]
        self.assertEquals(dhcp_object.tags.get('resource_id'),
                          ctx.instance.id)
        self.assertEquals(dhcp_object.tags.get('deployment_id'),
                          ctx.deployment.id)

    @mock_ec2
    def test_delete_dhcp_option_set(self, *_):
        client = self.create_client()
        args = dict(
            domain_name='example.com',
            domain_name_servers=['ns1.example.com', 'ns2.example.com']
        )
        dhcp_options = self.create_dhcp_options(client, args=args)
        ctx = self.get_mock_dhcp_node_instance_context(
            'test_delete_dhcp_option_set')
        ctx.instance.runtime_properties[
            constants.EXTERNAL_RESOURCE_ID] = dhcp_options.id
        error = self.assertRaises(
            NonRecoverableError, dhcp.delete_dhcp_options, ctx=ctx)
        self.assertIn('returned False', error.message)

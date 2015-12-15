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

EXTERNAL_RESOURCE_ID = 'aws_resource_id'
AVAILABILITY_ZONE = 'availability_zone'
AWS_CONFIG_PROPERTY = 'aws_config'
ROUTE_NOT_FOUND_ERROR = 'InvalidRoute.NotFound'

VPC = dict(
    AWS_RESOURCE_TYPE='vpc',
    CLOUDIFY_NODE_TYPE='cloudify.aws.nodes.VPC',
    ID_FORMAT='^vpc\-[0-9a-z]{8}$',
    NOT_FOUND_ERROR='InvalidVpcID.NotFound',
    REQUIRED_PROPERTIES=['cidr_block', 'instance_tenancy']
)

SUBNET = dict(
    AWS_RESOURCE_TYPE='subnet',
    CLOUDIFY_NODE_TYPE='cloudify.aws.nodes.Subnet',
    ID_FORMAT='^subnet\-[0-9a-z]{8}$',
    NOT_FOUND_ERROR='InvalidSubnetID.NotFound',
    REQUIRED_PROPERTIES=['cidr_block']
)

ROUTE_TABLE = dict(
    AWS_RESOURCE_TYPE='route_table',
    CLOUDIFY_NODE_TYPE='cloudify.aws.nodes.RouteTable',
    ID_FORMAT='^rtb\-[0-9a-z]{8}$',
    NOT_FOUND_ERROR='InvalidRouteTableID.NotFound',
    REQUIRED_PROPERTIES=[]
)

NETWORK_ACL = dict(
    AWS_RESOURCE_TYPE='network_acl',
    CLOUDIFY_NODE_TYPE='cloudify.aws.nodes.ACL',
    ID_FORMAT='^acl\-[0-9a-z]{8}$',
    NOT_FOUND_ERROR='InvalidNetworkAclID.NotFound',
    REQUIRED_PROPERTIES=[]
)

INTERNET_GATEWAY = dict(
    AWS_RESOURCE_TYPE='internet_gateway',
    CLOUDIFY_NODE_TYPE='cloudify.aws.nodes.InternetGateway',
    ID_FORMAT='^igw\-[0-9a-z]{8}$',
    NOT_FOUND_ERROR='InvalidInternetGatewayID.NotFound',
    REQUIRED_PROPERTIES=[]
)

VPN_GATEWAY = dict(
    AWS_RESOURCE_TYPE='vpn_gateway',
    CLOUDIFY_NODE_TYPE='cloudify.aws.nodes.VPNGateway',
    ID_FORMAT='^vgw\-[0-9a-z]{8}$',
    NOT_FOUND_ERROR='InvalidVpnGatewayID.NotFound',
    REQUIRED_PROPERTIES=[]
)

CUSTOMER_GATEWAY = dict(
    AWS_RESOURCE_TYPE='customer_gateway',
    CLOUDIFY_NODE_TYPE='cloudify.aws.nodes.CustomerGateway',
    ID_FORMAT='^cgw\-[0-9a-z]{8}$',
    NOT_FOUND_ERROR='InvalidCustomerGatewayID.NotFound',
    REQUIRED_PROPERTIES=[]
)

DHCP_OPTIONS = dict(
    AWS_RESOURCE_TYPE='dhcp_options',
    CLOUDIFY_NODE_TYPE='cloudify.aws.nodes.DHCPOptions',
    ID_FORMAT='^dopt\-[0-9a-z]{8}$',
    NOT_FOUND_ERROR='InvalidDhcpOptionID.NotFound',
    REQUIRED_PROPERTIES=[]
)

GATEWAY_VPC_RELATIONSHIP = \
    'cloudify.aws.relationships.gateway_connected_to_vpc'
SUBNET_IN_VPC = \
    'cloudify.aws.relationships.subnet_contained_in_vpc'
ROUTE_TABLE_VPC_RELATIONSHIP = \
    'cloudify.aws.relationships.routetable_contained_in_vpc'
ROUTE_TABLE_GATEWAY_RELATIONSHIP = \
    'cloudify.aws.relationships.route_table_to_gateway'
INSTANCE_VPC_RELATIONSHIP = \
    'cloudify.aws.relationships.instance_connected_to_vpc'
NETWORK_ACL_IN_VPC_RELATIONSHIP = \
    'cloudify.aws.relationships.network_acl_contained_in_vpc'
NETWORK_ACL_IN_SUBNET_RELATIONSHIP = \
    'cloudify.aws.relationships.network_acl_associated_with_subnet'
VPC_PEERING_RELATIONSHIP = \
    'cloudify.aws.relationships.vpc_connected_to_peer'
DHCP_VPC_RELATIONSHIP = \
    'cloudify.aws.relationships.dhcp_options_associated_with_vpc'
CUSTOMER_VPC_RELATIONSHIP = \
    'cloudify.aws.relationships.customer_gateway_connected_to_vpn_gateway'

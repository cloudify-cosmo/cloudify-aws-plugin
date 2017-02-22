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

# instance module constants
INSTANCE_STATE_STARTED = 16
INSTANCE_STATE_TERMINATED = 48
INSTANCE_STATE_STOPPED = 80

# ELB Default Values
HEALTH_CHECK_INTERVAL = 30
HEALTH_CHECK_HEALTHY_THRESHOLD = 3
HEALTH_CHECK_TIMEOUT = 5
HEALTH_CHECK_UNHEALTHY_THRESHOLD = 5

EXTERNAL_RESOURCE_ID = 'aws_resource_id'
AVAILABILITY_ZONE = 'availability_zone'
AWS_CONFIG_PROPERTY = 'aws_config'
ROUTE_NOT_FOUND_ERROR = 'InvalidRoute.NotFound'

INSTANCE_INTERNAL_ATTRIBUTES = \
    ['private_dns_name', 'public_dns_name',
     'public_ip_address', 'ip']

ENI_INTERNAL_ATTRIBUTES = \
    ['subnet_id', 'vpc_id',
     'description', 'owner_id', 'requester_managed',
     'status', 'mac_address', 'private_ip_address',
     'source_dest_check', 'groups',
     'private_ip_addresses']

AWS_TYPE_PROPERTY = 'external_type'  # resource's openstack type
RELATIONSHIP_INSTANCE = 'relationship-instance'
NODE_INSTANCE = 'node-instance'

INSTANCE = dict(
        AWS_RESOURCE_TYPE='instance',
        CLOUDIFY_NODE_TYPE='cloudify.aws.nodes.Instance',
        ID_FORMAT='^i\-[0-9a-z]{8}$',
        NOT_FOUND_ERROR='InvalidInstanceID.NotFound',
        REQUIRED_PROPERTIES=['image_id', 'instance_type'],
        STATES=[{'name': 'create',
                 'success': ['running'],
                 'waiting': ['pending'],
                 'failed': []},
                {'name': 'start',
                 'success': ['running', 16],
                 'waiting': ['pending'],
                 'failed': []},
                {'name': 'stop',
                 'success': ['stopped', 80],
                 'waiting': ['stopping'],
                 'failed': []},
                {'name': 'delete',
                 'success': ['terminated'],
                 'waiting': ['shutting-down', 48],
                 'failed': []}]
)

SECURITYGROUP = dict(
        AWS_RESOURCE_TYPE='group',
        CLOUDIFY_NODE_TYPE='cloudify.aws.nodes.SecurityGroup',
        ID_FORMAT='^sg\-[0-9a-z]{8}$',
        NOT_FOUND_ERROR='InvalidGroup.NotFound',
        REQUIRED_PROPERTIES=['description', 'rules'],
        STATES=[{}]
)

SUBNET = dict(
        AWS_RESOURCE_TYPE='subnet',
        CLOUDIFY_NODE_TYPE='cloudify.aws.nodes.Subnet',
        ID_FORMAT='^subnet\-[0-9a-z]{8}$',
        NOT_FOUND_ERROR='InvalidSubnetID.NotFound',
        REQUIRED_PROPERTIES=['cidr_block'],
        STATES=[{'name': 'create',
                 'success': ['available'],
                 'waiting': ['pending'],
                 'failed': []}]
)

VPC = dict(
        AWS_RESOURCE_TYPE='vpc',
        CLOUDIFY_NODE_TYPE='cloudify.aws.nodes.VPC',
        ID_FORMAT='^vpc\-[0-9a-z]{8}$',
        NOT_FOUND_ERROR='InvalidVpcID.NotFound',
        REQUIRED_PROPERTIES=['cidr_block', 'instance_tenancy'],
        STATES=[{'name': 'create',
                 'success': ['available'],
                 'waiting': ['pending'],
                 'failed': []}]
)

KEYPAIR = dict(
        AWS_RESOURCE_TYPE='keypair',
        CLOUDIFY_NODE_TYPE='cloudify.aws.nodes.KeyPair',
        NOT_FOUND_ERROR='InvalidKeyPair.NotFound',
        REQUIRED_PROPERTIES=['private_key_path'],
        STATES=[{}]
)

ELB = dict(
        AWS_RESOURCE_TYPE='load_balancer',
        CLOUDIFY_NODE_TYPE='cloudify.aws.nodes.ElasticLoadBalancer',
        NOT_FOUND_ERROR='LoadBalancerNotFound',
        REQUIRED_PROPERTIES=['elb_name', 'zones', 'listeners'],
        STATES=[{}]
)

ELASTICIP = dict(
        AWS_RESOURCE_TYPE='elasticip',
        CLOUDIFY_NODE_TYPE='cloudify.aws.nodes.ElasticIP',
        NOT_FOUND_ERROR='InvalidAddress.NotFound',
        REQUIRED_PROPERTIES=[],
        ALLOCATION_ID='allocation_id',
        VPC_DOMAIN='vpc',
        ELASTIC_IP_DOMAIN_PROPERTY='domain',
        STATES=[{}]
)

ZONE = 'zone'
EBS = dict(
    AWS_RESOURCE_TYPE='volume',
    CLOUDIFY_NODE_TYPE='cloudify.aws.nodes.Volume',
    ID_FORMAT='^vol\-[0-9a-z]{8}$',
    NOT_FOUND_ERROR='InvalidVolume.NotFound',
    REQUIRED_PROPERTIES=['size', ZONE, 'device'],
    VOLUME_SNAPSHOT_ATTRIBUTE='snapshots_ids',
    VOLUME_AVAILABLE='available',
    VOLUME_CREATING='creating',
    VOLUME_IN_USE='in-use',
    STATES=[{'name': 'create',
             'success': ['available', 'in-use'],
             'waiting': ['creating'],
             'failed': []},
            {'name': 'delete',
             'success': ['deleted'],
             'waiting': ['deleting'],
             'failed': []}]
)

ENI = dict(
    AWS_RESOURCE_TYPE='network_interface',
    CLOUDIFY_NODE_TYPE='cloudify.aws.nodes.Interface',
    ID_FORMAT='^eni\-[0-9a-z]{8}$',
    REQUIRED_PROPERTIES=[],
    NOT_FOUND_ERROR='InvalidInterface.NotFound',
    STATES=[{'name': 'create',
             'success': ['available', 'in-use'],
             'waiting': ['creating'],
             'failed': []},
            {'name': 'delete',
             'success': ['deleted'],
             'waiting': ['deleting'],
             'failed': []}]
)

ROUTE_TABLE = dict(
        AWS_RESOURCE_TYPE='route_table',
        CLOUDIFY_NODE_TYPE='cloudify.aws.nodes.RouteTable',
        ID_FORMAT='^rtb\-[0-9a-z]{8}$',
        NOT_FOUND_ERROR='InvalidRouteTableID.NotFound',
        REQUIRED_PROPERTIES=[],
        STATES=[{}]
)

NETWORK_ACL = dict(
        AWS_RESOURCE_TYPE='network_acl',
        CLOUDIFY_NODE_TYPE='cloudify.aws.nodes.ACL',
        ID_FORMAT='^acl\-[0-9a-z]{8}$',
        NOT_FOUND_ERROR='InvalidNetworkAclID.NotFound',
        REQUIRED_PROPERTIES=[],
        STATES=[{}]
)

INTERNET_GATEWAY = dict(
        AWS_RESOURCE_TYPE='internet_gateway',
        CLOUDIFY_NODE_TYPE='cloudify.aws.nodes.InternetGateway',
        ID_FORMAT='^igw\-[0-9a-z]{8}$',
        NOT_FOUND_ERROR='InvalidInternetGatewayID.NotFound',
        REQUIRED_PROPERTIES=[],
        STATES=[{}]
)

VPN_GATEWAY = dict(
        AWS_RESOURCE_TYPE='vpn_gateway',
        CLOUDIFY_NODE_TYPE='cloudify.aws.nodes.VPNGateway',
        ID_FORMAT='^vgw\-[0-9a-z]{8}$',
        NOT_FOUND_ERROR='InvalidVpnGatewayID.NotFound',
        REQUIRED_PROPERTIES=[],
        STATES=[{'name': 'create',
                 'success': ['available'],
                 'waiting': ['pending'],
                 'failed': ['error']},
                {'name': 'delete',
                 'success': ['deleted'],
                 'waiting': ['deleting'],
                 'failed': ['error']}]
)

CUSTOMER_GATEWAY = dict(
        AWS_RESOURCE_TYPE='customer_gateway',
        CLOUDIFY_NODE_TYPE='cloudify.aws.nodes.CustomerGateway',
        ID_FORMAT='^cgw\-[0-9a-z]{8}$',
        NOT_FOUND_ERROR='InvalidCustomerGatewayID.NotFound',
        REQUIRED_PROPERTIES=[],
        STATES=[{'name': 'create',
                 'success': ['available'],
                 'waiting': ['pending'],
                 'failed': ['error']},
                {'name': 'delete',
                 'success': ['deleted'],
                 'waiting': ['deleting'],
                 'failed': ['error']}]
)

DHCP_OPTIONS = dict(
        AWS_RESOURCE_TYPE='dhcp_options',
        CLOUDIFY_NODE_TYPE='cloudify.aws.nodes.DHCPOptions',
        ID_FORMAT='^dopt\-[0-9a-z]{8}$',
        NOT_FOUND_ERROR='InvalidDhcpOptionID.NotFound',
        REQUIRED_PROPERTIES=[],
        STATES=[{}]
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

INSTANCE_INTERNAL_ATTRIBUTES_POST_CREATE = \
    ['vpc_id', 'subnet_id', 'placement']
AGENTS_SECURITY_GROUP = 'agents_security_group'
AGENTS_KEYPAIR = 'agents_keypair'
AGENTS_AWS_INSTANCE_PARAMETERS = 'agents_instance_parameters'
INSTANCE_KEYPAIR_RELATIONSHIP = 'instance_connected_to_keypair'
INSTANCE_SUBNET_RELATIONSHIP = 'instance_contained_in_subnet'
INSTANCE_SUBNET_CONNECTED_TO_RELATIONSHIP = 'instance_connected_to_subnet'
INSTANCE_ENI_RELATIONSHIP = 'instance_connected_to_eni'

ADMIN_PASSWORD_PROPERTY = 'password'  # the server's password

RUN_INSTANCE_PARAMETERS = {
    'image_id': None, 'key_name': None, 'security_groups': None,
    'user_data': None, 'addressing_type': None,
    'instance_type': 'm1.small', 'placement': None, 'kernel_id': None,
    'ramdisk_id': None, 'monitoring_enabled': False, 'subnet_id': None,
    'block_device_map': None, 'disable_api_termination': False,
    'instance_initiated_shutdown_behavior': None,
    'private_ip_address': None, 'placement_group': None,
    'client_token': None, 'security_group_ids': None,
    'additional_info': None, 'instance_profile_name': None,
    'instance_profile_arn': None, 'tenancy': None, 'ebs_optimized': False,
    'network_interfaces': None, 'dry_run': False
}

AWS_CONFIG_PATH_ENV_VAR_NAME = "AWS_CONFIG_PATH"

# Boto config schema (section > options)
BOTO_CONFIG_SCHEMA = {
    'Credentials': ['aws_access_key_id', 'aws_secret_access_key'],
    'Boto': ['ec2_region_name', 'ec2_region_endpoint']
}

INSTANCE_SECURITY_GROUP_RELATIONSHIP = 'instance_connected_to_security_group'
SECURITY_GROUP_VPC_RELATIONSHIP = 'security_group_contained_in_vpc'
RUNTIME_PROPERTIES = [AWS_TYPE_PROPERTY, EXTERNAL_RESOURCE_ID]
SECURITY_GROUP_RULE_RELATIONSHIP = 'security_group_uses_rule'

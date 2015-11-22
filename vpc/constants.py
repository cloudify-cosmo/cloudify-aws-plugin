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

VPC_REQUIRED_PROPERTIES = ['cidr_block', 'instance_tenancy']
SUBNET_REQUIRED_PROPERTIES = ['cidr_block']
DHCP_REQUIRED_PROPERTIES = []
NETWORK_ACL_REQUIRED_PROPERTIES = []
GATEWAY_ACL_REQUIRED_PROPERTIES = []
ROUTES_ACL_REQUIRED_PROPERTIES = []

VPC_SUBNET_RELATIONSHIP_TYPE = 'subnet_contained_in_vpc'
VPC_NETWORK_ACL_SUBNET_TYPE = 'network_acl_associated_with_subnet'
VPC_ROUTE_ASSOCIATED_WITH_VPC = 'route_associated_with_vpc'

EXTERNAL_RESOURCE_ID = 'aws_resource_id'

AVAILABILITY_ZONE = 'availability_zone'

INSTANCE_VPC_STATE = {
    'instance': 'running',
    'vpc': 'available'
}

VPC_PEERING_CONNECTION_STATE = 'pending-acceptance'

VPN_GATEWAY_TYPE = 'cloudify.aws.nodes.VPNGateway'
INTERNET_GATEWAY_TYPE = 'cloudify.aws.nodes.InternetGateway'
CUSTOMER_GATEWAY_TYPE = 'cloudify.aws.nodes.CustomerGateway'
# Copyright (c) 2018 Cloudify Platform Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
    EC2.VPN Gateway
    ~~~~~~~~~~~~~~
    AWS EC2 VPN Gateway interface
"""
# Cloudify
from cloudify_aws.common import decorators, utils
from cloudify_aws.ec2 import EC2Base
from cloudify_aws.common.constants import EXTERNAL_RESOURCE_ID

# Boto
from botocore.exceptions import ClientError

RESOURCE_TYPE = 'EC2 VPN Gateway'
VPNGATEWAYS = 'VpnGateways'
VPNGATEWAY_ID = 'VpnGatewayId'
VPNGATEWAY_IDS = 'VpnGatewayIds'
VPC_ID = 'VpcId'
VPC_TYPE = 'cloudify.nodes.aws.ec2.Vpc'
VPC_TYPE_DEPRECATED = 'cloudify.aws.nodes.Vpc'


class EC2VPNGateway(EC2Base):
    """
        EC2 VPN Gateway interface
    """
    def __init__(self, ctx_node, resource_id=None, client=None, logger=None):
        EC2Base.__init__(self, ctx_node, resource_id, client, logger)
        self.type_name = RESOURCE_TYPE

    @property
    def properties(self):
        """Gets the properties of an external resource"""
        params = {VPNGATEWAY_IDS: [self.resource_id]}
        try:
            resources = \
                self.client.describe_vpn_gateways(**params)
        except ClientError:
            pass
        else:
            return resources.get(VPNGATEWAYS)[0] if resources else None

    @property
    def status(self):
        """Gets the status of an external resource"""
        props = self.properties
        if not props:
            return None
        return props['State']

    def create(self, params):
        """
            Create a new AWS EC2 VPN Gateway.
        """
        return self.make_client_call('create_vpn_gateway', params)

    def delete(self, params=None):
        """
            Deletes an existing AWS EC2 VPN Gateway.
        """
        self.logger.debug('Deleting %s with parameters: %s'
                          % (self.type_name, params))
        res = self.client.delete_vpn_gateway(**params)
        self.logger.debug('Response: %s' % res)
        return res

    def attach(self, params):
        '''
            Attach an AWS EC2 VPN Gateway to a VPC.
        '''
        self.logger.debug('Attaching %s with: %s'
                          % (self.type_name, params.get(VPC_ID, None)))
        res = self.client.attach_vpn_gateway(**params)
        self.logger.debug('Response: %s' % res)
        return res['VpcAttachment']

    def detach(self, params):
        '''
            Detach an AWS EC2 VPN Gateway from a VPC.
        '''
        self.logger.debug('Detaching %s from: %s'
                          % (self.type_name, params.get(VPC_ID, None)))
        res = self.client.detach_vpn_gateway(**params)
        self.logger.debug('Response: %s' % res)
        return res


@decorators.aws_resource(resource_type=RESOURCE_TYPE)
def prepare(ctx, resource_config, **_):
    """Prepares an AWS EC2 VPN Gateway"""
    # Save the parameters
    ctx.instance.runtime_properties['resource_config'] = resource_config


@decorators.aws_resource(EC2VPNGateway, RESOURCE_TYPE)
@decorators.wait_for_status(status_good=['available'],
                            status_pending=['pending'])
@decorators.tag_resources
def create(ctx, iface, resource_config, **_):
    """Creates an AWS EC2 VPN Gateway"""

    # Create a copy of the resource config for clean manipulation.
    params = \
        dict() if not resource_config else resource_config.copy()

    # Actually create the resource
    create_response = iface.create(params)['VpnGateway']
    ctx.instance.runtime_properties['create_response'] = \
        utils.JsonCleanuper(create_response).to_dict()
    utils.update_resource_id(ctx.instance, create_response.get(VPNGATEWAY_ID))


@decorators.aws_resource(EC2VPNGateway, RESOURCE_TYPE,
                         ignore_properties=True)
@decorators.wait_for_delete(status_deleted=['deleted'],
                            status_pending=['deleting'])
@decorators.untag_resources
def delete(iface, resource_config, **_):
    """Deletes an AWS EC2 VPN Gateway"""

    # Create a copy of the resource config for clean manipulation.
    params = \
        dict() if not resource_config else resource_config.copy()
    vpn_gateway_id = params.get(VPNGATEWAY_ID)

    if not vpn_gateway_id:
        vpn_gateway_id = iface.resource_id

    params.update({VPNGATEWAY_ID: vpn_gateway_id})
    iface.delete(params)


@decorators.aws_resource(EC2VPNGateway, RESOURCE_TYPE)
def attach(ctx, iface, resource_config, **_):
    '''Attaches an AWS EC2 VPN Gateway to a VPC'''
    params = dict() if not resource_config else resource_config.copy()

    vpn_gateway_id = params.get(VPNGATEWAY_ID)
    if not vpn_gateway_id:
        vpn_gateway_id = iface.resource_id

    params.update({VPNGATEWAY_ID: vpn_gateway_id})
    params.pop('Type')

    vpc_id = params.get(VPC_ID)
    if not vpc_id:
        targ = \
            utils.find_rel_by_node_type(ctx.instance, VPC_TYPE) or \
            utils.find_rel_by_node_type(ctx.instance, VPC_TYPE_DEPRECATED)

        # Attempt to use the VPC ID from parameters.
        # Fallback to connected VPC.
        params[VPC_ID] = \
            vpc_id or \
            targ.target.instance.runtime_properties.get(EXTERNAL_RESOURCE_ID)

    # # Actually attach the resources
    attached_vpc_list = iface.attach(params)
    attached_vpc_id = attached_vpc_list.get(VPC_ID)
    ctx.instance.runtime_properties['vpc_id'] = attached_vpc_id


@decorators.aws_resource(EC2VPNGateway, RESOURCE_TYPE,
                         ignore_properties=True)
def detach(ctx, iface, resource_config, **_):
    '''Detach an AWS EC2 VPN Gateway from a VPC'''
    params = dict() if not resource_config else resource_config.copy()

    vpn_gateway_id = params.get(VPNGATEWAY_ID)
    if not vpn_gateway_id:
        vpn_gateway_id = iface.resource_id

    params.update({VPNGATEWAY_ID: vpn_gateway_id})

    vpc_id = params.get(VPC_ID) or ctx.instance.runtime_properties[
        'vpc_id']

    params.update({VPC_ID: vpc_id})
    iface.detach(params)

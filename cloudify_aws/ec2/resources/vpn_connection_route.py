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
    EC2.VPN Connection Route
    ~~~~~~~~~~~~~~
    AWS EC2 VPN Connection Route interface
"""
from __future__ import unicode_literals

# Cloudify
from cloudify_aws.common import decorators, utils
from cloudify_aws.ec2 import EC2Base


RESOURCE_TYPE = 'EC2 VPN Connection Route'
VPN_CONNECTION_ID = 'VpnConnectionId'
DESTINATION_CIDR_BLOCK = 'DestinationCidrBlock'


class EC2VPNConnectionRoute(EC2Base):
    """
        EC2 VPN Connection Route interface
    """
    def __init__(self, ctx_node, resource_id=None, client=None, logger=None):
        EC2Base.__init__(self, ctx_node, resource_id, client, logger)
        self.type_name = RESOURCE_TYPE

    @property
    def properties(self):
        """Gets the properties of an external resource"""
        pass

    @property
    def status(self):
        """Gets the status of an external resource"""
        pass

    def create(self, params):
        """Create a new AWS EC2 VPN Connection Route."""
        return self.make_client_call(
            'create_vpn_connection_route', params)

    def delete(self, params=None):
        """ Deletes an existing AWS EC2 VPN Connection Route."""
        self.client.delete_vpn_connection_route(**params)


@decorators.aws_resource(EC2VPNConnectionRoute, resource_type=RESOURCE_TYPE)
def prepare(ctx, resource_config, **_):
    """Prepares an AWS EC2 VPN Connection Route"""
    # Save the parameters
    ctx.instance.runtime_properties['resource_config'] = resource_config


@decorators.aws_resource(EC2VPNConnectionRoute, RESOURCE_TYPE)
def create(ctx, iface, resource_config, **_):
    """Creates an AWS EC2 VPN Connection Route"""
    resource_id = \
        utils.get_resource_id(
            ctx.node,
            ctx.instance,
            resource_config.get(VPN_CONNECTION_ID),
            use_instance_id=True
        )
    utils.update_resource_id(ctx.instance, resource_id)
    # Actually create the resource
    create_response = iface.create(resource_config)
    ctx.instance.runtime_properties['create_response'] = \
        utils.JsonCleanuper(create_response).to_dict()
    ctx.instance.runtime_properties['VPN_CONNECTION_ID'] = \
        resource_config.get(VPN_CONNECTION_ID)
    ctx.instance.runtime_properties['DESTINATION_CIDR_BLOCK'] = \
        resource_config.get(DESTINATION_CIDR_BLOCK)


@decorators.aws_resource(EC2VPNConnectionRoute, RESOURCE_TYPE)
def delete(ctx, iface, resource_config, **_):
    """Deletes an AWS EC2 VPN Connection Route"""
    vpn_connection = ctx.instance.runtime_properties.get('VPN_CONNECTION_ID')
    cider_block = ctx.instance.runtime_properties.get('DESTINATION_CIDR_BLOCK')

    params = dict(VpnConnectionId=vpn_connection,
                  DestinationCidrBlock=cider_block) \
        if not resource_config else resource_config.copy()
    iface.delete(params)

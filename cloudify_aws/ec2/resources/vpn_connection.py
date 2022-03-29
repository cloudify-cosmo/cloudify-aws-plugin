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
    EC2.VPN Connection
    ~~~~~~~~~~~~~~
    AWS EC2 VPN Connection interface
"""
from __future__ import unicode_literals


# Cloudify
from cloudify_aws.common import decorators, utils
from cloudify_aws.ec2 import EC2Base
from cloudify_aws.common import constants

RESOURCE_TYPE = 'EC2 VPN Connection'
VPN_CONNECTION_ID = 'VpnConnectionId'
VPN_CONNECTION_IDS = 'VpnConnectionIds'
VPN_CONNECTION = 'VpnConnection'
VPN_CONNECTIONS = 'VpnConnections'


class EC2VPNConnection(EC2Base):
    """
        EC2 VPN Connection interface
    """
    def __init__(self, ctx_node, resource_id=None, client=None, logger=None):
        EC2Base.__init__(self, ctx_node, resource_id, client, logger)
        self.type_name = RESOURCE_TYPE
        connection_id = ctx_node.properties.get(
            'resource_config', {}).get('kwargs', {}).get(VPN_CONNECTION_ID)
        if connection_id:
            self._describe_vpn_connection_filter = {
                VPN_CONNECTION_IDS: [connection_id]
            }
        elif self.resource_id:
            self._describe_vpn_connection_filter = {
                VPN_CONNECTION_IDS: [self.resource_id]
            }
        else:
            self._describe_vpn_connection_filter = {}
        self._describe_call = 'describe_vpn_connections'
        self._type_key = VPN_CONNECTIONS
        self._id_key = VPN_CONNECTION_ID
        self._ids_key = VPN_CONNECTION_IDS

    @property
    def describe_vpn_connection_filter(self):
        return self._describe_vpn_connection_filter

    @property
    def status(self):
        """Gets the status of an external resource"""
        props = self.properties
        if not props:
            return None
        return props.get('State')

    def create(self, params):
        """Create a new AWS EC2 VPN Connection."""
        return self.make_client_call('create_vpn_connection', params)

    def delete(self, params=None):
        """ Deletes an existing AWS EC2 VPN Connection."""
        self.client.delete_vpn_connection(**params)


def prepare_describe_vpn_connection_filter(params, iface):
    iface._describe_vpn_connection_filter = {
        VPN_CONNECTION_IDS: [params.get(VPN_CONNECTION_ID)],
    }


@decorators.aws_resource(EC2VPNConnection, resource_type=RESOURCE_TYPE)
def prepare(ctx, resource_config, **_):
    """Prepares an AWS EC2 VPN Connection"""
    # Save the parameters
    ctx.instance.runtime_properties['resource_config'] = resource_config


@decorators.aws_resource(EC2VPNConnection, RESOURCE_TYPE)
@decorators.wait_for_status(
    status_good=['available'],
    status_pending=['pending'],
    fail_on_missing=False)
def create(ctx, iface, resource_config, **_):
    """Creates an AWS EC2 VPN Connection"""
    # Actually create the resource
    create_response = iface.create(resource_config)[VPN_CONNECTION]
    ctx.instance.runtime_properties['create_response'] = \
        utils.JsonCleanuper(create_response).to_dict()
    if create_response:
        resource_id = \
            utils.get_resource_id(
                ctx.node,
                ctx.instance,
                create_response.get(VPN_CONNECTION_ID),
                use_instance_id=True
            )

        utils.update_resource_id(ctx.instance, resource_id)
        prepare_describe_vpn_connection_filter(create_response, iface)


@decorators.aws_resource(EC2VPNConnection, RESOURCE_TYPE)
@decorators.wait_for_delete(
    status_deleted=['deleted'],
    status_pending=['available', 'deleting', 'pending'])
def delete(ctx, iface, resource_config, **_):
    """Deletes an AWS EC2 VPN Connection"""
    deleted_params = dict()
    resource_id = \
        ctx.instance.runtime_properties[constants.EXTERNAL_RESOURCE_ID]
    deleted_params[VPN_CONNECTION_ID] = resource_id

    vpn_connection_config = ctx.instance.runtime_properties['resource_config']
    deleted_params['DryRun'] = vpn_connection_config.get('DryRun') or False
    iface.delete(deleted_params)

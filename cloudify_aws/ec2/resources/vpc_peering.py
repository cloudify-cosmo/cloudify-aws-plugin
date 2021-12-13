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
    EC2.VPCPeering
    ~~~~~~~~~~~~~~
    AWS EC2 VPC Peering interface
"""
from __future__ import unicode_literals

# Boto
from botocore.exceptions import ClientError, ParamValidationError

# Cloudify
from cloudify_aws.common import decorators, utils
from cloudify_aws.ec2 import EC2Base
from cloudify_aws.common import constants

RESOURCE_TYPE = 'EC2 Vpc Peering'
VPC_PEERING_CONNECTION = 'VpcPeeringConnection'
VPC_PEERING_CONNECTIONS = 'VpcPeeringConnections'
VPC_PEERING_CONNECTION_IDS = 'VpcPeeringConnectionIds'
VPC_PEERING_CONNECTION_ID = 'VpcPeeringConnectionId'

ACCEPTER_VPC_PEERING_CONNECTION = 'AccepterPeeringConnectionOptions'
REQUESTER_VPC_PEERING_CONNECTION = 'RequesterPeeringConnectionOptions'
PEER_VPC_ID = 'PeerVpcId'


class EC2VpcPeering(EC2Base):
    """EC2 Vpc Peering interface"""
    def __init__(self, ctx_node, resource_id=None, client=None, logger=None):
        EC2Base.__init__(self, ctx_node, resource_id, client, logger)
        self.type_name = RESOURCE_TYPE
        self._describe_vpc_peering_filter = {}

    @property
    def describe_vpc_peering_filter(self):
        return self._describe_vpc_peering_filter

    @property
    def properties(self):
        """Gets the properties of an external resource"""
        try:
            self.logger.info('Filter: {}'.format(
                self.describe_vpc_peering_filter))
            resources = \
                self.client.describe_vpc_peering_connections(
                    **self.describe_vpc_peering_filter
                )
        except (ClientError, ParamValidationError):
            resources = {}
        for vpc in self.describe_vpc_peering_filter.get(
                VPC_PEERING_CONNECTION_IDS, []):
            for vpc_peering_connection in resources.get(
                    VPC_PEERING_CONNECTIONS):
                if vpc == vpc_peering_connection['RequesterVpcInfo']['VpcId']:
                    return vpc_peering_connection

    @property
    def status(self):
        """Gets the status of an external resource"""
        props = self.properties
        if not props:
            return None
        return props.get('Status')

    def create(self, params):
        """Create a new AWS EC2 Vpc Peering."""
        return self.make_client_call('create_vpc_peering_connection', params)

    def update(self, params):
        """Updates a new AWS EC2 Vpc Peering."""
        self.logger.debug(
            'Updating {} with parameters: '
            '{}'.format(self.type_name, params)
        )
        res = self.client.modify_vpc_peering_connection_options(**params)
        self.logger.debug('Response: {}'.format(res))
        return res

    def delete(self, params=None):
        """Deletes an existing AWS EC2 Vpc Peering."""
        res = self.client.delete_vpc_peering_connection(**params)
        self.logger.debug('Response: {}'.format(res))
        return res

    def accept(self, params):
        """Updates a new AWS EC2 Vpc Peering."""
        self.logger.debug(
            'Accepting {} with parameters: '
            '{}'.format(self.type_name, params)
        )
        res = self.client.accept_vpc_peering_connection(**params)
        self.logger.debug('Response: {}'.format(res))
        return res

    def reject(self, params):
        """Rejects a new AWS EC2 Vpc Peering."""
        self.logger.debug(
            'Rejecting {} with parameters: '
            '{}'.format(self.type_name, params)
        )
        res = self.client.reject_vpc_peering_connection(**params)
        self.logger.debug('Response: {}'.format(res))
        return res


def prepare_describe_vpc_peering_filter(params, iface):
    iface._describe_vpc_peering_filter = {
        VPC_PEERING_CONNECTION_IDS: [params.get(PEER_VPC_ID)],
    }


@decorators.aws_resource(EC2VpcPeering, resource_type=RESOURCE_TYPE)
def prepare(ctx, resource_config, iface, **_):
    """Prepares an AWS EC2 Vpc Peering """
    # Save the parameters
    ctx.instance.runtime_properties['resource_config'] = resource_config
    prepare_describe_vpc_peering_filter(resource_config.copy(), iface)


@decorators.aws_resource(EC2VpcPeering, RESOURCE_TYPE)
@decorators.tag_resources
def create(ctx, iface, resource_config, **_):
    """Creates an AWS EC2 Vpc Peering"""
    params = dict() if not resource_config else resource_config.copy()

    # Accepter and Requester options are not part of create api, so we
    # Should check them if they are exists and then remove them
    accepter_vpc_options = params.get(ACCEPTER_VPC_PEERING_CONNECTION)
    requester_vpc_options = params.get(REQUESTER_VPC_PEERING_CONNECTION)

    if accepter_vpc_options:
        del params[ACCEPTER_VPC_PEERING_CONNECTION]

    if requester_vpc_options:
        del params[REQUESTER_VPC_PEERING_CONNECTION]

    # Actually create the resource
    create_response = iface.create(params)[VPC_PEERING_CONNECTION]
    ctx.instance.runtime_properties['create_response'] = \
        utils.JsonCleanuper(create_response).to_dict()
    if create_response:
        resource_id = \
            utils.get_resource_id(
                ctx.node,
                ctx.instance,
                create_response.get(VPC_PEERING_CONNECTION_ID),
                use_instance_id=True
            )

        utils.update_resource_id(ctx.instance, resource_id)
        prepare_describe_vpc_peering_filter(resource_config.copy(), iface)


@decorators.aws_resource(EC2VpcPeering, RESOURCE_TYPE)
def modify(ctx, iface, resource_config, **_):
    """Modifies an AWS EC2 Vpc Peering"""
    params = dict() if not resource_config else resource_config.copy()
    modify_options_param = dict()
    accepter_vpc_options = params.get(ACCEPTER_VPC_PEERING_CONNECTION)
    requester_vpc_options = params.get(REQUESTER_VPC_PEERING_CONNECTION)

    if accepter_vpc_options or requester_vpc_options:

        # Set the peer vpc id to update for
        modify_options_param[VPC_PEERING_CONNECTION_ID] = \
            ctx.instance.runtime_properties[constants.EXTERNAL_RESOURCE_ID]

        # Add accepter options to the params for modify if exists
        if accepter_vpc_options:
            modify_options_param[ACCEPTER_VPC_PEERING_CONNECTION]\
                = accepter_vpc_options

        # Add requester options to the params for modify if exists
        if requester_vpc_options:
            modify_options_param[ACCEPTER_VPC_PEERING_CONNECTION]\
                = accepter_vpc_options

        iface.update(modify_options_param)


@decorators.aws_resource(EC2VpcPeering, RESOURCE_TYPE)
@decorators.untag_resources
def delete(ctx, iface, resource_config, **_):
    """Deletes an AWS EC2 Vpc"""
    deleted_params = dict()

    # Get the resource_id of vpc peering connection
    resource_id = \
        ctx.instance.runtime_properties[constants.EXTERNAL_RESOURCE_ID]

    params = dict() if not resource_config else resource_config.copy()
    if params and resource_id:
        deleted_params[VPC_PEERING_CONNECTION_ID] = resource_id
        deleted_params['DryRun'] = params.get('DryRun') or False

    iface.delete(deleted_params)


@decorators.aws_resource(EC2VpcPeering, RESOURCE_TYPE)
def accept(ctx, iface, resource_config, **_):
    """Accepts an AWS EC2 Vpc Peer Request"""
    params = dict() if not resource_config else resource_config.copy()
    resource_id = \
        utils.get_resource_id(
            ctx.node,
            ctx.instance,
            params.get(VPC_PEERING_CONNECTION_ID),
            use_instance_id=True
        )

    utils.update_resource_id(ctx.instance, resource_id)
    iface.accept(params)


@decorators.aws_resource(EC2VpcPeering, RESOURCE_TYPE)
def reject(ctx, iface, resource_config, **_):
    """Rejects an AWS EC2 Vpc Peer Request"""
    params = dict() if not resource_config else resource_config.copy()
    resource_id = \
        utils.get_resource_id(
            ctx.node,
            ctx.instance,
            params.get(VPC_PEERING_CONNECTION_ID),
            use_instance_id=True
        )

    utils.update_resource_id(ctx.instance, resource_id)
    iface.reject(params)

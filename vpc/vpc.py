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

from boto import exception
from . import constants
from . import connection
from ec2 import utils as ec2_utils
from core.base import AwsBaseNode, AwsBaseRelationship
from cloudify import ctx
from cloudify.decorators import operation
from cloudify.exceptions import NonRecoverableError, RecoverableError

RESOURCE_TYPE = 'vpc'


@operation
def creation_validation(**_):
    return Vpc().creation_validation()


@operation
def create_vpc(**_):
    return Vpc().created()


@operation
def delete(**_):
    return Vpc().deleted()


@operation
def create_vpc_peering_connection(source_account_id, routes, **_):
    return VpcPeeringConnection(source_account_id, routes).associated()


@operation
def delete_vpc_peering_connection(**_):
    return VpcPeeringConnection().disassociated()


@operation
def accept_vpc_peering_connection(**_):
    target_aws_config = ctx.target.node.properties['aws_config']
    client = \
        connection.VPCConnectionClient().client(aws_config=target_aws_config)
    return VpcPeeringConnection(client=client).accept_vpc_peering_connection()


class VpcPeeringConnection(AwsBaseRelationship):

    def __init__(self, source_account_id=None, routes=None, client=None):
        super(VpcPeeringConnection, self).__init__(client=client)
        self.InvalidNotFoundError = 'InvalidVpcPeeringConnectionId.NotFound'
        self.resource_id = None
        self.source_account_id = source_account_id
        self.routes = routes
        self.source_vpc_id = \
            ctx.source.instance.runtime_properties.get('vpc_id')
        self.target_vpc_id = \
            ctx.target.instance.runtime_properties.get(
                constants.EXTERNAL_RESOURCE_ID
            )
        self.source_route_table_id =\
            ctx.source.instance.runtime_properties.get(
                constants.EXTERNAL_RESOURCE_ID
            )
        self.source_vpc_peering_connection_id = \
            self.get_vpc_peering_connection_id(
                ctx.source.instance,
                self.source_vpc_id,
                'vpc_id')
        self.target_vpc_peering_connection_id = \
            self.get_vpc_peering_connection_id(
                ctx.target.instance,
                self.target_vpc_id,
                'vpc_peer_id')
        self.source_get_all_matching = self.client.get_all_route_tables
        self.target_get_all_matching = self.client.get_all_vpcs

    def associated(self):
        if self.associate_external_resource():
            ctx.logger.info(
                'executing vpc peering connection association '
                'despite the fact that this is an external relationship'
            )
        if self.associate():
            return self.post_associate()

        raise NonRecoverableError(
            'Unable to associate {0} with {1}.'
            .format(self.source_resource_id, self.target_resource_id))

    def associate(self):

        associate_args = self.generate_associate_args()
        vpc_peering_connection = \
            self.raise_on_none(self.client.create_vpc_peering_connection,
                               associate_args)
        self.resource_id = vpc_peering_connection.id

        for route in self.routes:
            route.update(
                route_table_id=self.source_route_table_id,
                vpc_peering_connection_id=self.resource_id
            )

            try:
                self.client.create_route(**route)
            except exception.EC2ResponseError as e:
                if '<Code>RouteAlreadyExists</Code>' in str(e):
                    return True
                raise RecoverableError('{0}'.format(str(e)))

        return True

    def generate_associate_args(self):
        return dict(
            vpc_id=self.source_vpc_id,
            peer_vpc_id=self.target_vpc_id,
            peer_owner_id=self.source_account_id
        )

    def disassociate(self):
        self.pre_disassociate()
        disassociate_args = dict(
            vpc_peering_connection_id=self.source_vpc_peering_connection_id
        )
        return self.raise_on_none(self.client.delete_vpc_peering_connection,
                                  disassociate_args)

    def post_associate(self):
        cx = dict(
            vpc_peering_connection_id=self.resource_id,
            vpc_id=self.source_vpc_id,
            vpc_peer_id=self.target_vpc_id,
            routes=self.routes
        )
        if 'vpc_peering_connections' \
                not in ctx.source.instance.runtime_properties:
            ctx.source.instance.runtime_properties[
                'vpc_peering_connections'] = []
        ctx.source.instance.runtime_properties[
            'vpc_peering_connections'].append(cx)
        if 'vpc_peering_connections' \
                not in ctx.target.instance.runtime_properties:
            ctx.target.instance.runtime_properties[
                'vpc_peering_connections'] = []
        ctx.target.instance.runtime_properties[
            'vpc_peering_connections'].append(cx)
        return True

    def pre_disassociate(self):
        vpc_peering_connections = \
            ctx.source.instance.runtime_properties \
            .get('vpc_peering_connections')
        for vpc_peering_connection in vpc_peering_connections:
            ctx.logger.info('{0}'.format(vpc_peering_connection))
            for route in vpc_peering_connection['routes']:
                delete_args = dict(
                    route_table_id=route['route_table_id'],
                    destination_cidr_block=route['destination_cidr_block']
                )
                self.raise_on_none(self.client.delete_route, delete_args)

    def get_vpc_peering_connection_id(self, ctx_instance,
                                      vpc_id, property_name):

        vpc_peering_connections = \
            ctx_instance.runtime_properties \
            .get('vpc_peering_connections')

        if not vpc_peering_connections:
            return None

        for vpc_peering_connection in vpc_peering_connections:
            if vpc_id in vpc_peering_connection[property_name]:
                return vpc_peering_connection['vpc_peering_connection_id']

        return None

    def accept_vpc_peering_connection(self):

        try:
            output = self.client.accept_vpc_peering_connection(
                self.target_vpc_peering_connection_id)
        except exception.EC2ResponseError as e:
            if self.InvalidNotFoundError in str(e):
                return NonRecoverableError('{0}'.format(str(e)))
            elif '<Code>VpcPeeringConnectionAlreadyExists</Code>' in str(e):
                return True
            raise RecoverableError('{0}'.format(str(e)))

        return output


class Vpc(AwsBaseNode):

    def __init__(self):
        super(Vpc, self).__init__(
            RESOURCE_TYPE, constants.VPC_REQUIRED_PROPERTIES
        )
        self.InvalidNotFoundError = 'InvalidVpcID.NotFound'
        self.get_all_function = self.client.get_all_vpcs

    def create_external_resource(self):

        if not self.external_resource:
            return False

        resource = self.get_all_matching([self.resource_id])

        if not resource:
            self.raise_cannot_use_external_resource(self.resource_id)

        ctx.instance.runtime_properties['default_dhcp_options_id'] = \
            resource[0].dhcp_options_id
        ec2_utils.set_external_resource_id(self.resource_id, ctx.instance)

        return True

    def create(self):

        create_args = dict(
            cidr_block=ctx.node.properties['cidr_block'],
            instance_tenancy=ctx.node.properties['instance_tenancy']
        )

        vpc = self.raise_on_none(self.client.create_vpc, create_args)
        self.resource_id = vpc.id
        ctx.instance.runtime_properties['default_dhcp_options_id'] = \
            vpc.dhcp_options_id
        return True

    def delete(self):
        vpc = self.get_resource()
        return self.raise_on_none(vpc.delete)

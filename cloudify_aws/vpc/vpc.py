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

# Third-party Imports
from boto import exception

# Cloudify imports
from cloudify_aws import constants, connection, utils
from cloudify_aws.base import AwsBaseNode, AwsBaseRelationship, RouteMixin
from cloudify import ctx
from cloudify.decorators import operation
from cloudify.exceptions import NonRecoverableError, RecoverableError


@operation
def creation_validation(**_):
    return Vpc().creation_validation()


@operation
def create_vpc(args=None, **_):
    utils.add_create_args(**_)
    return Vpc().create_helper(args)


@operation
def start(args=None, **_):
    return Vpc().start_helper(args)


@operation
def delete(args=None, **_):
    return Vpc().delete_helper(args)


@operation
def create_vpc_peering_connection(target_account_id, routes, args=None, **_):
    return VpcPeeringConnection(target_account_id,
                                routes).associate_helper(args)


@operation
def delete_vpc_peering_connection(args=None, **_):
    return VpcPeeringConnection().disassociate_helper(args)


@operation
def accept_vpc_peering_connection(args=None, **_):
    target_aws_config = ctx.target.node.properties['aws_config']
    client = \
        connection.VPCConnectionClient().client(aws_config=target_aws_config)
    return VpcPeeringConnection(client=client).accept_vpc_peering_connection(
        args)


class VpcPeeringConnection(AwsBaseRelationship, RouteMixin):

    def __init__(self, target_account_id=None, routes=None, client=None):
        super(VpcPeeringConnection, self).__init__(
            client=connection.VPCConnectionClient().client()
        )
        self.not_found_error = 'InvalidVpcPeeringConnectionId.NotFound'
        self.resource_id = None
        self.target_account_id = target_account_id \
            if target_account_id else None
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
                self.source_vpc_id,
                'vpc_peer_id')
        self.source_get_all_handler = {
            'function': self.client.get_all_route_tables,
            'argument':
            '{0}_ids'.format(constants.ROUTE_TABLE['AWS_RESOURCE_TYPE'])
        }

    def associate_helper(self, args):
        if self.use_source_external_resource_naively():
            ctx.logger.info(
                'executing vpc peering connection association '
                'despite the fact that this is an external relationship'
            )
        if self.associate(args):
            return self.post_associate()

        raise NonRecoverableError(
            'Unable to associate {0} with {1}.'
            .format(self.source_resource_id, self.target_resource_id))

    def associate(self, args):

        associate_args = utils.update_args(
            self._generate_association_args(),
            args)
        vpc_peering_connection = \
            self.execute(self.client.create_vpc_peering_connection,
                         associate_args, raise_on_falsy=True)
        self.resource_id = vpc_peering_connection.id

        for route in self.routes:
            route.update(
                route_table_id=self.source_route_table_id,
                vpc_peering_connection_id=self.resource_id
            )
            self.create_route(self.source_route_table_id, route,
                              route_table_ctx_instance=ctx.source.instance)

        return True

    def _generate_association_args(self):
        return dict(
            vpc_id=self.source_vpc_id,
            peer_vpc_id=self.target_vpc_id,
            peer_owner_id=self.target_account_id
        )

    def disassociate(self, args):
        self.delete_routes()
        self.delete_target_routes()
        disassociate_args = dict(
            vpc_peering_connection_id=self.source_vpc_peering_connection_id
        )
        disassociate_args = utils.update_args(
            disassociate_args,
            args)

        return self.execute(self.client.delete_vpc_peering_connection,
                            disassociate_args, raise_on_falsy=True)

    def post_associate(self):
        cx = dict(
            vpc_peering_connection_id=self.resource_id,
            vpc_id=self.source_vpc_id,
            vpc_peer_id=self.target_vpc_id,
            routes=self.routes
        )
        target_peering_connection = dict(
            vpc_peering_connection_id=self.resource_id,
            vpc_id=self.target_vpc_id,
            vpc_peer_id=self.source_vpc_id,
            routes=[]
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
            'vpc_peering_connections'].append(target_peering_connection)
        return True

    def delete_routes(self):
        vpc_peering_connections = \
            ctx.source.instance.runtime_properties \
            .get('vpc_peering_connections')
        for vpc_peering_connection in vpc_peering_connections:
            ctx.logger.info('{0}'.format(vpc_peering_connection))
            for route in vpc_peering_connection['routes']:
                self.delete_route(
                    self.source_route_table_id, route,
                    route_table_ctx_instance=ctx.source.instance)

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

    def accept_vpc_peering_connection(self, args):

        try:
            output = self.client.accept_vpc_peering_connection(
                self.target_vpc_peering_connection_id)
        except exception.EC2ResponseError as e:
            if self.not_found_error in str(e):
                raise NonRecoverableError('{0}'.format(str(e)))
            elif '<Code>VpcPeeringConnectionAlreadyExists</Code>' in str(e):
                return True
            raise RecoverableError('{0}'.format(str(e)))

        if output:
            if not self.add_route_to_target_vpc():
                raise NonRecoverableError(
                    'Unable to save route to target VPC route tables.')

        return True

    def add_route_to_target_vpc(self):
        """ Adds a return route on to the target VPC route tables
        :return: Boolean, True if all were successful, False if
        at least one failed.
        """

        source_vpc_cidr_block = ''
        target_vpc_peering_connections = []

        vpcs = self.execute(self.client.get_all_vpcs)
        for vpc in vpcs:
            if vpc.id == self.source_vpc_id:
                source_vpc_cidr_block = vpc.cidr_block

        new_route = dict(
            destination_cidr_block=source_vpc_cidr_block,
            vpc_peering_connection_id=self.source_vpc_peering_connection_id
        )

        route_tables = self.execute(self.client.get_all_route_tables)
        for route_table in route_tables:
            if route_table.vpc_id == self.target_vpc_id:
                route_created = self.create_route(
                    route_table_id=route_table.id,
                    route=new_route
                )
                created_route = new_route
                created_route.update({'route_table_id': route_table.id})
                ctx.logger.debug('created target vpc route: {0}'.format(
                    created_route))
                for vpc_peering_connection in \
                        ctx.target.instance.runtime_properties[
                            'vpc_peering_connections']:
                    if vpc_peering_connection['vpc_peering_connection_id'] \
                            == self.source_vpc_peering_connection_id:
                        vpc_peering_connection['routes'].append(created_route)
                        target_vpc_peering_connections.append(
                            vpc_peering_connection)
                if not route_created:
                    return False

        ctx.target.instance.runtime_properties['vpc_peering_connections'] = \
            target_vpc_peering_connections

        return True

    def delete_target_routes(self):
        target_aws_config = ctx.target.node.properties['aws_config']
        client = connection.VPCConnectionClient().client(
            aws_config=target_aws_config)
        target_vpc_peering_connections = \
            ctx.target.instance.runtime_properties \
            .get('vpc_peering_connections')
        for vpc_peering_connection in target_vpc_peering_connections:
            ctx.logger.debug('VPC peering connection: {0}'.format(
                vpc_peering_connection))
            for route in vpc_peering_connection['routes']:
                args = dict(
                    route_table_id=route['route_table_id'],
                    destination_cidr_block=route['destination_cidr_block']
                )
                try:
                    output = client.delete_route(**args)
                except exception.EC2ResponseError as e:
                    if constants.ROUTE_NOT_FOUND_ERROR in str(e):
                        ctx.logger.info(
                            'Could not delete route: {0} route not '
                            'found on route_table.'
                            .format(route, route['route_table_id']))
                        return True
                    raise NonRecoverableError('{0}'.format(str(e)))

                if output:
                    if route in vpc_peering_connection['routes']:
                        vpc_peering_connection['routes'].remove(route)
                    return True
                return False


class Vpc(AwsBaseNode):

    def __init__(self):
        super(Vpc, self).__init__(
            constants.VPC['AWS_RESOURCE_TYPE'],
            constants.VPC['REQUIRED_PROPERTIES'],
            client=connection.VPCConnectionClient().client(),
            resource_states=constants.VPC['STATES']
        )
        self.not_found_error = constants.VPC['NOT_FOUND_ERROR']
        self.get_all_handler = {
            'function': self.client.get_all_vpcs,
            'argument': '{0}_ids'.format(constants.VPC['AWS_RESOURCE_TYPE'])
        }

    def create(self, args):

        create_args = dict(
            cidr_block=ctx.node.properties['cidr_block'],
            instance_tenancy=ctx.node.properties['instance_tenancy']
        )
        create_args = utils.update_args(
            create_args,
            args)
        vpc = self.execute(self.client.create_vpc,
                           create_args, raise_on_falsy=True)
        self.resource_id = vpc.id
        utils.set_external_resource_id(vpc.id, ctx.instance)
        ctx.instance.runtime_properties['default_dhcp_options_id'] = \
            vpc.dhcp_options_id
        return True

    def start(self, args):
        return True

    def delete(self, args):
        vpc = self.get_resource()
        if not vpc:
            return True
        return self.execute(vpc.delete, raise_on_falsy=True)

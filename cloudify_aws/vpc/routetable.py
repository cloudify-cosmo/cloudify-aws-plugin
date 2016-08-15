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

# Cloudify imports
from cloudify_aws import constants, utils, connection
from cloudify_aws.base import AwsBaseNode, AwsBaseRelationship, RouteMixin
from cloudify import ctx
from cloudify.decorators import operation
from cloudify.exceptions import NonRecoverableError


@operation
def creation_validation(**_):
    return RouteTable().creation_validation()


@operation
def create_route_table(routes, args=None, **_):
    return RouteTable(routes).created(args)


@operation
def start_route_table(args=None, **_):
    return RouteTable().started(args)


@operation
def delete_route_table(args=None, **_):
    return RouteTable().deleted(args)


@operation
def associate_route_table(**_):
    return RouteTableSubnetAssociation().associated()


@operation
def disassociate_route_table(**_):
    return RouteTableSubnetAssociation().disassociated()


@operation
def create_route_to_gateway(destination_cidr_block, args=None, **_):
    return RouteTableGatewayAssociation(
        destination_cidr_block).associated(args)


@operation
def delete_route_from_gateway(**_):
    return RouteTableGatewayAssociation().disassociated()


class RouteTableGatewayAssociation(AwsBaseRelationship, RouteMixin):

    def __init__(self, destination_cidr_block=None):
        super(RouteTableGatewayAssociation, self).__init__(
            client=connection.VPCConnectionClient().client()
        )
        self.source_get_all_handler = {
            'function': self.client.get_all_route_tables,
            'argument':
            '{0}_ids'.format(constants.ROUTE_TABLE['AWS_RESOURCE_TYPE'])
        }
        self.destination_cidr_block = destination_cidr_block

    def associate(self, args):

        route = dict(
            destination_cidr_block=self.destination_cidr_block if
            self.destination_cidr_block else
            ctx.target.node.properties.get('cidr_block'),
            gateway_id=ctx.target.instance.runtime_properties[
                constants.EXTERNAL_RESOURCE_ID]
        )

        return self.create_route(
            ctx.source.instance.runtime_properties[
                constants.EXTERNAL_RESOURCE_ID],
            route, ctx.source.instance
        )

    def disassociate(self, args):
        route = dict(
            destination_cidr_block=ctx.target.node.properties['cidr_block'],
            gateway_id=ctx.target.instance.runtime_properties[
                constants.EXTERNAL_RESOURCE_ID]
        )
        return self.delete_route(
            ctx.source.instance.runtime_properties.get(
                constants.EXTERNAL_RESOURCE_ID),
            route,
            route_table_ctx_instance=ctx.source.instance
        )


class RouteTableSubnetAssociation(AwsBaseRelationship):
    def __init__(self):
        super(RouteTableSubnetAssociation, self).__init__(
            client=connection.VPCConnectionClient().client()
        )
        self.association_id = \
            ctx.source.instance.runtime_properties.get(
                'association_id', None)
        self.source_get_all_handler = {
            'function': self.client.get_all_route_tables,
            'argument':
            '{0}_ids'.format(constants.ROUTE_TABLE['AWS_RESOURCE_TYPE'])
        }

    def associate(self, args=None):
        associate_args = dict(
            route_table_id=self.source_resource_id,
            subnet_id=self.target_resource_id
        )
        associate_args = utils.update_args(associate_args, args)
        self.association_id = \
            self.execute(self.client.associate_route_table,
                         associate_args, raise_on_falsy=True)
        return True

    def disassociate(self, args=None):
        disassociate_args = dict(association_id=self.association_id)
        disassociate_args = utils.update_args(disassociate_args, args)
        return self.execute(self.client.disassociate_route_table,
                            disassociate_args, raise_on_falsy=True)

    def post_associate(self):
        ctx.source.instance.runtime_properties['association_id'] = \
            self.association_id
        ctx.source.instance.runtime_properties['subnet_id'] = \
            self.target_resource_id
        return True

    def post_disassociate(self):
        ctx.source.instance.runtime_properties.pop('association_id')
        ctx.source.instance.runtime_properties.pop('subnet_id')
        return True


class RouteTable(AwsBaseNode, RouteMixin):

    def __init__(self, routes=None):
        super(RouteTable, self).__init__(
            constants.ROUTE_TABLE['AWS_RESOURCE_TYPE'],
            constants.ROUTE_TABLE['REQUIRED_PROPERTIES'],
            client=connection.VPCConnectionClient().client()
        )
        self.not_found_error = constants.ROUTE_TABLE['NOT_FOUND_ERROR']
        self.get_all_handler = {
            'function': self.client.get_all_route_tables,
            'argument':
            '{0}_ids'.format(constants.ROUTE_TABLE['AWS_RESOURCE_TYPE'])
        }
        self.routes = \
            ctx.instance.runtime_properties.get('routes') \
            if 'routes' \
            in ctx.instance.runtime_properties.keys() else routes

    def create(self, args=None):
        create_args = utils.update_args(self._generate_creation_args(),
                                        args)
        route_table = \
            self.execute(self.client.create_route_table,
                         create_args, raise_on_falsy=True)
        self.resource_id = route_table.id
        for route in self.routes:
            self.create_route(route_table.id, route, ctx.instance)
        return True

    def _generate_creation_args(self):
        vpc = self.get_containing_vpc()
        return dict(vpc_id=vpc.id)

    def get_containing_vpc(self):
        relationships = \
            self.get_related_targets_and_types(ctx.instance.relationships)
        vpc_ids = \
            self.get_target_ids_of_relationship_type(
                constants.ROUTE_TABLE_VPC_RELATIONSHIP, relationships)
        if not len(vpc_ids) == 1:
            raise NonRecoverableError(
                'routetable can only be connected to one vpc')
        vpc = self.filter_for_single_resource(
            self.client.get_all_vpcs,
            {'vpc_ids': vpc_ids[0]},
            constants.VPC['NOT_FOUND_ERROR']
        )
        return vpc

    def post_create(self):
        vpc = self.get_containing_vpc()
        ctx.instance.runtime_properties['vpc_id'] = vpc.id
        ctx.instance.runtime_properties['routes'] = self.routes
        utils.set_external_resource_id(self.resource_id, ctx.instance)
        ctx.logger.info(
            'Added {0} {1} to Cloudify.'
            .format(self.aws_resource_type, self.resource_id))
        return True

    def start(self, args):
        return True

    def delete(self, args):
        for route in self.routes:
            self.delete_route(
                ctx.instance.runtime_properties.get(
                    constants.EXTERNAL_RESOURCE_ID),
                route,
                route_table_ctx_instance=ctx.instance
            )
        delete_args = dict(
            route_table_id=ctx.instance.runtime_properties.get(
                constants.EXTERNAL_RESOURCE_ID
            )
        )
        delete_args = utils.update_args(delete_args, args)
        return self.execute(self.client.delete_route_table,
                            delete_args, raise_on_falsy=True)

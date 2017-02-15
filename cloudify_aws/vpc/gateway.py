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
from cloudify_aws.base import AwsBaseNode, AwsBaseRelationship
from cloudify import ctx
from cloudify.decorators import operation


@operation
def creation_validation(**_):
    if 'cloudify.aws.nodes.InternetGateway' in ctx.node.type_hierarchy:
        return InternetGateway().creation_validation()
    if 'cloudify.aws.nodes.VPNGateway' in ctx.node.type_hierarchy:
        return VpnGateway().creation_validation()
    if 'cloudify.aws.nodes.CustomerGateway' in ctx.node.type_hierarchy:
        return CustomerGateway().creation_validation()


@operation
def create_internet_gateway(args=None, **_):
    return InternetGateway().create_helper(args)


def start_internet_gateway(args=None, **_):
    return InternetGateway().start_helper(args)


@operation
def delete_internet_gateway(args=None, **_):
    return InternetGateway().delete_helper(args)


@operation
def create_vpn_gateway(args=None, **_):
    return VpnGateway().create_helper(args)


@operation
def start_vpn_gateway(args=None, **_):
    return VpnGateway().start_helper(args)


@operation
def delete_vpn_gateway(args=None, **_):
    return VpnGateway().delete_helper(args)


@operation
def create_customer_gateway(args=None, **_):
    return CustomerGateway().create_helper(args)


@operation
def start_customer_gateway(args=None, **_):
    return CustomerGateway().start_helper(args)


@operation
def delete_customer_gateway(args=None, **_):
    return CustomerGateway().delete_helper(args)


@operation
def create_vpn_connection(routes, args=None, **_):
    return VpnConnection(routes).associate_helper(args)


@operation
def delete_vpn_connection(args=None, **_):
    return VpnConnection().disassociate_helper(args)


@operation
def attach_gateway(args=None, **_):
    return GatewayVpcAttachment().associate_helper(args)


@operation
def detach_gateway(args=None, **_):
    return GatewayVpcAttachment().disassociate_helper(args)


class VpnConnection(AwsBaseRelationship):

    def __init__(self, routes=None):
        super(VpnConnection, self).__init__(
            client=connection.VPCConnectionClient().client()
        )
        self.vpn_type = ctx.source.node.properties['type']
        self.routes = \
            routes if routes else \
            ctx.source.instance.runtime_properties.get('routes', None)
        self.vpn_connection_id = \
            ctx.source.instance.runtime_properties.get(
                'vpn_connection') if 'vpn_connection' in \
            ctx.source.instance.runtime_properties.keys() else None
        self.source_get_all_handler = {
            'function': self.client.get_all_customer_gateways,
            'argument':
            '{0}_ids'.format(constants.CUSTOMER_GATEWAY['AWS_RESOURCE_TYPE'])
        }

    def associate(self, args):
        associate_args = utils.update_args(
            self.generate_associate_args(self.routes),
            args)
        vpn_connection = self.execute(self.client.create_vpn_connection,
                                      associate_args, raise_on_falsy=True)
        ctx.source.instance.runtime_properties['vpn_connection'] = \
            vpn_connection.id
        ctx.source.instance.runtime_properties['vpn_gateway'] = \
            vpn_connection.vpn_gateway_id
        if 'routes' not in ctx.source.instance.runtime_properties.keys():
            ctx.source.instance.runtime_properties['routes'] = []
        if self.routes:
            for route in self.routes:
                args = self.generate_route_args(vpn_connection.id, route)
                self.execute(self.client.create_vpn_connection_route,
                             args, raise_on_falsy=True)
                ctx.source.instance.runtime_properties['routes'].append(route)
        return True

    def generate_associate_args(self, routes):

        return dict(
            type=self.vpn_type,
            customer_gateway_id=self.source_resource_id,
            vpn_gateway_id=self.target_resource_id,
            static_routes_only=False if not routes or not
            ctx.source.node.properties['bgp_asn'] else True
        )

    def generate_route_args(self, vpn_connection_id, route):
        args = dict(
            destination_cidr_block=route['destination_cidr_block'],
            vpn_connection_id=vpn_connection_id
        )
        return args

    def disassociate(self, args):
        if self.routes:
            for route in self.routes:
                args = self.generate_route_args(self.vpn_connection_id, route)
                if self.execute(
                        self.client.delete_vpn_connection_route,
                        args, raise_on_falsy=True):
                    ctx.source.instance.runtime_properties['routes'].remove(
                        route)
        disassociate_args = dict(vpn_connection_id=self.vpn_connection_id)
        disassociate_args = utils.update_args(disassociate_args, args)
        return self.execute(self.client.delete_vpn_connection,
                            disassociate_args, raise_on_falsy=True)


class GatewayVpcAttachment(AwsBaseRelationship):
    def __init__(self, routes=None):
        super(GatewayVpcAttachment, self).__init__(
            client=connection.VPCConnectionClient().client()
        )
        self.vpn_type = 'ipsec.1'
        if self.is_vpn_gateway():
            self.attachment_function = self.client.attach_vpn_gateway
            self.attachment_args = dict(
                vpn_gateway_id=self.source_resource_id,
                vpc_id=self.target_resource_id
            )
            self.detachment_function = self.client.detach_vpn_gateway
            self.detachment_args = dict(
                vpn_gateway_id=self.source_resource_id,
                vpc_id=self.target_resource_id
            )
            self.source_get_all_handler = {
                'function': self.client.get_all_vpn_gateways,
                'argument':
                '{0}_ids'.format(constants.VPN_GATEWAY['AWS_RESOURCE_TYPE'])
            }
        else:
            self.attachment_function = self.client.attach_internet_gateway
            self.attachment_args = dict(
                internet_gateway_id=self.source_resource_id,
                vpc_id=self.target_resource_id
            )
            self.detachment_function = self.client.detach_internet_gateway
            self.detachment_args = dict(
                internet_gateway_id=self.source_resource_id,
                vpc_id=self.target_resource_id
            )
            self.source_get_all_handler = {
                'function': self.client.get_all_internet_gateways,
                'argument':
                    '{0}_ids'.format(
                        constants.INTERNET_GATEWAY['AWS_RESOURCE_TYPE'])
            }

    def associate(self, args):
        attachment_args = utils.update_args(self.attachment_args, args)
        return self.execute(self.attachment_function,
                            attachment_args, raise_on_falsy=True)

    def disassociate(self, args):
        detachment_args = utils.update_args(self.detachment_args, args)
        return self.execute(self.detachment_function,
                            detachment_args,
                            raise_on_falsy=True)

    def is_vpn_gateway(self):
        if constants.VPN_GATEWAY['CLOUDIFY_NODE_TYPE'] in \
                ctx.source.node.type_hierarchy \
                and constants.CUSTOMER_GATEWAY['CLOUDIFY_NODE_TYPE'] \
                not in ctx.source.node.type_hierarchy:
            return True
        return False

    def post_associate(self):
        ctx.source.instance.runtime_properties['vpc_id'] = \
            self.target_resource_id

    def post_disassociate(self):
        utils.unassign_runtime_property_from_resource(
            'vpc_id', ctx.source.instance)


class InternetGateway(AwsBaseNode):

    def __init__(self):
        super(InternetGateway, self).__init__(
            constants.INTERNET_GATEWAY['AWS_RESOURCE_TYPE'],
            constants.INTERNET_GATEWAY['REQUIRED_PROPERTIES'],
            client=connection.VPCConnectionClient().client()
        )
        self.not_found_error = constants.INTERNET_GATEWAY['NOT_FOUND_ERROR']
        self.get_all_handler = {
            'function': self.client.get_all_internet_gateways,
            'argument':
            '{0}_ids'.format(constants.INTERNET_GATEWAY['AWS_RESOURCE_TYPE'])
        }

    def create(self, args):
        gateway = self.execute(self.client.create_internet_gateway,
                               raise_on_falsy=True)
        self.resource_id = gateway.id
        return True

    def start(self, args):
        return True

    def delete(self, args):
        delete_args = dict(internet_gateway_id=self.resource_id)
        delete_args = utils.update_args(delete_args, args)
        return self.execute(self.client.delete_internet_gateway,
                            delete_args)


class VpnGateway(AwsBaseNode):

    def __init__(self):
        super(VpnGateway, self).__init__(
            constants.VPN_GATEWAY['AWS_RESOURCE_TYPE'],
            constants.VPN_GATEWAY['REQUIRED_PROPERTIES'],
            client=connection.VPCConnectionClient().client()
        )
        self.not_found_error = constants.VPN_GATEWAY['NOT_FOUND_ERROR']
        self.get_all_handler = {
            'function': self.client.get_all_vpn_gateways,
            'argument':
                '{0}_ids'.format(constants.VPN_GATEWAY['AWS_RESOURCE_TYPE'])
        }

    def create(self, args):
        create_args = dict(
            type=ctx.node.properties['type'],
            availability_zone=ctx.node.properties.get(
                'availability_zone', None)
        )
        create_args = utils.update_args(create_args, args)
        gateway = self.execute(self.client.create_vpn_gateway,
                               create_args, raise_on_falsy=True)
        self.resource_id = gateway.id
        return True

    def start(self, args):
        return True

    def delete(self, args):
        delete_args = dict(vpn_gateway_id=self.resource_id)
        delete_args = utils.update_args(delete_args, args)
        return self.execute(self.client.delete_vpn_gateway, delete_args)


class CustomerGateway(AwsBaseNode):

    def __init__(self):
        super(CustomerGateway, self).__init__(
            constants.CUSTOMER_GATEWAY['AWS_RESOURCE_TYPE'],
            constants.CUSTOMER_GATEWAY['REQUIRED_PROPERTIES'],
            client=connection.VPCConnectionClient().client()
        )
        self.not_found_error = constants.CUSTOMER_GATEWAY['NOT_FOUND_ERROR']
        self.get_all_handler = {
            'function': self.client.get_all_customer_gateways,
            'argument':
            '{0}_ids'.format(constants.CUSTOMER_GATEWAY['AWS_RESOURCE_TYPE'])
        }

    def create(self, args):
        create_args = dict(
            type=ctx.node.properties['type'],
            ip_address=ctx.node.properties['ip_address'],
            bgp_asn=ctx.node.properties['bgp_asn']
        )
        create_args = utils.update_args(create_args, args)
        gateway = self.execute(self.client.create_customer_gateway,
                               create_args, raise_on_falsy=True)
        self.resource_id = gateway.id
        return True

    def start(self, args):
        return True

    def delete(self, args):
        delete_args = dict(customer_gateway_id=self.resource_id)
        delete_args = utils.update_args(delete_args, args)
        return self.execute(self.client.delete_customer_gateway,
                            delete_args)

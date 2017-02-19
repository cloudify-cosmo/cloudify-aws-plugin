"""
# Copyright (c) 2017 GigaSpaces Technologies Ltd. All rights reserved
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
"""

# Third-party Imports
from boto import exception

# Cloudify imports
from cloudify import ctx
from cloudify.decorators import operation
from cloudify_aws.base import AwsBaseNode, AwsBaseRelationship
from cloudify_aws import utils
from cloudify.exceptions import NonRecoverableError, RecoverableError


@operation
def create(args=None, **_):
    """ Create the Network Interface """
    return Interface().create_helper(args)


@operation
def start(args, **_):
    return Interface().start_helper(args)


@operation
def delete(args=None, **_):
    """ Delete the Network Interface """
    return Interface().delete_helper(args)


@operation
def associate(args=None, **_):
    """ Attach the Network Interface """
    return InterfaceAttachment().associate_helper(args)


@operation
def disassociate(args=None, **_):
    """ Dettach the Network Interface """
    return InterfaceAttachment().disassociate_helper(args)


class InterfaceAttachment(AwsBaseRelationship):

    def __init__(self, client=None):
        super(InterfaceAttachment, self).__init__(client=client)
        self.resource_id = None
        self.source_get_all_handler = {
            'function': self.client.get_all_network_interfaces,
            'argument':
                '{0}_ids'.format('network_interface')
        }

    def associate(self, args=None, **_):
        """ Associates an ENI created by Cloudify with an EC2 Instance
        that was also created by Cloudify.
        """

        network_interface_id = self.source_resource_id
        instance_id = self.target_resource_id

        attachment_args = dict(network_interface_id=network_interface_id,
                               instance_id=instance_id,
                               device_index=1)

        attachment_args = utils.update_args(attachment_args, args)

        try:
            output = self.execute(self.client.attach_network_interface,
                                  attachment_args,
                                  raise_on_falsy=True)
        except (exception.EC2ResponseError,
                exception.BotoServerError) as e:
            raise NonRecoverableError('{0}'.format(str(e)))

        if not output:
            raise RecoverableError(
                'Failed to attach eni    {0} to instance {1}'
                .format(self.source_resource_id,
                        self.target_resource_id)
            )

        network_interface = self.get_source_resource()
        ctx.source.instance.runtime_properties['attachment_id'] = \
            network_interface.attachment.id

        return output

    def disassociate(self, args=None, **_):
        """ Disassocates an ENI created by Cloudify from an EC2 Instance
        that was also created by Cloudify.
        """

        attachment_id = \
            ctx.source.instance.runtime_properties.pop('attachment_id')

        detach_args = dict(attachment_id=attachment_id)

        detach_args = utils.update_args(detach_args, args)

        try:
            output = self.execute(self.client.detach_network_interface,
                                  detach_args, raise_on_falsy=True)
        except (exception.EC2ResponseError,
                exception.BotoServerError) as e:
            raise NonRecoverableError('{0}'.format(str(e)))

        if not output:
            ctx.source.instance.runtime_properties['attachment_id'] = \
                attachment_id
            raise RecoverableError(
                'Failed to detach network interface {0} '
                'from instance {1}'
                .format(
                    self.source_resource_id,
                    self.target_resource_id
                )
            )
        return output


class Interface(AwsBaseNode):

    def __init__(self, client=None):
        super(Interface, self).__init__(
            'network_interface',
            [],
            client=client
        )
        self.get_all_handler = {
            'function': self.client.get_all_network_interfaces,
            'argument': '{0}_ids'.format('network_interface')
        }

    def create(self, args=None, **_):

        create_args = ctx.node.properties['parameters']

        list_of_subnets = \
            utils.get_target_external_resource_ids(
                'cloudify.aws.relationships.connected_to_subnet', ctx.instance
            )

        if not list_of_subnets:
            ctx.logger.debug('There is no relationship of type '
                             'cloudify.aws.relationships.connected_to_subnet '
                             'The user is expected to provide a '
                             'parameters.subnet_id property.')
        elif len(list_of_subnets) == 1:
            ctx.logger.info('Setting subnet ID to {0}'
                            .format(list_of_subnets[0]))
            create_args.update({'subnet_id': list_of_subnets[0]})
        elif len(list_of_subnets) > 1 \
                or len(list_of_subnets) == 1 and \
                ctx.node.properties['parameters'].get('subnet_id') is not None:
            raise NonRecoverableError(
                'More than one subnet was specified. '
                'A network interface can only exist in one subnet.'
            )

        create_args = utils.update_args(create_args, args)

        ctx.logger.info(
            'Attempting to create Network Interface with these API '
            'parameters: {0}.'
            .format(create_args))

        try:
            network_interface = self.execute(
                self.client.create_network_interface,
                create_args, raise_on_falsy=True)
        except (exception.EC2ResponseError,
                exception.BotoServerError) as e:
            raise NonRecoverableError('{0}'.format(str(e)))

        self.resource_id = network_interface.id

        ctx.instance.runtime_properties['subnet_id'] = \
            network_interface.subnet_id
        ctx.instance.runtime_properties['vpc_id'] = \
            network_interface.vpc_id
        ctx.instance.runtime_properties['description'] = \
            network_interface.description
        ctx.instance.runtime_properties['owner_id'] = \
            network_interface.owner_id
        ctx.instance.runtime_properties['requester_managed'] = \
            network_interface.requester_managed
        ctx.instance.runtime_properties['status'] = \
            network_interface.status
        ctx.instance.runtime_properties['mac_address'] = \
            network_interface.mac_address
        ctx.instance.runtime_properties['private_ip_address'] = \
            network_interface.private_ip_address
        ctx.instance.runtime_properties['source_dest_check'] = \
            network_interface.source_dest_check
        ctx.instance.runtime_properties['groups'] = \
            [group.id for group in network_interface.groups]
        ctx.instance.runtime_properties['private_ip_addresses'] = \
            [(private_ip.private_ip_address, private_ip.primary)
             for private_ip in network_interface.private_ip_addresses]

        return True

    def delete(self, args=None, **_):

        network_interface_id = self.resource_id

        delete_args = dict(network_interface_id=network_interface_id)
        delete_args = utils.update_args(delete_args, args)

        try:
            output = self.execute(self.client.delete_network_interface,
                                  delete_args,
                                  raise_on_falsy=True)
        except (exception.EC2ResponseError,
                exception.BotoServerError) as e:
            raise NonRecoverableError('{0}'.format(str(e)))

        return output

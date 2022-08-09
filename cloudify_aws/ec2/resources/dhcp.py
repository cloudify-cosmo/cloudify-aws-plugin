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
    EC2.DhcpOptions
    ~~~~~~~~~~~~~~
    AWS EC2 DhcpOptions interface
"""

# Cloudify
from cloudify_aws.common import decorators, utils
from cloudify_aws.ec2 import EC2Base
from cloudify_aws.common.constants import EXTERNAL_RESOURCE_ID

RESOURCE_TYPE = 'EC2 Dhcp Options'
DHCPOPTIONS = 'DhcpOptions'
DHCPOPTIONS_ID = 'DhcpOptionsId'
DHCPOPTIONS_IDS = 'DhcpOptionsIds'
VPC_ID = 'VpcId'
VPC_TYPE = 'cloudify.nodes.aws.ec2.Vpc'
VPC_TYPE_DEPRECATED = 'cloudify.aws.nodes.Vpc'


class EC2DHCPOptions(EC2Base):
    """
        EC2 DhcpOptions interface
    """
    def __init__(self, ctx_node, resource_id=None, client=None, logger=None):
        EC2Base.__init__(self, ctx_node, resource_id, client, logger)
        self.type_name = RESOURCE_TYPE
        self._describe_call = 'describe_dhcp_options'
        self._type_key = DHCPOPTIONS
        self._id_key = DHCPOPTIONS_ID
        self._ids_key = DHCPOPTIONS_IDS

    def create(self, params):
        """
            Create a new AWS EC2 DhcpOptions.
        """
        return self.make_client_call('create_dhcp_options', params)

    def delete(self, params=None):
        """
            Deletes an existing AWS EC2 DhcpOptions.
        """
        self.logger.debug('Deleting %s with parameters: %s'
                          % (self.type_name, params))
        res = self.client.delete_dhcp_options(**params)
        self.logger.debug('Response: %s' % res)
        return res

    def attach(self, params):
        '''
            Attach an AWS EC2 DhcpOptions to a VPC.
        '''
        self.logger.debug('Attaching %s with: %s'
                          % (self.type_name, params.get(VPC_ID, None)))
        res = self.client.associate_dhcp_options(**params)
        self.logger.debug('Response: %s' % res)
        return res

    def detach(self, params):
        '''
            Detach an AWS EC2 VPN Gateway from a VPC.
        '''
        self.logger.debug('Detaching %s from: %s'
                          % (self.type_name, params.get(VPC_ID, None)))
        self.logger.debug('Attaching default %s'
                          % (self.type_name))
        res = self.client.associate_dhcp_options(**params)
        self.logger.debug('Response: %s' % res)
        return res


@decorators.aws_resource(EC2DHCPOptions,
                         resource_type=RESOURCE_TYPE,
                         waits_for_status=False)
def prepare(ctx, resource_config, **_):
    """Prepares an AWS EC2 DhcpOptions"""
    # Save the parameters
    ctx.instance.runtime_properties['resource_config'] = resource_config


@decorators.aws_resource(EC2DHCPOptions, RESOURCE_TYPE, waits_for_status=False)
def create(ctx, iface, resource_config, **_):
    """Creates an AWS EC2 DhcpOptions"""

    # Actually create the resource
    create_response = iface.create(resource_config)[DHCPOPTIONS]
    ctx.instance.runtime_properties['create_response'] = \
        utils.JsonCleanuper(create_response).to_dict()
    dhcp_options_id = create_response.get(DHCPOPTIONS_ID, '')
    iface.update_resource_id(dhcp_options_id)
    utils.update_resource_id(ctx.instance, dhcp_options_id)


@decorators.aws_resource(EC2DHCPOptions,
                         RESOURCE_TYPE,
                         ignore_properties=True,
                         waits_for_status=False)
def delete(ctx, iface, resource_config, **_):
    """Deletes an AWS EC2 DhcpOptions"""
    # Create a copy of the resource config for clean manipulation.
    dhcp_options_id = resource_config.get(DHCPOPTIONS_ID)

    if not dhcp_options_id:
        resource_config[DHCPOPTIONS_ID] = \
            iface.resource_id or \
            ctx.instance.runtime_properties.get(EXTERNAL_RESOURCE_ID)

    iface.delete(resource_config)


@decorators.aws_resource(EC2DHCPOptions,
                         RESOURCE_TYPE,
                         waits_for_status=False)
def attach(ctx, iface, resource_config, **_):
    '''Attaches an AWS EC2 DhcpOptions to a VPC'''
    dhcp_options_id = resource_config.get(DHCPOPTIONS_ID)
    if not dhcp_options_id:
        dhcp_options_id = iface.resource_id

    resource_config.update({DHCPOPTIONS_ID: dhcp_options_id})
    resource_config.pop('DhcpConfigurations')

    vpc_id = resource_config.get(VPC_ID)
    if not vpc_id:
        targ = \
            utils.find_rel_by_node_type(ctx.instance, VPC_TYPE) or \
            utils.find_rel_by_node_type(ctx.instance, VPC_TYPE_DEPRECATED)

        # Attempt to use the VPC ID from parameters.
        # Fallback to connected VPC.
        resource_config[VPC_ID] = \
            vpc_id or \
            targ.target.instance.runtime_properties.get(EXTERNAL_RESOURCE_ID)

    ctx.instance.runtime_properties['vpc_id'] = vpc_id

    # # Actually attach the resources
    iface.attach(resource_config)


@decorators.aws_resource(EC2DHCPOptions,
                         RESOURCE_TYPE,
                         ignore_properties=True,
                         waits_for_status=False)
def detach(ctx, iface, resource_config, **_):
    '''Detach an AWS EC2 DhcpOptions from a VPC'''
    resource_config.update({DHCPOPTIONS_ID: 'default'})

    vpc_id = resource_config.get(VPC_ID) or \
        ctx.instance.runtime_properties['vpc_id']
    if not vpc_id:
        targ = \
            utils.find_rel_by_node_type(ctx.instance, VPC_TYPE) or \
            utils.find_rel_by_node_type(ctx.instance, VPC_TYPE_DEPRECATED)

        # Attempt to use the VPC ID from parameters.
        # Fallback to connected VPC.
        resource_config[VPC_ID] = \
            vpc_id or \
            targ.target.instance.runtime_properties.get(EXTERNAL_RESOURCE_ID)
    else:
        resource_config.update({VPC_ID: vpc_id})

    iface.detach(resource_config)

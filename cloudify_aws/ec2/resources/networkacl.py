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
    EC2.NetworkAcl
    ~~~~~~~~~~~~~~
    AWS EC2 NetworkAcl interface
"""
# Boto
from botocore.exceptions import ClientError

# Cloudify
from cloudify_aws.common import decorators, utils
from cloudify_aws.ec2 import EC2Base
from cloudify_aws.common.constants import EXTERNAL_RESOURCE_ID

RESOURCE_TYPE = 'EC2 Network Acl'
NETWORKACLS = 'NetworkAcls'
NETWORKACL_ID = 'NetworkAclId'
NETWORKACL_IDS = 'NetworkAclIds'
VPC_ID = 'VpcId'
VPC_TYPE = 'cloudify.nodes.aws.ec2.Vpc'
VPC_TYPE_DEPRECATED = 'cloudify.aws.nodes.Vpc'
SUBNET_ID = 'SubnetId'
SUBNET_TYPE = 'cloudify.nodes.aws.ec2.Subnet'
SUBNET_TYPE_DEPRECATED = 'cloudify.aws.nodes.Subnet'
ASSOCIATION_ID = 'AssociationId'
ASSOCIATION_SUBNET_ID = 'association.subnet-id'
FILTERS = 'Filters'
FILTERS_NAME = 'Name'
FILTER_VALUE = 'Values'


class EC2NetworkAcl(EC2Base):
    """
        EC2 NetworkAcl interface
    """
    def __init__(self, ctx_node, resource_id=None, client=None, logger=None):
        EC2Base.__init__(self, ctx_node, resource_id, client, logger)
        self.type_name = RESOURCE_TYPE

    @property
    def properties(self):
        """Gets the properties of an external resource"""
        params = {NETWORKACL_IDS: [self.resource_id]}
        try:
            resources = \
                self.client.describe_network_acls(**params)
        except ClientError:
            pass
        else:
            return resources.get(NETWORKACLS)[0] if resources else None

    def get_properties_by_filter(self, filter_key, filter_value):
        params = {FILTERS: [{FILTERS_NAME: filter_key,
                             FILTER_VALUE: [filter_value]}]}
        try:
            resources = self.client.describe_network_acls(**params)
        except ClientError:
            pass
        else:
            return resources.get(NETWORKACLS)[0] if resources else None

    def create(self, params):
        """
            Create a new AWS EC2 NetworkAcl.
        """
        return self.make_client_call('create_network_acl', params)

    def delete(self, params=None):
        """
            Deletes an existing AWS EC2 NetworkAcl.
        """
        self.logger.debug('Deleting %s with parameters: %s'
                          % (self.type_name, params))
        res = self.client.delete_network_acl(**params)
        self.logger.debug('Response: %s' % res)
        return res

    def attach(self, params):
        '''
            Attach an AWS EC2 NetworkAcl to a Subnet.
        '''
        self.logger.debug('Attaching %s with: %s'
                          % (self.type_name, params.get(SUBNET_ID, None)))
        res = self.client.replace_network_acl_association(**params)
        self.logger.debug('Response: %s' % res)
        return res

    def detach(self, params):
        '''
            Detach an AWS EC2 NetworkAcl from a Subnet.
        '''
        self.logger.debug('Detaching %s from: %s'
                          % (self.type_name, params.get(SUBNET_ID, None)))
        self.logger.debug('Attaching default %s'
                          % (self.type_name))
        res = self.client.replace_network_acl_association(**params)
        self.logger.debug('Response: %s' % res)
        return res


@decorators.aws_resource(resource_type=RESOURCE_TYPE)
def prepare(ctx, resource_config, **_):
    """Prepares an AWS EC2 NetworkAcl"""
    # Save the parameters
    ctx.instance.runtime_properties['resource_config'] = resource_config


@decorators.aws_resource(EC2NetworkAcl, RESOURCE_TYPE)
@decorators.tag_resources
def create(ctx, iface, resource_config, **_):
    """Creates an AWS EC2 NetworkAcl"""

    # Create a copy of the resource config for clean manipulation.
    params = \
        dict() if not resource_config else resource_config.copy()

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

    # Actually create the resource
    create_response = iface.create(params)['NetworkAcl']
    ctx.instance.runtime_properties['create_response'] = \
        utils.JsonCleanuper(create_response).to_dict()
    network_acl_id = create_response.get(NETWORKACL_ID, '')
    iface.update_resource_id(network_acl_id)
    utils.update_resource_id(ctx.instance, network_acl_id)


@decorators.aws_resource(EC2NetworkAcl, RESOURCE_TYPE,
                         ignore_properties=True)
@decorators.untag_resources
def delete(ctx, iface, resource_config, **_):
    """Deletes an AWS EC2 NetworkAcl"""

    # Create a copy of the resource config for clean manipulation.
    params = \
        dict() if not resource_config else resource_config.copy()
    network_acl_id = params.get(NETWORKACL_ID)

    if not network_acl_id:
        params[NETWORKACL_ID] = \
            iface.resource_id or \
            ctx.instance.runtime_properties.get(EXTERNAL_RESOURCE_ID)

    iface.delete(params)


@decorators.aws_resource(EC2NetworkAcl, RESOURCE_TYPE)
def attach(ctx, iface, resource_config, **_):
    '''Attaches an AWS EC2 NetworkACL to a Subnet'''
    params = dict() if not resource_config else resource_config.copy()

    network_acl_id = params.get(NETWORKACL_ID)
    if not network_acl_id:
        network_acl_id = iface.resource_id

    params.update({NETWORKACL_ID: network_acl_id})

    subnet_id = params.get(SUBNET_ID)
    if not subnet_id:
        targ = \
            utils.find_rel_by_node_type(ctx.instance, SUBNET_TYPE) or \
            utils.find_rel_by_node_type(ctx.instance, SUBNET_TYPE_DEPRECATED)

        # Attempt to use the SUBNET ID from parameters.
        # Fallback to connected SUBNET.
        params[SUBNET_ID] = \
            subnet_id or \
            targ.target.instance.runtime_properties.get(EXTERNAL_RESOURCE_ID)

    network_acl_associations = iface \
        .get_properties_by_filter(ASSOCIATION_SUBNET_ID, params[SUBNET_ID])
    params.pop(SUBNET_ID)
    network_acl_association_id = \
        network_acl_associations.get('Associations')[0]\
        .get('NetworkAclAssociationId')
    params.update({ASSOCIATION_ID: network_acl_association_id})
    default_acl_id = network_acl_associations.get('Associations')[0]\
        .get('NetworkAclId')
    ctx.instance.runtime_properties['default_acl_id'] = \
        default_acl_id

    # # Actually attach the resources
    new_network_acl_association_list = iface.attach(params)
    new_network_acl_association_id = new_network_acl_association_list \
        .get('NewAssociationId')
    ctx.instance.runtime_properties['association_id'] = \
        new_network_acl_association_id


@decorators.aws_resource(EC2NetworkAcl, RESOURCE_TYPE,
                         ignore_properties=True)
def detach(ctx, iface, resource_config, **_):
    '''Detach an AWS EC2 NetworkACL from a Subnet'''
    params = dict() if not resource_config else resource_config.copy()

    params.update({NETWORKACL_ID: ctx.instance.runtime_properties[
        'default_acl_id']})
    params.update({ASSOCIATION_ID: ctx.instance.runtime_properties[
        'association_id']})

    iface.detach(params)

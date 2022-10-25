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
        self._describe_call = 'describe_network_acls'
        self._type_key = NETWORKACLS
        self._id_key = NETWORKACL_ID
        self._ids_key = NETWORKACL_IDS

    def get_properties_by_filter(self, filter_key, filter_value):
        params = {FILTERS: [{FILTERS_NAME: filter_key,
                             FILTER_VALUE: [filter_value]}]}
        resources = self.get_network_acls(params)
        return None if not resources else resources.get(NETWORKACLS)[0]

    def get_network_acls(self, params=None):
        if not params:
            params = {NETWORKACL_IDS: [], FILTERS: []}
        try:
            return self.client.describe_network_acls(**params)
        except ClientError:
            return []

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

    def replace(self, params):
        '''
            Replace Network ACL association ID.
        '''
        self.logger.debug('Replacing association %s with: %s'
                          % (self.type_name, params))
        res = self.client.replace_network_acl_association(**params)
        self.logger.debug('Response: %s' % res)
        return res


@decorators.aws_resource(EC2NetworkAcl, resource_type=RESOURCE_TYPE)
def prepare(ctx, resource_config, **_):
    """Prepares an AWS EC2 NetworkAcl"""
    # Save the parameters
    ctx.instance.runtime_properties['resource_config'] = resource_config


@decorators.aws_resource(EC2NetworkAcl, RESOURCE_TYPE)
@decorators.tag_resources
def create(ctx, iface, resource_config, **_):
    """Creates an AWS EC2 NetworkAcl"""

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

    # Actually create the resource
    create_response = iface.create(resource_config)['NetworkAcl']
    ctx.instance.runtime_properties['create_response'] = \
        utils.JsonCleanuper(create_response).to_dict()
    network_acl_id = create_response.get(NETWORKACL_ID, '')
    iface.update_resource_id(network_acl_id)
    utils.update_resource_id(ctx.instance, network_acl_id)


@decorators.aws_resource(EC2NetworkAcl, RESOURCE_TYPE,
                         ignore_properties=True)
@decorators.untag_resources
def delete(ctx, iface, resource_config, dry_run=False, **_):
    """Deletes an AWS EC2 NetworkAcl"""
    resource_config['DryRun'] = dry_run
    network_acl_id = resource_config.get(NETWORKACL_ID)

    if not network_acl_id:
        resource_config[NETWORKACL_ID] = \
            iface.resource_id or \
            ctx.instance.runtime_properties.get(EXTERNAL_RESOURCE_ID)

    iface.delete(resource_config)


@decorators.aws_resource(EC2NetworkAcl, RESOURCE_TYPE)
def attach(ctx, iface, resource_config, **_):
    '''Attaches an AWS EC2 NetworkACL to a Subnet'''

    network_acl_id = resource_config.get(NETWORKACL_ID)

    if not network_acl_id:
        network_acl_id = iface.resource_id

    resource_config.update({NETWORKACL_ID: network_acl_id})

    # Really the user should not provide subnet_id param and will
    # only use a relationship. But this code used to be here so
    # we are stuck with it.
    subnet_id = resource_config.get(SUBNET_ID)
    network_acl_assoc_prop = {}
    subnet_ids = utils.find_ids_of_rels_by_node_type(
        ctx.instance, SUBNET_TYPE)
    if subnet_id:
        subnet_ids.append(subnet_id)
    try:
        vpc_id = utils.find_ids_of_rels_by_node_type(
            ctx.instance, VPC_TYPE)[0]
    except IndexError:
        vpc_id = None
    acl_associations = iface.get_network_acls()
    for acl in acl_associations['NetworkAcls']:
        if acl[VPC_ID] != vpc_id and len(acl['Associations']) < 1:
            continue
        for assoc in acl['Associations']:
            if assoc[SUBNET_ID] not in subnet_ids:
                continue
            ctx.logger.debug(
                'Performing network acl assoc for {0}'.format(assoc))
            if assoc[SUBNET_ID] not in network_acl_assoc_prop:
                network_acl_assoc_prop[assoc[SUBNET_ID]] = {}
            network_acl_assoc_prop[assoc[SUBNET_ID]]['original_acl'] = \
                assoc['NetworkAclId']
            network_acl_assoc_prop[assoc[SUBNET_ID]]['old_assoc_id'] = \
                assoc['NetworkAclAssociationId']
            params = {
                ASSOCIATION_ID: assoc['NetworkAclAssociationId'],
                NETWORKACL_ID: iface.resource_id
            }
            result = iface.replace(params)
            if 'NewAssociationId' in result:
                network_acl_assoc_prop[assoc[SUBNET_ID]]['new_assoc_id'] = \
                    result['NewAssociationId']
    ctx.instance.runtime_properties['network_acl_associations'] = \
        network_acl_assoc_prop


@decorators.aws_resource(EC2NetworkAcl, RESOURCE_TYPE,
                         ignore_properties=True)
def detach(ctx, iface, resource_config, **_):
    '''Detach an AWS EC2 NetworkACL from a Subnet'''
    try:
        vpc_id = utils.find_ids_of_rels_by_node_type(
            ctx.instance, VPC_TYPE)[0]
    except IndexError:
        vpc_id = None
    acl_associations = iface.get_network_acls()
    for acl in acl_associations['NetworkAcls']:
        if acl[VPC_ID] != vpc_id:
            continue
        if acl['IsDefault']:
            break
    for _, param in ctx.instance.runtime_properties.get(
            'network_acl_associations', {}).items():
        resource_config[NETWORKACL_ID] = acl['NetworkAclId']
        resource_config[ASSOCIATION_ID] = param['new_assoc_id']
        iface.replace(resource_config)

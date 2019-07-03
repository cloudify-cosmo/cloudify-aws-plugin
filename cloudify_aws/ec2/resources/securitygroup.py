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
'''
    EC2.SecurityGroup
    ~~~~~~~~~~~~~~
    AWS EC2 Security Group interface
'''
# Boto
from botocore.exceptions import ClientError

# Cloudify
from cloudify_aws.common import decorators, utils
from cloudify_aws.common.constants import EXTERNAL_RESOURCE_ID
from cloudify_aws.ec2 import EC2Base

RESOURCE_TYPE = 'EC2 Security Group'
GROUP = 'SecurityGroup'
GROUPS = 'SecurityGroups'
GROUPID = 'GroupId'
GROUPIDS = 'GroupIds'
GROUP_NAME = 'GroupName'

VPC_ID = 'VpcId'
VPC_TYPE = 'cloudify.nodes.aws.ec2.Vpc'
VPC_TYPE_DEPRECATED = 'cloudify.aws.nodes.Vpc'

CONTIN = 'cloudify.relationships.contained_in'


class EC2SecurityGroup(EC2Base):
    '''
        EC2 Security Group interface
    '''
    def __init__(self, ctx_node, resource_id=None, client=None, logger=None):
        EC2Base.__init__(self, ctx_node, resource_id, client, logger)
        self.type_name = RESOURCE_TYPE

    @property
    def properties(self):
        '''Gets the properties of an external resource'''
        params = {GROUPIDS: [self.resource_id]}
        try:
            resources = \
                self.client.describe_security_groups(**params)
        except ClientError:
            pass
        else:
            return None if not resources else resources.get(GROUPS, [None])[0]
        return None

    @property
    def status(self):
        '''Gets the status of an external resource'''
        props = self.properties
        if not props:
            return None
        return props['State']

    def create(self, params):
        '''
            Create a new AWS EC2 Vpc.
        '''
        return self.make_client_call('create_security_group', params)

    def delete(self, params=None):
        '''
            Deletes an existing AWS EC2 Security Group.
        '''
        self.logger.debug('Deleting %s with parameters: %s'
                          % (self.type_name, params))
        res = self.client.delete_security_group(**params)
        self.logger.debug('Response: %s' % res)
        return res

    def authorize_ingress(self, params):
        '''
            Authorize existing AWS EC2 Security Group ingress rules.
        '''
        self.logger.debug('Authorizing Ingress with parameters: %s'
                          % (params))
        res = self.client.authorize_security_group_ingress(**params)
        self.logger.debug('Response: %s' % res)
        return res

    def authorize_egress(self, params):
        '''
            Authorize existing AWS EC2 Security Group ingress rules.
        '''
        self.logger.debug('Authorizing Egress with parameters: %s'
                          % (params))
        res = self.client.authorize_security_group_egress(**params)
        self.logger.debug('Response: %s' % res)
        return res

    def revoke_ingress(self, params):
        '''
            Revoke existing AWS EC2 Security Group ingress rules.
        '''
        self.logger.debug('Revoking Ingress with parameters: %s'
                          % (params))
        res = self.client.revoke_security_group_ingress(**params)
        self.logger.debug('Response: %s' % res)
        return res

    def revoke_egress(self, params):
        '''
            Revoke existing AWS EC2 Security Group ingress rules.
        '''
        self.logger.debug('Revoking Egress with parameters: %s'
                          % (params))
        res = self.client.revoke_security_group_egress(**params)
        self.logger.debug('Response: %s' % res)
        return res


@decorators.aws_resource(EC2SecurityGroup, resource_type=RESOURCE_TYPE)
def prepare(ctx, iface, resource_config, **_):
    '''Prepares an AWS EC2 Security Group'''
    # Save the parameters
    ctx.instance.runtime_properties['resource_config'] = resource_config


@decorators.aws_resource(EC2SecurityGroup, RESOURCE_TYPE)
@decorators.tag_resources
def create(ctx, iface, resource_config, **_):
    '''Creates an AWS EC2 Security Group'''
    params = utils.clean_params(
        dict() if not resource_config else resource_config.copy())

    vpc_id = params.get(VPC_ID)

    # Try to get the group_name and if it does not exits then try to
    # generate new one based on instance_id
    group_name = params.get(GROUP_NAME)
    params[GROUP_NAME] = utils.get_ec2_vpc_resource_name(group_name)

    if not vpc_id:
        vpc = \
            utils.find_rel_by_node_type(
                ctx.instance,
                VPC_TYPE) or utils.find_rel_by_node_type(
                ctx.instance,
                VPC_TYPE_DEPRECATED)

    if vpc_id or vpc:
        params[VPC_ID] = \
            vpc_id or \
            vpc.target.instance.runtime_properties.get(
                EXTERNAL_RESOURCE_ID)

    # Actually create the resource
    create_response = iface.create(params)
    ctx.instance.runtime_properties['create_response'] = \
        utils.JsonCleanuper(create_response).to_dict()
    group_id = create_response.get(GROUPID, '')
    iface.update_resource_id(group_id)
    utils.update_resource_id(
        ctx.instance, group_id)


@decorators.aws_resource(EC2SecurityGroup, RESOURCE_TYPE)
@decorators.untag_resources
def delete(ctx, iface, resource_config, **_):
    '''Deletes an AWS EC2 Security Group'''

    params = \
        dict() if not resource_config else resource_config.copy()

    group_id = params.get(GROUPID)
    if not group_id:
        group_id = iface.resource_id

    iface.delete({GROUPID: group_id})


@decorators.aws_resource(EC2SecurityGroup, RESOURCE_TYPE)
def authorize_ingress_rules(ctx, iface, resource_config, **_):
    '''Authorize rules for an AWS EC2 Security Group'''
    params = \
        dict() if not resource_config else resource_config.copy()

    # Fill the GroupId Parameter
    group_id = params.get(GROUPID)
    if not group_id:
        group = \
            utils.find_rel_by_type(
                ctx.instance, CONTIN)
        group_id = \
            group.target.instance.runtime_properties.get(
                EXTERNAL_RESOURCE_ID, iface.resource_id)
        params[GROUPID] = group_id

    iface.authorize_ingress(params)


@decorators.aws_resource(EC2SecurityGroup, RESOURCE_TYPE)
def authorize_egress_rules(ctx, iface, resource_config, **_):
    '''Authorize rules for an AWS EC2 Security Group'''
    params = \
        dict() if not resource_config else resource_config.copy()

    # Fill the GroupId Parameter
    group_id = params.get(GROUPID)
    if not group_id:
        group = \
            utils.find_rel_by_type(
                ctx.instance, CONTIN)
        group_id = \
            group.target.instance.runtime_properties.get(
                EXTERNAL_RESOURCE_ID, iface.resource_id)
        params[GROUPID] = group_id

    iface.authorize_egress(params)


@decorators.aws_resource(EC2SecurityGroup, RESOURCE_TYPE)
def revoke_ingress_rules(ctx, iface, resource_config, **_):
    '''Revoke rules for an AWS EC2 Security Group'''
    params = \
        dict() if not resource_config else resource_config.copy()

    # Fill the GroupId Parameter
    group_id = params.get(GROUPID)
    if not group_id:
        group = \
            utils.find_rel_by_type(
                ctx.instance, CONTIN)
        group_id = \
            group.target.instance.runtime_properties.get(
                EXTERNAL_RESOURCE_ID, iface.resource_id)
        params[GROUPID] = group_id

    iface.revoke_ingress(params)


@decorators.aws_resource(EC2SecurityGroup, RESOURCE_TYPE)
def revoke_egress_rules(ctx, iface, resource_config, **_):
    '''Revoke rules for an AWS EC2 Security Group'''
    params = \
        dict() if not resource_config else resource_config.copy()

    # Fill the GroupId Parameter
    group_id = params.get(GROUPID)
    if not group_id:
        group = \
            utils.find_rel_by_type(
                ctx.instance, CONTIN)
        group_id = \
            group.target.instance.runtime_properties.get(
                EXTERNAL_RESOURCE_ID, iface.resource_id)
        params[GROUPID] = group_id

    iface.revoke_egress(params)

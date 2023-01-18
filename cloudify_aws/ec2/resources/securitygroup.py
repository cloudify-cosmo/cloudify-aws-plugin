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

from time import sleep

# Cloudify
from cloudify_aws.ec2 import EC2Base
from cloudify_aws.common import decorators, utils
from cloudify_aws.common.constants import EXTERNAL_RESOURCE_ID

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
        self._describe_call = 'describe_security_groups'
        self._ids_key = GROUPIDS
        self._type_key = GROUPS
        self._id_key = GROUPID

    @property
    def check_status(self):
        if self.properties:
            return 'OK'
        return 'NOT OK'

    @property
    def status(self):
        '''Gets the status of an external resource'''
        return self.properties

    def create(self, params):
        """
            Create a new AWS EC2 NetworkInterface.
        """
        self.create_response = self.make_client_call(
            'create_security_group', params)
        self.update_resource_id(self.create_response.get(GROUPID, ''))

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

    def wait(self):
        max_wait = 5
        counter = 0
        while not self.properties:
            self.logger.debug('Waiting for Security Group to be created.')
            sleep(5)
            if max_wait > counter:
                break
            counter += 1


@decorators.aws_resource(EC2SecurityGroup, resource_type=RESOURCE_TYPE)
def prepare(ctx, iface, resource_config, **_):
    '''Prepares an AWS EC2 Security Group'''
    # Save the parameters
    ctx.instance.runtime_properties['resource_config'] = resource_config


@decorators.aws_resource(EC2SecurityGroup,
                         RESOURCE_TYPE,
                         waits_for_status=False)
@decorators.tag_resources
def create(ctx, iface, resource_config, **_):
    '''Creates an AWS EC2 Security Group'''
    resource_config = _create_group_params(resource_config, ctx.instance)

    # Actually create the resource
    iface.create(resource_config)
    utils.update_resource_id(ctx.instance, iface.resource_id)
    iface.wait()


@decorators.aws_resource(EC2SecurityGroup, RESOURCE_TYPE)
@decorators.untag_resources
def delete(ctx, iface, resource_config, dry_run=False, **_):
    '''Deletes an AWS EC2 Security Group'''
    group_id = resource_config.get(GROUPID)
    if not group_id:
        group_id = iface.resource_id

    if dry_run:
        utils.exit_on_substring(iface,
                                'delete',
                                {GROUPID: group_id, 'DryRun': dry_run},
                                'Request would have succeeded')

    utils.exit_on_substring(iface,
                            'delete',
                            {GROUPID: group_id},
                            'InvalidGroup.NotFound')


@decorators.aws_resource(EC2SecurityGroup, RESOURCE_TYPE)
def authorize_ingress_rules(ctx, iface, resource_config, **_):
    '''Authorize rules for an AWS EC2 Security Group'''
    # Fill the GroupId Parameter
    group_id = resource_config.get(GROUPID)
    if not group_id:
        group = \
            utils.find_rel_by_type(
                ctx.instance, CONTIN)
        group_id = \
            group.target.instance.runtime_properties.get(
                EXTERNAL_RESOURCE_ID, iface.resource_id)
        resource_config[GROUPID] = group_id

    iface.authorize_ingress(resource_config)
    utils.update_expected_configuration(iface, ctx.instance.runtime_properties)


@decorators.aws_resource(EC2SecurityGroup, RESOURCE_TYPE)
def authorize_egress_rules(ctx, iface, resource_config, **_):
    '''Authorize rules for an AWS EC2 Security Group'''
    # Fill the GroupId Parameter
    group_id = resource_config.get(GROUPID)
    if not group_id:
        group = \
            utils.find_rel_by_type(
                ctx.instance, CONTIN)
        group_id = \
            group.target.instance.runtime_properties.get(
                EXTERNAL_RESOURCE_ID, iface.resource_id)
        resource_config[GROUPID] = group_id

    iface.authorize_egress(resource_config)


@decorators.aws_resource(EC2SecurityGroup, RESOURCE_TYPE)
def poststart_authorize(ctx, iface, resource_config, **_):
    group_id = resource_config.get(GROUPID)
    if not group_id:
        group = \
            utils.find_rel_by_type(
                ctx.instance, CONTIN)
        group_id = \
            group.target.instance.runtime_properties.get(
                EXTERNAL_RESOURCE_ID, iface.resource_id)
        resource_config[GROUPID] = group_id
    utils.update_expected_configuration(iface, ctx.instance.runtime_properties)


@decorators.aws_resource(EC2SecurityGroup, RESOURCE_TYPE)
def revoke_ingress_rules(ctx, iface, resource_config, **_):
    '''Revoke rules for an AWS EC2 Security Group'''
    # Fill the GroupId Parameter
    group_id = resource_config.get(GROUPID)
    if not group_id:
        group = \
            utils.find_rel_by_type(
                ctx.instance, CONTIN)
        group_id = \
            group.target.instance.runtime_properties.get(
                EXTERNAL_RESOURCE_ID, iface.resource_id)
        resource_config[GROUPID] = group_id

    utils.exit_on_substring(iface,
                            'revoke_ingress',
                            resource_config,
                            ['InvalidPermission.NotFound',
                             'InvalidGroup.NotFound'])


@decorators.aws_resource(EC2SecurityGroup, RESOURCE_TYPE)
def revoke_egress_rules(ctx, iface, resource_config, **_):
    '''Revoke rules for an AWS EC2 Security Group'''
    # Fill the GroupId Parameter
    group_id = resource_config.get(GROUPID)
    if not group_id:
        group = \
            utils.find_rel_by_type(
                ctx.instance, CONTIN)
        group_id = \
            group.target.instance.runtime_properties.get(
                EXTERNAL_RESOURCE_ID, iface.resource_id)
        resource_config[GROUPID] = group_id

    utils.exit_on_substring(iface,
                            'revoke_egress',
                            resource_config,
                            ['InvalidPermission.NotFound',
                             'InvalidGroup.NotFound'])


def _create_group_params(params, ctx_instance):
    vpc_id = params.get(VPC_ID)

    # Try to get the group_name and if it does not exits then try to
    # generate new one based on instance_id
    group_name = params.get(GROUP_NAME)
    params[GROUP_NAME] = utils.get_ec2_vpc_resource_name(group_name)
    vpc = None
    if not vpc_id:
        vpc = \
            utils.find_rel_by_node_type(
                ctx_instance,
                VPC_TYPE) or utils.find_rel_by_node_type(
                ctx_instance,
                VPC_TYPE_DEPRECATED)

    if vpc_id or vpc:
        params[VPC_ID] = \
            vpc_id or \
            vpc.target.instance.runtime_properties.get(
                EXTERNAL_RESOURCE_ID)
    return params


@decorators.aws_resource(class_decl=EC2SecurityGroup,
                         resource_type=RESOURCE_TYPE,
                         waits_for_status=False)
def check_drift(ctx, iface=None, **_):
    if 'cloudify.nodes.aws.ec2.SecurityGroup' in ctx.node.type_hierarchy:
        expected = iface.expected_configuration
        remote = iface.remote_configuration
        if 'IpPermissions' in expected:
            expected['IpPermissions'] = []
            ctx.instance.runtime_properties['expected_configuration'] = \
                expected
        if 'IpPermissions' in remote:
            remote['IpPermissions'] = []
            iface.remote_configuration = remote
    return utils.check_drift(RESOURCE_TYPE, iface, ctx.logger)


@decorators.aws_resource(class_decl=EC2SecurityGroup,
                         resource_type=RESOURCE_TYPE,
                         waits_for_status=False)
def poststart(ctx, iface=None, **_):
    utils.update_expected_configuration(iface, ctx.instance.runtime_properties)


interface = EC2SecurityGroup

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
    ELB.target_group
    ~~~~~~~~~~~~
    AWS ELB target group
'''
# Third Party imports
from cloudify.exceptions import NonRecoverableError

# Local imports
from cloudify_aws.common import decorators, utils
from cloudify_aws.elb import ELBBase
from cloudify_aws.common.connection import Boto3Connection
from cloudify_aws.common.constants import EXTERNAL_RESOURCE_ID

RESOURCE_TYPE = 'ELB Target Group'
TARGETGROUP_ARN = 'TargetGroupArn'
VPC_ID = 'VpcId'
VPC_TYPE = 'cloudify.nodes.aws.ec2.Vpc'
VPC_TYPE_DEPRECATED = 'cloudify.aws.nodes.VPC'
GRP_ATTR = 'Attributes'


class ELBTargetGroup(ELBBase):
    '''
        AWS ELB target group interface
    '''
    def __init__(self, ctx_node, resource_id=None, client=None, logger=None):
        ELBBase.__init__(
            self,
            ctx_node,
            resource_id,
            client or Boto3Connection(ctx_node).client('elbv2'),
            logger)
        self.type_name = RESOURCE_TYPE
        self._properties = {}

    @property
    def properties(self):
        '''Gets the properties of an external resource'''
        if not self._properties:
            if not self.resource_id:
                return
            params = {'TargetGroupArns': [self.resource_id]}
            try:
                resources = self.make_client_call(
                    'describe_target_groups', params)
            except NonRecoverableError:
                return
            if 'TargetGroups' in resources:
                for resource in resources['TargetGroups']:
                    if resource.get('TargetGroupArn', '') == self.resource_id:
                        self._properties = resource
                    elif resource.get('TargetGroupName',
                                      '') == self.resource_id:
                        self._properties = resource
        return self._properties

    @property
    def status(self):
        '''Gets the status of an external resource'''
        if self.properties:
            return self.properties.get('State', {}).get('Code')

    def create(self, params):
        '''
            Create a new AWS ELB Target Group.
        .. note:
            See http://bit.ly/2qDbr2l for config details.
        '''
        return self.make_client_call('create_target_group', params)

    def delete(self, params=None):
        '''
            Deletes an existing ELB Target Group.
        .. note:
            See http://bit.ly/2pWJDtz for config details.
        '''
        if TARGETGROUP_ARN not in params:
            params.update({TARGETGROUP_ARN: self.resource_id})
        self.logger.debug('Deleting %s with parameters: %s'
                          % (self.type_name, params))
        self.client.delete_target_group(**params)

    def modify_attribute(self, params):
        '''
            Modify a AWS ELB Target Group attributes.
        .. note:
            See http://bit.ly/2pwMHtb for config details.
        '''
        self.logger.debug('Modifying %s with parameters: %s'
                          % (self.type_name, params))
        res = self.client.modify_target_group_attributes(**params)
        self.logger.debug('Response: %s' % res)
        return res[GRP_ATTR]


@decorators.aws_resource(ELBTargetGroup, RESOURCE_TYPE)
def prepare(ctx, resource_config, **_):
    '''Prepares an ELB listener'''
    # Save the parameters
    ctx.instance.runtime_properties['resource_config'] = resource_config


@decorators.aws_resource(ELBTargetGroup, RESOURCE_TYPE)
def create(ctx, iface, resource_config, **_):
    '''Creates an AWS ELB target group'''
    # TG attributes are only applied in modify operation.
    resource_config.pop(GRP_ATTR, {})
    if VPC_ID not in resource_config:
        targs = \
            utils.find_rels_by_node_type(
                ctx.instance,
                VPC_TYPE) or utils.find_rels_by_node_name(
                ctx.instance,
                VPC_TYPE_DEPRECATED)
        tg_attr = targs[0].target.instance.runtime_properties
        resource_config[VPC_ID] = \
            tg_attr.get(EXTERNAL_RESOURCE_ID)
        del targs

    # Actually create the resource
    create_response = iface.create(resource_config)
    iface.update_resource_id(
        create_response['TargetGroups'][0][TARGETGROUP_ARN])
    utils.update_resource_id(
        ctx.instance, create_response['TargetGroups'][0][TARGETGROUP_ARN])
    utils.update_resource_arn(
        ctx.instance, create_response['TargetGroups'][0][TARGETGROUP_ARN])


@decorators.aws_resource(ELBTargetGroup, RESOURCE_TYPE,
                         ignore_properties=True)
@decorators.wait_for_delete(status_pending=[])
def delete(iface, resource_config, **_):
    '''Deletes an AWS target group'''
    iface.delete(resource_config)


@decorators.aws_resource(ELBTargetGroup, RESOURCE_TYPE)
def modify(ctx, iface, resource_config, **_):
    '''modify an AWS ELB target group attributes'''
    # Build API params
    params = \
        ctx.instance.runtime_properties.get('resource_config') \
        or resource_config
    if TARGETGROUP_ARN not in params:
        params.update(
            {TARGETGROUP_ARN: ctx.instance.runtime_properties.get(
                EXTERNAL_RESOURCE_ID)})
    modify_params_attributes = params.pop(GRP_ATTR, [])
    if modify_params_attributes:
        # Add the LB ARN
        modify_params = {}
        modify_params[TARGETGROUP_ARN] = params.get(TARGETGROUP_ARN)
        modify_params[GRP_ATTR] = modify_params_attributes
        # Actually modify the resource
        attributes = iface.modify_attribute(modify_params)
        ctx.instance.runtime_properties['resource_config'][TARGETGROUP_ARN] = \
            attributes

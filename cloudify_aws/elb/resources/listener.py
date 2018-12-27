# #######
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
#    * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    * See the License for the specific language governing permissions and
#    * limitations under the License.
'''
    ELB.listener
    ~~~~~~~~~~~~
    AWS ELB listener interface
'''
# Generic
import re
# Cloudify
from cloudify_aws.common import decorators, utils
from cloudify_aws.elb import ELBBase
from cloudify_aws.common.connection import Boto3Connection
from cloudify_aws.common.constants import EXTERNAL_RESOURCE_ARN
# Boto
from botocore.exceptions import ClientError

RESOURCE_TYPE = 'ELB Listener'
LISTENER_ARN = 'ListenerArn'
LB_ARN = 'LoadBalancerArn'
TARGET_ARN = 'TargetGroupArn'
LB_TYPE = 'cloudify.nodes.aws.elb.LoadBalancer'
TARGET_TYPE = 'cloudify.nodes.aws.elb.TargetGroup'
SIMPLE_ARN_REGEX = '^arn\:aws\:'
ARN_MATCHER = re.compile(SIMPLE_ARN_REGEX)


class ELBListener(ELBBase):
    '''
        AWS ELB listener interface
    '''
    def __init__(self, ctx_node, resource_id=None, client=None, logger=None):
        ELBBase.__init__(
            self,
            ctx_node,
            resource_id,
            client or Boto3Connection(ctx_node).client('elbv2'),
            logger)
        self.type_name = RESOURCE_TYPE

    @property
    def properties(self):
        '''Gets the properties of an external resource'''
        try:
            resources = self.client.describe_listeners(
                ListenerArns=[self.resource_id])
        except ClientError:
            pass
        else:
            return None \
                if not resources else resources['Listeners'][0]

    @property
    def status(self):
        '''Gets the status of an external resource'''
        props = self.properties
        if not props:
            return None
        return props['State']['Code']

    def create(self, params):
        '''
            Create a new AWS ELB listener.
        .. note:
            See http://bit.ly/2p741nK for config details.
        '''
        return self.make_client_call('create_listener', params)

    def delete(self, params=None):
        '''
            Deletes an existing ELB listener.
        .. note:
            See http://bit.ly/2oWfEln for config details.
        '''
        if LISTENER_ARN not in params.keys():
            params.update({LISTENER_ARN: self.resource_id})
        self.logger.debug('Deleting %s with parameters: %s'
                          % (self.type_name, params))
        self.client.delete_listener(**params)


@decorators.aws_resource(resource_type=RESOURCE_TYPE)
def prepare(ctx, resource_config, **_):
    '''Prepares an ELB listener'''
    # Save the parameters
    ctx.instance.runtime_properties['resource_config'] = resource_config


@decorators.aws_resource(ELBListener, RESOURCE_TYPE)
def create(ctx, iface, resource_config, **_):
    '''Creates an AWS ELB listener'''
    # Build API params
    params = \
        ctx.instance.runtime_properties['resource_config'] or resource_config

    if LB_ARN not in params:
        targs = \
            utils.find_rels_by_node_type(
                ctx.instance,
                LB_TYPE)
        lb_arn = \
            targs[0].target.instance.runtime_properties[EXTERNAL_RESOURCE_ARN]
        params.update({LB_ARN: lb_arn})

    for action in params.get('DefaultActions', []):
        target_grp = action.get(TARGET_ARN)
        if not ARN_MATCHER.match(action.get(target_grp, '')):
            targs = \
                utils.find_rels_by_node_type(
                    ctx.instance,
                    TARGET_TYPE)
            for targ in targs:
                target_group_arn = \
                    targ.target.instance.runtime_properties[
                        EXTERNAL_RESOURCE_ARN]
                if targ.target.node.name == target_grp:
                    action.update({TARGET_ARN: target_group_arn})

    # Actually create the resource
    create_response = iface.create(params)
    iface.update_resource_id(
        create_response['Listeners'][0][LISTENER_ARN])
    utils.update_resource_id(
        ctx.instance, create_response['Listeners'][0][LISTENER_ARN])
    utils.update_resource_arn(
        ctx.instance, create_response['Listeners'][0][LISTENER_ARN])


@decorators.aws_resource(ELBListener, RESOURCE_TYPE,
                         ignore_properties=True)
def delete(iface, resource_config, **_):
    '''Deletes an AWS ELB listener'''
    iface.delete(resource_config)

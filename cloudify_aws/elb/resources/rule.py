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
    ELB.rule
    ~~~~~~~~~~~~
    AWS ELB rule interface
'''
# Standard Imports
import re

# Third Party imports
from botocore.exceptions import ClientError, ParamValidationError

# Local imports
from cloudify_aws.common import decorators, utils
from cloudify_aws.elb import ELBBase
from cloudify_aws.common.connection import Boto3Connection
from cloudify_aws.common.constants import EXTERNAL_RESOURCE_ARN

RESOURCE_TYPE = 'ELB Rule'
RULE_ARN = 'RuleArn'
LISTENER_ARN = 'ListenerArn'
TARGET_ARN = 'TargetGroupArn'
LISTENER_TYPE = 'cloudify.nodes.aws.elb.Listener'
TARGET_TYPE = 'cloudify.nodes.aws.elb.TargetGroup'
SIMPLE_ARN_REGEX = '^arn\:aws\:'
ARN_MATCHER = re.compile(SIMPLE_ARN_REGEX)


class ELBRule(ELBBase):
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
        self._properties = {}
        self.type_name = RESOURCE_TYPE

    @property
    def properties(self):
        '''Gets the properties of an external resource'''
        if not self.resource_id:
            return
        if not self._properties:
            try:
                resources = self.client.describe_rules(
                    RuleArns=[self.resource_id])
            except (ParamValidationError, ClientError):
                pass
            else:
                if 'Rules' in resources:
                    for rule in resources['Rules']:
                        if rule.get('RuleArn') == self.resource_id:
                            self._properties = rule
        return self._properties

    @property
    def status(self):
        '''Gets the status of an external resource'''
        return self.properties

    def create(self, params):
        '''
            Create a new AWS ELB Rule.
        .. note:
            See http://bit.ly/2pE0hez for config details.
        '''
        return self.make_client_call('create_rule', params)

    def delete(self, params=None):
        '''
            Deletes an existing ELB Rule.
        .. note:
            See http://bit.ly/2oWfEln for config details.
        '''
        if LISTENER_ARN not in params:
            params.update({RULE_ARN: self.resource_id})
        self.logger.debug('Deleting %s with parameters: %s'
                          % (self.type_name, params))
        self.client.delete_rule(**params)


@decorators.aws_resource(ELBRule,
                         RESOURCE_TYPE,
                         waits_for_status=False)
def prepare(ctx, resource_config, **_):
    '''Prepares an ELB rule'''
    # Save the parameters
    ctx.instance.runtime_properties['resource_config'] = resource_config


@decorators.aws_resource(ELBRule,
                         RESOURCE_TYPE,
                         waits_for_status=False)
def create(ctx, iface, resource_config, **_):
    '''Creates an AWS ELB rule'''
    # Build API params
    # TODO check if this should stay
    resource_config = \
        resource_config or ctx.instance.runtime_properties['resource_config']

    if LISTENER_ARN not in resource_config:
        targs = \
            utils.find_rels_by_node_type(
                ctx.instance,
                LISTENER_TYPE)
        listener_arn = \
            targs[0].target.instance.runtime_properties[EXTERNAL_RESOURCE_ARN]
        resource_config.update({LISTENER_ARN: listener_arn})
        del targs

    for action in resource_config.get('Actions', []):
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
    create_response = iface.create(resource_config)
    iface.update_resource_id(
        create_response['Rules'][0][RULE_ARN])
    utils.update_resource_id(
        ctx.instance, create_response['Rules'][0][RULE_ARN])
    utils.update_resource_arn(
        ctx.instance, create_response['Rules'][0][RULE_ARN])


@decorators.aws_resource(ELBRule, RESOURCE_TYPE,
                         ignore_properties=True,
                         waits_for_status=False)
def delete(iface, resource_config, **_):
    '''Deletes an AWS ELB rule'''
    iface.delete(resource_config)

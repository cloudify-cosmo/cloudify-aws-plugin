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
    ELB.load_balancer
    ~~~~~~~~~~~~
    AWS ELB load balancer interface
'''

from cloudify.exceptions import NonRecoverableError

# Local imports
from cloudify_aws.common._compat import text_type
from cloudify_aws.common import decorators, utils
from cloudify_aws.elb import ELBBase
from cloudify_aws.common.connection import Boto3Connection
from cloudify_aws.common.constants import (
    EXTERNAL_RESOURCE_ARN,
    EXTERNAL_RESOURCE_ID
)

RESOURCE_TYPE = 'ELB Load Balancer'
RESOURCE_NAME = 'LoadBalancerName'
LB_ARN = 'LoadBalancerArn'
LB_ATTR = 'Attributes'
SUBNET_TYPE = 'cloudify.nodes.aws.ec2.Subnet'
SUBNET_TYPE_DEPRECATED = 'cloudify.aws.nodes.Subnet'
SECGROUP_TYPE = 'cloudify.nodes.aws.ec2.SecurityGroup'
SECGROUP_TYPE_DEPRECATED = 'cloudify.aws.nodes.SecurityGroup'
SUBNETS = 'Subnets'
SECGROUPS = 'SecurityGroups'


class ELBLoadBalancer(ELBBase):
    '''
        AWS ELB load balancer interface
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
        self._describe_call = 'describe_load_balancers'

    @property
    def properties(self):
        '''Gets the properties of an external resource'''
        if not self.resource_id:
            return
        if not self._properties:
            res = self.get_describe_result({'Names': [self.resource_id]})
            self.logger.info('Describe LB response: {}'.format(res))
            names = []
            if 'LoadBalancers' in res:
                for elb in res['LoadBalancers']:
                    lb_name = elb.get('LoadBalancerName')
                    name = elb.get('Name')
                    if lb_name:
                        names.append(lb_name)
                    if name:
                        names.append(name)
                    if self.resource_id in names:
                        self._properties = elb
        return self._properties

    @property
    def status(self):
        '''Gets the status of an external resource'''
        return self.properties.get('State', {}).get('Code')

    def create(self, params):
        '''
            Create a new AWS ELB load balancer.
        .. note:
            See http://bit.ly/2pwMHtb for config details.
        '''
        return self.make_client_call('create_load_balancer', params)

    def delete(self, params=None):
        '''
            Deletes an existing ELB load balancer.
        .. note:
            See http://bit.ly/2pwRpY9 for config details.
        '''
        self.logger.debug('Deleting %s with parameters: %s'
                          % (self.type_name, params))
        self.client.delete_load_balancer(**params)

    def modify_attribute(self, params):
        '''
            Modify a AWS ELB load balancer attributes.
        .. note:
            See http://bit.ly/2pwMHtb for config details.
        '''
        self.logger.debug('Modifying %s with parameters: %s'
                          % (self.type_name, params))
        res = self.client.modify_load_balancer_attributes(**params)
        self.logger.debug('Response: %s' % res)
        return res[LB_ATTR]


@decorators.aws_resource(ELBLoadBalancer,
                         RESOURCE_TYPE,
                         waits_for_status=False)
def prepare(ctx, resource_config, **_):
    '''Prepares an ELB load balancer'''
    # Save the parameters
    ctx.instance.runtime_properties['resource_config'] = resource_config


@decorators.aws_resource(ELBLoadBalancer, RESOURCE_TYPE)
@decorators.wait_for_status(
    status_good=['active'],
    status_pending=['provisioning'])
@decorators.aws_params('Name')
def create(ctx, iface, resource_config, params, **_):
    '''Creates an AWS ELB load balancer'''

    # LB attributes are only applied in modify operation.
    params.pop(LB_ATTR, {})
    # Add Subnets
    subnets_from_params = params.get(SUBNETS, [])
    subnets = \
        utils.find_rels_by_node_type(
            ctx.instance,
            SUBNET_TYPE) or utils.find_rels_by_node_name(
            ctx.instance,
            SUBNET_TYPE_DEPRECATED)
    for subnet in subnets:
        subnet_id = \
            subnet.target.instance.runtime_properties[EXTERNAL_RESOURCE_ID]
        subnets_from_params.append(subnet_id)
    params[SUBNETS] = subnets_from_params
    # Add Security Groups
    secgroups_from_params = params.get(SECGROUPS, [])
    secgroups = \
        utils.find_rels_by_node_type(
            ctx.instance,
            SECGROUP_TYPE) or \
        utils.find_rels_by_node_type(
            ctx.instance,
            SECGROUP_TYPE_DEPRECATED)

    for secgroup in secgroups:
        secgroup_id = \
            secgroup.target.instance.runtime_properties[EXTERNAL_RESOURCE_ID]
        secgroups_from_params.append(secgroup_id)
    params[SECGROUPS] = secgroups_from_params

    # Actually create the resource
    output = iface.create(params)
    lb_id = output['LoadBalancers'][0][RESOURCE_NAME]
    iface.resource_id = lb_id
    try:
        utils.update_resource_id(
            ctx.instance, lb_id)
        utils.update_resource_arn(
            ctx.instance, output['LoadBalancers'][0][LB_ARN])
    except (IndexError, KeyError) as e:
        raise NonRecoverableError(
            '{0}: {1} or {2} not located in response: {3}'.format(
                text_type(e), RESOURCE_NAME, LB_ARN, output))


@decorators.aws_resource(ELBLoadBalancer,
                         RESOURCE_TYPE,
                         waits_for_status=False)
def modify(ctx, iface, resource_config, **_):
    '''modify an AWS ELB load balancer attributes'''
    if LB_ARN not in resource_config:
        resource_config.update(
            {LB_ARN: ctx.instance.runtime_properties.get(
                EXTERNAL_RESOURCE_ARN)})
    modify_params_attributes = resource_config.pop(LB_ATTR, {})
    if modify_params_attributes:
        # Add the LB ARN
        modify_params = {}
        modify_params[LB_ARN] = resource_config.get(LB_ARN)
        modify_params[LB_ATTR] = modify_params_attributes
        # Actually modify the resource
        attributes = iface.modify_attribute(modify_params)
        if 'resource_config' not in ctx.instance.runtime_properties:
            ctx.instance.runtime_properties['resource_config'] = {}
        ctx.instance.runtime_properties['resource_config'][LB_ATTR] = \
            attributes


@decorators.aws_resource(ELBLoadBalancer, RESOURCE_TYPE,
                         ignore_properties=True)
@decorators.wait_for_delete(status_pending=['active'])
def delete(ctx, iface, resource_config, **_):
    '''Deletes an AWS ELB load balancer'''
    if LB_ARN not in resource_config:
        resource_config.update({LB_ARN: iface.properties.get(LB_ARN)})
    iface.delete(resource_config)

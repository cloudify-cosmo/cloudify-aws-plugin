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
    ELB.classic.load_balancer
    ~~~~~~~~~~~~
    AWS ELB load balancer interface
"""
# Third Party imports
from botocore.exceptions import ClientError, ParamValidationError

# Local imports
from cloudify.exceptions import OperationRetry
from cloudify_aws.common import decorators, utils
from cloudify_aws.elb import ELBBase
from cloudify_aws.common.connection import Boto3Connection
from cloudify_aws.common.constants import EXTERNAL_RESOURCE_ID

RESOURCE_TYPE = 'ELB Classic Load Balancer'
RESOURCE_NAME = 'LoadBalancerName'
LB_ARN = 'LoadBalancerArn'
SUBNET_TYPE = 'cloudify.nodes.aws.ec2.Subnet'
SUBNET_TYPE_DEPRECATED = 'cloudify.aws.nodes.Subnet'
SECGROUP_TYPE = 'cloudify.nodes.aws.ec2.SecurityGroup'
SECGROUP_TYPE_DEPRECATED = 'cloudify.aws.nodes.SecurityGroup'
SUBNETS = 'Subnets'
SECGROUPS = 'SecurityGroups'


class ELBClassicLoadBalancer(ELBBase):
    """
        AWS ELB classic load balancer interface
    """
    def __init__(self, ctx_node, resource_id=None, client=None, logger=None):
        ELBBase.__init__(
            self,
            ctx_node,
            resource_id,
            client or Boto3Connection(ctx_node).client('elb'),
            logger)
        self.type_name = RESOURCE_TYPE

    @property
    def properties(self):
        """Gets the properties of an external resource"""
        try:
            resources = self.client.describe_load_balancers(
                LoadBalancerNames=[self.resource_id])
        except (ParamValidationError, ClientError):
            pass
        else:
            return resources['LoadBalancerDescriptions'][0] \
                if resources else None

    @property
    def status(self):
        """Gets the status of an external resource"""
        props = self.properties
        if not props:
            return None
        return props.get('State', {}).get('Code')

    def create(self, params):
        """
            Create a new AWS ELB classic load balancer.
        .. note:
            See http://bit.ly/2qtaai1 for config details.
        """
        return self.make_client_call('create_load_balancer', params)

    def delete(self, params=None):
        """
            Deletes an existing ELB classic load balancer.
        .. note:
            See http://bit.ly/2qsY7kS for config details.
        """
        self.logger.debug('Deleting %s with parameters: %s'
                          % (self.type_name, params))
        self.client.delete_load_balancer(**params)

    def modify_attributes(self, params):
        """
            Modify a AWS ELB classic load balancer attributes.
        .. note:
            See http://bit.ly/2pwMHtb for config details.
        """
        self.logger.debug('Modifying %s with parameters: %s'
                          % (self.type_name, params))
        res = self.client.modify_load_balancer_attributes(**params)
        self.logger.debug('Response: %s' % res)
        return res

    def register_instances(self, params):
        """
            Register a AWS ELB classic load balancer attributes.
        .. note:
            See http://bit.ly/2pIXB10 for config details.
        """
        return self.make_client_call(
            'register_instances_with_load_balancer', params)

    def deregister_instances(self, params):
        """
            Deregister a AWS ELB classic load balancer attributes.
        .. note:
            See http://bit.ly/2pIXB10 for config details.
        """
        return self.make_client_call(
            'deregister_instances_from_load_balancer', params)


@decorators.aws_resource(ELBClassicLoadBalancer,
                         RESOURCE_TYPE,
                         waits_for_status=False)
def prepare(ctx, resource_config, **_):
    """Prepares an ELB classic load balancer"""
    # Save the parameters
    ctx.instance.runtime_properties['resource_config'] = resource_config


@decorators.aws_resource(ELBClassicLoadBalancer,
                         RESOURCE_TYPE,
                         waits_for_status=False)
@decorators.aws_params(RESOURCE_NAME, params_priority=False)
def create(ctx, iface, resource_config, params, **_):
    """Creates an AWS ELB classic load balancer"""

    # Add Subnets
    subnets_list = params.get(SUBNETS, [])
    params[SUBNETS] = \
        utils.add_resources_from_rels(
            ctx.instance,
            SUBNET_TYPE,
            subnets_list) or utils.add_resources_from_rels(
            ctx.instance,
            SUBNET_TYPE_DEPRECATED,
            subnets_list)

    # Add Security Groups
    secgroups_list = params.get(SECGROUPS, [])
    params[SECGROUPS] = \
        utils.add_resources_from_rels(
            ctx.instance,
            SECGROUP_TYPE,
            secgroups_list) or \
        utils.add_resources_from_rels(
            ctx.instance,
            SECGROUP_TYPE_DEPRECATED,
            secgroups_list)

    create_response = iface.create(params)

    # Actually create the resource
    ctx.instance.runtime_properties['DNSName'] = \
        create_response['DNSName']
    ctx.instance.runtime_properties['create_response'] = \
        create_response


@decorators.aws_resource(ELBClassicLoadBalancer,
                         RESOURCE_TYPE,
                         ignore_properties=True,
                         waits_for_status=False)
def start(ctx, iface, resource_config, **_):
    """modify an AWS ELB load balancer attributes"""

    # Create a copy of the resource config for clean manipulation.
    params = \
        dict() if not resource_config else resource_config.copy()

    if not params:
        return

    lb = params.get(RESOURCE_NAME)
    if not lb:
        lb = ctx.instance.runtime_properties.get(RESOURCE_NAME)
        params.update(({RESOURCE_NAME: lb}))

    # Actually modify the resource
    attributes = iface.modify_attributes(params)
    ctx.instance.runtime_properties['LoadBalancerAttributes'] = \
        attributes


@decorators.aws_resource(ELBClassicLoadBalancer,
                         RESOURCE_TYPE,
                         ignore_properties=True,
                         waits_for_status=False)
def delete(ctx, iface, resource_config, **_):
    """Deletes an AWS ELB classic load balancer"""

    # Create a copy of the resource config for clean manipulation.
    params = \
        dict() if not resource_config else resource_config.copy()

    lb_arn = params.get(LB_ARN)
    if not lb_arn:
        params.update({RESOURCE_NAME: iface.resource_id})

    iface.delete(params)


@decorators.aws_relationship(ELBClassicLoadBalancer, RESOURCE_TYPE)
def assoc(ctx, **_):
    """associate instance with ELB classic LB"""
    instance_id = \
        ctx.source.instance.runtime_properties.get(
            EXTERNAL_RESOURCE_ID)
    lb = ctx.target.instance.runtime_properties.get(EXTERNAL_RESOURCE_ID)
    iface = \
        ELBClassicLoadBalancer(ctx.target.node, lb, logger=ctx.logger)
    if ctx.operation.retry_number == 0:
        iface.register_instances(
            {RESOURCE_NAME: lb, 'Instances': [{'InstanceId': instance_id}]})
    if 'instances' not in ctx.target.instance.runtime_properties:
        ctx.target.instance.runtime_properties['instances'] = []
    instances_list = ctx.target.instance.runtime_properties['instances']
    if instance_id not in instances_list:
        instances_list.append(instance_id)
    ctx.target.instance.runtime_properties['instances'] = instances_list
    actual_instance_ids = \
        [i['InstanceId'] for i in iface.properties['Instances']]
    if instance_id not in actual_instance_ids:
        raise OperationRetry(
            'Waiting for Instance {0} to be added to ELB {1}.'.format(
                instance_id, lb))


@decorators.aws_relationship(ELBClassicLoadBalancer, RESOURCE_TYPE)
def disassoc(ctx, **_):
    """disassociate instance with ELB classic LB"""
    instance_id = \
        ctx.source.instance.runtime_properties.get(
            EXTERNAL_RESOURCE_ID)
    lb = ctx.target.instance.runtime_properties.get(
        EXTERNAL_RESOURCE_ID)
    iface = \
        ELBClassicLoadBalancer(ctx.target.node, lb, logger=ctx.logger)
    iface.deregister_instances(
        {RESOURCE_NAME: lb, 'Instances': [{'InstanceId': instance_id}]})
    instances_list = ctx.target.instance.runtime_properties['instances']
    instances_list.remove(instance_id)
    ctx.target.instance.runtime_properties['instances'] = instances_list
    if instance_id in [i['InstanceId'] for i in iface.properties['Instances']]:
        raise OperationRetry(
            'Waiting for Instance {0} to be removed from ELB {1}.'.format(
                instance_id, lb))

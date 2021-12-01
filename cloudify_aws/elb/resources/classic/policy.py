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
    ELB.classic.policy
    ~~~~~~~~~~~~
    AWS ELB classic policy interface
"""
# Third party imports
from botocore.exceptions import ClientError

from cloudify.exceptions import OperationRetry

# Local imports
from cloudify_aws.elb import ELBBase
from cloudify_aws.common._compat import text_type
from cloudify_aws.common import decorators, utils
from cloudify_aws.common.connection import Boto3Connection
from cloudify_aws.common.constants import EXTERNAL_RESOURCE_ID

RESOURCE_TYPE = 'ELB classic policy'
RESOURCE_NAME = 'PolicyName'
RESOURCE_NAMES = 'PolicyNames'
LB_NAME = 'LoadBalancerName'
LB_PORT = 'LoadBalancerPort'
LB_TYPE = 'cloudify.nodes.aws.elb.Classic.LoadBalancer'
LISTENER_TYPE = 'cloudify.nodes.aws.elb.Classic.Listener'


class ELBClassicPolicy(ELBBase):
    """
        AWS ELB classic policy interface
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
        return None

    @property
    def status(self):
        """Gets the status of an external resource"""
        return None

    def create(self, params):
        """
            Create a new AWS ELB classic policy.
        .. note:
            See http://bit.ly/2oYIQrZ for config details.
        """
        return self.make_client_call('create_load_balancer_policy', params)

    def create_sticky(self, params):
        """
            Create a new AWS ELB classic policy.
        .. note:
            See http://bit.ly/2oYIQrZ for config details.
        """
        self.logger.debug('Creating %s with parameters: %s'
                          % (self.type_name, params))
        res = \
            self.client.create_lb_cookie_stickiness_policy(**params)
        self.logger.debug('Response: %s' % res)
        return res

    def start(self, params):
        """
            Refresh the AWS ELB classic policies.
        .. note:
            See http://bit.ly/2qBuhb5 for config details.
        """
        self.logger.debug('Creating %s with parameters: %s'
                          % (self.type_name, params))
        res = self.client.set_load_balancer_policies_of_listener(**params)
        self.logger.debug('Response: %s' % res)
        return res

    def delete(self, params=None):
        """
            Deletes an existing ELB classic policy.
        .. note:
            See http://bit.ly/2qGiN5e for config details.
        """
        self.logger.debug('Deleting %s with parameters: %s'
                          % (self.type_name, params))
        return self.client.delete_load_balancer_policy(**params)


@decorators.aws_resource(ELBClassicPolicy, RESOURCE_TYPE)
def prepare(ctx, resource_config, **_):
    """Prepares an ELB classic policy"""
    # Save the parameters
    ctx.instance.runtime_properties['resource_config'] = resource_config


@decorators.aws_resource(ELBClassicPolicy, RESOURCE_TYPE)
@decorators.aws_params(RESOURCE_NAME, params_priority=False)
def create(ctx, iface, resource_config, params, **_):
    """Creates an AWS ELB classic policy"""

    lb_name = params.get(LB_NAME)
    if not lb_name:
        targs = \
            utils.find_rels_by_node_type(
                ctx.instance,
                LB_TYPE)
        lb_name = \
            targs[0].target.instance.runtime_properties[
                EXTERNAL_RESOURCE_ID]
        params.update({LB_NAME: lb_name})

    ctx.instance.runtime_properties[LB_NAME] = \
        lb_name

    # Actually create the resource
    iface.create(params)


@decorators.aws_resource(ELBClassicPolicy, RESOURCE_TYPE)
def create_sticky(ctx, iface, resource_config, **_):
    """Creates an AWS ELB classic policy"""

    # Create a copy of the resource config for clean manipulation.
    params = \
        dict() if not resource_config else resource_config.copy()

    lb_name = params.get(LB_NAME)
    policy_name = params.get(RESOURCE_NAME)

    if not lb_name:
        targs = \
            utils.find_rels_by_node_type(
                ctx.instance,
                LB_TYPE)
        lb_name = \
            targs[0].target.instance.runtime_properties[
                EXTERNAL_RESOURCE_ID]
        params.update({LB_NAME: lb_name})

    ctx.instance.runtime_properties[LB_NAME] = \
        lb_name
    ctx.instance.runtime_properties[RESOURCE_NAME] = \
        policy_name

    # Actually create the resource
    iface.create_sticky(params)


@decorators.aws_resource(ELBClassicPolicy,
                         RESOURCE_TYPE,
                         ignore_properties=True)
def start_sticky(ctx, iface, resource_config, **_):
    """Starts an AWS ELB classic policy"""

    # Create a copy of the resource config for clean manipulation.
    params = \
        dict() if not resource_config else resource_config.copy()

    lb_name = params.get(LB_NAME)
    lb_port = params.get(LB_PORT)
    policy_names = params.get(RESOURCE_NAMES)

    # This operations requires the LoadBalancerName, LoadBalancerPort,
    # and the PolicyName.
    if not lb_name:
        targs = \
            utils.find_rels_by_node_type(
                ctx.instance,
                LB_TYPE)
        lb_name = \
            targs[0].target.instance.runtime_properties[
                EXTERNAL_RESOURCE_ID]
        ctx.instance.runtime_properties[LB_NAME] = \
            lb_name
        params.update({LB_NAME: lb_name})

    # The LoadBalancerPort can come either from the resource config,
    # or it can come from a relationship to a Listener or a LoadBalancer.
    # A listener is prefered because only one LoadBalancerPort is expected
    # to be defined per listener, whereas a LoadBalancer many listeners
    # are defined. If many listeners are found then the first listener is
    # used.
    if not lb_port:
        targs = \
            utils.find_rels_by_node_type(
                ctx.instance,
                LISTENER_TYPE)
        if not targs:
            targs = \
                utils.find_rels_by_node_type(
                    ctx.instance,
                    LB_TYPE)
            instance_cfg = \
                targs[0].target.instance.runtime_properties['resource_config']
        else:
            instance_cfg = \
                targs[0].target.instance.runtime_properties['resource_config']
        listener = instance_cfg.get('Listeners', [{}])[0]
        lb_port = listener.get(LB_PORT)
        params.update({LB_PORT: lb_port})

    # This API call takes a list of policies as an argument.
    # However this node type represents only one policy.
    # Therefore we restrict the usage.
    if not policy_names:
        policy_names = ctx.instance.runtime_properties[RESOURCE_NAME]
        params.update({RESOURCE_NAMES: [policy_names]})

    # Actually create the resource
    iface.start(params)


@decorators.aws_resource(ELBClassicPolicy, RESOURCE_TYPE)
def delete(ctx, iface, resource_config, **_):
    """Deletes an AWS ELB classic policy"""

    # Create a copy of the resource config for clean manipulation.
    params = \
        dict() if not resource_config else resource_config.copy()

    lb = params.get(LB_NAME) or ctx.instance.runtime_properties.get(LB_NAME)
    policy = \
        params.get(RESOURCE_NAME) or \
        ctx.instance.runtime_properties.get(RESOURCE_NAME)

    lb_delete_params = {
        LB_NAME: lb,
        RESOURCE_NAME: policy
    }

    try:
        iface.delete(lb_delete_params)
    except ClientError as e:
        if _.get('force'):
            raise OperationRetry('Retrying: {0}'.format(text_type(e)))
        pass

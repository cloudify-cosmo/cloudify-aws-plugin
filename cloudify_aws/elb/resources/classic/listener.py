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
    ELB.classic.listener
    ~~~~~~~~~~~~
    AWS ELB classic listener interface
"""
# Cloudify
from cloudify_aws.common import decorators, utils
from cloudify_aws.elb import ELBBase
from cloudify_aws.common.connection import Boto3Connection
from cloudify_aws.common.constants import EXTERNAL_RESOURCE_ID

RESOURCE_TYPE = 'ELB classic Listener'
LISTENER_ARN = 'ListenerArn'
LB_NAME = 'LoadBalancerName'
LB_PORT = 'LoadBalancerPort'
LB_PORTS = 'LoadBalancerPorts'
LB_TYPE = 'cloudify.nodes.aws.elb.Classic.LoadBalancer'
LISTENERS = 'Listeners'


class ELBClassicListener(ELBBase):
    """
        AWS ELB classic listener interface
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
        props = self.properties
        if not props:
            return None

        # pylint: disable=E1136
        return props['State']['Code']

    def create(self, params):
        """
            Create a new AWS ELB classic listener.
        .. note:
            See http://bit.ly/2p741nK for config details.
        """
        return self.make_client_call('create_load_balancer_listeners', params)

    def delete(self, params=None):
        """
            Deletes an existing ELB classic listener.
        .. note:
            See http://bit.ly/2oWfEln for config details.
        """
        self.logger.debug('Deleting %s with parameters: %s'
                          % (self.type_name, params))
        return self.client.delete_load_balancer_listeners(**params)


@decorators.aws_resource(ELBClassicListener, RESOURCE_TYPE)
def prepare(ctx, resource_config, **_):
    """Prepares an ELB classic listener"""
    # Save the parameters
    ctx.instance.runtime_properties['resource_config'] = resource_config


@decorators.aws_resource(ELBClassicListener, RESOURCE_TYPE)
def create(ctx, iface, resource_config, **_):
    """Creates an AWS ELB classic listener"""

    # Create a copy of the resource config for clean manipulation.
    params = utils.clean_params(
        dict() if not resource_config else resource_config.copy())

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

    ctx.instance.runtime_properties[LB_NAME] = lb_name

    # Actually create the resource
    iface.create(params)


@decorators.aws_resource(ELBClassicListener, RESOURCE_TYPE)
def delete(ctx, iface, resource_config, **_):
    """Deletes an AWS ELB classic listener"""

    # Create a copy of the resource config for clean manipulation.
    params = \
        dict() if not resource_config else resource_config.copy()

    lb = params.get(LB_NAME)
    if not lb:
        lb = ctx.instance.runtime_properties[LB_NAME]

    for listener in params.get(LISTENERS, []):
        ports = [listener.get(LB_PORT)]
        iface.delete({LB_NAME: lb, LB_PORTS: ports})

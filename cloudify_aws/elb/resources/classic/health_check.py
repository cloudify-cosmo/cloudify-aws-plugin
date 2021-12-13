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
    ELB.classic.health_check
    ~~~~~~~~~~~~
    AWS ELB classic health check interface
"""
# Cloudify
from cloudify_aws.common import decorators, utils
from cloudify_aws.elb import ELBBase
from cloudify_aws.common.connection import Boto3Connection
from cloudify_aws.common.constants import EXTERNAL_RESOURCE_ID

RESOURCE_TYPE = 'ELB classic health check'
LB_NAME = 'LoadBalancerName'
LB_TYPE = 'cloudify.nodes.aws.elb.Classic.LoadBalancer'


class ELBClassicHealthCheck(ELBBase):
    """
        AWS ELB classic health check interface
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
            Configure a new AWS ELB classic health check.
        .. note:
            See http://bit.ly/2p741nK for config details.
        """
        return self.make_client_call('configure_health_check', params)

    def delete(self, params=None):
        return None


@decorators.aws_resource(ELBClassicHealthCheck,
                         RESOURCE_TYPE,
                         waits_for_status=False)
def prepare(ctx, resource_config, **_):
    """Prepares an ELB classic health check"""
    # Save the parameters
    ctx.instance.runtime_properties['resource_config'] = resource_config


@decorators.aws_resource(ELBClassicHealthCheck,
                         RESOURCE_TYPE,
                         waits_for_status=False)
def create(ctx, iface, resource_config, **_):
    """Creates an AWS ELB classic health check"""

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

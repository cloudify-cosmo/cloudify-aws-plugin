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
    EKSNodeGroup
    ~~~~~~~~~~~~~~
    AWS EKS Node Group interface
"""

from __future__ import unicode_literals

# Boto

from botocore.exceptions import ClientError, ParamValidationError

from cloudify.exceptions import OperationRetry

# Cloudify
from cloudify_aws.common import decorators, utils
from cloudify_aws.eks import EKSBase

RESOURCE_TYPE = 'EKS Node Group'
CLUSTER_NAME = 'clusterName'
NODEGROUP_NAME = 'nodegroupName'
NODEGROUP_ARN = 'nodegroupArn'
NODEGROUP = 'nodegroup'


class EKSNodeGroup(EKSBase):
    """
        EKS Node Group interface
    """
    def __init__(self, ctx_node, resource_id=None, client=None, logger=None):
        EKSBase.__init__(self, ctx_node, resource_id, client, logger)
        self.type_name = RESOURCE_TYPE
        self.describe_param = {}

    @property
    def properties(self):
        """Gets the properties of an external resource"""
        try:
            properties = \
                self.client.describe_nodegroup(
                    **self.describe_param
                )[NODEGROUP]
        except (ParamValidationError, ClientError):
            pass
        else:
            return None if not properties else properties

    @property
    def status(self):
        """Gets the status of an external resource"""
        props = self.properties
        if not props:
            return None
        return props.get('status')

    @property
    def check_status(self):
        if self.status in ['ACTIVE']:
            return 'OK'
        return 'NOT OK'

    def create(self, params):
        """
            Create a new AWS EKS Node Group.
        """
        return self.make_client_call('create_nodegroup', params)

    def wait_for_nodegroup(self, params, status):
        """
            wait for AWS EKS Node Group.
        """
        waiter = self.client.get_waiter(status)
        waiter.wait(
            clusterName=params.get(CLUSTER_NAME),
            nodegroupName=params.get(NODEGROUP_NAME),
            WaiterConfig={
                'Delay': 30,
                'MaxAttempts': 40
            }
        )

    def start(self, params):
        """
            Updates the AWS EKS Node Group.
        """
        return self.make_client_call('update_nodegroup_config', params)

    def delete(self, params=None):
        """
            Deletes an existing AWS EKS Node Group.
        """
        res = self.client.delete_nodegroup(
            **{CLUSTER_NAME: params.get(CLUSTER_NAME),
               NODEGROUP_NAME: params.get(NODEGROUP_NAME)}
        )
        self.logger.debug('Response: {}'.format(res))
        return res


def prepare_describe_node_group_filter(params, iface):
    iface.describe_param = {
        CLUSTER_NAME: params.get(CLUSTER_NAME),
        NODEGROUP_NAME: params.get(NODEGROUP_NAME),
    }
    return iface


@decorators.aws_resource(EKSNodeGroup,
                         resource_type=RESOURCE_TYPE,
                         waits_for_status=False)
def prepare(ctx, resource_config, **_):
    """Prepares an AWS EKS Node Group"""
    # Save the parameters
    ctx.instance.runtime_properties['resource_config'] = resource_config


@decorators.aws_resource(EKSNodeGroup, RESOURCE_TYPE, waits_for_status=False)
def create(ctx, iface, resource_config, **_):
    """Creates an AWS EKS Node Group"""
    params = dict() if not resource_config else resource_config.copy()
    resource_id = \
        utils.get_resource_id(
            ctx.node,
            ctx.instance,
            params.get(NODEGROUP_NAME),
            use_instance_id=True
        )

    utils.update_resource_id(ctx.instance, resource_id)
    iface = prepare_describe_node_group_filter(resource_config.copy(), iface)
    try:
        response = iface.create(params)
    except ClientError as e:
        raise OperationRetry(
            'Waiting for cluster to be ready...{e}'.format(e=e))
    if response and response.get(NODEGROUP):
        resource_arn = response.get(NODEGROUP).get(NODEGROUP_ARN)
        utils.update_resource_arn(ctx.instance, resource_arn)
    # wait for nodegroup to be active
    ctx.logger.info("Waiting for NodeGroup to become Active")
    iface.wait_for_nodegroup(params, 'nodegroup_active')


@decorators.aws_resource(EKSNodeGroup, RESOURCE_TYPE, waits_for_status=False)
def start(ctx, iface, resource_config, **_):
    """Updates an AWS EKS Node Group"""
    params = dict() if not resource_config else resource_config.copy()
    resource_id = \
        utils.get_resource_id(
            ctx.node,
            ctx.instance,
            params.get(NODEGROUP_NAME),
            use_instance_id=True
        )
    utils.update_resource_id(ctx.instance, resource_id)
    iface = prepare_describe_node_group_filter(resource_config.copy(), iface)
    valid_keys = [
        "clusterName", "nodegroupName", "labels", "taints",
        "scalingConfig", "updateConfig", "clientRequestToken"
    ]
    valid_params = {x: params.get(x) for x in valid_keys
                    if params.get(x) is not None}
    try:
        response = iface.start(valid_params)
    except ClientError as e:
        raise OperationRetry(
            'Waiting for cluster to be ready...{e}'.format(e=e))
    if response and response.get(NODEGROUP):
        resource_arn = response.get(NODEGROUP).get(NODEGROUP_ARN)
        utils.update_resource_arn(ctx.instance, resource_arn)
    # wait for nodegroup to be active
    ctx.logger.info("Waiting for NodeGroup to become \"Active\".")
    iface.wait_for_nodegroup(params, 'nodegroup_active')


@decorators.aws_resource(EKSNodeGroup, RESOURCE_TYPE, waits_for_status=False)
def delete(ctx, iface, resource_config, **_):
    """Deletes an AWS EKS Node Group"""

    params = dict() if not resource_config else resource_config.copy()
    iface.delete(params)
    # wait for nodegroup to be deleted
    ctx.logger.info("Waiting for NodeGroup to be deleted")
    iface.wait_for_nodegroup(params, 'nodegroup_deleted')


interface = EKSNodeGroup

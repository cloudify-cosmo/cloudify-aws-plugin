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
from botocore.exceptions import ClientError, WaiterError

# Cloudify
from cloudify_aws.common import decorators, utils
from cloudify_aws.eks import EKSBase
from cloudify.exceptions import OperationRetry, NonRecoverableError

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
        self._id_key = NODEGROUP_NAME
        self._type_key = NODEGROUP
        self._properties = {}
        self._describe_call = 'describe_nodegroup'
        self._describe_param = {}
        self.ctx_node = ctx_node
        self._cluster_name = None or self.initial_configuration.get(
            CLUSTER_NAME)
        self._node_group_name = None or self.initial_configuration.get(
            self._id_key)

    @property
    def cluster_name(self):
        if not self._cluster_name:
            self._cluster_name = self.initial_configuration.get(CLUSTER_NAME)
        return self._cluster_name

    @cluster_name.setter
    def cluster_name(self, value):
        self._cluster_name = value

    @property
    def node_group_name(self):
        if not self.resource_id and not self._node_group_name:
            return self.initial_configuration.get(self._id_key)
        if self._node_group_name:
            return self._node_group_name
        return self.resource_id

    @node_group_name.setter
    def node_group_name(self, value):
        self._node_group_name = value

    @property
    def describe_param(self):
        if not self._describe_param:
            self._describe_param = {
                CLUSTER_NAME: self.cluster_name,
                NODEGROUP_NAME: self.node_group_name
            }
        return self._describe_param

    @describe_param.setter
    def describe_param(self, value):
        self._describe_param = value

    def wait_for_status(self):
        try:
            self.wait_for_nodegroup(
                self.describe_param, 'nodegroup_active',
                max_attempt=30)
        except WaiterError:
            raise OperationRetry('Waiting for nodegroup...')

    # @property
    # def properties(self):
    #     """Gets the properties of an external resource"""
    #     try:
    #         self.logger.info(
    #             'Describe params: {}'.format(self.describe_params))
    #         result = self.client.describe_nodegroup(**self.describe_params)
    #         self.logger.info('Describe result: {}'.format(result))
    #         properties = result[NODEGROUP]
    #     except (ParamValidationError, ClientError):
    #         pass
    #     else:
    #         return None if not properties else properties

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

    def describe(self, params=None):
        """
            Create a new AWS EKS Node Group.
        """
        params = params or self.describe_param
        return self.get_describe_result(params)

    def wait_for_nodegroup(self, params, status, max_attempt=None):
        """
            wait for AWS EKS Node Group.
        """

        max_attempt = max_attempt or 30
        waiter = self.client.get_waiter(status)
        try:
            waiter.wait(
                clusterName=params.get(CLUSTER_NAME),
                nodegroupName=params.get(NODEGROUP_NAME),
                WaiterConfig={
                    'Delay': 30,
                    'MaxAttempts': max_attempt
                }
            )
        except WaiterError:
            self.logger.error('Timed out waiting {} {}'.format(
                self.resource_id, self.status))
            raise

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


@decorators.aws_resource(EKSNodeGroup, RESOURCE_TYPE)
@decorators.wait_for_status(status_pending=['CREATING', 'UPDATING'],
                            status_good=['ACTIVE', 'available'])
def create(ctx, iface, resource_config, **_):
    """Creates an AWS EKS Node Group"""
    resource_id = \
        utils.get_resource_id(
            ctx.node,
            ctx.instance,
            resource_config.get(NODEGROUP_NAME),
            use_instance_id=True
        )

    utils.update_resource_id(ctx.instance, resource_id)
    iface.node_group_name = resource_config.get(NODEGROUP_NAME)
    iface.cluster_name = resource_config.get(CLUSTER_NAME)
    try:
        response = iface.create(resource_config)
    except (NonRecoverableError, ClientError) as e:
        if 'ResourceInUseException' not in str(e):
            raise e
    else:
        resource_arn = response.get(NODEGROUP).get(NODEGROUP_ARN)
        utils.update_resource_arn(ctx.instance, resource_arn)
        resource_id = response.get(NODEGROUP).get(NODEGROUP_NAME)
        utils.update_resource_id(ctx.instance, resource_id)
        iface.update_resource_id(resource_id)
        ctx.instance.runtime_properties["cluster_name"] = \
            response.get(NODEGROUP).get("clusterName")
        ctx.instance.runtime_properties['create_response'] = \
            utils.JsonCleanuper(response).to_dict()
    # wait for nodegroup to be active
    ctx.logger.info("Waiting for NodeGroup to become Active")
    iface.wait_for_nodegroup(resource_config, 'nodegroup_active')


@decorators.aws_resource(EKSNodeGroup, RESOURCE_TYPE, waits_for_status=False)
def start(ctx, iface, resource_config, **_):
    """Updates an AWS EKS Node Group"""
    resource_id = \
        utils.get_resource_id(
            ctx.node,
            ctx.instance,
            resource_config.get(NODEGROUP_NAME),
            use_instance_id=True
        )
    utils.update_resource_id(ctx.instance, resource_id)
    iface = prepare_describe_node_group_filter(resource_config.copy(), iface)
    valid_keys = [
        "clusterName", "nodegroupName", "labels", "taints",
        "scalingConfig", "updateConfig", "clientRequestToken"
    ]
    valid_params = {x: resource_config.get(x) for x in valid_keys
                    if resource_config.get(x) is not None}
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
    iface.wait_for_nodegroup(resource_config, 'nodegroup_active')


@decorators.aws_resource(EKSNodeGroup, RESOURCE_TYPE, waits_for_status=False)
def delete(ctx, iface, resource_config, **_):
    """Deletes an AWS EKS Node Group"""

    iface.delete(resource_config)
    # wait for nodegroup to be deleted
    ctx.logger.info("Waiting for NodeGroup to be deleted")
    iface.wait_for_nodegroup(resource_config, 'nodegroup_deleted')


@decorators.aws_resource(class_decl=EKSNodeGroup,
                         resource_type=RESOURCE_TYPE,
                         waits_for_status=False)
def check_drift(ctx, iface=None, **_):
    return utils.check_drift(RESOURCE_TYPE, iface, ctx.logger)


@decorators.aws_resource(class_decl=EKSNodeGroup,
                         resource_type=RESOURCE_TYPE,
                         waits_for_status=False)
def poststart(ctx, iface=None, **_):
    utils.update_expected_configuration(iface, ctx.instance.runtime_properties)


interface = EKSNodeGroup

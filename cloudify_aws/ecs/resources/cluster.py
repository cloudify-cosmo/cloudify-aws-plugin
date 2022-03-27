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
    ECSCluster
    ~~~~~~~~~~~~~~
    AWS ECS Cluster interface
"""

from __future__ import unicode_literals

from cloudify.exceptions import NonRecoverableError
# Cloudify
from cloudify_aws.common import decorators, utils
from cloudify_aws.ecs import ECSBase

RESOURCE_TYPE = 'ECS Cluster'
CLUSTERS = 'clusters'
CLUSTER = 'cluster'
CLUSTER_ARN = 'clusterArn'
CLUSTER_RESOURCE_NAME = 'clusterName'


class ECSCluster(ECSBase):
    """
        ECSCluster interface
    """
    def __init__(self, ctx_node, resource_id=None, client=None, logger=None):
        ECSBase.__init__(self, ctx_node, resource_id, client, logger)
        self._properties = {}
        self.type_name = RESOURCE_TYPE
        self.describe_cluster_filter = {}

    @property
    def properties(self):
        """Gets the properties of an external resource"""
        if not self._properties:
            try:
                resources = self.make_client_call(
                    'describe_clusters', self.describe_cluster_filter)
            except NonRecoverableError:
                return
            if CLUSTERS in resources:
                for resource in resources[CLUSTERS]:
                    if resource.get(CLUSTER_RESOURCE_NAME) == self.resource_id:
                        self._properties = resource
        return self._properties

    @property
    def status(self):
        """Gets the status of an external resource"""
        if self.properties:
            return self.properties.get('status')

    def create(self, params):
        """
            Create a new AWS ECS cluster.
        """
        return self.make_client_call('create_cluster', params)

    def delete(self, params=None):
        """
            Deletes an existing AWS ECS cluster.
        """
        res = self.client.delete_cluster(
            **{CLUSTER: params.get(CLUSTER_RESOURCE_NAME)}
        )
        self.logger.debug('Response: {}'.format(res))
        return res


def prepare_describe_cluster_filter(params, iface):
    iface.describe_cluster_filter = {
        CLUSTERS: [params.get(CLUSTER_RESOURCE_NAME)],
    }
    return iface


@decorators.aws_resource(ECSCluster, RESOURCE_TYPE)
def prepare(ctx, resource_config, **_):
    """Prepares an AWS ECS Cluster"""
    # Save the parameters
    ctx.instance.runtime_properties['resource_config'] = resource_config


@decorators.aws_resource(ECSCluster, RESOURCE_TYPE)
def create(ctx, iface, resource_config, **_):
    """Creates an AWS ECS Cluster"""
    resource_id = \
        utils.get_resource_id(
            ctx.node,
            ctx.instance,
            resource_config.get(CLUSTER_RESOURCE_NAME),
            use_instance_id=True
        )

    utils.update_resource_id(ctx.instance, resource_id)
    iface = prepare_describe_cluster_filter(resource_config.copy(), iface)
    response = iface.create(resource_config)
    if response and response.get(CLUSTER):
        resource_arn = response[CLUSTER].get(CLUSTER_ARN)
        utils.update_resource_arn(ctx.instance, resource_arn)


@decorators.aws_resource(ECSCluster, RESOURCE_TYPE)
def delete(ctx, iface, resource_config, **_):
    """Deletes an AWS ECS Cluster"""
    iface.delete(resource_config)

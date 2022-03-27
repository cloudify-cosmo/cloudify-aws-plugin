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
    ECSService
    ~~~~~~~~~~~~~~
    AWS ECS Service interface
"""

from __future__ import unicode_literals

# Boto

from botocore.exceptions import ClientError, ParamValidationError

# Cloudify
from cloudify_aws.common import decorators, utils
from cloudify_aws.ecs import ECSBase
from cloudify_aws.common.constants import EXTERNAL_RESOURCE_ID

from cloudify.exceptions import NonRecoverableError

RESOURCE_TYPE = 'ECS Service'
CLUSTER = 'cluster'
CLUSTER_TYPE = 'cloudify.nodes.aws.ecs.Cluster'
SERVICES = 'services'
SERVICE = 'service'
SERVICE_ARN = 'serviceArn'
SERVICE_RESOURCE = 'serviceName'


class ECSService(ECSBase):
    """
        ECSService interface
    """
    def __init__(self, ctx_node, resource_id=None, client=None, logger=None):
        ECSBase.__init__(self, ctx_node, resource_id, client, logger)
        self.type_name = RESOURCE_TYPE
        self.describe_service_filter = {}

    @property
    def properties(self):
        """Gets the properties of an external resource"""
        try:
            resources = \
                self.client.describe_services(
                    **self.describe_service_filter
                )
        except (ParamValidationError, ClientError):
            pass
        else:
            return None if not resources else resources.get(SERVICES)[0]

    @property
    def status(self):
        """Gets the status of an external resource"""
        props = self.properties
        if not props:
            return None
        return props.get('status')

    def create(self, params):
        """
            Create a new AWS ECS Service.
        """
        return self.make_client_call('create_service', params)

    def delete(self, params=None):
        """
            Deletes an existing AWS ECS Service.
        """
        # Update service by set desiredCount 0 so that
        # We can remove it
        res = None
        self._update_service(params)
        self.logger.debug('Response: {}'.format(res))

        res = self.client.delete_service(**params)
        self.logger.debug('Response: {}'.format(res))
        return res

    def _update_service(self, params):
        """
        Updates an AWS ECS Service
        """
        params['desiredCount'] = 0
        res = self.client.update_service(**params)
        self.logger.debug('Response: {}'.format(res))
        del params['desiredCount']


def prepare_describe_service_filter(params, iface):
    iface.describe_service_filter = {
        CLUSTER: params.get(CLUSTER),
        SERVICES: [params.get(SERVICE_RESOURCE)],
    }
    return iface


def get_cluster_name(ctx):
    target_node = utils.find_rel_by_node_type(
        ctx.instance,
        CLUSTER_TYPE
    )
    if target_node is None:
        raise NonRecoverableError(
            'Service must be connected to type {0}'.format(
                CLUSTER_TYPE))
    cluster_name = \
        target_node.target.instance.runtime_properties.get(
            EXTERNAL_RESOURCE_ID
        )
    return cluster_name


@decorators.aws_resource(ECSService, RESOURCE_TYPE)
def prepare(ctx, resource_config, **_):
    """Prepares an AWS ECS Service"""
    # Save the parameters
    ctx.instance.runtime_properties['resource_config'] = resource_config


@decorators.aws_resource(ECSService, RESOURCE_TYPE)
def create(ctx, iface, resource_config, **_):
    """Creates an AWS ECS Service"""
    # Get the cluster name from either params or a relationship.
    cluster_name = resource_config.get(CLUSTER)
    if not cluster_name:
        resource_config[CLUSTER] = get_cluster_name(ctx)

    ctx.instance.runtime_properties[SERVICE] = \
        resource_config.get(SERVICE_RESOURCE)
    utils.update_resource_id(
        ctx.instance, resource_config.get(SERVICE_RESOURCE))

    iface = prepare_describe_service_filter(resource_config.copy(), iface)
    response = iface.create(resource_config)
    if response and response.get(SERVICE):
        resource_arn = response[SERVICE].get(SERVICE_ARN)
        utils.update_resource_arn(ctx.instance, resource_arn)


@decorators.aws_resource(ECSService, RESOURCE_TYPE)
def delete(ctx, iface, resource_config, **_):
    """Deletes an AWS ECS Service"""

    cluster_name = get_cluster_name(ctx)
    service_name = ctx.instance.runtime_properties.get(SERVICE)
    params = {CLUSTER: cluster_name, SERVICE: service_name}
    iface.delete(params)

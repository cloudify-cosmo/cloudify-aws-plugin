# #######
# Copyright (c) 2021 Cloudify Platform Ltd. All rights reserved
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

from cloudify.decorators import workflow
from cloudify.workflows import ctx as wtx
from cloudify.exceptions import NonRecoverableError

from .resources import get_resources
from ..common.utils import (
    get_regions,
    create_deployments,
    install_deployments
)

AWS_TYPE = 'cloudify.nodes.resources.AmazonWebServices'


def discover_resources(node_id=None,
                       resource_types=None,
                       regions=None,
                       ctx=None,
                       **_):

    discovered_resources = {}
    ctx = ctx or wtx
    node_id = node_id or get_aws_account_node_id(ctx.nodes)
    node = ctx.get_node(node_id)
    for node_instance in node.instances:
        if not isinstance(regions, list) and not regions:
            regions = get_regions(node, ctx.deployment.id)
        resources = get_resources(node, regions, resource_types, ctx.logger)
        discovered_resources.update(resources)
        node_instance._node_instance.runtime_properties['resources'] = \
            resources
        return discovered_resources
    raise NonRecoverableError(
        'No node instances of the provided node ID {n} exist. '
        'Please install the account blueprint.'.format(n=node_id))


def deploy_resources(group_id,
                     blueprint_id,
                     deployment_ids,
                     inputs,
                     labels,
                     ctx,
                     **_):
    """Create new deployments and execute install.

    :param group_id: The new Group ID.
    :param blueprint_id: The child blueprint ID.
    :param deployment_ids: A list of deployment IDs.
    :param inputs: A list of inputs in order of the deployment IDs.
    :param ctx:
    :param _:
    :return:
    """
    if not deployment_ids:
        return
    ctx.logger.info(
        'Creating deployments {dep} with blueprint {blu} '
        'with these inputs: {inp} and with these labels: {lab}'.format(
            dep=deployment_ids, blu=blueprint_id, inp=inputs, lab=labels))
    create_deployments(group_id, blueprint_id, deployment_ids, inputs, labels)


@workflow
def discover_and_deploy(node_id=None,
                        resource_types=None,
                        regions=None,
                        blueprint_id=None,
                        ctx=None,
                        **_):
    """This workflow will check against the parent "Account" node for
    resources of the types found in resource_types in regions.
    Then we deploy child deployments of those resources.

    :param node_id: An AWS_TYPE node template name.
    :param resource_types: List of crawlable types. (AWS::EKS::CLUSTER)
    :param regions: List of regions.
    :param blueprint_id: The blueprint ID to create child deployments with.
    :param ctx:
    :param _:
    :return:
    """

    ctx = ctx or wtx
    blueprint_id = blueprint_id or ctx.blueprint.id
    label_list = [{'csys-env-type': 'environment'},
                  {'csys-obj-parent': ctx.deployment.id}]
    # Refresh the AWS_TYPE nodes list..
    resources = discover_resources(node_id=node_id,
                                   resource_types=resource_types,
                                   regions=regions,
                                   ctx=ctx)
    # Loop over the resources to create new deployments from them.
    resource_type = None
    for region_name, resource_types in resources.items():
        deployment_ids_list = []
        inputs_list = []
        for resource_type, resources in resource_types.items():
            for resource_name, resource in resources.items():
                # We are now at the resource level.
                # Create the inputs and deployment ID for the new deployment.
                inputs_list.append(
                    {
                        'resource_name': resource_name,
                        'aws_region_name': region_name
                    }
                )
                deployment_ids_list.append(
                    generate_deployment_ids(ctx.deployment.id, resource_name)
                )

            if deployment_ids_list:
                label_list.append({'csys-env-type': resource_type})
                deploy_resources(ctx.deployment.id,
                                 blueprint_id,
                                 deployment_ids_list,
                                 inputs_list,
                                 label_list,
                                 ctx)
                del label_list[-1]
            deployment_ids_list = []
            inputs_list = []
    install_deployments(ctx.deployment.id)


def get_aws_account_node_id(nodes):
    """ Check and see if the Workflow Context Node is a supported account type.

    :param nodes: list of nodes from CTX.
    :return:
    """
    for node in nodes:
        if AWS_TYPE in node.type_hierarchy:
            return node.id
    raise NonRecoverableError(
        'The deployment has no nodes of type {t}.'.format(t=AWS_TYPE))


def generate_deployment_ids(deployment_id, resource_name):
    """ Create a simple child deployment name. I use a method because it
    makes the above code slightly less messy.

    :param deployment_id:
    :param resource_name:
    :return:
    """
    return '{parent}-{child}'.format(
        parent=deployment_id,
        child=resource_name)

#########
# Copyright (c) 2016 GigaSpaces Technologies Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
#  * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  * See the License for the specific language governing permissions and
#  * limitations under the License.

from cloudify_aws.boto3_connection import connection, b3operation

from cloudify.exceptions import NonRecoverableError
from cloudify.decorators import operation

from cloudify_aws.utils import get_relationships
from apigateway.resource import get_parents


@operation
def creation_validation(ctx):
    apis = set(
        get_parents(rel.target.instance)[1]
        for rel
        in get_relationships(
            ctx,
            filter_relationships=(
                'cloudify.aws.relationships.deployment_depends_on_method'))
        )

    api = get_relationships(
            ctx,
            filter_relationships='cloudify.aws.relationships.'
            'deployment_of_rest_api')
    if len(api) != 1 or len(apis) != 1:
        raise NonRecoverableError(
                "An API deployment must be related to a RestApi via "
                "'cloudify.aws.relationships.deployment_of_rest_api', "
                "and must be related to at least one method of the same API.")
    # TODO: using a private attr, is there a better way to get back to the node
    # from the instance object?
    apis_name = list(apis)[0]._node.name

    if apis_name != api[0].target.node.name:
        raise NonRecoverableError(
                "The deployment API must be the same API which the methods "
                "belong to.")


def get_deployment_props(ctx):
    props = ctx.node.properties

    stage_name = ctx.node.name
    if 'name' in props:
        stage_name = props['name']
    description = 'deployment for {}'.format(ctx.node.name)
    if 'description' in props:
        description = props['description']
    return stage_name, description


@b3operation
def create(ctx):
    props = ctx.node.properties
    client = connection(props['aws_config']).client('apigateway')

    api = get_relationships(
            ctx,
            filter_relationships=[
                'cloudify.aws.relationships.deployment_of_rest_api'],
            )[0].target.instance
    name, description = get_deployment_props(ctx)

    deployment = client.create_deployment(
        restApiId=api.runtime_properties['id'],
        stageName=name,
        stageDescription=description,
        description=description,
        )

    ctx.instance.runtime_properties.update({
        'id': deployment['id'],
        'name': name,
        'url': api.runtime_properties['url'] + name,
        })


@b3operation
def delete(ctx):
    props = ctx.node.properties
    client = connection(props['aws_config']).client('apigateway')

    api = get_relationships(
            ctx,
            filter_relationships=[
                'cloudify.aws.relationships.deployment_of_rest_api'],
            )[0].target.instance
    name, _ = get_deployment_props(ctx)
    deployment_id = ctx.instance.runtime_properties['id']

    if client.get_stage(
            restApiId=api.runtime_properties['id'],
            stageName=name
            )['deploymentId'] == deployment_id:
        client.delete_stage(
                restApiId=api.runtime_properties['id'],
                stageName=name)

    client.delete_deployment(
        restApiId=api.runtime_properties['id'],
        deploymentId=deployment_id)

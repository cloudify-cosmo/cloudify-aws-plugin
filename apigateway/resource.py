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

from core.boto3_connection import connection

from cloudify.decorators import operation
from cloudify.exceptions import NonRecoverableError


def get_parents(instance):
    for rel in instance.relationships:
        if rel.type in [
                'cloudify.aws.relationships.resource_in_api',
                'cloudify.aws.relationships.method_in_resource',
                'cloudify.aws.relationships.api_connected_to_lambda']:
            parent = rel.target.instance
            if rel.target.node.type == 'cloudify.aws.nodes.RestApi':
                return parent, rel.target.instance
            return parent, get_parents(parent)[1]
    raise NonRecoverableError("Didn't find the correct relationships")


@operation
def create(ctx):
    props = ctx.node.properties
    client = connection(props['aws_config']).client('apigateway')

    parent, api = get_parents(ctx.instance)

    resource = client.create_resource(
        restApiId=api.runtime_properties['id'],
        parentId=parent.runtime_properties['resource_id'],
        pathPart=ctx.node.name,
        )

    ctx.instance.runtime_properties.update({
        'id': resource['id'],
        'resource_id': resource['id'],
        })


@operation
def delete(ctx):
    props = ctx.node.properties
    client = connection(props['aws_config']).client('apigateway')

    _, api = get_parents(ctx.instance)

    client.delete_resource(
        restApiId=api.runtime_properties['id'],
        resourceId=ctx.instance.runtime_properties['id'],
        )

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


def get_root_resource(client, api):
    for item in client.get_resources(restApiId=api['id'])['items']:
        if item['path'] == '/':
            return item['id']
    raise NonRecoverableError(
        "Couldn't find the API's root resource. Something is wrong")


@operation
def create(ctx):
    props = ctx.node.properties
    client = connection(props['aws_config']).client('apigateway')

    api = client.create_rest_api(
        name=ctx.node.name,
        description=ctx.node.properties['description'],
        )

    ctx.instance.runtime_properties.update({
        'id': api['id'],
        'resource_id': get_root_resource(client, api),
        })


@operation
def delete(ctx):
    props = ctx.node.properties
    client = connection(props['aws_config']).client('apigateway')

    client.delete_rest_api(restApiId=ctx.instance.runtime_properties['id'])

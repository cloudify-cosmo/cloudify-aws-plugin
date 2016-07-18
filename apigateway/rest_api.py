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

from functools import partial

from cloudify.exceptions import NonRecoverableError

from cloudify_aws.boto3_connection import (
        connection,
        b3operation,
        run_maybe_throttled_call,
        )


api_url_template = "https://{api_id}.execute-api.{region}.amazonaws.com"


def get_root_resource(client, api):
    for item in client.get_resources(restApiId=api['id'])['items']:
        if item['path'] == '/':
            return item['id']
    raise NonRecoverableError(
        "Couldn't find the API's root resource. Something is wrong")


@b3operation
def create(ctx):
    props = ctx.node.properties
    client = connection(props['aws_config']).client('apigateway')

    api = run_maybe_throttled_call(
        ctx,
        partial(
            client.create_rest_api,
            name=ctx.node.name,
            description=ctx.node.properties['description'],
            )
        )
    if api is None:
        return

    ctx.instance.runtime_properties.update({
        'id': api['id'],
        'resource_id': get_root_resource(client, api),
        'url': api_url_template.format(
            api_id=api['id'],
            region=props['aws_config']['ec2_region_name']),
        })


@b3operation
def delete(ctx):
    props = ctx.node.properties
    client = connection(props['aws_config']).client('apigateway')

    run_maybe_throttled_call(
        ctx,
        partial(
            client.delete_rest_api,
            restApiId=ctx.instance.runtime_properties['id'],
            )
        )

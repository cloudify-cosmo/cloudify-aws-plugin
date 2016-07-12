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

from cloudify.exceptions import NonRecoverableError
from cloudify.decorators import operation
from .resource import get_parents


uri_template = (
    "arn:aws:apigateway:{region}:lambda:path/"
    "{api_version}/functions/{lambda_arn}/invocations")


def generate_lambda_uri(ctx, client, lambda_arn):
    return uri_template.format(
        region=client.meta.region_name,
        api_version=client.meta.service_model.api_version,
        lambda_arn=lambda_arn,
        )


@operation
def creation_validation(ctx):
    if 'cloudify.aws.relationships.method_in_resource' not in [
            rel.type for rel in ctx.node.relationships]:
        raise NonRecoverableError(
                "An API Method must be related to either an ApiResource or "
                "a RestApi (root resource) via "
                "'cloudify.aws.relationships.method_in_resource'")


@operation
def create(ctx):
    props = ctx.node.properties
    client = connection(props['aws_config']).client('apigateway')

    parent, api = get_parents(ctx.instance)

    client.put_method(
        restApiId=api.runtime_properties['id'],
        resourceId=parent.runtime_properties['resource_id'],
        httpMethod=props['http_method'],
        authorizationType=props['auth_type'],
        )


@operation
def delete(ctx):
    props = ctx.node.properties
    client = connection(props['aws_config']).client('apigateway')

    parent, api = get_parents(ctx.instance)

    client.delete_method(
        restApiId=api.runtime_properties['id'],
        resourceId=parent.runtime_properties['resource_id'],
        httpMethod=props['http_method'],
        )


@operation
def connect_lambda(ctx):
    sprops = ctx.source.node.properties
    client = connection(sprops['aws_config']).client('apigateway')

    parent, api = get_parents(ctx.source.instance)

    lambda_uri = generate_lambda_uri(
        ctx, client,
        ctx.target.instance.runtime_properties['arn'],
        )

    client.put_integration(
        restApiId=api.runtime_properties['id'],
        resourceId=parent.runtime_properties['resource_id'],
        type='AWS',
        httpMethod=sprops['http_method'],
        integrationHttpMethod=sprops['http_method'],
        uri=lambda_uri,
        )


@operation
def disconnect_lambda(ctx):
    sprops = ctx.source.properties
    client = connection(sprops['aws_config']).client('apigateway')

    parent, api = get_parents(ctx.source.instance)

    client.delete_integration(
        restApiId=api.runtime_properties['id'],
        resourceId=parent['resource_id'],
        httpMethod=sprops['http_method'],
        )

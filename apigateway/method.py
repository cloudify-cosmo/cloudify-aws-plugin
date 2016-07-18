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
from .resource import get_parents


lambda_uri_template = (
    "arn:aws:apigateway:{region}:lambda:path/"
    "{api_version}/functions/{lambda_arn}/invocations")
api_uri_template = (
    "arn:aws:execute-api:{region}:{account_id}:{api_id}/*/"
    "{http_method}{resource}"
    )


def generate_lambda_uri(ctx, client, lambda_arn):
    return lambda_uri_template.format(
        region=client.meta.region_name,
        api_version=client.meta.service_model.api_version,
        lambda_arn=lambda_arn,
        )


def generate_api_uri(ctx, client):
    account_id = ctx.target.instance.runtime_properties[
            'arn'].split(':')[4]
    # Only the account id field is all-digits
    assert int(account_id)

    parent, api = get_parents(ctx.source.instance)

    resource_path = client.get_resource(
        restApiId=api.runtime_properties['id'],
        resourceId=parent.runtime_properties['resource_id'],
        )['path']

    uri = api_uri_template.format(
        region=client.meta.region_name,
        account_id=account_id,
        http_method=ctx.source.node.properties['http_method'],
        resource=resource_path,
        api_id=api.runtime_properties['id'],
        )

    ctx.logger.info("api_uri: {}".format(uri))
    return uri


@operation
def creation_validation(ctx):
    if len(get_relationships(
            ctx,
            filter_relationships='cloudify.aws.relationships.'
            'method_in_resource')) != 1:
        raise NonRecoverableError(
                "An API Method must be related to either an ApiResource or "
                "a RestApi (root resource) via "
                "'cloudify.aws.relationships.method_in_resource'")


@b3operation
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


@b3operation
def delete(ctx):
    props = ctx.node.properties
    client = connection(props['aws_config']).client('apigateway')

    parent, api = get_parents(ctx.instance)

    client.delete_method(
        restApiId=api.runtime_properties['id'],
        resourceId=parent.runtime_properties['resource_id'],
        httpMethod=props['http_method'],
        )


def get_connected_lambda(source, target):
    props = source.instance.runtime_properties
    linked = props.setdefault(
        'linked_lambdas', {})
    # TODO: fix this in cloudify.manager.DirtyTrackingDict instead: setdefault
    props._set_changed()
    return linked.setdefault(target.node.name, {})


@b3operation
def connect_lambda(ctx):
    sprops = ctx.source.node.properties
    sclient = connection(sprops['aws_config']).client('apigateway')
    tclient = connection(sprops['aws_config']).client('lambda')

    parent, api = get_parents(ctx.source.instance)

    lambda_uri = generate_lambda_uri(
        ctx, tclient,
        ctx.target.instance.runtime_properties['arn'],
        )

    sclient.put_integration(
        restApiId=api.runtime_properties['id'],
        resourceId=parent.runtime_properties['resource_id'],
        type='AWS',
        httpMethod=sprops['http_method'],
        integrationHttpMethod="POST",
        uri=lambda_uri,
        )

    runtime_props = get_connected_lambda(ctx.source, ctx.target)

    sclient.put_integration_response(
        restApiId=api.runtime_properties['id'],
        resourceId=parent.runtime_properties['resource_id'],
        httpMethod=sprops['http_method'],
        statusCode="200",
        selectionPattern=".*",
        )

    sclient.put_method_response(
        restApiId=api.runtime_properties['id'],
        resourceId=parent.runtime_properties['resource_id'],
        httpMethod=sprops['http_method'],
        statusCode="200",
        )

    sclient.create_deployment(
        restApiId=api.runtime_properties['id'],
        stageName='prod',
        )

    # Authorize the endpoint to call the lambda function
    function_name = ctx.target.instance.runtime_properties['name']
    api_uri = generate_api_uri(ctx, sclient)

    runtime_props['statement_id'] = '{}-{}'.format(
        ctx.source.node.name, ctx.target.node.name)

    tclient.add_permission(
        FunctionName=function_name,
        StatementId=runtime_props['statement_id'],
        Action='lambda:InvokeFunction',
        Principal='apigateway.amazonaws.com',
        SourceArn=api_uri,
        )


@b3operation
def disconnect_lambda(ctx):
    sprops = ctx.source.node.properties
    sclient = connection(sprops['aws_config']).client('apigateway')
    tclient = connection(sprops['aws_config']).client('lambda')

    parent, api = get_parents(ctx.source.instance)

    tclient.remove_permission(
        FunctionName=ctx.target.instance.runtime_properties['name'],
        StatementId=get_connected_lambda(
            ctx.source,
            ctx.target)['statement_id'],
        )

    sclient.delete_integration(
        restApiId=api.runtime_properties['id'],
        resourceId=parent.runtime_properties['resource_id'],
        httpMethod=sprops['http_method'],
        )

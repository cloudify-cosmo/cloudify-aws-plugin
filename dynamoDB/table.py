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

from time import sleep

from cloudify.exceptions import NonRecoverableError
from cloudify.decorators import operation
from core.boto3_connection import connection


def _table_name(ctx):
    """Construct the name to use in AWS"""
    return '{}-{}'.format(ctx.deployment.id, ctx.instance.id)


@operation
def create(ctx):
    props = ctx.node.properties
    client = connection(props['aws_config']).client('dynamodb')

    table_name = _table_name(ctx)

    import pdb ; pdb.set_trace()

    client.create_table(
        TableName=table_name,
        AttributeDefinitions=[
            {'AttributeName': n,
             'AttributeType': t}
            for n, t
            in props['attribute_definitions']
            ],
        KeySchema=[
            {'AttributeName': n,
             'KeyType': t}
            for n, t
            in props['key_schema']
            ],
        ProvisionedThroughput={
            'ReadCapacityUnits': props['read_capacity'],
            'WriteCapacityUnits': props['write_capacity'],
            },
        StreamSpecification={
            'StreamEnabled': True,
            'StreamViewType': 'NEW_IMAGE',
            },
        )

    while True:
        response = client.describe_table(TableName=table_name)
        status = response['Table']['TableStatus']
        if status == 'ACTIVE':
            ctx.instance.runtime_properties['name'] = table_name
            ctx.instance.runtime_properties[
                'arn'] = response['Table']['TableArn']
            return response
        elif status in ['UPDATING', 'DELETING']:
            raise NonRecoverableError('WHAT IS HAPPENING TO ME')
        sleep(3)


@operation
def delete(ctx):
    props = ctx.node.properties
    client = connection(props['aws_config']).client('dynamodb')

    client.delete_table(
            TableName=ctx.instance.runtime_properties['name'],
            )

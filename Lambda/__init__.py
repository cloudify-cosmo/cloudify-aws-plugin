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

import os
import shutil
import subprocess
import tempfile
import zipfile
from contextlib import contextmanager

from botocore.exceptions import ClientError

from cloudify.exceptions import NonRecoverableError
from cloudify.decorators import operation
from core.boto3_connection import connection


@contextmanager
def tmp_tmp_dir():
    try:
        tmpdir = tempfile.mkdtemp(prefix='cloudify_aws_zip_')
        yield tmpdir
    finally:
        shutil.rmtree(tmpdir)


def zip_dir(path, zip):
    for root, _, files in os.walk(path):
        for file in files:
            zip.write(
                os.path.join(root, file),
                # Keep the bit of the path after `path` or the zip ends up flat
                os.path.normpath(os.path.join(root, file).replace(path, '')),
                )


def zip_lambda(ctx, path, runtime):
    """
    Zip up a software package as a AWS Lambda
    """
    with tmp_tmp_dir() as tmp:
        zipdir = os.path.join(tmp, 'zipdir')
        os.mkdir(zipdir)

        if 'python' in runtime:
            try:
                ctx.download_resource(
                    os.path.join('resources', path),
                    os.path.join(zipdir, path),
                    )
            except IOError as e:
                # TODO: What's the exception for resources on a manager?
                if e.errno != 2:
                    raise
                # It's not a resource file, must be a Python package
                subprocess.check_call([
                    'pip', 'install',
                    '--target', zipdir,
                    path,
                    ],
                    stderr=subprocess.STDOUT)
                # TODO: possibly strip out .py files and leave just .pyc?

            with zipfile.ZipFile(
                    os.path.join(tmp, 'lambda.zip'), 'w') as zip:
                zip_dir(zipdir, zip)
            return open(zip.filename, 'rb').read()

    raise NotImplementedError(
        "zip procedure for {} is not implemented".format(runtime))


@operation
def create(ctx):
    props = ctx.node.properties
    client = connection(props['aws_config']).client('lambda')

    lambda_name = '{}-{}'.format(ctx.deployment.id, ctx.instance.id)

    zipfile = zip_lambda(ctx, props['code_path'], props['runtime'])
    function = client.create_function(
        FunctionName=lambda_name,
        Runtime=props['runtime'],
        Handler=props['handler'],
        Code={'ZipFile': zipfile},
        Role=props['role'],
        )

    ctx.instance.runtime_properties.update({
        'name': lambda_name,
        'arn': function['FunctionArn'],
        })


@operation
def delete(ctx):
    props = ctx.node.properties
    client = connection(props['aws_config']).client('lambda')
    client.delete_function(
        FunctionName=ctx.instance.runtime_properties['name'],
        )


@operation
def connect_dynamodb_stream(ctx):
    lclient = connection(ctx.source.node.properties['aws_config']).client(
            'lambda')
    dclient = connection(ctx.target.node.properties['aws_config']).client(
            'dynamodb')

    stream_arn = dclient.describe_table(
            TableName=ctx.target.instance.runtime_properties['name']
            )['Table']['LatestStreamArn']
    try:
        mapping = lclient.create_event_source_mapping(
                FunctionName=ctx.source.instance.runtime_properties['name'],
                EventSourceArn=stream_arn,
                StartingPosition='TRIM_HORIZON',
                )
    except ClientError as e:
        if e.response['ResponseMetadata']['HTTPStatusCode']:
            raise NonRecoverableError(e)
        raise

    mappings = ctx.source.instance.runtime_properties.setdefault(
            'dynamodb_stream_mappings', {})
    mappings[ctx.target.instance.id] = mapping['UUID']
    # TODO: fix this in cloudify.manager.DirtyTrackingDict instead: setdefault
    ctx.source.instance.runtime_properties._set_changed()


@operation
def disconnect_dynamodb_stream(ctx):
    lclient = connection(ctx.source.node.properties['aws_config']).client(
            'lambda')
    try:
        lclient.delete_event_source_mapping(
                UUID=ctx.source.instance.runtime_properties[
                    'dynamodb_stream_mappings'][ctx.target.instance.id])
    except ClientError as e:
        if e.response['ResponseMetadata']['HTTPStatusCode']:
            raise NonRecoverableError(e)
        raise

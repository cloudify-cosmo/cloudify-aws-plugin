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
import tempfile
import zipfile
from contextlib import contextmanager

import boto3

from cloudify.decorators import operation


def connection(aws_conf):
    return boto3.Session(
        aws_access_key_id=aws_conf['aws_access_key_id'],
        aws_secret_access_key=aws_conf['aws_secret_access_key'],
        region_name=aws_conf['ec2_region_name'],
        ).client('lambda')


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
                file,
                )


def zip_lambda(ctx, path, runtime):
    """
    Zip up a software package as a AWS Lambda
    """
    # TODO: support grabbing a package from pip/url
    # TODO: support collecting dependencies for large modules
    with tmp_tmp_dir() as tmp:
        zipdir = os.path.join(tmp, 'zipdir')
        os.mkdir(zipdir)
        import pdb ; pdb.set_trace()
        ctx.download_resource(
            os.path.join('resources', path),
            os.path.join(zipdir, path),
            )

        if 'python' in runtime:
                with zipfile.ZipFile(
                        os.path.join(tmp, 'lambda.zip'), 'w') as zip:
                    zip_dir(zipdir, zip)
                return open(zip.filename, 'rb').read()

    raise NotImplementedError(
        "zip procedure for {} is not implemented".format(runtime))


@operation
def create(ctx):
    props = ctx.node.properties
    client = connection(props['aws_config'])

    zipfile = zip_lambda(ctx, props['code_path'], props['runtime'])
    client.create_function(
        FunctionName=ctx.instance.id,
        Runtime=props['runtime'],
        Handler=props['handler'],
        Code={'ZipFile': zipfile},
        Role=props['role'],
        )


@operation
def delete(ctx):
    props = ctx.node.properties
    client = connection(props['aws_config'])
    client.delete_function(
        FunctionName=ctx.instance.id,
        )

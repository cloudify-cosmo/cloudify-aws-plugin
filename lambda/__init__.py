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

from cloudify import ctx
from cloudify.decorators import operation


def connection(aws_conf):
    return boto3.Session(
        aws_access_key_id=aws_conf['aws_access_key_id'],
        aws_secret_access_key=aws_conf['aws_secret_access_key'],
        region=aws_conf['ec2_region_name'],
        ).client('lambda')


@contextmanager
def tmp_tmp_dir():
    try:
        tmpdir = tempfile.mkdtemp(prefix='cloudify_aws_zip_')
        yield tmpdir
    finally:
        shutil.rmtree(tmpdir)


def zip_lambda(path, runtime):
    """
    Zip up a software package as a AWS Lambda
    """
    if 'python' in runtime:
        with tmp_tmp_dir() as tmp:
            with zipfile.ZipFile(os.path.join(tmp, 'lambda.zip')) as zip:
                zip.write(path)
            return open(path, 'b').read()

    raise NotImplementedError(
        "zip procedure for {} is not implemented".format(runtime))


@operation
def create(*args, **kwargs):
    props = ctx.node.properties
    ctx.logger.info(props)
    client = connection(props['aws_config'])

    zipfile = zip_lambda(props['code_path'], props['runtime'])
    client.create_function(
        FunctionName=props['function_name'],
        Runtime=props['runtime'],
        Handler=props['handler'],
        Code={'ZipFile': zipfile},
        Role=props['role'],
        )


@operation
def delete(*args, **kwargs):
    raise NotImplementedError()

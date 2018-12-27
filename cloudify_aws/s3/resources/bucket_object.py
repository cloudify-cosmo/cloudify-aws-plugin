# #######
# Copyright (c) 2018 GigaSpaces Technologies Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
#    * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    * See the License for the specific language governing permissions and
#    * limitations under the License.
"""
    S3.Object
    ~~~~~~~~~~~~~~
    AWS S3 Bucket Object interface
"""
# Standard Imports
import sys
import tempfile
import urllib

# Third Party Imports
from botocore.exceptions import ClientError
from cloudify.exceptions import (
    NonRecoverableError,
    HttpException,
)
from cloudify import ctx
from cloudify.utils import exception_to_error_cause

# Local Imports
from cloudify_aws.common import decorators, utils
from cloudify_aws.s3 import S3Base
from cloudify_aws.common.constants import EXTERNAL_RESOURCE_ID

RESOURCE_TYPE = 'S3 Bucket Object'
BUCKET = 'Bucket'
BUCKET_OBJECT_BODY = 'Body'
BUCKET_TYPE = 'cloudify.nodes.aws.s3.Bucket'

OBJECT_KEY = 'Key'
OBJECT_PATH = 'path'
OBJECT_SOURCE_TYPE = 'source_type'
OBJECT_LOCAL_SOURCE = 'local'
OBJECT_REMOTE_SOURCE = 'remote'
OBJECT_BYTES_SOURCE = 'bytes'


class S3BucketObject(S3Base):
    """
        AWS S3 Bucket Object interface
    """
    def __init__(self, ctx_node, aws_config=None,
                 resource_id=None, client=None, logger=None):
        S3Base.__init__(self, ctx_node, aws_config,
                        resource_id, client, logger)
        self.type_name = RESOURCE_TYPE
        self.resource_config = self.get_resource_config(ctx_node)
        self._bucket_name = self.resource_config[BUCKET] if \
            self.resource_config.get(BUCKET) else None

    def get_resource_config(self, node):
        return node.properties['resource_config']['kwargs'] if \
            node.properties.get('resource_config') \
            and node.properties['resource_config'].get('kwargs') else None

    @property
    def bucket_name(self):
        return self._bucket_name

    @bucket_name.setter
    def bucket_name(self, value):
        self._bucket_name = value

    @property
    def properties(self):
        """Gets the properties of an external resource"""
        resource = None
        try:
            resource = \
                self.client.head_object(
                    **{OBJECT_KEY: self.resource_id,
                       BUCKET: self.bucket_name})
        except ClientError:
            pass

        return resource

    @property
    def status(self):
        """Gets the status of an external resource"""
        if self.properties:
            return 'available'
        return None

    def create(self, params):
        """
            Create a new AWS S3 Bucket Object.
        """
        return self.make_client_call('put_object', params)

    def delete(self, params=None):
        """
            Deletes an existing AWS S3 Bucket Object.
        """
        self.logger.debug('Deleting {0} with parameters: {1}'
                          .format(self.type_name, params))
        self.client.delete_object(**params)


def _read_file_chunks(file_object, chunk_size=1024):
    while True:
        response = file_object.read(chunk_size)
        if not response:
            break
        yield response


def _download_remote_file(file_url):
    """
    Try to download the file provided by the blueprint so because
    execution directory on a manager is not the blueprint root and want to
    make sure file is accessible by manager context

    :param file_url: ``str``: file path under blueprint root,
    :return: file path which can be accessed by cloudify manager

    """
    # Make temp file to write file to
    _, file_path = tempfile.mkstemp()

    # Try to download and read file url
    target_file = urllib.urlopen(file_url)

    # Open "file_path" for write
    with open(file_path, 'w') as fh:
        for output in _read_file_chunks(target_file):
            fh.write(output)

    # Return file_path to be uploaded
    return file_path


def _download_local_file(local_path):
    """
    This is a method to download local file using context manager
    :param local_path: ``str``: local file path which is relative to
    blueprint package
    :return: path
    """
    try:
        path = ctx.download_resource(local_path)
    except HttpException as error:
        _, _, tb = sys.exc_info()
        raise NonRecoverableError(
            '{} file does not exist.'.format(local_path),
            causes=[exception_to_error_cause(error, tb)])
    return path


@decorators.aws_resource(resource_type=RESOURCE_TYPE)
def prepare(ctx, resource_config, **_):
    """Prepares an AWS S3 Bucket Object"""
    # Save the parameters
    ctx.instance.runtime_properties['resource_config'] = resource_config


@decorators.check_swift_resource
@decorators.aws_resource(S3BucketObject, RESOURCE_TYPE)
def create(ctx, iface, resource_config, **_):
    """Creates an AWS S3 Bucket Object"""

    # Create a copy of the resource config for clean manipulation.
    params = \
        dict() if not resource_config else resource_config.copy()

    # Get the bucket object key from params
    object_key = params.get(OBJECT_KEY)
    if not object_key:
        raise NonRecoverableError('{} param is required'.format(OBJECT_KEY))

    utils.update_resource_id(ctx.instance, object_key)
    source_type = ctx.node.properties.get(OBJECT_SOURCE_TYPE)

    cloudify_path = None
    object_body = None

    # If "source_type" is either local or remote then we need to download
    # the file from remote or local directory and then parse the data as
    # bytes and prepared it to be sent on the "Body" param for "put_object"
    # method
    if source_type in [OBJECT_LOCAL_SOURCE, OBJECT_REMOTE_SOURCE]:
        path = ctx.node.properties.get(OBJECT_PATH)
        if not path:
            raise NonRecoverableError(
                'path param must be provided when '
                'source_type is selected as remote or local')

        if source_type == OBJECT_LOCAL_SOURCE:
            cloudify_path = _download_local_file(path)

        elif source_type == OBJECT_REMOTE_SOURCE:
            cloudify_path = _download_remote_file(path)

        try:
            object_body = open(cloudify_path, 'rb')
        except IOError as error:
            _, _, tb = sys.exc_info()
            raise NonRecoverableError(
                'Failed to open file {0},'
                ' with error message {1}'
                ''.format(path, error.strerror,
                          causes=[exception_to_error_cause(error, tb)]))

        # Set the updated path url so that it can
        # be uploaded to the AWS S3 bucket
        params[BUCKET_OBJECT_BODY] = object_body

    # If the "source_type" is "bytes" then the body should provided from the
    #  blueprint and follow the boto3 API documents
    elif source_type == OBJECT_BYTES_SOURCE:
        if not params.get(BUCKET_OBJECT_BODY):
            raise NonRecoverableError('Body param must be provided when '
                                      'source_type is selected as bytes')

    # Get the bucket name from either params or a relationship.
    bucket_name = params.get(BUCKET)
    if not bucket_name:
        targ = utils.find_rel_by_node_type(
            ctx.instance,
            BUCKET_TYPE
        )
        bucket_name = \
            targ.target.instance.runtime_properties.get(
                EXTERNAL_RESOURCE_ID
            )
        params[BUCKET] = bucket_name

    iface.bucket_name = bucket_name
    ctx.instance.runtime_properties[BUCKET] = bucket_name

    # Actually create the resource
    iface.create(params)


@decorators.check_swift_resource
@decorators.aws_resource(S3BucketObject, RESOURCE_TYPE,
                         ignore_properties=True)
def delete(ctx, iface, resource_config, **_):
    """Deletes an AWS S3 Bucket Object"""

    # Create a copy of the resource config for clean manipulation.
    params = \
        dict() if not resource_config else resource_config.copy()

    # Add the required BUCKET parameter.
    bucket_name = params.get(BUCKET)
    if not bucket_name:
        bucket_name = ctx.instance.runtime_properties.get(BUCKET)
        params.update({BUCKET: bucket_name})

    # Add the required object key parameter
    object_key = params.get(OBJECT_KEY)
    if not object_key:
        params.update({OBJECT_KEY: iface.resource_id})

    iface.bucket_name = bucket_name

    # Actually delete the resource
    iface.delete(params)

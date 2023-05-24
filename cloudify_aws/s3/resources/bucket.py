# Copyright (c) 2018 Cloudify Platform Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
    S3.Bucket
    ~~~~~~~~~~~~~~
    AWS S3 Bucket interface
"""
# Cloudify
from cloudify_aws.s3 import S3Base
from cloudify_aws.common import decorators
from cloudify.exceptions import NonRecoverableError

# Boto
from botocore.exceptions import ClientError, ParamValidationError

RESOURCE_TYPE = 'S3 Bucket'
RESOURCE_NAME = 'Bucket'
LOCATION = 'Location'


class S3Bucket(S3Base):
    """
        AWS S3 Bucket interface
    """
    def __init__(self, ctx_node, aws_config=None, resource_id=None,
                 client=None, logger=None):
        S3Base.__init__(self, ctx_node, aws_config,
                        resource_id, client, logger)
        self.type_name = RESOURCE_TYPE

    @property
    def properties(self):
        """Gets the properties of an external resource"""
        try:
            resources = self.client.list_buckets()
        except (ParamValidationError, ClientError):
            pass
        else:
            for resource in resources:
                if resource.get(RESOURCE_NAME) is self.resource_id:
                    return resource
            return None

    @property
    def status(self):
        """Gets the status of an external resource"""
        props = self.properties
        if not props:
            return None
        return props['Status']

    def create(self, params):
        """
            Create a new AWS S3 Bucket.
        """
        return self.make_client_call('create_bucket', params)

    def delete(self, params=None):
        """
            Deletes an existing AWS S3 Bucket.
        """
        self.logger.debug('Deleting %s with parameters: %s'
                          % (self.type_name, params))
        self.client.delete_bucket(**params)

    def put_public_access_block(self, params):
        """
            put PublicAccessBlock configuration.
        """
        self.client.put_public_access_block(
            Bucket=params['Bucket'],
            PublicAccessBlockConfiguration={
                'BlockPublicAcls': True,
                'IgnorePublicAcls': True,
                'BlockPublicPolicy': False,
                'RestrictPublicBuckets': False
            }
        )

    def delete_objects(self, bucket):
        list_objects = self.client.list_objects(Bucket=bucket)
        for object in list_objects.get('Contents', []):
            key = object.get('Key')
            if key:
                self.logger.debug(
                    'Deleting object {0} from bucket {1}.'
                    .format(key, bucket))
                delete_object = \
                    self.client.delete_object(
                        Bucket=bucket, Key=key)
                self.logger.debug(
                    'Response {0}'.format(delete_object))


@decorators.aws_resource(S3Bucket, RESOURCE_TYPE)
def prepare(ctx, resource_config, **_):
    """Prepares an AWS S3 Bucket"""
    # Save the parameters
    ctx.instance.runtime_properties['resource_config'] = resource_config


@decorators.check_swift_resource
@decorators.aws_resource(S3Bucket, RESOURCE_TYPE)
@decorators.aws_params(RESOURCE_NAME)
def create(ctx, iface, resource_config, params, **_):
    """Creates an AWS S3 Bucket"""

    if 'CreateBucketConfiguration' in params:
        if params['CreateBucketConfiguration'].get(
                'LocationConstraint') == 'us-east-1':
            del params['CreateBucketConfiguration']['LocationConstraint']
        # to avoid malformed XML because of empty dict
        if not params['CreateBucketConfiguration']:
            del params['CreateBucketConfiguration']

    # Actually create the resource
    try:
        bucket = iface.create(params)
    except NonRecoverableError as e:
        acl = params.pop('ACL', '')
        if "InvalidBucketAclWithObjectOwnership" not in str(e) \
                and "Bucket cannot have ACLs" not in str(e) \
                    and 'public-read' not in acl:
            raise e
        ctx.logger.error('Deprecation warning, the AWS API has changed \
            and ACL-public is no longer valid.')
        bucket = iface.create(params)

    iface.put_public_access_block(params)
    ctx.instance.runtime_properties[LOCATION] = bucket.get(LOCATION)


@decorators.check_swift_resource
@decorators.aws_resource(S3Bucket, RESOURCE_TYPE, ignore_properties=True)
def delete(ctx, iface, resource_config, **_):
    """Deletes an AWS S3 Bucket"""
    bucket = resource_config.get(RESOURCE_NAME)
    # Add the required RESOURCE_NAME parameter.
    if not bucket:
        bucket = iface.resource_id
        resource_config.update({RESOURCE_NAME: bucket})

    # Actually delete the resource
    iface.delete_objects(bucket)
    iface.delete(resource_config)

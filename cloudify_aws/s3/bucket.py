########
# Copyright (c) 2015 GigaSpaces Technologies Ltd. All rights reserved
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

# Stdlib imports
import string

# Third party imports
from botocore.exceptions import ClientError

# Cloudify imports
from cloudify import ctx
from cloudify.decorators import operation
from cloudify.exceptions import NonRecoverableError

# This package imports
from cloudify_aws import constants, utils
from cloudify_aws.base import AwsBaseNode
from cloudify_aws.connection import EC2ConnectionClient


@operation
def create(args=None, **_):
    return Bucket().created(args)


@operation
def configure(args=None, **_):
    return Bucket().configure(args)


@operation
def delete(args=None, **_):
    return Bucket().deleted(args)


class Bucket(AwsBaseNode):
    def __init__(self, client=None):
        client = client or EC2ConnectionClient().client3('s3')
        super(Bucket, self).__init__(
            constants.S3_BUCKET['AWS_RESOURCE_TYPE'],
            constants.S3_BUCKET['REQUIRED_PROPERTIES'],
            client=client,
            resource_id_key=constants.S3_BUCKET['RESOURCE_ID_KEY'],
        )
        self.not_found_error = constants.S3_BUCKET['NOT_FOUND_ERROR']
        self.get_all_handler = {
            'function': self.client.list_buckets,
            'argument': 'Bucket',
            'results_key': 'Buckets',
            'id_key': 'Name',
        }
        self.resource_id = ctx.node.properties['name']
        if self.is_external_resource:
            ctx.instance.runtime_properties[constants.EXTERNAL_RESOURCE_ID] = (
                ctx.node.properties['name']
            )

    def _generate_creation_args(self):
        create_args = dict(
            Bucket=ctx.node.properties['name'],
            ACL=ctx.node.properties['permissions'],
        )
        return create_args

    def _generate_website_args(self):
        index = ctx.node.properties['website_index_page']
        error = ctx.node.properties['website_error_page']
        website_args = dict(
            Bucket=ctx.node.properties['name'],
            WebsiteConfiguration={
                'ErrorDocument': {
                    'Key': error,
                },
                'IndexDocument': {
                    'Suffix': index,
                },
            },
        )
        return website_args

    def create(self, args=None):
        self.validate_bucket_name(ctx.node.properties['name'])

        create_args = utils.update_args(self._generate_creation_args(),
                                        args)

        self.execute(
            self.client.create_bucket,
            create_args,
        )
        ctx.instance.runtime_properties[constants.EXTERNAL_RESOURCE_ID] = (
            ctx.node.properties['name']
        )
        return True

    def configure(self, args=None):
        index = ctx.node.properties['website_index_page']
        error = ctx.node.properties['website_error_page']
        if (index, error) == ('', ''):
            # Neither the index nor the error page were defined, this bucket is
            # not intended to be a website
            pass
        elif '' in (index, error):
            raise NonRecoverableError(
                'For the bucket to be configured as a website, both '
                'website_index_page and website_error_page must be set.'
            )
        else:
            if '/' in index:
                raise NonRecoverableError(
                    'S3 bucket website default page must not contain a /'
                )
            website_args = utils.update_args(self._generate_website_args(),
                                             args)
            self.execute(
                self.client.put_bucket_website,
                website_args,
            )

        ctx.instance.runtime_properties['url'] = self._get_bucket_url()

        return True

    def validate_bucket_name(self, bucket_name):
        # From docs.aws.amazon.com/AmazonS3/latest/dev/BucketRestrictions.html
        invalid_bucket_message = (
            'Bucket names must be between 3 and 63 characters in length, '
            'inclusive. '
            'Bucket names containing dots will be rejected as these will '
            'render virtual hosting of these buckets unusable with SSL. '
            'Bucket names can contain lower case letters, numbers, and '
            'hyphens. '
            'Bucket names must start and end with a lower case letter or '
            'number. '
            'Bucket {name} did not meet these requirements.'
        )

        valid_start_and_end = string.lowercase + string.digits
        valid_characters = string.lowercase + string.digits + '-'

        if (
            3 <= len(bucket_name) <= 63 and
            all(char in valid_characters for char in bucket_name) and
            bucket_name[0] in valid_start_and_end and
            bucket_name[-1] in valid_start_and_end
        ):
            return True
        else:
            raise NonRecoverableError(
                invalid_bucket_message.format(name=bucket_name),
            )

    def _get_bucket_url(self):
        ctx.logger.debug('Getting bucket URL')

        bucket_name = ctx.node.properties['name']

        bucket_region = self.execute(
            self.client.head_bucket,
            {'Bucket': bucket_name},
        )['ResponseMetadata']['HTTPHeaders']['x-amz-bucket-region']

        try:
            # Cannot use execute as the error simply indicates this is not
            # a web bucket.
            self.client.get_bucket_website(Bucket=bucket_name)
            web_bucket = True
        except ClientError as err:
            if 'NoSuchWebsiteConfiguration' in str(err):
                web_bucket = False
            else:
                raise

        if web_bucket:
            url = 'http://{bucket}.s3-website-{region}.amazonaws.com/'
        else:
            url = 'https://s3.amazonaws.com/{bucket}/'

        return url.format(
            bucket=bucket_name,
            region=bucket_region,
        )

    def _generate_deletion_args(self):
        return dict(
            Bucket=ctx.node.properties['name'],
        )

    def delete(self, args=None):
        delete_args = utils.update_args(self._generate_deletion_args(),
                                        args)

        self.execute(
            self.client.delete_bucket,
            delete_args,
        )
        return True

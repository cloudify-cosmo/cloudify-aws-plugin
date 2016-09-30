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

# Third party imports

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
    return Object().created(args)


@operation
def delete(args=None, **_):
    return Object().deleted(args)


class Object(AwsBaseNode):
    def __init__(self, client=None):
        client = client or EC2ConnectionClient().client3('s3')

        ctx.instance.runtime_properties[constants.EXTERNAL_RESOURCE_ID] = (
            '{bucket}:{key}'  # Can only be populated after client exists
        )
        super(Object, self).__init__(
            constants.S3_OBJECT['AWS_RESOURCE_TYPE'],
            constants.S3_OBJECT['REQUIRED_PROPERTIES'],
            client=client,
        )

        bucket_name, _ = self._get_bucket_details()

        ctx.instance.runtime_properties[constants.EXTERNAL_RESOURCE_ID] = (
            '{bucket}:{key}'.format(
                bucket=bucket_name,
                key=ctx.node.properties['name'],
            )
        )

        self.not_found_error = constants.S3_OBJECT['NOT_FOUND_ERROR']
        self.get_all_handler = {
            'function': self.client.list_objects,
            'argument': 'Bucket',
            'results_key': 'Contents',
            'id_key': 'Key',
        }

    def _get_bucket_details(self):
        relationships = ctx.instance.relationships

        if len(relationships) == 0:
            raise NonRecoverableError(
                'S3 objects must be contained in S3 buckets using a '
                '{rel} relationship.'.format(
                    rel=constants.OBJECT_BUCKET_RELATIONSHIP,
                )
            )

        bucket_name = None
        target = constants.OBJECT_BUCKET_RELATIONSHIP
        for relationship in relationships:
            if relationship.type == target:
                bucket_name = relationship.target.node.properties['name']

        if bucket_name is None:
            raise NonRecoverableError(
                'Could not get containing bucket name from related node.'
            )

        # If we got here, we should be dealing with a real bucket, so we'll
        # just retrieve the permissions
        bucket_permissions = self.execute(
            self.client.get_bucket_acl,
            {'Bucket': bucket_name},
        )
        bucket_permissions.pop('ResponseMetadata')

        return bucket_name, bucket_permissions

    def _generate_creation_args(self):
        bucket_name, bucket_permissions = self._get_bucket_details()

        object_acl = ctx.node.properties.get('permissions', bucket_permissions)

        contents = ctx.node.properties.get('contents')
        filename = ctx.node.properties.get('filename')

        if contents and filename:
            raise NonRecoverableError(
                'Only one of contents or filename must be specified. '
                'Both have been specified.'
            )
        elif not contents and not filename:
            raise NonRecoverableError(
                'One of contents or filename must be specified. '
                'Neither has been specified.'
            )

        if filename:
            # It's a file, get a file handle for it
            contents = ctx.download_resource(ctx.node.properties['filename'])
            contents = open(contents)
        else:
            # It's a string, provide it
            contents = ctx.node.properties['contents']

        create_key_args = {
            'Body': contents,
            'Bucket': bucket_name,
            'Key': ctx.node.properties['name'],
            'ContentType': ctx.node.properties['content_type'],
        }
        if not isinstance(object_acl, dict):
            create_key_args['ACL'] = object_acl

        return create_key_args

    def _generate_put_acl_args(self):
        bucket_name, bucket_permissions = self._get_bucket_details()

        object_acl = ctx.node.properties.get('permissions', bucket_permissions)

        return dict(
            Bucket=bucket_name,
            Key=ctx.node.properties['name'],
            AccessControlPolicy=object_acl,
        )

    def create(self, args=None):
        create_key_args = utils.update_args(self._generate_creation_args(),
                                            args)

        self.execute(
            self.client.put_object,
            create_key_args,
        )

        if ctx.node.properties.get('filename'):
            try:
                create_key_args['Body'].close()
            except AttributeError:
                # If someone overrides the Body key when we're using a file,
                # we'll just have to let it close eventually itself
                pass

        bucket_name, bucket_permissions = self._get_bucket_details()
        object_acl = ctx.node.properties.get('permissions', bucket_permissions)
        if isinstance(object_acl, dict):
            acl_args = utils.update_args(self._generate_put_acl_args(),
                                         args)

            self.execute(
                self.client.put_object_acl,
                acl_args,
            )
        return True

    def _generate_delete_args(self):
        bucket_name, _ = self._get_bucket_details()

        return dict(
            Bucket=bucket_name,
            Key=ctx.node.properties['name'],
        )

    def delete(self, args=None):
        delete_args = utils.update_args(self._generate_delete_args(),
                                        args)

        self.execute(
            self.client.delete_object,
            delete_args,
        )
        return True

    def get_resource(self):
        bucket_name, _ = self._get_bucket_details()

        keys = self.execute(
            self.client.list_objects,
            {'Bucket': bucket_name},
        )

        keys = keys.get('Contents', [])
        for key in keys:
            if key['Key'] == ctx.node.properties['name']:
                return key

        # If we get here, no key was found
        return None

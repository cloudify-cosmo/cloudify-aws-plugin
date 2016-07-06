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
import testtools
from mock import patch, Mock
from botocore.exceptions import ClientError

# Cloudify imports
from cloudify.exceptions import NonRecoverableError

# This package imports
from cloudify_aws.s3 import object
from cloudify_aws import constants


class TestObject(testtools.TestCase):

    def setUp(self):
        super(TestObject, self).setUp()

    def make_node_context(self,
                          ctx,
                          name,
                          contents='',
                          filename='',
                          load_contents_from_file=True,
                          content_type='application/octet-stream',
                          permissions=None,
                          runtime_properties=None):
        ctx.node.properties = {
            'name': name,
            'contents': contents,
            'filename': filename,
            'content_type': content_type,
            'use_external_resource': False,
        }
        if permissions is not None:
            ctx.node.properties['permissions'] = permissions

        if runtime_properties is None:
            runtime_properties = {}
        ctx.instance.runtime_properties = runtime_properties

        ctx.type = 'node-instance'

    def configure_mock_connection(self,
                                  mock_conn):
        mock_client = Mock()

        mock_conn.return_value.client3.return_value = mock_client

        return mock_client

    def make_bucket_relationship(self, bucket_name):
        relationship = Mock()
        relationship.type = constants.OBJECT_BUCKET_RELATIONSHIP
        relationship.target.node.properties = {
            'name': bucket_name,
        }
        return relationship

    @patch('cloudify_aws.s3.object.EC2ConnectionClient')
    @patch('cloudify_aws.s3.object.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_init_fails_with_no_relationships(self,
                                              mock_ctx,
                                              mock_ctx2,
                                              mock_ctx3,
                                              mock_conn):
        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            self.make_node_context(context, 'otherbucket')
            context.instance = mock_ctx.instance
            context.instance.relationships = []

        self.assertRaises(
            NonRecoverableError,
            object.Object,
        )

    @patch('cloudify_aws.s3.object.EC2ConnectionClient')
    @patch('cloudify_aws.s3.object.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_init_fails_wrong_relationship(self,
                                           mock_ctx,
                                           mock_ctx2,
                                           mock_ctx3,
                                           mock_conn):
        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            self.make_node_context(context, 'somebucket')
            context.instance = mock_ctx.instance
            relationship = Mock()
            relationship.type = 'notright'
            context.instance.relationships = [relationship]

        self.assertRaises(
            NonRecoverableError,
            object.Object,
        )

    @patch('cloudify_aws.s3.object.EC2ConnectionClient')
    @patch('cloudify_aws.s3.object.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_init_gets_details(self,
                               mock_ctx,
                               mock_ctx2,
                               mock_ctx3,
                               mock_conn):
        mock_client = self.configure_mock_connection(mock_conn)

        mock_client.get_bucket_acl.return_value = {
            'expected': 'yes',
            'ResponseMetadata': 'stuff',
        }

        bucket_name = 'testbucket'
        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            self.make_node_context(context, bucket_name)
            context.instance = mock_ctx.instance
            context.instance.relationships = [
                self.make_bucket_relationship(bucket_name=bucket_name)
            ]

        object.Object()

        mock_client.get_bucket_acl.assert_called_once_with(
            Bucket=bucket_name,
        )

    @patch('cloudify_aws.s3.object.Object._get_bucket_details')
    @patch('cloudify_aws.s3.object.EC2ConnectionClient')
    @patch('cloudify_aws.s3.object.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_create_first_object_in_bucket(self,
                                           mock_ctx,
                                           mock_ctx2,
                                           mock_ctx3,
                                           mock_conn,
                                           mock_details):
        mock_client = self.configure_mock_connection(mock_conn)

        bucket_name = 'goodbucket'
        bucket_permissions = {'bad_people': 'not_allowed'}
        mock_details.return_value = (
            bucket_name,
            bucket_permissions,
        )

        object_name = 'myobject'

        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            self.make_node_context(
                context,
                object_name,
                contents=' ',
            )
            context.instance = mock_ctx.instance

        mock_client.list_objects.return_value = {}

        object.Object().created()

    @patch('cloudify_aws.s3.object.Object._get_bucket_details')
    @patch('cloudify_aws.s3.object.EC2ConnectionClient')
    @patch('cloudify_aws.s3.object.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_create_with_permissions_preset(self,
                                            mock_ctx,
                                            mock_ctx2,
                                            mock_ctx3,
                                            mock_conn,
                                            mock_details):
        mock_client = self.configure_mock_connection(mock_conn)

        bucket_name = 'goodbucket'
        bucket_permissions = {'bad_people': 'not_allowed'}
        mock_details.return_value = (
            bucket_name,
            bucket_permissions,
        )

        object_name = 'second'
        permissions = 'public'
        contents = ' '
        content_type = 'type'

        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            self.make_node_context(
                context,
                name=object_name,
                permissions=permissions,
                content_type=content_type,
                contents=contents,
            )
            context.instance = mock_ctx.instance

        mock_client.list_objects.return_value = {}

        object.Object().created()
        mock_client.put_object.assert_called_once_with(
            Body=contents,
            Bucket=bucket_name,
            Key=object_name,
            ContentType=content_type,
            ACL=permissions,
        )

    @patch('cloudify_aws.s3.object.Object._get_bucket_details')
    @patch('cloudify_aws.s3.object.EC2ConnectionClient')
    @patch('cloudify_aws.s3.object.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_create_inherit_bucket_permissions(self,
                                               mock_ctx,
                                               mock_ctx2,
                                               mock_ctx3,
                                               mock_conn,
                                               mock_details):
        mock_client = self.configure_mock_connection(mock_conn)

        bucket_name = 'goodbucket'
        bucket_permissions = {'bad_people': 'not_allowed'}
        mock_details.return_value = (
            bucket_name,
            bucket_permissions,
        )

        object_name = 'second'
        contents = ' '
        content_type = 'type'

        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            self.make_node_context(
                context,
                name=object_name,
                content_type=content_type,
                contents=contents,
            )
            context.instance = mock_ctx.instance

        mock_client.list_objects.return_value = {}

        object.Object().created()
        mock_client.put_object.assert_called_once_with(
            Body=contents,
            Bucket=bucket_name,
            Key=object_name,
            ContentType=content_type,
        )
        mock_client.put_object_acl.assert_called_once_with(
            Bucket=bucket_name,
            Key=object_name,
            AccessControlPolicy=bucket_permissions,
        )

    @patch('__builtin__.open')
    @patch('cloudify_aws.s3.object.Object._get_bucket_details')
    @patch('cloudify_aws.s3.object.EC2ConnectionClient')
    @patch('cloudify_aws.s3.object.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_create_from_file(self,
                              mock_ctx,
                              mock_ctx2,
                              mock_ctx3,
                              mock_conn,
                              mock_details,
                              mock_open):
        mock_client = self.configure_mock_connection(mock_conn)

        bucket_name = 'goodbucket'
        bucket_permissions = {'bad_people': 'not_allowed'}
        mock_details.return_value = (
            bucket_name,
            bucket_permissions,
        )

        object_name = 'second'
        filename = 'myfile'
        content_type = 'test'

        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            self.make_node_context(
                context,
                name=object_name,
                content_type=content_type,
                filename=filename,
            )
            context.instance = mock_ctx.instance
            context.download_resource = mock_ctx.download_resource

        mock_client.list_objects.return_value = {}

        object.Object().created()
        mock_client.put_object.assert_called_once_with(
            Body=mock_open.return_value,
            Bucket=bucket_name,
            Key=object_name,
            ContentType=content_type,
        )
        mock_client.put_object_acl.assert_called_once_with(
            Bucket=bucket_name,
            Key=object_name,
            AccessControlPolicy=bucket_permissions,
        )
        # Make sure we called open with the right file
        mock_open.assert_called_once_with(
            mock_ctx.download_resource(filename)
        )
        # Make sure we closed the file
        mock_open.return_value.close.assert_called_once_with()

    @patch('__builtin__.open')
    @patch('cloudify_aws.s3.object.Object._get_bucket_details')
    @patch('cloudify_aws.s3.object.EC2ConnectionClient')
    @patch('cloudify_aws.s3.object.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_create_from_string(self,
                                mock_ctx,
                                mock_ctx2,
                                mock_ctx3,
                                mock_conn,
                                mock_details,
                                mock_open):
        mock_client = self.configure_mock_connection(mock_conn)

        bucket_name = 'goodbucket'
        bucket_permissions = {'bad_people': 'not_allowed'}
        mock_details.return_value = (
            bucket_name,
            bucket_permissions,
        )

        object_name = 'second'
        contents = 'wonderful object in s3'
        content_type = 'test'

        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            self.make_node_context(
                context,
                name=object_name,
                content_type=content_type,
                contents=contents,
            )
            context.instance = mock_ctx.instance

        mock_client.list_objects.return_value = {}

        object.Object().create()
        mock_client.put_object.assert_called_once_with(
            Body=contents,
            Bucket=bucket_name,
            Key=object_name,
            ContentType=content_type,
        )
        self.assertEqual(mock_open.call_count, 0)

    @patch('cloudify_aws.s3.object.Object._get_bucket_details')
    @patch('cloudify_aws.s3.object.EC2ConnectionClient')
    @patch('cloudify_aws.s3.object.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_delete_key(self,
                        mock_ctx,
                        mock_ctx2,
                        mock_ctx3,
                        mock_conn,
                        mock_details):
        mock_client = self.configure_mock_connection(mock_conn)
        object_name = 'test'
        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            self.make_node_context(
                context,
                name=object_name,
                runtime_properties={'created': True},
            )
            context.instance = mock_ctx.instance

        bucket_name = 'goodbucket'
        bucket_permissions = {'bad_people': 'not_allowed'}
        mock_details.return_value = (
            bucket_name,
            bucket_permissions,
        )

        object.Object().delete()

        mock_client.delete_object.assert_called_once_with(
            Bucket=bucket_name,
            Key=object_name,
        )

    @patch('cloudify_aws.s3.object.Object._get_bucket_details')
    @patch('cloudify_aws.s3.object.EC2ConnectionClient')
    @patch('cloudify_aws.s3.object.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_delete_key_client_error(self,
                                     mock_ctx,
                                     mock_ctx2,
                                     mock_ctx3,
                                     mock_conn,
                                     mock_details):
        mock_client = self.configure_mock_connection(mock_conn)
        mock_client.delete_object.side_effect = ClientError(
            {'Error': {'Message': 'ItAllWentWrong'}},
            'test_failure',
        )

        object_name = 'test'
        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            self.make_node_context(
                context,
                name=object_name,
                runtime_properties={'created': True},
            )
            context.instance = mock_ctx.instance

        bucket_name = 'goodbucket'
        bucket_permissions = {'bad_people': 'not_allowed'}
        mock_details.return_value = (
            bucket_name,
            bucket_permissions,
        )

        self.assertRaises(
            NonRecoverableError,
            object.Object().delete,
        )

        mock_client.delete_object.assert_called_once_with(
            Bucket=bucket_name,
            Key=object_name,
        )

    @patch('cloudify_aws.s3.object.Object')
    def test_create_calls_correct_method(self, mock_object):
        args = [1, 2, 3]
        expected = 'the right result'
        mock_object.return_value.created.return_value = expected

        result = object.create(args)

        self.assertEqual(result, expected)
        mock_object.return_value.created.assert_called_once_with(args)

    @patch('cloudify_aws.s3.object.Object')
    def test_delete_calls_correct_method(self, mock_object):
        args = [1, 2, 3]
        expected = 'the right result'
        mock_object.return_value.deleted.return_value = expected

        result = object.delete(args)

        self.assertEqual(result, expected)
        mock_object.return_value.deleted.assert_called_once_with(args)

    @patch('cloudify_aws.s3.object.Object._get_bucket_details')
    @patch('cloudify_aws.s3.object.EC2ConnectionClient')
    @patch('cloudify_aws.s3.object.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_get_resource(self,
                          mock_ctx,
                          mock_ctx2,
                          mock_ctx3,
                          mock_conn,
                          mock_details):
        mock_client = self.configure_mock_connection(mock_conn)

        bucket_name = 'goodbucket'
        bucket_permissions = {'bad_people': 'not_allowed'}
        mock_details.return_value = (
            bucket_name,
            bucket_permissions,
        )

        mock_client.list_objects.return_value = {
            'Contents': [
                {
                    'Key': bucket_name,
                    'correct': True,
                },
            ]
        }

        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            self.make_node_context(context, bucket_name)
            context.instance = mock_ctx.instance

        result = object.Object().get_resource()

        mock_client.list_objects.assert_called_once_with(
            Bucket=bucket_name
        )

        self.assertEqual(
            result,
            {
                'Key': bucket_name,
                'correct': True,
            },
        )

    @patch('cloudify_aws.s3.object.Object._get_bucket_details')
    @patch('cloudify_aws.s3.object.EC2ConnectionClient')
    @patch('cloudify_aws.s3.object.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_get_resource_missing(self,
                                  mock_ctx,
                                  mock_ctx2,
                                  mock_ctx3,
                                  mock_conn,
                                  mock_details):
        mock_client = self.configure_mock_connection(mock_conn)

        bucket_name = 'goodbucket'
        bucket_permissions = {'bad_people': 'not_allowed'}
        mock_details.return_value = (
            bucket_name,
            bucket_permissions,
        )

        mock_client.list_objects.return_value = {
            'Contents': [
                {
                    'Key': 'incorrect',
                },
            ]
        }

        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            self.make_node_context(context, bucket_name)
            context.instance = mock_ctx.instance

        result = object.Object().get_resource()

        mock_client.list_objects.assert_called_once_with(
            Bucket=bucket_name
        )

        self.assertIsNone(result)

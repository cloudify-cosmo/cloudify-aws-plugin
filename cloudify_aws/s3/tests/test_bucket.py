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
from cloudify_aws.s3 import bucket


class TestBucket(testtools.TestCase):

    def setUp(self):
        super(TestBucket, self).setUp()

    def make_node_context(self,
                          ctx,
                          bucket_name='mybucket',
                          use_external_resource=False,
                          permissions='public',
                          website_index_page='',
                          website_error_page='',
                          runtime_properties=None):
        ctx.node.properties = {
            'name': bucket_name,
            'use_external_resource': use_external_resource,
            'permissions': permissions,
            'website_index_page': website_index_page,
            'website_error_page': website_error_page,
        }

        if runtime_properties is None:
            runtime_properties = {}
        ctx.instance.runtime_properties = runtime_properties

        ctx.type = 'node-instance'

    def configure_mock_connection(self,
                                  mock_conn,
                                  web_bucket=True,
                                  existing_buckets=(),
                                  bucket_region='eregion'):
        mock_client = Mock()
        mock_client.head_bucket.return_value = {
            'ResponseMetadata': {
                'HTTPHeaders': {
                    'x-amz-bucket-region': bucket_region
                },
            }
        }

        mock_client.list_buckets.return_value = {
            'Buckets': [{'Name': bucket} for bucket in existing_buckets],
        }

        mock_conn.return_value.client3.return_value = mock_client

        if not web_bucket:
            mock_client.get_bucket_website.side_effect = ClientError(
                {'Error': {'Message': 'NoSuchWebsiteConfiguration'}},
                'test_non_web_bucket'
            )

        return mock_client

    @patch('cloudify_aws.s3.bucket.EC2ConnectionClient')
    @patch('cloudify_aws.s3.bucket.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_invalid_bucket_name_uppercase(self, mock_ctx, mock_ctx2,
                                           mock_ctx3, mock_conn):
        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            self.make_node_context(context)
        self.assertRaises(
            NonRecoverableError,
            bucket.Bucket().validate_bucket_name,
            'Badbucket',
        )

    @patch('cloudify_aws.s3.bucket.EC2ConnectionClient')
    @patch('cloudify_aws.s3.bucket.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_invalid_bucket_name_too_short(self, mock_ctx, mock_ctx2,
                                           mock_ctx3, mock_conn):
        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            self.make_node_context(context)
        self.assertRaises(
            NonRecoverableError,
            bucket.Bucket().validate_bucket_name,
            'aa',
        )

    @patch('cloudify_aws.s3.bucket.EC2ConnectionClient')
    @patch('cloudify_aws.s3.bucket.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_invalid_bucket_name_too_long(self, mock_ctx, mock_ctx2,
                                          mock_ctx3, mock_conn):
        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            self.make_node_context(context)
        self.assertRaises(
            NonRecoverableError,
            bucket.Bucket().validate_bucket_name,
            'a' * 64,
        )

    @patch('cloudify_aws.s3.bucket.EC2ConnectionClient')
    @patch('cloudify_aws.s3.bucket.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_invalid_bucket_name_hyphen_start(self, mock_ctx, mock_ctx2,
                                              mock_ctx3, mock_conn):
        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            self.make_node_context(context)
        self.assertRaises(
            NonRecoverableError,
            bucket.Bucket().validate_bucket_name,
            '-badbucket',
        )

    @patch('cloudify_aws.s3.bucket.EC2ConnectionClient')
    @patch('cloudify_aws.s3.bucket.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_invalid_bucket_name_hyphen_end(self, mock_ctx, mock_ctx2,
                                            mock_ctx3, mock_conn):
        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            self.make_node_context(context)
        self.assertRaises(
            NonRecoverableError,
            bucket.Bucket().validate_bucket_name,
            'badbucket-',
        )

    @patch('cloudify_aws.s3.bucket.EC2ConnectionClient')
    @patch('cloudify_aws.s3.bucket.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_invalid_bucket_name_contains_dot(self, mock_ctx, mock_ctx2,
                                              mock_ctx3, mock_conn):
        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            self.make_node_context(context)
        self.assertRaises(
            NonRecoverableError,
            bucket.Bucket().validate_bucket_name,
            'bad.bucket',
        )

    @patch('cloudify_aws.s3.bucket.EC2ConnectionClient')
    @patch('cloudify_aws.s3.bucket.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_valid_bucket_name(self, mock_ctx, mock_ctx2,
                               mock_ctx3, mock_conn):
        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            self.make_node_context(context)
        self.assertTrue(
            bucket.Bucket().validate_bucket_name('1good-bucket')
        )

    @patch('cloudify_aws.s3.bucket.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    @patch('cloudify_aws.s3.bucket.EC2ConnectionClient')
    def test_get_web_bucket_url(self, mock_conn, mock_ctx,
                                mock_ctx2, mock_ctx3):
        bucket_name = 'mybucket'

        self.configure_mock_connection(mock_conn)

        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            self.make_node_context(context, bucket_name=bucket_name)

        expected = 'http://mybucket.s3-website-eregion.amazonaws.com/'

        result = bucket.Bucket()._get_bucket_url()

        self.assertEqual(result, expected)

    @patch('cloudify_aws.s3.bucket.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    @patch('cloudify_aws.s3.bucket.EC2ConnectionClient')
    def test_get_non_web_bucket_url(self, mock_conn, mock_ctx,
                                    mock_ctx2, mock_ctx3):
        bucket_name = 'mybucket'
        self.configure_mock_connection(
            mock_conn,
            web_bucket=False,
        )

        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            self.make_node_context(context, bucket_name=bucket_name)

        expected = 'https://s3.amazonaws.com/mybucket/'

        result = bucket.Bucket()._get_bucket_url()

        self.assertEqual(result, expected)

    @patch('cloudify_aws.s3.bucket.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    @patch('cloudify_aws.s3.bucket.EC2ConnectionClient')
    def test_get_web_bucket_other_failure(self, mock_conn, mock_ctx,
                                          mock_ctx2, mock_ctx3):
        bucket_name = 'mybucket'
        mock_client = self.configure_mock_connection(
            mock_conn,
            web_bucket=False,
        )

        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            self.make_node_context(context, bucket_name=bucket_name)

        mock_client.get_bucket_website.side_effect = ClientError(
            {'Error': {'Message': 'SadThingsHappening'}},
            'test_get_web_bucket_failure'
        )

        self.assertRaises(
            ClientError,
            bucket.Bucket()._get_bucket_url,
        )

    @patch('cloudify_aws.s3.bucket.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    @patch('cloudify_aws.s3.bucket.EC2ConnectionClient')
    def test_create_bucket_existing_does_not_exist(self, mock_conn, mock_ctx,
                                                   mock_ctx2, mock_ctx3):
        bucket_name = 'not-existing'
        self.configure_mock_connection(
            mock_conn,
            web_bucket=False,
        )

        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            self.make_node_context(
                context,
                bucket_name=bucket_name,
                use_external_resource=True,
            )

        self.assertRaises(
            NonRecoverableError,
            bucket.Bucket().created,
        )

    @patch('cloudify_aws.s3.bucket.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    @patch('cloudify_aws.s3.bucket.EC2ConnectionClient')
    def test_create_bucket_bad_name(self, mock_conn, mock_ctx,
                                    mock_ctx2, mock_ctx3):
        bucket_name = 'badly.named'
        self.configure_mock_connection(
            mock_conn,
            web_bucket=False,
        )

        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            self.make_node_context(context, bucket_name=bucket_name)

        self.assertRaises(
            NonRecoverableError,
            bucket.Bucket().created,
        )

    @patch('cloudify_aws.s3.bucket.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    @patch('cloudify_aws.s3.bucket.EC2ConnectionClient')
    def test_create_bucket_not_web(self, mock_conn, mock_ctx,
                                   mock_ctx2, mock_ctx3):
        bucket_name = 'new-1'
        mock_client = self.configure_mock_connection(
            mock_conn,
            web_bucket=False,
        )

        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            self.make_node_context(
                context,
                bucket_name=bucket_name,
                permissions='thinkhappythoughts',
            )

        bucket.Bucket().created()

        mock_client.create_bucket.assert_called_once_with(
            Bucket=bucket_name,
            ACL='thinkhappythoughts',
        )

    @patch('cloudify_aws.s3.bucket.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    @patch('cloudify_aws.s3.bucket.EC2ConnectionClient')
    def test_create_bucket_client_error(self, mock_conn, mock_ctx,
                                        mock_ctx2, mock_ctx3):
        bucket_name = 'new-1'
        mock_client = self.configure_mock_connection(
            mock_conn,
            web_bucket=False,
        )

        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            self.make_node_context(context, bucket_name=bucket_name)

        mock_client.create_bucket.side_effect = ClientError(
            {'Error': {'Message': 'ItAllWentWrong'}},
            'test_failure',
        )

        self.assertRaises(
            NonRecoverableError,
            bucket.Bucket().created,
        )

    @patch('cloudify_aws.s3.bucket.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    @patch('cloudify_aws.s3.bucket.EC2ConnectionClient')
    def test_configure_bucket_not_web(self, mock_conn, mock_ctx, mock_ctx2,
                                      mock_ctx3):
        bucket_name = 'notweb.1'
        mock_client = self.configure_mock_connection(
            mock_conn,
            web_bucket=False,
        )

        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            self.make_node_context(
                context,
                bucket_name=bucket_name,
            )

        expected = 'https://s3.amazonaws.com/notweb.1/'

        bucket.Bucket().configure()

        url = mock_ctx3.instance.runtime_properties['url']

        self.assertEqual(url, expected)

        self.assertEqual(
            mock_client.put_bucket_website.call_count,
            0,
        )

    @patch('cloudify_aws.s3.bucket.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    @patch('cloudify_aws.s3.bucket.EC2ConnectionClient')
    def test_configure_bucket_web_index_but_not_error(self, mock_conn,
                                                      mock_ctx, mock_ctx2,
                                                      mock_ctx3):
        bucket_name = 'brokeweb-1'
        self.configure_mock_connection(
            mock_conn,
            web_bucket=False,
        )

        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            self.make_node_context(
                context,
                bucket_name=bucket_name,
                website_index_page='test',
            )

        self.assertRaises(
            NonRecoverableError,
            bucket.Bucket().configure,
        )

    @patch('cloudify_aws.s3.bucket.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    @patch('cloudify_aws.s3.bucket.EC2ConnectionClient')
    def test_configure_bucket_web_error_but_not_index(self, mock_conn,
                                                      mock_ctx, mock_ctx2,
                                                      mock_ctx3):
        bucket_name = 'brokeweb-2'
        self.configure_mock_connection(
            mock_conn,
            web_bucket=False,
        )

        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            self.make_node_context(
                context,
                bucket_name=bucket_name,
                website_error_page='test',
            )

        self.assertRaises(
            NonRecoverableError,
            bucket.Bucket().configure,
        )

    @patch('cloudify_aws.s3.bucket.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    @patch('cloudify_aws.s3.bucket.EC2ConnectionClient')
    def test_configure_bucket_web_invalid_index(self, mock_conn, mock_ctx,
                                                mock_ctx2, mock_ctx3):
        bucket_name = 'brokeweb-3'
        self.configure_mock_connection(
            mock_conn,
            web_bucket=False,
        )

        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            self.make_node_context(
                context,
                bucket_name=bucket_name,
                website_index_page='test/index.html',
                website_error_page='error.html',
            )

        self.assertRaises(
            NonRecoverableError,
            bucket.Bucket().configure,
        )

    @patch('cloudify_aws.s3.bucket.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    @patch('cloudify_aws.s3.bucket.EC2ConnectionClient')
    def test_configure_bucket_web(self, mock_conn, mock_ctx, mock_ctx2,
                                  mock_ctx3):
        bucket_name = 'web-1'
        index = 'index.html'
        error = 'error.html'
        mock_client = self.configure_mock_connection(
            mock_conn,
            bucket_region='krasia-nw-1',
        )

        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            self.make_node_context(
                context,
                bucket_name=bucket_name,
                permissions='thinkwebbythoughts',
                website_index_page='index.html',
                website_error_page='error.html',
            )

        expected = 'http://web-1.s3-website-krasia-nw-1.amazonaws.com/'

        bucket.Bucket().configure()

        url = mock_ctx3.instance.runtime_properties['url']

        self.assertEqual(url, expected)

        mock_client.put_bucket_website.assert_called_once_with(
            Bucket=bucket_name,
            WebsiteConfiguration={
                'ErrorDocument': {
                    'Key': error,
                },
                'IndexDocument': {
                    'Suffix': index,
                },
            },
        )

    @patch('cloudify_aws.s3.bucket.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    @patch('cloudify_aws.s3.bucket.EC2ConnectionClient')
    def test_delete_bucket_existing(self, mock_conn, mock_ctx, mock_ctx2,
                                    mock_ctx3):
        bucket_name = 'leave-existing-1'
        mock_client = self.configure_mock_connection(
            mock_conn,
            existing_buckets=[bucket_name],
        )

        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            self.make_node_context(
                context,
                bucket_name=bucket_name,
                use_external_resource=True,
            )

        bucket.Bucket().deleted()

        # We shouldn't connect to AWS at all if we are 'deleting' pre-existing
        # resources
        self.assertEqual(mock_client.call_count, 0)

    @patch('cloudify_aws.s3.bucket.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    @patch('cloudify_aws.s3.bucket.EC2ConnectionClient')
    def test_delete_bucket_successfully(self, mock_conn, mock_ctx, mock_ctx2,
                                        mock_ctx3):
        bucket_name = 'delete-1'
        mock_client = self.configure_mock_connection(
            mock_conn,
            existing_buckets=[bucket_name],
        )

        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            self.make_node_context(
                context,
                bucket_name=bucket_name,
            )

        bucket.Bucket().deleted()

        mock_client.delete_bucket.assert_called_once_with(
            Bucket=bucket_name,
        )

    @patch('cloudify_aws.s3.bucket.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    @patch('cloudify_aws.s3.bucket.EC2ConnectionClient')
    def test_delete_bucket_failure(self, mock_conn, mock_ctx,
                                   mock_ctx2, mock_ctx3):
        bucket_name = 'delete-1'
        mock_client = self.configure_mock_connection(
            mock_conn,
        )

        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            self.make_node_context(
                context,
                bucket_name=bucket_name,
            )

        mock_client.delete_bucket.side_effect = ClientError(
            {'Error': {'Message': 'ItAllWentWrong'}},
            'test_failure',
        )

        self.assertRaises(
            NonRecoverableError,
            bucket.Bucket().deleted,
        )

    @patch('cloudify_aws.s3.bucket.Bucket')
    def test_create_calls_correct_method(self, mock_bucket):
        args = [1, 2, 3]
        expected = 'the right result'
        mock_bucket.return_value.created.return_value = expected

        result = bucket.create(args)

        self.assertEqual(result, expected)
        mock_bucket.return_value.created.assert_called_once_with(args)

    @patch('cloudify_aws.s3.bucket.Bucket')
    def test_delete_calls_correct_method(self, mock_bucket):
        args = [1, 2, 3]
        expected = 'the right result'
        mock_bucket.return_value.deleted.return_value = expected

        result = bucket.delete(args)

        self.assertEqual(result, expected)
        mock_bucket.return_value.deleted.assert_called_once_with(args)

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

import unittest
from mock import patch
from cloudify.state import current_ctx
from cloudify_aws.common.tests.test_base import TestBase, CLIENT_CONFIG
from cloudify_aws.common.tests.test_base import DEFAULT_RUNTIME_PROPERTIES
from cloudify_aws.common.tests.test_base import DELETE_RESPONSE
from cloudify_aws.s3.resources.bucket import S3Bucket, RESOURCE_NAME, LOCATION
from cloudify_aws.s3.resources import bucket

# Constants
BUCKET_TYPE = 'cloudify.nodes.aws.s3.Bucket'
BUCKET_TH = ['cloudify.nodes.Root',
             'cloudify.nodes.aws.s3.BaseBucket',
             BUCKET_TYPE]

NODE_PROPERTIES = {
    'resource_id': 'CloudifyBucket',
    'use_external_resource': False,
    'resource_config': {RESOURCE_NAME: 'bucket'},
    'client_config': CLIENT_CONFIG
}

RUNTIME_PROPERTIES_AFTER_CREATE = {
    'aws_resource_id': 'bucket',
    'resource_config': {},
    LOCATION: 'location'
}


class TestS3Bucket(TestBase):

    def setUp(self):
        super(TestS3Bucket, self).setUp()
        self.bucket = S3Bucket('', resource_id=True,
                               client=True, logger=None)
        self.fake_boto, self.fake_client = self.fake_boto_client('s3')

        self.mock_patch = patch('boto3.client', self.fake_boto)
        self.mock_patch.start()

    def tearDown(self):
        self.mock_patch.stop()
        self.fake_boto = None
        self.fake_client = None
        super(TestS3Bucket, self).tearDown()

    def test_class_properties(self):
        effect = self.get_client_error_exception(name='S3 Bucket')
        self.bucket.client = self.make_client_function('list_buckets',
                                                       side_effect=effect)
        res = self.bucket.properties
        self.assertIsNone(res)

        value = [{'Bucket': 'test_name'}]
        self.bucket.client = self.make_client_function('list_buckets',
                                                       return_value=value)
        res = self.bucket.properties
        self.assertIsNone(res)

        self.bucket.resource_id = 'test_name'
        res = self.bucket.properties
        self.assertEqual(res['Bucket'], 'test_name')

    def test_class_status(self):
        value = [{'Bucket': 'test_name', 'Status': 'ok'}]
        self.bucket.client = self.make_client_function('list_buckets',
                                                       return_value=value)
        res = self.bucket.status
        self.assertIsNone(res)

        self.bucket.resource_id = 'test_name'
        res = self.bucket.status
        self.assertEqual(res, 'ok')

    def test_class_delete_objects(self):
        value = {'Contents': [{'Key': 'key_id'}]}
        self.bucket.client = self.make_client_function('list_objects',
                                                       return_value=value)
        self.bucket.client = self.make_client_function(
            'delete_object', return_value={}, client=self.bucket.client
        )
        self.bucket.resource_id = 'test_name'
        self.bucket.delete_objects('bucket_name')

    def test_class_create(self):
        value = {'Location': 'test'}
        self.bucket.client = self.make_client_function('create_bucket',
                                                       return_value=value)
        res = self.bucket.create(value)
        self.assertEqual(res, value)

    def test_class_delete(self):
        params = {}
        self.bucket.client = self.make_client_function('delete_bucket')
        self.bucket.delete(params)
        self.assertTrue(self.bucket.client.delete_bucket.called)

        params = {RESOURCE_NAME: 'bucket', LOCATION: 'location'}
        self.bucket.delete(params)
        self.assertEqual(params[LOCATION], 'location')

    def test_prepare(self):
        _ctx = self.get_mock_ctx(
            'test_prepare',
            test_properties=NODE_PROPERTIES,
            test_runtime_properties=RUNTIME_PROPERTIES_AFTER_CREATE,
            type_hierarchy=BUCKET_TH,
            type_node=BUCKET_TYPE,
        )

        current_ctx.set(_ctx)

        bucket.prepare(ctx=_ctx, resource_config=None, iface=None, params=None)

        self.assertEqual(
            _ctx.instance.runtime_properties['resource_config'],
            {'Bucket': 'bucket'})

    def test_create_raises_UnknownServiceError(self):
        self._prepare_create_raises_UnknownServiceError(
            type_hierarchy=BUCKET_TH,
            type_node=BUCKET_TYPE,
            type_name='s3',
            type_class=bucket,
        )

    def test_create(self):
        _ctx = self.get_mock_ctx(
            'test_create',
            test_properties=NODE_PROPERTIES,
            test_runtime_properties=DEFAULT_RUNTIME_PROPERTIES,
            type_hierarchy=BUCKET_TH,
            type_node=BUCKET_TYPE,
        )

        current_ctx.set(_ctx)

        self.fake_client.create_bucket = self.mock_return(
            {LOCATION: 'location'})

        bucket.create(ctx=_ctx, resource_config=None, iface=None, params=None)

        self.fake_boto.assert_called_with('s3', **CLIENT_CONFIG)

        self.fake_client.create_bucket.assert_called_with(Bucket='bucket')

        self.assertEqual(
            _ctx.instance.runtime_properties,
            RUNTIME_PROPERTIES_AFTER_CREATE
        )

    def test_delete(self):
        _ctx = self.get_mock_ctx(
            'test_delete',
            test_properties=NODE_PROPERTIES,
            test_runtime_properties=RUNTIME_PROPERTIES_AFTER_CREATE,
            type_hierarchy=BUCKET_TH,
            type_node=BUCKET_TYPE,
            ctx_operation_name='cloudify.interfaces.lifecycle.delete'
        )

        current_ctx.set(_ctx)

        self.fake_client.delete_bucket = self.mock_return(DELETE_RESPONSE)

        bucket.delete(ctx=_ctx, resource_config={}, iface=None)

        self.fake_boto.assert_called_with('s3', **CLIENT_CONFIG)

        self.fake_client.delete_bucket.assert_called_with(
            Bucket='bucket'
        )


if __name__ == '__main__':
    unittest.main()

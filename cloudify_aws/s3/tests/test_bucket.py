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
from cloudify_aws.common.tests.test_base import \
    TestBase, mock_decorator
from cloudify_aws.s3.resources.bucket import \
    S3Bucket, RESOURCE_NAME, LOCATION
from mock import patch, MagicMock
from cloudify_aws.s3.resources import bucket


class TestS3Bucket(TestBase):

    def setUp(self):
        super(TestS3Bucket, self).setUp()
        self.bucket = S3Bucket('', resource_id=True,
                               client=True, logger=None)
        self.mock_resource = patch(
            'cloudify_aws.common.decorators.aws_resource', mock_decorator
        )
        self.mock_resource.start()
        reload(bucket)

    def tearDown(self):
        self.mock_resource.stop()

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
        ctx = self.get_mock_ctx("Backet")
        bucket.prepare(ctx, 'config')
        self.assertEqual(ctx.instance.runtime_properties['resource_config'],
                         'config')

    def test_create(self):
        ctx = self.get_mock_ctx("Backet")
        config = {RESOURCE_NAME: 'bucket'}
        iface = MagicMock()
        iface.create = self.mock_return({LOCATION: 'location'})
        bucket.create(ctx=ctx, iface=iface, resource_config=config)
        self.assertEqual(ctx.instance.runtime_properties[LOCATION],
                         'location')

    def test_delete(self):
        ctx = self.get_mock_ctx("Backet")
        iface = MagicMock()
        bucket.delete(ctx=ctx, iface=iface, resource_config={})
        self.assertTrue(iface.delete.called)


if __name__ == '__main__':
    unittest.main()

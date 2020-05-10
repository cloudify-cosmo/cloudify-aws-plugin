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

# Standard imports
import unittest

# Third party imports
from mock import patch, MagicMock

# Local imports
from cloudify_aws.common._compat import reload_module
from cloudify_aws.s3.resources.lifecycle_configuration import (
    S3BucketLifecycleConfiguration, BUCKET, RULES, ID)
from cloudify_aws.common.tests.test_base import TestBase, mock_decorator
from cloudify_aws.common.constants import EXTERNAL_RESOURCE_ID
from cloudify_aws.s3.resources import lifecycle_configuration

PATCH_PREFIX = 'cloudify_aws.s3.resources.lifecycle_configuration.'


class TestS3BucketLifecycleConfiguration(TestBase):

    def setUp(self):
        super(TestS3BucketLifecycleConfiguration, self).setUp()
        self.config = S3BucketLifecycleConfiguration("ctx_node",
                                                     resource_id=True,
                                                     client=MagicMock(),
                                                     logger=None)
        mock1 = patch('cloudify_aws.common.decorators.aws_resource',
                      mock_decorator)
        mock1.start()
        reload_module(lifecycle_configuration)

    def test_class_properties(self):
        effect = self.get_client_error_exception(name='S3 Bucket')
        self.config.client = self.make_client_function(
            'get_bucket_lifecycle_configuration',
            side_effect=effect)
        res = self.config.properties
        self.assertIsNone(res)

        self.config.client = self.make_client_function(
            'get_bucket_lifecycle_configuration',
            return_value={})
        res = self.config.properties
        self.assertIsNone(res)

        value = {RULES: [{ID: 'id'}]}
        self.config.client = self.make_client_function(
            'get_bucket_lifecycle_configuration',
            return_value=value)
        res = self.config.properties
        self.assertEqual(res, 'id')

    def test_class_status(self):
        self.config.client = self.make_client_function(
            'get_bucket_lifecycle_configuration',
            return_value={})
        res = self.config.status
        self.assertIsNone(res)

        value = {RULES: [{ID: {'Status': 'ok'}}]}
        self.config.client = self.make_client_function(
            'get_bucket_lifecycle_configuration',
            return_value=value)
        res = self.config.status
        self.assertEqual(res, 'ok')

    def test_class_create(self):
        value = 'test'
        self.config.client = self.make_client_function('put_bucket_lifecycle',
                                                       return_value=value)
        res = self.config.create({})
        self.assertEqual(res, 'test')

    def test_class_delete(self):
        params = {BUCKET: 'bucket'}
        self.config.delete(params)
        self.assertTrue(self.config.client.delete_bucket_lifecycle.called)

    def test_prepare(self):
        ctx = self.get_mock_ctx("Bucket")
        lifecycle_configuration.prepare(ctx, 'config')
        self.assertEqual(ctx.instance.runtime_properties['resource_config'],
                         'config')

    def test_create(self):
        ctx = self.get_mock_ctx("Bucket")
        config = {BUCKET: 'bucket'}
        iface = MagicMock()
        lifecycle_configuration.create(ctx, iface, config)
        self.assertEqual(ctx.instance.runtime_properties[BUCKET],
                         'bucket')

        config = {}
        ctx_target = self.get_mock_relationship_ctx(
            "bucket",
            test_target=self.get_mock_ctx("Bucket", {},
                                          {EXTERNAL_RESOURCE_ID: 'ext_id'}))
        iface = MagicMock()
        iface.create = self.mock_return('location')
        with patch(PATCH_PREFIX + 'utils') as utils:
            utils.find_rel_by_node_type = self.mock_return(ctx_target)
            utils.clean_params = self.mock_return({})
            lifecycle_configuration.create(ctx, iface, config)
            self.assertEqual(ctx.instance.runtime_properties[BUCKET],
                             'ext_id')

    def test_delete(self):
        iface = MagicMock()
        lifecycle_configuration.delete(iface, {})
        self.assertTrue(iface.delete.called)


if __name__ == '__main__':
    unittest.main()

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
from __future__ import unicode_literals
import unittest

# Third part imports
from mock import patch, MagicMock
from cloudify.state import current_ctx
from cloudify.mocks import MockCloudifyContext


# Local imports
from cloudify_aws.common._compat import reload_module
from cloudify_aws.common.tests.test_base import TestBase, mock_decorator
from cloudify_aws.s3.resources.bucket_policy\
    import (S3BucketPolicy, BUCKET, POLICY)
from cloudify_aws.common.constants import EXTERNAL_RESOURCE_ID
from cloudify_aws.s3.resources import bucket_policy

PATCH_PREFIX = 'cloudify_aws.s3.resources.bucket_policy.'


class TestS3BucketPolicy(TestBase):

    def setUp(self):
        super(TestS3BucketPolicy, self).setUp()
        self.resource_config = {
            'kwargs': {
                'Policy': {
                    'Version': '2012-10-17',
                    'Statement':
                        [
                            {
                                'Sid': 'EveryoneGetPlugin',
                                'Effect': 'Allow',
                                'Principal': '*',
                                'Action': ['s3:GetObject'],
                                'Resource': 'arn:aws:s3:::test-bucket',
                            }
                        ]
                }
            }
        }
        self.client_config = {
            'aws_access_key_id': 'test_access_key_id',
            'aws_secret_access_key': 'test_secret_access_key',
            'region_name': 'test_region_name',
        }

        properties = {
            'resource_config': self.resource_config,
            'client_config': self.client_config
        }

        _ctx = MockCloudifyContext(
            node_id="s3_bucket_policy_node_id",
            node_name="s3_bucket_policy_node_name",
            deployment_id="s3_bucket_policy_node_name",
            properties=properties,
            runtime_properties={},
            relationships=[],
            operation={'retry_number': 0}
        )

        current_ctx.set(_ctx)
        self.ctx = _ctx
        self.policy = S3BucketPolicy(self.ctx._node, resource_id=True,
                                     client=True, logger=None)

        mock1 = patch('cloudify_aws.common.decorators.aws_resource',
                      mock_decorator)
        mock1.start()
        reload_module(bucket_policy)

    def test_class_properties(self):
        effect = self.get_client_error_exception(name='S3 Bucket')
        self.policy.client = self.make_client_function('get_bucket_policy',
                                                       side_effect=effect)
        res = self.policy.properties
        self.assertIsNone(res)

        value = {'Policy': 'test_name'}
        self.policy.client = self.make_client_function('get_bucket_policy',
                                                       return_value=value)
        res = self.policy.properties
        self.assertEqual(res, 'test_name')

        self.policy.client = self.make_client_function('get_bucket_policy',
                                                       return_value={})
        res = self.policy.properties
        self.assertIsNone(res)

    def test_class_status(self):
        self.policy.client = self.make_client_function('get_bucket_policy',
                                                       return_value={})
        res = self.policy.status
        self.assertIsNone(res)

        value = {'Policy': {'Status': 'ok'}}
        self.policy.client = self.make_client_function('get_bucket_policy',
                                                       return_value=value)
        res = self.policy.status
        self.assertEqual(res, 'ok')

    def test_class_create(self):
        value = 'test'
        self.policy.client = self.make_client_function('put_bucket_policy',
                                                       return_value=value)
        res = self.policy.create({})
        self.assertEqual(res, 'test')

    def test_class_delete(self):
        params = {}
        self.policy.client = self.make_client_function('delete_bucket_policy')
        self.policy.delete(params)
        self.assertTrue(self.policy.client.delete_bucket_policy.called)

    def test_prepare(self):
        ctx = self.ctx
        bucket_policy.prepare(ctx, 'config')
        self.assertEqual(ctx.instance.runtime_properties['resource_config'],
                         'config')

    def test_create(self):
        ctx = self.ctx
        config = {BUCKET: 'bucket', POLICY: 'policy'}
        iface = MagicMock()
        iface.create = self.mock_return('location')
        bucket_policy.create(ctx, iface, config)
        self.assertEqual(ctx.instance.runtime_properties[POLICY], 'policy')

        config = {BUCKET: 'bucket', POLICY: ['policy']}
        iface = MagicMock()
        iface.create = self.mock_return('location')
        bucket_policy.create(ctx, iface, config)
        self.assertEqual(ctx.instance.runtime_properties[POLICY], '["policy"]')

        config = {POLICY: 'policy'}
        ctx_target = self.get_mock_relationship_ctx(
            "bucket",
            test_target=self.get_mock_ctx("Bucket",
                                          {},
                                          {EXTERNAL_RESOURCE_ID: 'ext_id'}))
        iface = MagicMock()
        iface.create = self.mock_return('location')
        with patch(PATCH_PREFIX + 'utils') as utils:
            utils.find_rel_by_node_type = self.mock_return(ctx_target)
            utils.clean_params = self.mock_return({POLICY: 'policy'})
            bucket_policy.create(ctx, iface, config)
            self.assertEqual(ctx.instance.runtime_properties[BUCKET],
                             'ext_id')
            self.assertEqual(ctx.instance.runtime_properties[POLICY],
                             'policy')

    def test_delete(self):
        iface = MagicMock()
        bucket_policy.delete(iface, {})
        self.assertTrue(iface.delete.called)


if __name__ == '__main__':
    unittest.main()

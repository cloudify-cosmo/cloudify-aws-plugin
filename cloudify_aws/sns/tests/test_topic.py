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

from cloudify.state import current_ctx

# Local imports
from cloudify_aws.common._compat import reload_module
from cloudify_aws.sns.resources import topic
from cloudify_aws.common.tests.test_base import (
    TestBase,
    mock_decorator
)
from cloudify_aws.sns.resources.topic import (
    SNSTopic,
    SUB_ARN,
    TOPIC_ARN
)

PATCH_PREFIX = 'cloudify_aws.sns.resources.topic.'


class TestSNSTopic(TestBase):

    def setUp(self):
        super(TestSNSTopic, self).setUp()
        self.topic = SNSTopic("ctx_node",
                              resource_id=True,
                              client=MagicMock(),
                              logger=None)
        mock1 = patch('cloudify_aws.common.decorators.aws_resource',
                      mock_decorator)
        mock1.start()
        reload_module(topic)

    def test_class_properties(self):
        effect = self.get_client_error_exception(name='S3 SNS')
        self.topic.client = self.make_client_function(
            'list_topics',
            side_effect=effect)
        res = self.topic.properties
        self.assertIsNone(res)

        self.topic.client = self.make_client_function(
            'list_topics',
            return_value={})
        res = self.topic.properties
        self.assertIsNone(res)

        value = [{TOPIC_ARN: 'arn'}]
        self.topic.client = self.make_client_function(
            'list_topics',
            return_value=value)
        self.topic.resource_id = 'arn'
        res = self.topic.properties
        self.assertEqual(res, 'arn')

    def test_class_status(self):
        res = self.topic.status
        self.assertIsNone(res)

        value = [{TOPIC_ARN: 'arn'}]
        self.topic.client = self.make_client_function(
            'list_topics',
            return_value=value)
        self.topic.resource_id = 'arn'
        res = self.topic.status
        self.assertEqual(res, 'available')

    def test_class_create(self):
        value = {TOPIC_ARN: 'arn'}
        self.topic.client = self.make_client_function(
            'create_topic',
            return_value=value)
        res = self.topic.create({})
        self.assertEqual(res, 'arn')

    def test_class_subscribe(self):
        value = {SUB_ARN: 'arn'}
        self.topic.client = self.make_client_function(
            'subscribe',
            return_value=value)
        res = self.topic.subscribe({})
        self.assertEqual(res, 'arn')

    def test_class_delete(self):
        self.topic.client = self.make_client_function(
            'delete_topic', return_value='del')
        self.topic.delete({})
        self.assertTrue(self.topic.client.delete_topic.called)

    def test_prepare(self):
        ctx = self.get_mock_ctx("SNS")
        topic.prepare(ctx, 'config')
        self.assertEqual(ctx.instance.runtime_properties['resource_config'],
                         'config')

    def test_create(self):
        ctx = self.get_mock_ctx("SNS")
        current_ctx.set(ctx=ctx)
        iface = MagicMock()
        topic.create(ctx, iface, {})
        self.assertTrue(iface.create.called)

    def test_delete(self):
        ctx = self.get_mock_ctx("SNS")
        config = {TOPIC_ARN: 'arn'}
        iface = MagicMock()
        topic.delete(ctx, iface, config)
        self.assertTrue(iface.delete.called)

        config = {}
        iface = MagicMock()
        topic.delete(ctx, iface, config)
        self.assertTrue(iface.delete.called)


if __name__ == '__main__':
    unittest.main()

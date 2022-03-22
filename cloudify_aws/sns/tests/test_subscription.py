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

from cloudify.exceptions import OperationRetry, NonRecoverableError

# local imports
from cloudify_aws.common._compat import reload_module
from cloudify_aws.sns.resources import subscription
from cloudify_aws.common.tests.test_base import (
    TestBase,
    mock_decorator
)
from cloudify_aws.sns.resources.subscription import (
    SNSSubscription,
    SUB_ARN,
    TOPIC_ARN,
    CONFIRM_AUTHENTICATED
)

PATCH_PREFIX = 'cloudify_aws.sns.resources.subscription.'


class TestSNSSubscription(TestBase):

    def setUp(self):
        super(TestSNSSubscription, self).setUp()
        self.subscription = SNSSubscription("ctx_node",
                                            resource_id=True,
                                            client=MagicMock(),
                                            logger=None)
        mock1 = patch('cloudify_aws.common.decorators.aws_resource',
                      mock_decorator)
        mock1.start()
        reload_module(subscription)

    def test_class_properties(self):
        effect = self.get_client_error_exception(name='S3 SNS')
        self.subscription.client = self.make_client_function(
            'list_subscriptions',
            side_effect=effect)
        res = self.subscription.properties
        self.assertIsNone(res)

        self.subscription.client = self.make_client_function(
            'list_subscriptions',
            return_value={})
        res = self.subscription.properties
        self.assertIsNone(res)

        value = {'Subscriptions': [{SUB_ARN: 'arn'}]}
        self.subscription.client = self.make_client_function(
            'list_subscriptions',
            return_value=value)
        self.subscription.resource_id = 'arn'
        res = self.subscription.properties
        self.assertEqual(res, value['Subscriptions'][0])

    def test_class_status(self):
        res = self.subscription.status
        self.assertIsNone(res)

        value = {'Subscriptions': [{SUB_ARN: 'arn'}]}
        self.subscription.client = self.make_client_function(
            'list_subscriptions',
            return_value=value)
        self.subscription.resource_id = 'arn'
        res = self.subscription.status
        self.assertTrue(res)

    def test_class_create(self):
        self.subscription.confirm = MagicMock()
        self.subscription.create({})
        self.assertTrue(self.subscription.confirm.called)

    def test_class_confirm(self):
        value = {'Attributes': 'atr'}
        self.subscription.client = self.make_client_function(
            'get_subscription_attributes',
            return_value=value)
        res = self.subscription.confirm({})
        self.assertEqual(res, 'atr')

    def test_class_delete(self):
        self.subscription.client = self.make_client_function(
            'unsubscribe', return_value='del')
        res = self.subscription.delete({})
        self.assertEqual(res, 'del')

    def test_prepare(self):
        ctx = self.get_mock_ctx("SNS")
        subscription.prepare(ctx, 'config')
        self.assertEqual(ctx.instance.runtime_properties['resource_config'],
                         'config')

    def test_create(self):
        ctx = self.get_mock_ctx("SNS")
        config = {TOPIC_ARN: 'topic', 'Endpoint': 'endpoint'}
        iface = MagicMock()
        with patch(PATCH_PREFIX + 'utils') as utils, \
                patch(PATCH_PREFIX + 'SNSTopic') as topic:
            utils.validate_arn = self.mock_return(False)
            subscription.create(ctx, iface, config)
            self.assertTrue(topic().subscribe.called)

        config = {'Endpoint': 'endpoint'}
        iface = MagicMock()
        with patch(PATCH_PREFIX + 'utils') as utils, \
                patch(PATCH_PREFIX + 'SNSTopic') as topic:
            utils.validate_arn = self.mock_return(True)
            utils.find_rels_by_node_type = self.mock_return(MagicMock())
            subscription.create(ctx, iface, config)
            self.assertTrue(topic().subscribe.called)

        config = {TOPIC_ARN: 'topic', 'Endpoint': 'endpoint'}
        iface = MagicMock()
        with patch(PATCH_PREFIX + 'utils') as utils, \
                patch(PATCH_PREFIX + 'SNSTopic') as topic:
            utils.validate_arn = self.mock_return(True)
            utils.find_rels_by_node_name = self.mock_return(MagicMock())
            subscription.create(ctx, iface, config)
            self.assertTrue(topic().subscribe.called)

        ctx = self.get_mock_ctx("SNS")
        config = {TOPIC_ARN: 'topic'}
        iface = MagicMock()
        with patch(PATCH_PREFIX + 'utils') as utils, \
                patch(PATCH_PREFIX + 'SNSTopic') as topic:
            utils.validate_arn = self.mock_return(False)
            with self.assertRaises(NonRecoverableError):
                subscription.create(ctx, iface, config)
                self.assertFalse(topic().subscribe.called)

    def test_start(self):
        ctx = self.get_mock_ctx("SNS")
        ctx.operation.retry = MagicMock()
        config = {SUB_ARN: 'arn'}
        iface = MagicMock()
        iface.confirm = self.mock_return([])
        self.assertRaises(
            OperationRetry,
            subscription.start,
            ctx,
            iface,
            config)

        config = {SUB_ARN: 'arn'}
        iface = MagicMock()
        iface.confirm = self.mock_return([CONFIRM_AUTHENTICATED])
        ctx.operation.retry = MagicMock()
        subscription.start(ctx, iface, config)

        config = {}
        iface = MagicMock()
        iface.confirm = self.mock_return([CONFIRM_AUTHENTICATED])
        ctx.operation.retry = MagicMock()
        subscription.start(ctx, iface, config)

    def test_delete(self):
        ctx = self.get_mock_ctx("SNS")
        config = {SUB_ARN: 'arn'}
        iface = MagicMock()
        subscription.delete(ctx, iface, config)
        self.assertTrue(iface.delete.called)

        config = {}
        iface = MagicMock()
        subscription.delete(ctx, iface, config)
        self.assertTrue(iface.delete.called)


if __name__ == '__main__':
    unittest.main()

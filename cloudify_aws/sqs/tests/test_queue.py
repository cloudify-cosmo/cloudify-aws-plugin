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

# Third party imports
from mock import patch, MagicMock
from botocore.exceptions import UnknownServiceError

from cloudify.state import current_ctx

# Local imports
from cloudify_aws.common._compat import text_type
from cloudify_aws.common.tests.test_base import TestBase, CLIENT_CONFIG
from cloudify_aws.common.tests.test_base import DELETE_RESPONSE
from cloudify_aws.sqs.resources import queue


# Constants
QUEUE_TH = ['cloudify.nodes.Root',
            'cloudify.nodes.aws.SQS.Queue']

RESOURCE_CONFIG = {
    'QueueName': 'test-queue',
    'Attributes': {
        'Policy': {
            "Version": "2012-10-17",
            "Statement": [{
                "Sid": "Sid1",
                "Effect": "Deny",
                "Principal": "*",
                "Action": [
                    "SQS:SendMessage",
                    "SQS:ReceiveMessage"
                ],
                "Resource": "test-queue"
            }]
        },
        'MessageRetentionPeriod': '86400',
        'VisibilityTimeout': '180'
    }
}

NODE_PROPERTIES = {
    'use_external_resource': False,
    'resource_config': {
        'kwargs': RESOURCE_CONFIG
    },
    'client_config': CLIENT_CONFIG
}

RUNTIME_PROPERTIES = {
    'resource_config': {
    }
}

RUNTIME_PROPERTIES_AFTER_CREATE = {
    'aws_resource_arn': 'fake_QueueArn',
    'aws_resource_id': 'fake_QueueUrl',
    'resource_config': {},
}

POLICY_STRING = (
    """{"Version": "2012-10-17", "Statement": [{"Action": ["SQS:SendMessag""" +
    """e", "SQS:ReceiveMessage"], "Sid": "Sid1", "Resource": "test-queue",""" +
    """ "Effect": "Deny", "Principal": "*"}]}"""
)


class TestSQSQueue(TestBase):

    def setUp(self):
        super(TestSQSQueue, self).setUp()

        self.fake_boto, self.fake_client = self.fake_boto_client('sqs')

        self.mock_patch = patch('boto3.client', self.fake_boto)
        self.mock_patch.start()

    def tearDown(self):
        self.mock_patch.stop()
        self.fake_boto = None
        self.fake_client = None

        super(TestSQSQueue, self).tearDown()

    def test_prepare(self):
        self._prepare_check(
            type_hierarchy=QUEUE_TH,
            type_name='sqs',
            type_class=queue
        )

    def test_create_raises_UnknownServiceError(self):
        _ctx = self.get_mock_ctx(
            'test_create',
            test_properties=NODE_PROPERTIES,
            test_runtime_properties=RUNTIME_PROPERTIES,
            type_hierarchy=QUEUE_TH
        )

        current_ctx.set(_ctx)

        with self.assertRaises(UnknownServiceError) as error:
            queue.create(ctx=_ctx, resource_config=None, iface=None)

        self.assertEqual(
            text_type(error.exception),
            "Unknown service: 'sqs'. Valid service names are: ['rds']"
        )

        self.fake_boto.assert_called_with('sqs', **CLIENT_CONFIG)

    def test_create(self):
        _ctx = self.get_mock_ctx(
            'test_create',
            test_properties=NODE_PROPERTIES,
            test_runtime_properties=RUNTIME_PROPERTIES,
            type_hierarchy=QUEUE_TH
        )

        current_ctx.set(_ctx)

        self.fake_client.create_queue = MagicMock(return_value={
            'QueueUrl': 'fake_QueueUrl'
        })

        queue.create(ctx=_ctx, resource_config=None, iface=None)

        self.fake_boto.assert_called_with('sqs', **CLIENT_CONFIG)

        self.fake_client.get_queue_attributes.assert_called_with(
            AttributeNames=['QueueArn'], QueueUrl='fake_QueueUrl'
        )

        self.assertEqual(
            _ctx.instance.runtime_properties,
            {
                'aws_resource_arn': 'None',
                'aws_resource_id': 'fake_QueueUrl',
                'resource_config': {},
            }
        )

    def test_create_with_arn(self):
        node_properties = {
            'use_external_resource': False,
            'resource_config': {
                'kwargs': {
                    'QueueName': 'test-queue',
                    'Attributes': {
                        'Policy': POLICY_STRING,
                        'MessageRetentionPeriod': '86400',
                        'VisibilityTimeout': '180'
                    }
                }
            },
            'client_config': CLIENT_CONFIG
        }

        _ctx = self.get_mock_ctx(
            'test_create',
            test_properties=node_properties,
            test_runtime_properties=RUNTIME_PROPERTIES,
            type_hierarchy=QUEUE_TH
        )

        current_ctx.set(_ctx)

        self.fake_client.create_queue = MagicMock(return_value={
            'QueueUrl': 'fake_QueueUrl'
        })

        self.fake_client.get_queue_attributes = MagicMock(return_value={
            'Attributes': {
                'QueueArn': 'fake_QueueArn'
            }
        })
        queue.create(ctx=_ctx, resource_config=None, iface=None)

        self.fake_boto.assert_called_with('sqs', **CLIENT_CONFIG)

        self.fake_client.create_queue.assert_called_with(
            Attributes={
                'Policy': POLICY_STRING,
                'MessageRetentionPeriod': '86400',
                'VisibilityTimeout': '180'
            },
            QueueName='test-queue'
        )

        self.fake_client.get_queue_attributes.assert_called_with(
            AttributeNames=['QueueArn'], QueueUrl='fake_QueueUrl'
        )

        self.assertEqual(
            _ctx.instance.runtime_properties,
            RUNTIME_PROPERTIES_AFTER_CREATE
        )

    def test_delete(self):
        _ctx = self.get_mock_ctx(
            'test_delete',
            test_properties=NODE_PROPERTIES,
            test_runtime_properties=RUNTIME_PROPERTIES_AFTER_CREATE,
            type_hierarchy=QUEUE_TH,
            ctx_operation_name='cloudify.interfaces.lifecycle.delete'
        )

        current_ctx.set(_ctx)

        self.fake_client.delete_queue = self.mock_return(DELETE_RESPONSE)

        queue.delete(ctx=_ctx, resource_config={}, iface=None)

        self.fake_boto.assert_called_with('sqs', **CLIENT_CONFIG)

        self.fake_client.delete_queue.assert_called_with(
            QueueUrl='fake_QueueUrl'
        )

        self.assertEqual(
            _ctx.instance.runtime_properties,
            {}
        )

    def test_SQSQueueClass_status(self):
        test_instance = queue.SQSQueue(
            "ctx_node", resource_id='queue_id', client=self.fake_client,
            logger=None
        )

        self.assertEqual(test_instance.status, None)

    def test_SQSQueueClass_properties(self):
        test_instance = queue.SQSQueue(
            "ctx_node", resource_id='queue_id', client=self.fake_client,
            logger=None
        )

        self.assertEqual(test_instance.properties, None)

        self.fake_client.list_queues.assert_called_with(
            QueueNamePrefix='queue_id'
        )

    def test_SQSQueueClass_properties_list_queue(self):
        self.fake_client.list_queues = MagicMock(
            return_value={
                'QueueUrls': ['c']
            }
        )

        test_instance = queue.SQSQueue(
            "ctx_node", resource_id='queue_id', client=self.fake_client,
            logger=None
        )

        self.assertEqual(test_instance.properties, 'c')

        self.fake_client.list_queues.assert_called_with(
            QueueNamePrefix='queue_id'
        )


if __name__ == '__main__':
    unittest.main()

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

from cloudify.exceptions import OperationRetry

# Local imports
from cloudify_aws.common._compat import reload_module
from cloudify_aws.ec2.resources import spot_fleet_request
from cloudify_aws.common.tests.test_base import (
    TestBase,
    mock_decorator
)
from cloudify_aws.ec2.resources.spot_fleet_request import (
    SpotFleetRequest,
    SpotFleetRequestId,
    SpotFleetRequestIds,
    EC2SpotFleetRequest,
)


class TestEC2SpotFleetRequest(TestBase):

    def setUp(self):
        super(TestEC2SpotFleetRequest, self).setUp()
        self.spot_fleet_request = EC2SpotFleetRequest(
            "ctx_node", resource_id='foo', client=True, logger=None)
        mock1 = patch('cloudify_aws.common.decorators.aws_resource',
                      mock_decorator)
        mock2 = patch('cloudify_aws.common.decorators.wait_for_status',
                      mock_decorator)
        mock1.start()
        mock2.start()
        reload_module(spot_fleet_request)

    def test_class_properties(self):
        value = {}
        self.spot_fleet_request.client = self.make_client_function(
            'describe_spot_fleet_requests', return_value=value)
        res = self.spot_fleet_request.properties
        self.assertEqual({}, res)

        value = {
            'SpotFleetRequestConfigs': [
                {
                    SpotFleetRequestId: 'foo',
                    'SpotFleetRequestConfig': {}
                }
            ]
        }
        self.spot_fleet_request.client = self.make_client_function(
            'describe_spot_fleet_requests', return_value=value)
        res = self.spot_fleet_request.properties
        self.assertEqual(res[SpotFleetRequestId], 'foo')

    def test_class_status_none(self):
        value = {}
        self.spot_fleet_request.client = self.make_client_function(
            'describe_spot_fleet_requests', return_value=value)
        res = self.spot_fleet_request.status
        self.assertIsNone(res)

    def test_class_status_active(self):
        value = {
            'SpotFleetRequestConfigs': [
                {
                    SpotFleetRequestId: 'foo',
                    'SpotFleetRequestState': 'active',
                    'SpotFleetRequestConfig': {}
                }
            ]
        }
        self.spot_fleet_request.resource_id = 'foo'
        self.spot_fleet_request.client = self.make_client_function(
            'describe_spot_fleet_requests', return_value=value)
        res = self.spot_fleet_request.status
        self.assertEqual(res, 'active')

    def test_class_create(self):
        value = {SpotFleetRequestId: 'foo'}
        self.spot_fleet_request.client = self.make_client_function(
            'request_spot_fleet', return_value=value)
        res = self.spot_fleet_request.create(value)
        self.assertEqual(res[SpotFleetRequestId], value[SpotFleetRequestId])

    def test_class_delete(self):
        params = {SpotFleetRequestIds: 'foo', 'TerminateInstances': True}
        self.spot_fleet_request.client = self.make_client_function(
            'cancel_spot_fleet_requests')
        self.spot_fleet_request.delete(params)
        self.assertTrue(
            self.spot_fleet_request.client.cancel_spot_fleet_requests.called)

    def test_prepare(self):
        ctx = self.get_mock_ctx(SpotFleetRequest)
        config = {'SpotFleetRequestConfig': {'foo': 'bar'}}
        iface = MagicMock()
        iface.create = self.mock_return(config)
        spot_fleet_request.prepare(ctx, iface, config)
        self.assertEqual(
            ctx.instance.runtime_properties['resource_config'], config)

    def test_create(self):
        ctx = self.get_mock_ctx(SpotFleetRequest)
        config = {'SpotFleetRequestConfig': {SpotFleetRequestId: 'foo'}}
        self.spot_fleet_request.resource_id = \
            config['SpotFleetRequestConfig'][SpotFleetRequestId]
        iface = MagicMock()
        iface.create = self.mock_return({SpotFleetRequestId: 'foo'})
        spot_fleet_request.create(ctx=ctx, iface=iface, resource_config=config)
        self.assertEqual(self.spot_fleet_request.resource_id, 'foo')

    def test_delete(self):
        ctx = self.get_mock_ctx(SpotFleetRequest)
        iface = MagicMock()
        with self.assertRaises(OperationRetry):
            spot_fleet_request.delete(
                ctx=ctx, iface=iface, resource_config={})

    def test_poststart(self):
        ctx = self.get_mock_ctx(SpotFleetRequest)
        config = {
            'SpotFleetRequestConfig': {
                SpotFleetRequestId: 'foo',
                'TargetCapacity': 1
            }
        }
        self.spot_fleet_request.resource_id = \
            config['SpotFleetRequestConfig'][SpotFleetRequestId]
        instance_list = {
            'ActiveInstances': [
                {
                    'InstanceId': 'foo',
                    'InstanceType': 'bar',
                    'SpotInstanceRequestId': 'foo',
                    'InstanceHealth': 'baz'
                },
            ],
            'NextToken': 'string',
            'SpotFleetRequestId': 'foo'
        }
        self.spot_fleet_request._properties = config
        self.spot_fleet_request.client = self.make_client_function(
            'describe_spot_fleet_instances', return_value=instance_list)

        spot_fleet_request.poststart(
            ctx=ctx, iface=self.spot_fleet_request, resource_config={})
        self.assertTrue(
            'foo' in ctx.instance.runtime_properties['instance_ids']
        )


if __name__ == '__main__':
    unittest.main()

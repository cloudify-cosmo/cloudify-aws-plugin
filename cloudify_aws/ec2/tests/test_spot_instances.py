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
from cloudify_aws.ec2.resources import spot_instances as mod
from cloudify_aws.common.tests.test_base import (
    TestBase,
    mock_decorator
)


class TestEC2SpotInstances(TestBase):

    def setUp(self):
        self.spot_instances = mod.EC2SpotInstances(
            "ctx_node",
            resource_id='spot instance',
            client=True,
            logger=None)
        mock1 = patch('cloudify_aws.common.decorators.aws_resource',
                      mock_decorator)
        mock2 = patch('cloudify_aws.common.decorators.wait_for_status',
                      mock_decorator)
        mock1.start()
        mock2.start()
        reload_module(mod)

    def test_class_properties(self):
        effect = self.get_client_error_exception(name='EC2 Spot Instances')
        self.spot_instances.client = self.make_client_function(
            'describe_spot_instance_requests', side_effect=effect)
        res = self.spot_instances.properties
        self.assertEquals(res, {})

        value = {}
        self.spot_instances.client = self.make_client_function(
            'describe_spot_instance_requests', return_value=value)
        res = self.spot_instances.properties
        self.assertEquals(res, {})

    def test_class_properties_not_empty(self):
        value = {mod.REQUESTS: [{mod.REQUEST_ID: 'spot instance'}]}
        self.spot_instances.resource_id = 'spot instance'
        self.spot_instances.client = self.make_client_function(
            'describe_spot_instance_requests', return_value=value)
        res = self.spot_instances.properties
        self.assertEqual(res, {mod.REQUEST_ID: 'spot instance'})

    def test_class_status(self):
        value = {
            mod.REQUESTS: [
                {mod.REQUEST_ID: 'spot instance', 'State': None}]
        }
        self.spot_instances.resource_id = 'spot instance'
        self.spot_instances.client = self.make_client_function(
            'describe_spot_instance_requests', return_value=value)
        res = self.spot_instances.status
        self.assertIsNone(res)

    def test_class_status_not_none(self):

        value = {
            mod.REQUESTS: [
                {mod.REQUEST_ID: 'spot instance', 'State': 'open'}]
        }
        self.spot_instances.resource_id = 'spot instance'
        self.spot_instances.client = self.make_client_function(
            'describe_spot_instance_requests', return_value=value)
        res = self.spot_instances.status
        self.assertEqual(res, 'open')

    def test_class_create(self):
        value = {mod.REQUESTS: 'test'}
        self.spot_instances.client = self.make_client_function(
            'request_spot_instances', return_value=value)
        res = self.spot_instances.create(value)
        self.assertEqual(res[mod.REQUESTS], value[mod.REQUESTS])

    def test_class_delete(self):
        params = {}
        self.spot_instances.client = self.make_client_function(
            'cancel_spot_instance_requests')
        self.spot_instances.delete(params)
        self.assertTrue(
            self.spot_instances.client.cancel_spot_instance_requests.called)
        params = {mod.REQUESTS: 'spot instances'}
        self.spot_instances.delete(params)
        self.assertEqual(params[mod.REQUESTS], 'spot instances')

    def test_prepare(self):
        ctx = self.get_mock_ctx(mod.REQUESTS)
        config = {mod.REQUEST_ID: 'spot instances'}
        mod.prepare(ctx, mod.EC2SpotInstances, config)
        self.assertEqual(ctx.instance.runtime_properties['resource_config'],
                         config)

    def test_create(self):
        _tp = \
            {
                'os_family': 'windows',
                'agent_config': {'install_method': 'init_script'}
            }
        ctx = self.get_mock_ctx(mod.REQUESTS)
        ctx = self.get_mock_ctx(
            mod.REQUESTS,
            test_properties=_tp,
            type_hierarchy=['cloudify.nodes.Root', 'cloudify.nodes.Compute'])
        ctx.agent.init_script = lambda: 'SCRIPT'
        ctx.node.properties['agent_config']['install_method'] = 'init_script'
        current_ctx.set(ctx)
        config = {mod.REQUEST_ID: 'spot instances'}
        self.spot_instances.resource_id = config[mod.REQUEST_ID]
        iface = MagicMock()
        iface.create = self.mock_return({mod.REQUESTS: [config]})
        mod.create(ctx=ctx, iface=iface, resource_config=config)
        self.assertEqual(self.spot_instances.resource_id, 'spot instances')

    def test_delete(self):
        ctx = self.get_mock_ctx(mod.REQUESTS)
        iface = MagicMock()
        mod.delete(ctx=ctx, iface=iface, resource_config={})
        self.assertTrue(iface.delete.called)


if __name__ == '__main__':
    unittest.main()

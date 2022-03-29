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
from cloudify_aws.common.constants import EXTERNAL_RESOURCE_ARN
from cloudify_aws.elb.resources import listener
from cloudify_aws.common.tests.test_base import (
    TestBase,
    mock_decorator
)
from cloudify_aws.elb.resources.listener import (
    ELBListener,
    LISTENER_ARN,
    LB_ARN,
    TARGET_ARN
)

PATCH_PREFIX = 'cloudify_aws.elb.resources.listener.'


class TestELBListener(TestBase):

    def setUp(self):
        super(TestELBListener, self).setUp()
        self.listener = ELBListener("ctx_node", resource_id=True,
                                    client=MagicMock(), logger=None)
        mock1 = patch('cloudify_aws.common.decorators.aws_resource',
                      mock_decorator)
        mock1.start()
        reload_module(listener)

    def test_class_properties(self):
        effect = self.get_client_error_exception(name='S3 ELB')
        self.listener.client = self.make_client_function('describe_listeners',
                                                         side_effect=effect)
        res = self.listener.properties
        self.assertEqual(res, {})

        value = []
        self.listener.client = self.make_client_function('describe_listeners',
                                                         return_value=value)
        res = self.listener.properties
        self.assertEqual(res, {})

        self.listener.resource_id = True
        value = {'Listeners': [{'ListenerArn': True}]}
        self.listener.client = self.make_client_function('describe_listeners',
                                                         return_value=value)
        res = self.listener.properties
        self.assertEqual(res, {'ListenerArn': True})

    def test_class_status(self):
        value = []
        self.listener.client = self.make_client_function('describe_listeners',
                                                         return_value=value)
        res = self.listener.status
        self.assertEqual(res, {})

        value = {'Listeners': [{'ListenerArn': True, 'State': {'Code': 'ok'}}]}
        self.listener.client = self.make_client_function('describe_listeners',
                                                         return_value=value)
        self.listener.resource_id = True
        res = self.listener.status
        self.assertEqual(res, {'ListenerArn': True, 'State': {'Code': 'ok'}})

    def test_class_create(self):
        value = {'Listeners': [{LISTENER_ARN: 'id'}]}
        self.listener.client = self.make_client_function('create_listener',
                                                         return_value=value)
        res = self.listener.create(value)['Listeners'][0][LISTENER_ARN]
        self.assertEqual(res, 'id')

    def test_class_delete(self):
        params = {}
        self.listener.client = self.make_client_function('delete_listener')
        self.listener.delete(params)
        self.assertTrue(self.listener.client.delete_listener.called)

        params = {LISTENER_ARN: 'id'}
        self.listener.delete(params)
        self.assertTrue(self.listener.client.delete_listener.called)

    def test_prepare(self):
        ctx = self.get_mock_ctx("ELB")
        listener.prepare(ctx, 'config')
        self.assertEqual(ctx.instance.runtime_properties['resource_config'],
                         'config')

    def test_create(self):
        ctx = self.get_mock_ctx("ELB", {}, {'resource_config': {}})
        ctx_target = self.get_mock_relationship_ctx(
            "elb",
            test_target=self.get_mock_ctx("elb", {},
                                          {EXTERNAL_RESOURCE_ARN: 'ext_id'}))
        iface = MagicMock()
        config = {LB_ARN: 'listener', 'DefaultActions': [{TARGET_ARN: ''}]}
        with patch(PATCH_PREFIX + 'utils') as utils:
            utils.find_rel_by_node_type = self.mock_return(ctx_target)
            listener.create(ctx, iface, config)
            self.assertTrue(iface.create.called)
            self.assertEqual(
                config,
                {'DefaultActions': [{'TargetGroupArn': ''}],
                 'LoadBalancerArn': 'listener'})

        config = {'DefaultActions': [{TARGET_ARN: 'elb'}]}
        with patch(PATCH_PREFIX + 'utils') as utils:
            utils.find_rels_by_node_type = self.mock_return([ctx_target])
            listener.create(ctx, iface, config)
            self.assertTrue(iface.create.called)
            self.assertEqual(
                config,
                {'DefaultActions': [{'TargetGroupArn': 'ext_id'}],
                 'LoadBalancerArn': 'ext_id'})

    def test_delete(self):
        iface = MagicMock()
        listener.delete(iface, {})
        self.assertTrue(iface.delete.called)


if __name__ == '__main__':
    unittest.main()

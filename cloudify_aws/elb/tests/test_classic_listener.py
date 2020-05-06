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
from cloudify_aws.common.constants import EXTERNAL_RESOURCE_ID
from cloudify_aws.elb.resources.classic import listener
from cloudify_aws.common.tests.test_base import (
    TestBase,
    mock_decorator
)
from cloudify_aws.elb.resources.classic.listener import (
    ELBClassicListener,
    LISTENERS,
    LB_NAME,
    LB_PORT
)

PATCH_PREFIX = 'cloudify_aws.elb.resources.classic.listener.'


class TestELBClassicListener(TestBase):

    def setUp(self):
        super(TestELBClassicListener, self).setUp()
        self.listener = ELBClassicListener("ctx_node", resource_id=True,
                                           client=MagicMock(), logger=None)
        mock1 = patch('cloudify_aws.common.decorators.aws_resource',
                      mock_decorator)
        mock1.start()
        reload_module(listener)

    def test_class_properties(self):
        res = self.listener.properties
        self.assertIsNone(res)

    def test_class_status(self):
        res = self.listener.status
        self.assertIsNone(res)

    def test_class_create(self):
        self.listener.client = self.make_client_function(
            'create_load_balancer_listeners', return_value='id')
        res = self.listener.create({})
        self.assertEqual(res, 'id')

    def test_class_delete(self):
        self.listener.client = self.make_client_function(
            'delete_load_balancer_listeners', return_value='del')
        res = self.listener.delete({})
        self.assertEqual(res, 'del')

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
                                          {EXTERNAL_RESOURCE_ID: 'ext_id'}))
        iface = MagicMock()
        config = {LB_NAME: 'listener'}
        listener.create(ctx, iface, config)
        self.assertTrue(iface.create.called)

        config = {}
        ctx = self.get_mock_ctx("ELB", {}, {'resource_config': {}})
        with patch(PATCH_PREFIX + 'utils') as utils:
            utils.find_rels_by_node_type = self.mock_return([ctx_target])
            listener.create(ctx, iface, config)
            self.assertTrue(iface.create.called)

    def test_delete(self):
        ctx = self.get_mock_ctx("ELB", {}, {'resource_config': {}})
        iface = MagicMock()
        config = {LB_NAME: 'listener', LISTENERS: [{LB_PORT: 'port'}]}
        listener.delete(ctx, iface, config)
        self.assertTrue(iface.delete.called)

        ctx = self.get_mock_ctx("ELB", {}, {'resource_config': {},
                                            LB_NAME: 'name'})
        iface = MagicMock()
        config = {LISTENERS: [{LB_PORT: 'port'}]}
        listener.delete(ctx, iface, config)
        self.assertTrue(iface.delete.called)


if __name__ == '__main__':
    unittest.main()

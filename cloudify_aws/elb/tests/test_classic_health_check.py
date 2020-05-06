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
from cloudify_aws.elb.resources.classic import health_check
from cloudify_aws.common.tests.test_base import (
    TestBase,
    mock_decorator
)
from cloudify_aws.elb.resources.classic.health_check import (
    ELBClassicHealthCheck,
    LB_NAME
)

PATCH_PREFIX = 'cloudify_aws.elb.resources.classic.health_check.'


class TestELBClassicHealthCheck(TestBase):

    def setUp(self):
        super(TestELBClassicHealthCheck, self).setUp()
        self.health_check = ELBClassicHealthCheck("ctx_node", resource_id=True,
                                                  client=MagicMock(),
                                                  logger=None)
        mock1 = patch('cloudify_aws.common.decorators.aws_resource',
                      mock_decorator)
        mock1.start()
        reload_module(health_check)

    def test_class_properties(self):
        res = self.health_check.properties
        self.assertIsNone(res)

    def test_class_status(self):
        res = self.health_check.status
        self.assertIsNone(res)

    def test_class_create(self):
        value = {}
        self.health_check.client = self.make_client_function(
            'configure_health_check', return_value='id')
        res = self.health_check.create(value)
        self.assertEqual(res, 'id')

    def test_class_delete(self):
        params = {}
        self.assertIsNone(self.health_check.delete(params))

    def test_prepare(self):
        ctx = self.get_mock_ctx("ELB")
        health_check.prepare(ctx, 'config')
        self.assertEqual(ctx.instance.runtime_properties['resource_config'],
                         'config')

    def test_create(self):
        ctx = self.get_mock_ctx("ELB", {}, {'resource_config': {}})
        ctx_target = self.get_mock_relationship_ctx(
            "elb",
            test_target=self.get_mock_ctx("elb", {},
                                          {EXTERNAL_RESOURCE_ID: 'ext_id'}))
        iface = MagicMock()
        config = {LB_NAME: 'lb_name'}
        health_check.create(ctx, iface, config)
        self.assertTrue(iface.create.called)

        ctx = self.get_mock_ctx("ELB", {}, {'resource_config': {}})
        config = {}
        with patch(PATCH_PREFIX + 'utils') as utils:
            utils.find_rels_by_node_type = self.mock_return([ctx_target])
            health_check.create(ctx, iface, config)
            self.assertTrue(iface.create.called)


if __name__ == '__main__':
    unittest.main()


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
from cloudify_aws.route53.resources import record_set
from cloudify.exceptions import NonRecoverableError
from cloudify_aws.common.tests.test_base import (
    TestBase,
    mock_decorator
)

PATCH_PREFIX = 'cloudify_aws.route53.resources.record_set.'


class TestRecordSet(TestBase):
    def _get_ctx(self):
        _test_name = 'test_properties'
        _test_node_properties = {
            'use_external_resource': False
        }
        _test_runtime_properties = {'resource_config': False}
        return self.get_mock_ctx(_test_name, _test_node_properties,
                                 _test_runtime_properties,
                                 None,
                                 ctx_operation_name='foo.foo.foo.configure')

    def _get_relationship_context(self):
        _test_name = 'test_recordset'
        _test_node_properties = {
            'use_external_resource': False,
            'resource_id': 'target'
        }
        _test_runtime_properties = {'resource_config': {},
                                    '_set_changed': True}
        source = self.get_mock_ctx("source_node", _test_node_properties,
                                   _test_runtime_properties)
        target = self.get_mock_ctx("target_node", _test_node_properties,
                                   _test_runtime_properties)
        return self.get_mock_relationship_ctx(_test_name,
                                              _test_node_properties,
                                              _test_runtime_properties,
                                              source,
                                              target)

    def setUp(self):
        super(TestRecordSet, self).setUp()
        mock1 = patch('cloudify_aws.common.decorators.aws_resource',
                      mock_decorator)
        mock2 = patch('cloudify_aws.common.decorators.aws_relationship',
                      mock_decorator)
        mock1.start()
        mock2.start()
        reload_module(record_set)

    def test_prepare(self):
        ctx = self._get_ctx()
        record_set.prepare(ctx, MagicMock(), 'resource_config')
        self.assertEqual(ctx.instance.runtime_properties['resource_config'],
                         {'ChangeBatch': {'Changes': ['resource_config']}})

    def test_create(self):
        ctx = self._get_ctx()
        with patch(PATCH_PREFIX + 'utils'), \
                patch(PATCH_PREFIX + 'Route53HostedZone') as zone:
            record_set.create(ctx, zone, {})
            self.assertTrue(zone.change_resource_record_sets.called)

    def test_delete(self):
        ctx = self._get_ctx()
        with patch(PATCH_PREFIX + 'utils'), \
                patch(PATCH_PREFIX + 'Route53HostedZone'):
            with self.assertRaises(NonRecoverableError):
                record_set.delete(ctx, MagicMock(), 'res_type', 'foo')

        ctx = self._get_ctx()
        with patch(PATCH_PREFIX + 'utils'), \
                patch(PATCH_PREFIX + 'Route53HostedZone') as zone:
            params = {'HostedZoneId': 'zid',
                      'ChangeBatch': {'Changes':
                                      [{'ResourceRecordSet': 'rec_set',
                                        'Action': 'delete'}]}}
            ctx.instance.runtime_properties['resource_config'] = params
            record_set.delete(ctx, MagicMock(), {}, 'res_type')
            self.assertFalse(zone.change_resource_record_sets.called)

        ctx = self._get_ctx()
        with patch(PATCH_PREFIX + 'utils'), \
                patch(PATCH_PREFIX + 'Route53HostedZone') as zone:
            params = {'HostedZoneId': 'zid',
                      'ChangeBatch': {'Changes':
                                      [{'ResourceRecordSet': 'rec_set',
                                        'Action': 'create'}]}}
            ctx.instance.runtime_properties['resource_config'] = params
            record_set.delete(ctx, zone, {}, 'res_type')
            self.assertTrue(zone.change_resource_record_sets.called)

    def test_prepare_assoc(self):
        ctx = self._get_relationship_context()
        ctx.source.instance.runtime_properties['resource_config'] = {'VPC': {}}
        iface = MagicMock()
        iface.create = self.mock_return(('res_id', 'res_arn'))
        with patch(PATCH_PREFIX + 'utils') as utils:
            utils.is_node_type = self.mock_return(True)
            utils.get_resource_id = self.mock_return('res_id')
            record_set.prepare_assoc(ctx, MagicMock())
            rprop = ctx.source.instance.runtime_properties['resource_config']
            self.assertEqual(
                rprop['HostedZoneId'],
                'res_id')

    def test_detach_from(self):
        record_set.detach_from(None)


if __name__ == '__main__':
    unittest.main()


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
from cloudify_aws.route53.resources import hosted_zone
from cloudify_aws.common import constants
from cloudify_aws.common.tests.test_base import (
    TestBase,
    mock_decorator
)

PATCH_PREFIX = 'cloudify_aws.route53.resources.hosted_zone.'


class TestHostedZone(TestBase):
    def _get_ctx(self):
        _test_name = 'test_properties'
        _test_node_properties = {
            'use_external_resource': False
        }
        _test_runtime_properties = {'resource_config': False}
        return self.get_mock_ctx(_test_name, _test_node_properties,
                                 _test_runtime_properties,
                                 None)

    def _get_relationship_context(self):
        _test_name = 'test_lambda'
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
        super(TestHostedZone, self).setUp()
        mock1 = patch('cloudify_aws.common.decorators.aws_resource',
                      mock_decorator)
        mock2 = patch('cloudify_aws.common.decorators.wait_for_delete',
                      mock_decorator)
        mock3 = patch('cloudify_aws.common.decorators.aws_relationship',
                      mock_decorator)
        mock1.start()
        mock2.start()
        mock3.start()
        reload_module(hosted_zone)

    def test_class_properties(self):
        res_id = "test_resource"
        client = self.make_client_function("get_hosted_zone",
                                           return_value="zone")
        route = hosted_zone.Route53HostedZone(None, res_id, client,
                                              MagicMock())
        res = route.properties
        self.assertEqual(res, "zone")

        client = self.make_client_function(
            "get_hosted_zone",
            side_effect=self.get_client_error_exception("Error"))
        route = hosted_zone.Route53HostedZone(None, res_id, client,
                                              MagicMock())
        res = route.properties
        self.assertIsNone(res)

    def test_class_status(self):
        res_id = "test_resource"
        client = self.make_client_function("get_hosted_zone",
                                           return_value="zone")
        route = hosted_zone.Route53HostedZone(None, res_id, client,
                                              MagicMock())
        res = route.status
        self.assertEqual(res, "available")

        client = self.make_client_function(
            "get_hosted_zone",
            side_effect=self.get_client_error_exception("Error"))
        route = hosted_zone.Route53HostedZone(None, res_id, client,
                                              MagicMock())
        res = route.status
        self.assertIsNone(res)

    def test_class_create(self):
        res_id = "test_resource"
        params = {'HostedZone': {'Id': 'test_id'}}
        client = self.make_client_function("create_hosted_zone",
                                           return_value=params)
        route = hosted_zone.Route53HostedZone(None, res_id, client,
                                              MagicMock())

        self.assertEqual(
            route.create(params)['HostedZone']['Id'], "test_id")

    def test_class_delete(self):
        res_id = "test_resource"
        client = self.make_client_function("delete_hosted_zone",
                                           return_value='deleted')
        route = hosted_zone.Route53HostedZone(None, res_id, client,
                                              MagicMock())
        res = route.delete()
        self.assertEqual(res, "deleted")

    def test_class_change_resource(self):
        res_id = "test_resource"
        params = {'ChangeInfo': 'changed'}
        client = self.make_client_function("change_resource_record_sets",
                                           return_value=params)
        route = hosted_zone.Route53HostedZone(None, res_id, client,
                                              MagicMock())
        res = route.change_resource_record_sets(params)
        self.assertEqual(res, "changed")

    def test_class_list_resource(self):
        res_id = "test_resource"
        params = {'ResourceRecordSets': 'listed'}
        client = self.make_client_function("list_resource_record_sets",
                                           return_value=params)
        route = hosted_zone.Route53HostedZone(None, res_id, client,
                                              MagicMock())
        res = route.list_resource_record_sets(params)
        self.assertEqual(res, "listed")

    def test_prepare(self):
        ctx = self._get_ctx()
        hosted_zone.prepare(ctx, 'config', MagicMock())
        self.assertEqual(ctx.instance.runtime_properties['resource_config'],
                         'config')

    def test_create(self):
        ctx = self._get_ctx()
        resource_config = {'config': None}
        iface = MagicMock()
        iface.create = self.mock_return({'HostedZone': {'Id': 'id'}})
        hosted_zone.create(ctx, iface, resource_config)
        rprop = ctx.instance.runtime_properties
        self.assertEqual(rprop[constants.EXTERNAL_RESOURCE_ID], 'id')
        self.assertEqual(rprop[constants.EXTERNAL_RESOURCE_ARN], 'id')

    def test_delete(self):
        ctx = self._get_ctx()
        resource_config = {'config': None}
        iface = MagicMock()
        iface.create = self.mock_return(('res_id', 'res_arn'))
        hosted_zone.delete(ctx, iface, resource_config, 'rest_type', False)
        self.assertTrue(iface.delete.called)

        # default types skiped
        iface.list_resource_record_sets = self.mock_return([{'Type': 'NS'}])
        hosted_zone.delete(ctx, iface, resource_config, 'rest_type', True)
        self.assertTrue(iface.delete.called)

        iface.list_resource_record_sets = self.mock_return([{'Type': 'SOA'}])
        hosted_zone.delete(ctx, iface, resource_config, 'rest_type', True)
        self.assertTrue(iface.delete.called)

        # non default
        iface.list_resource_record_sets = self.mock_return([{'Type': None}])
        hosted_zone.delete(ctx, iface, resource_config, 'rest_type', True)
        self.assertTrue(iface.delete.called)
        self.assertTrue(iface.change_resource_record_sets.called)

    def test_prepare_assoc(self):
        ctx = self._get_relationship_context()
        ctx.source.instance.runtime_properties['resource_config'] = {'VPC': {}}
        resource_config = {'config': None}
        iface = MagicMock()
        iface.create = self.mock_return(('res_id', 'res_arn'))
        with patch(PATCH_PREFIX + 'utils') as utils, \
                patch(PATCH_PREFIX + 'detect_vpc_region',
                      self.mock_return('vpc_region')), \
                patch(PATCH_PREFIX + 'Boto3Connection'):
            utils.is_node_type = self.mock_return(True)
            utils.get_resource_id = self.mock_return('res_id')
            hosted_zone.prepare_assoc(ctx, iface, resource_config)
            rprop = ctx.source.instance.runtime_properties
            self.assertEqual(
                rprop['resource_config']['VPC'],
                {'VPCId': 'res_id', 'VPCRegion': 'vpc_region'})

    def test_detach_from(self):
        hosted_zone.detach_from(None, None, None)

    def test_detect_vpc_region(self):
        client = MagicMock()
        client.describe_subnets = self.mock_return([])
        res = hosted_zone.detect_vpc_region(client, 'vpc_id')
        self.assertIsNone(res)

        subnets = {'Subnets': [{'AvailabilityZone': 'zone_id'}]}
        client.describe_subnets = self.mock_return(subnets)
        client.describe_availability_zones = self.mock_return([])
        res = hosted_zone.detect_vpc_region(client, 'vpc_id')
        self.assertIsNone(res)

        subnets = {'Subnets': [{'AvailabilityZone': 'zone_id'}]}
        client.describe_subnets = self.mock_return(subnets)
        zones = {'AvailabilityZones': [{'RegionName': 'regname'}]}
        client.describe_availability_zones = self.mock_return(zones)
        res = hosted_zone.detect_vpc_region(client, 'vpc_id')
        self.assertEqual(res, 'regname')


if __name__ == '__main__':
    unittest.main()

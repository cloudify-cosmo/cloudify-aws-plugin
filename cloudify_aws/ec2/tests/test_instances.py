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

import unittest
from cloudify_aws.common.tests.test_base import TestBase, mock_decorator
from cloudify_aws.ec2.resources.instances import (
    EC2Instances, INSTANCES, RESERVATIONS, INSTANCE_ID,
    GROUP_TYPE, NETWORK_INTERFACE_TYPE, SUBNET_TYPE,
    INSTANCE_IDS)
from mock import patch, MagicMock
from cloudify_aws.ec2.resources import instances
from cloudify.state import current_ctx
from cloudify.exceptions import OperationRetry


class TestEC2Instances(TestBase):

    def setUp(self):
        self.instances = EC2Instances("ctx_node", resource_id=True,
                                      client=True, logger=None)
        mock1 = patch('cloudify_aws.common.decorators.aws_resource',
                      mock_decorator)
        mock2 = patch('cloudify_aws.common.decorators.wait_for_status',
                      mock_decorator)
        mock1.start()
        mock2.start()
        reload(instances)

    def test_class_properties(self):
        effect = self.get_client_error_exception(name='EC2 Instances')
        self.instances.client = \
            self.make_client_function('describe_instances',
                                      side_effect=effect)
        res = self.instances.properties
        self.assertIsNone(res)

        value = {}
        self.instances.client = \
            self.make_client_function('describe_instances',
                                      return_value=value)
        res = self.instances.properties
        self.assertIsNone(res)

        value = {RESERVATIONS: [{INSTANCES: [{INSTANCE_ID: 'test_name'}]}]}
        self.instances.client = \
            self.make_client_function('describe_instances',
                                      return_value=value)
        res = self.instances.properties
        self.assertEqual(res[INSTANCE_ID], 'test_name')

    def test_class_status(self):
        value = {}
        self.instances.client = \
            self.make_client_function('describe_instances',
                                      return_value=value)
        res = self.instances.status
        self.assertIsNone(res)

        value = {RESERVATIONS: [{INSTANCES: [{
            INSTANCE_ID: 'test_name', 'State': {'Code': 16}}]}]}
        self.instances.client = \
            self.make_client_function('describe_instances',
                                      return_value=value)
        res = self.instances.status
        self.assertEqual(res, 16)

    def test_class_create(self):
        value = {RESERVATIONS: [{INSTANCES: [{INSTANCE_IDS: ['test_name']}]}]}
        self.instances.client = \
            self.make_client_function('run_instances',
                                      return_value=value)
        res = self.instances.create(value)
        self.assertEqual(res, value)

    def test_class_start(self):
        value = {INSTANCE_IDS: ['test_name']}
        self.instances.client = \
            self.make_client_function('start_instances',
                                      return_value=value)
        res = self.instances.start(value)
        self.assertEqual(res, value)

    def test_class_stop(self):
        value = {INSTANCE_IDS: ['test_name']}
        self.instances.client = \
            self.make_client_function('stop_instances',
                                      return_value=value)
        res = self.instances.stop(value)
        self.assertEqual(res, value)

    def test_class_delete(self):
        params = {INSTANCE_ID: 'test_name'}
        self.instances.client = \
            self.make_client_function('terminate_instances')
        self.instances.delete(params)
        self.assertTrue(self.instances.client.terminate_instances
                        .called)

        params = {INSTANCE_ID: 'test_name'}
        self.instances.delete(params)
        self.assertEqual(params[INSTANCE_ID], 'test_name')

    def test_prepare(self):
        ctx = self.get_mock_ctx(
            "EC2Instances",
            type_hierarchy=['cloudify.nodes.Root', 'cloudify.nodes.Compute'])
        params = {'ImageId': 'test image', 'InstanceType': 'test type'}
        instances.prepare(ctx, EC2Instances, params)
        self.assertEqual(ctx.instance.runtime_properties['resource_config'],
                         params)

    def test_create(self):
        ctx = self.get_mock_ctx(
            "EC2Instances",
            test_properties={'os_family': 'linux'},
            type_hierarchy=['cloudify.nodes.Root', 'cloudify.nodes.Compute'])
        current_ctx.set(ctx=ctx)
        params = {'ImageId': 'test image', 'InstanceType': 'test type'}
        self.instances.resource_id = 'test_name'
        iface = MagicMock()
        value = {INSTANCES: [{INSTANCE_ID: 'test_name'}]}
        iface.create = self.mock_return(value)
        instances.create(ctx=ctx, iface=iface, resource_config=params)
        self.assertEqual(self.instances.resource_id,
                         'test_name')

    def test_create_with_relationships(self):
        ctx = self.get_mock_ctx(
            "EC2Instances",
            test_properties={'os_family': 'linux'},
            type_hierarchy=['cloudify.nodes.Root', 'cloudify.nodes.Compute'])
        current_ctx.set(ctx=ctx)
        params = {'ImageId': 'test image', 'InstanceType': 'test type'}
        self.instances.resource_id = 'test_name'
        iface = MagicMock()
        with patch('cloudify_aws.common.utils.find_rel_by_node_type'):
            instances.create(ctx=ctx, iface=iface, resource_config=params)
            self.assertEqual(self.instances.resource_id,
                             'test_name')

    def test_delete(self):
        ctx = self.get_mock_ctx(
            "EC2Instances",
            test_properties={'os_family': 'linux'},
            type_hierarchy=['cloudify.nodes.Root', 'cloudify.nodes.Compute'])
        current_ctx.set(ctx=ctx)
        iface = MagicMock()
        instances.delete(ctx=ctx, iface=iface, resource_config={})
        self.assertTrue(iface.delete.called)
        for prop in ['ip',
                     'private_ip_address',
                     'public_ip_address',
                     'create_response']:
            self.assertTrue(prop not in ctx.instance.runtime_properties)

    def test_create_relatonships(self):
        _source_ctx, _target_ctx, _group_rel = \
            self._create_common_relationships(
                'test_node',
                source_type_hierarchy=['cloudify.nodes.Root',
                                       'cloudify.nodes.Compute'],
                target_type_hierarchy=['cloudify.nodes.Root',
                                       GROUP_TYPE])

        _source_ctx, _target_ctx, _subnet_type = \
            self._create_common_relationships(
                'test_node',
                source_type_hierarchy=['cloudify.nodes.Root',
                                       'cloudify.nodes.Compute'],
                target_type_hierarchy=['cloudify.nodes.Root',
                                       SUBNET_TYPE])

        _source_ctx, _target_ctx, _nic_type = \
            self._create_common_relationships(
                'test_node',
                source_type_hierarchy=['cloudify.nodes.Root',
                                       'cloudify.nodes.Compute'],
                target_type_hierarchy=['cloudify.nodes.Root',
                                       NETWORK_INTERFACE_TYPE])

        _ctx = self.get_mock_ctx(
            "EC2Instances",
            test_properties={'os_family': 'linux'},
            type_hierarchy=['cloudify.nodes.Root', 'cloudify.nodes.Compute'],
            test_relationships=[_group_rel, _subnet_type, _nic_type])
        current_ctx.set(_ctx)
        params = {'ImageId': 'test image', 'InstanceType': 'test type'}
        iface = MagicMock()
        self.instances.resource_id = 'test_name'
        with patch('cloudify_aws.common.utils.find_rels_by_node_type'):
            instances.create(ctx=_ctx, iface=iface, resource_config=params)
            self.assertEqual(self.instances.resource_id, 'test_name')

    def test_multiple_nics(self):

        _source_ctx1, _target_ctx1, _nic_type1 = \
            self._create_common_relationships(
                'test_node',
                source_type_hierarchy=['cloudify.nodes.Root',
                                       'cloudify.nodes.Compute',
                                       'cloudify.nodes.aws.ec2.Instances'],
                target_type_hierarchy=['cloudify.nodes.Root',
                                       NETWORK_INTERFACE_TYPE])
        _target_ctx1.instance.runtime_properties['aws_resource_id'] = 'eni-0'

        _source_ctx2, _target_ctx2, _nic_type2 = \
            self._create_common_relationships(
                'test_node',
                source_type_hierarchy=['cloudify.nodes.Root',
                                       'cloudify.nodes.Compute',
                                       'cloudify.nodes.aws.ec2.Instances'],
                target_type_hierarchy=['cloudify.nodes.Root',
                                       NETWORK_INTERFACE_TYPE])
        _target_ctx2.instance.runtime_properties['aws_resource_id'] = 'eni-1'

        _ctx = self.get_mock_ctx(
            "EC2Instances",
            test_properties={'os_family': 'linux'},
            type_hierarchy=['cloudify.nodes.Root',
                            'cloudify.nodes.Compute',
                            'cloudify.nodes.aws.ec2.Instances'],
            test_relationships=[_nic_type1, _nic_type2])

        current_ctx.set(_ctx)
        params = {
            'ImageId': 'test image',
            'InstanceType': 'test type',
            'NetworkInterfaces': [
                {
                    'NetworkInterfaceId': 'eni-2',
                    'DeviceIndex': 2
                }
            ]
        }
        iface = MagicMock()
        value = {INSTANCES: [{INSTANCE_ID: 'test_name'}]}
        iface.create = self.mock_return(value)
        instances.create(ctx=_ctx, iface=iface, resource_config=params)

    def test_start(self):
        ctx = self.get_mock_ctx(
            "EC2Instances",
            test_properties={'os_family': 'linux'},
            type_hierarchy=['cloudify.nodes.Root', 'cloudify.nodes.Compute'])
        current_ctx.set(ctx=ctx)
        iface = MagicMock()
        iface.status = 0
        self.instances.resource_id = 'test_name'
        try:
            instances.start(ctx, iface, {})
        except OperationRetry:
            pass
        self.assertTrue(iface.start.called)

    def test_modify_instance_attribute(self):
        ctx = self.get_mock_ctx(
            "EC2Instances",
            test_properties={'os_family': 'linux'},
            type_hierarchy=['cloudify.nodes.Root', 'cloudify.nodes.Compute'])
        current_ctx.set(ctx=ctx)
        iface = MagicMock()
        iface.status = 0
        self.instances.resource_id = 'test_name'
        try:
            instances.modify_instance_attribute(
                ctx, iface, {INSTANCE_ID: self.instances.resource_id})
        except OperationRetry:
            pass
        self.assertTrue(iface.modify_instance_attribute.called)

    def test_stop(self):
        ctx = self.get_mock_ctx(
            "EC2Instances",
            test_properties={'os_family': 'linux'},
            type_hierarchy=['cloudify.nodes.Root', 'cloudify.nodes.Compute'])
        current_ctx.set(ctx=ctx)
        iface = MagicMock()
        instances.stop(ctx, iface, {})
        self.assertTrue(iface.stop.called)

    def test_with_userdata(self):
        """ this tests that handle user data returns the expected output
        """
        _tp = \
            {
                'os_family': 'windows',
                'agent_config': {'install_method': 'init_script'}
            }

        ctx = self.get_mock_ctx(
            "EC2Instances",
            test_properties=_tp,
            type_hierarchy=['cloudify.nodes.Root', 'cloudify.nodes.Compute'])
        current_ctx.set(ctx=ctx)
        ctx.agent.init_script = lambda: 'SCRIPT'
        ctx.node.properties['agent_config']['install_method'] = 'init_script'
        current_ctx.set(ctx=ctx)
        params = \
            {
                'ImageId': 'test image',
                'InstanceType': 'test type',
                'UserData': ''
            }
        handle_userdata_output = \
            instances._handle_userdata(params['UserData'])
        expected_userdata = 'SCRIPT'
        self.assertIn(expected_userdata,
                      handle_userdata_output)


if __name__ == '__main__':
    unittest.main()

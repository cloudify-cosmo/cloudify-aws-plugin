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
from mock import MagicMock

from cloudify.state import current_ctx
from cloudify.mocks import MockCloudifyContext
from cloudify.exceptions import NonRecoverableError

from cloudify_aws.common import utils
from cloudify_aws.common._compat import text_type
from cloudify_aws.common.tests.test_base import TestBase


class TestUtils(TestBase):

    def test_get_resource_id(self):
        _test_name = 'test_get_resource_id'
        _test_node_properties = {
            'use_external_resource': False
        }
        _test_runtime_properties = {
            'resource_config': {}
        }
        _ctx = self.get_mock_ctx(
            _test_name,
            test_properties=_test_node_properties,
            test_runtime_properties=_test_runtime_properties,
            type_hierarchy=['cloudify.nodes.Root']
        )
        current_ctx.set(_ctx)
        self.assertEqual(utils.get_resource_id(), None)

        with self.assertRaises(NonRecoverableError):
            utils.get_resource_id(raise_on_missing=True)

    def test_get_resource_arn(self):
        _test_name = 'test_get_resource_arn'
        _test_node_properties = {
            'use_external_resource': False
        }
        _test_runtime_properties = {
            'resource_config': {}
        }
        _ctx = self.get_mock_ctx(
            _test_name,
            test_properties=_test_node_properties,
            test_runtime_properties=_test_runtime_properties,
            type_hierarchy=['cloudify.nodes.Root']
        )
        current_ctx.set(_ctx)
        self.assertEqual(utils.get_resource_arn(), None)

        with self.assertRaises(NonRecoverableError):
            utils.get_resource_arn(raise_on_missing=True)

    def test_update_resource_id(self):
        mock_instance = MagicMock()

        mock_instance.runtime_properties = {}

        utils.update_resource_id(mock_instance, 'val')

        self.assertEqual(mock_instance.runtime_properties,
                         {'aws_resource_id': 'val'})

    def test_update_resource_arn(self):
        mock_instance = MagicMock()

        mock_instance.runtime_properties = {}

        utils.update_resource_arn(mock_instance, 'val')

        self.assertEqual(mock_instance.runtime_properties,
                         {'aws_resource_arn': 'val'})

    def test_get_parent_resource_id_empty(self):
        mock_instance = MagicMock()
        mock_instance.relationships = []

        self.assertEqual(
            utils.get_parent_resource_id(mock_instance,
                                         raise_on_missing=False),
            None
        )

    def test_get_parent_resource_id(self):
        mock_child = MagicMock()
        mock_child.type_hierarchy = 'some_type'
        mock_child.target.instance.runtime_properties = {
            'aws_resource_id': 'a'
        }

        mock_instance = MockCloudifyContext(
            'parent_id',
            deployment_id='deployment_id',
            properties={'a': 'b'},
            runtime_properties={'c': 'd'},
            relationships=[mock_child]
        )

        current_ctx.set(mock_instance)

        with self.assertRaises(NonRecoverableError):
            utils.get_parent_resource_id(mock_instance.instance)

        self.assertEqual(
            utils.get_parent_resource_id(mock_instance.instance, 'some_type'),
            'a'
        )

    def test_is_node_type(self):

        node = MagicMock()
        node.type_hierarchy = ['cloudify.nodes.Root', 'cloudify.nodes.Network']

        self.assertTrue(utils.is_node_type(node, 'cloudify.nodes.Root'))
        self.assertFalse(utils.is_node_type(node, 'cloudify.nodes.Compute'))

    def test_get_ancestor_resource_id_empty(self):
        mock_instance = MagicMock()
        mock_instance.relationships = []

        self.assertEqual(
            utils.get_ancestor_resource_id(
                mock_instance, 'cloudify.nodes.Root', raise_on_missing=False
            ), None
        )

        with self.assertRaises(NonRecoverableError):
            utils.get_ancestor_resource_id(
                mock_instance, 'cloudify.nodes.Root'
            )

    def _prepare_for_find_rel(self):

        mock_relation = MagicMock()
        mock_relation.type_hierarchy = 'cloudify.relationships.contained_in'
        mock_relation.target.instance.runtime_properties = {
            'aws_resource_id': 'b'
        }
        mock_relation.target.node.type_hierarchy = ['cloudify.nodes.Compute']
        mock_relation.target.node.id = 'cloud-sample-node'

        mock_child = MagicMock()
        mock_child.type_hierarchy = 'cloudify.relationships.contained_in'
        mock_child.target.instance.runtime_properties = {
            'aws_resource_id': 'a'
        }
        mock_child.target.node.type_hierarchy = ['cloudify.nodes.Root']
        mock_child.target.node.id = 'aws-sample-node'
        mock_child.target.instance.relationships = [mock_relation]

        mock_instance = MockCloudifyContext(
            'parent_id',
            deployment_id='deployment_id',
            properties={'a': 'b'},
            runtime_properties={'c': 'd'},
            relationships=[mock_child]
        )

        current_ctx.set(mock_instance)

        return mock_instance, mock_child

    def test_get_ancestor_resource_id(self):

        mock_instance, mock_child = self._prepare_for_find_rel()

        self.assertEqual(
            utils.get_ancestor_resource_id(
                mock_instance.instance, 'cloudify.nodes.Root'
            ), 'a'
        )

        self.assertEqual(
            utils.get_ancestor_resource_id(
                mock_instance.instance, 'cloudify.nodes.Compute'
            ), 'b'
        )

    def test_filter_boto_params(self):
        self.assertEqual(
            utils.filter_boto_params({'a': 'b', 'c': 'd', 'e': 'f', 'g': None},
                                     ['a', 'e', 'g'],),
            {'a': 'b', 'e': 'f'}
        )

        self.assertEqual(
            utils.filter_boto_params({'a': 'b', 'c': 'd', 'e': 'f', 'g': None},
                                     ['a', 'e', 'g'], True),
            {'a': 'b', 'e': 'f', 'g': None}
        )

    def test_find_rel_by_node_type(self):

        mock_instance, mock_child = self._prepare_for_find_rel()

        self.assertEqual(
            utils.find_rel_by_node_type(
                mock_instance.instance, 'cloudify.nodes.Network'
            ), None
        )

        self.assertEqual(
            utils.find_rel_by_node_type(
                mock_instance.instance, 'cloudify.nodes.Root'
            ), mock_child
        )

    def test_find_resource_id_by_type(self):

        mock_instance, mock_child = self._prepare_for_find_rel()

        self.assertEqual(
            utils.find_resource_id_by_type(
                mock_instance.instance, 'cloudify.nodes.Network'
            ), None
        )

        self.assertEqual(
            utils.find_resource_id_by_type(
                mock_instance.instance, 'cloudify.nodes.Root'
            ), 'a'
        )

    def test_add_resources_from_rels(self):

        mock_instance, mock_child = self._prepare_for_find_rel()

        self.assertEqual(
            utils.add_resources_from_rels(
                mock_instance.instance, 'cloudify.nodes.Network', []
            ), []
        )

        self.assertEqual(
            utils.add_resources_from_rels(
                mock_instance.instance, 'cloudify.nodes.Root', []
            ), ['a']
        )

    def test_find_rels_by_node_name(self):
        mock_instance, mock_child = self._prepare_for_find_rel()

        self.assertEqual(
            utils.find_rels_by_node_name(
                mock_instance.instance, 'aws'
            ), [mock_child]
        )

    def test_validate_arn(self):
        self.assertTrue(utils.validate_arn('arn:aws:11'))

    def test_get_uuid(self):
        self.assertTrue(utils.get_uuid())

    def test_region(self):
        # based on: https://docs.aws.amazon.com/
        # /AmazonRDS/latest/UserGuide/Concepts.RegionsAndAvailabilityZones.html
        check_cases = {
            "us-east-2": True,
            "us-east-1": True,
            "us-west-1": True,
            "us-west-2": True,
            "ap-south-1": True,
            "ap-northeast-3": True,
            "ap-northeast-2": True,
            "ap-southeast-1": True,
            "ap-southeast-2": True,
            "ap-northeast-1": True,
            "ca-central-1": True,
            "cn-north-1": True,
            "cn-northwest-1": True,
            "eu-central-1": True,
            "eu-west-1": True,
            "eu-west-2": True,
            "eu-west-3": True,
            "eu-north-1": True,
            "sa-east-1": True,
            "us-gov-east-1": True,
            "us-gov-west-1": True,
            "uk-kindom-one": False,
            "1-1-1": False,
            "a-b-c": False
        }
        for region in check_cases:
            if check_cases[region]:
                utils.check_region_name(region)
            else:
                with self.assertRaises(NonRecoverableError):
                    utils.check_region_name(region)

    def test_zone(self):
        check_cases = {
            "us-east-1e": True,
            "us-east-2a": True,
            "us-east-55": False,
            "us-1-1e": False,
            "1-west-1e": False,
        }
        for zone in check_cases:
            if check_cases[zone]:
                utils.check_availability_zone(zone)
            else:
                with self.assertRaises(NonRecoverableError):
                    utils.check_availability_zone(zone)

    def test_get_tags_list(self):
        a = [{'Key': 'foo',
              'Value': 'bar'}]
        b = [{'Key': 'baz',
              'Value': 1}]
        c = [{'Key': 'qux',
              'Value': True}]
        c.extend(c)
        out = utils.get_tags_list(a, b, c)
        self.assertTrue(
            all([isinstance(t['Value'], text_type) for t in out]))
        self.assertTrue(len(out) is 3)


if __name__ == '__main__':
    unittest.main()

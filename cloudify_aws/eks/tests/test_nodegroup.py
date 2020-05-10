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
from cloudify_aws.common.tests.test_base import (
    TestBase,
    mock_decorator
)
from cloudify_aws.eks.resources.node_group import EKSNodeGroup
from cloudify_aws.eks.resources import node_group
from cloudify_aws.common import constants


class TestEKSNodeGroup(TestBase):

    def setUp(self):
        super(TestEKSNodeGroup, self).setUp()

        self.node_group = EKSNodeGroup("ctx_node", resource_id=True,
                                       client=True, logger=None)
        self.mock_resource = patch(
            'cloudify_aws.common.decorators.aws_resource', mock_decorator
        )
        self.mock_resource.start()
        reload_module(node_group)

    def tearDown(self):
        self.mock_resource.stop()

        super(TestEKSNodeGroup, self).tearDown()

    def test_class_properties(self):
        effect = self.get_client_error_exception(name=node_group.RESOURCE_TYPE)
        self.node_group.client = \
            self.make_client_function('describe_nodegroup', side_effect=effect)
        self.assertIsNone(self.node_group.properties)

        response = \
            {
                node_group.NODEGROUP:
                    {
                        'nodegroupArn': 'test_node_group_arn',
                        'nodegroupName': 'test_node_group_name',
                        'clusterName': 'test_cluster_name',
                        'status': 'test_status',
                    },
            }

        self.node_group.describe_param = {
            node_group.CLUSTER_NAME: 'test_cluster_name',
            node_group.NODEGROUP_NAME: 'test_node_group_name'
        }
        self.node_group.client = \
            self.make_client_function('describe_nodegroup',
                                      return_value=response)

        self.assertEqual(
            self.node_group.properties[node_group.CLUSTER_NAME],
            'test_cluster_name'
        )
        self.assertEqual(
            self.node_group.properties[node_group.NODEGROUP_NAME],
            'test_node_group_name'
        )

    def test_class_status(self):
        response = {
            node_group.NODEGROUP: {
                'nodegroupArn': 'test_node_group_arn',
                'nodegroupName': 'test_node_group_name',
                'clusterName': 'test_cluster_name',
                'status': 'test_status',
            },
        }
        self.node_group.client = \
            self.make_client_function('describe_nodegroup',
                                      return_value=response)

        self.assertEqual(self.node_group.status, 'test_status')

    def test_class_status_empty(self):
        response = {node_group.NODEGROUP: {}}
        self.node_group.client = \
            self.make_client_function('describe_nodegroup',
                                      return_value=response)

        self.assertIsNone(self.node_group.status)

    def test_class_create(self):
        params = {
            node_group.CLUSTER_NAME: 'test_cluster_name',
            node_group.NODEGROUP_NAME: 'test_node_group_name'
        }
        response = \
            {
                node_group.NODEGROUP: {
                    'nodegroupArn': 'test_node_group_arn',
                    'nodegroupName': 'test_node_group_name',
                    'clusterName': 'test_cluster_name',
                    'status': 'test_status',
                },
            }
        self.node_group.client = self.make_client_function(
            'create_nodegroup', return_value=response)

        self.assertEqual(
            self.node_group.create(params)[node_group.NODEGROUP],
            response.get(node_group.NODEGROUP))

    def test_class_delete(self):
        params = {
            node_group.CLUSTER_NAME: 'test_cluster_name',
            node_group.NODEGROUP_NAME: 'test_node_group_name'
        }
        response = \
            {
                node_group.NODEGROUP: {
                    'nodegroupArn': 'test_node_group_arn',
                    'nodegroupName': 'test_node_group_name',
                    'clusterName': 'test_cluster_name',
                    'status': 'test_status',
                },
            }

        self.node_group.client = self.make_client_function(
            'delete_nodegroup', return_value=response)

        self.assertEqual(self.node_group.delete(params), response)

    def test_prepare(self):
        ctx = self.get_mock_ctx("NodeGroup")
        node_group.prepare(ctx, 'config')
        self.assertEqual(
            ctx.instance.runtime_properties['resource_config'],
            'config')

    def test_create(self):
        ctx = self.get_mock_ctx("NodeGroup")
        config = {
            node_group.CLUSTER_NAME: 'test_cluster_name',
            node_group.NODEGROUP_NAME: 'test_node_group_name'
        }
        iface = MagicMock()
        response = \
            {
                node_group.NODEGROUP: {
                    'nodegroupArn': 'test_node_group_arn',
                    'nodegroupName': 'test_node_group_name',
                    'clusterName': 'test_cluster_name',
                    'status': 'test_status',
                },
            }

        iface.create = self.mock_return(response)
        node_group.create(ctx, iface, config)
        self.assertEqual(
            ctx.instance.runtime_properties[constants.EXTERNAL_RESOURCE_ID],
            'test_node_group_name'
        )

    def test_delete(self):
        iface = MagicMock()
        ctx = self.get_mock_ctx("NodeGroup")
        node_group.delete(ctx, iface, {})
        self.assertTrue(iface.delete.called)


if __name__ == '__main__':
    unittest.main()

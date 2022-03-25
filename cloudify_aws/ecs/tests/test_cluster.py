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
from cloudify_aws.ecs.resources.cluster import ECSCluster
from cloudify_aws.ecs.resources import cluster
from cloudify_aws.common import constants


class TestECSCluster(TestBase):

    def setUp(self):
        super(TestECSCluster, self).setUp()

        self.cluster = ECSCluster("ctx_node", resource_id='test_cluster_name',
                                  client=True, logger=None)
        self.mock_resource = patch(
            'cloudify_aws.common.decorators.aws_resource', mock_decorator
        )
        self.mock_resource.start()
        reload_module(cluster)

    def tearDown(self):
        self.mock_resource.stop()

        super(TestECSCluster, self).tearDown()

    def test_class_properties(self):
        effect = self.get_client_error_exception(name=cluster.RESOURCE_TYPE)
        self.cluster.client = self.make_client_function(
            'describe_clusters', side_effect=effect)
        self.assertIsNone(self.cluster.properties)

        response = \
            {
                cluster.CLUSTERS: [
                    {
                        'clusterArn': 'test_cluster_arn',
                        'clusterName': 'test_cluster_name',
                        'status': 'test_status',
                        'registeredContainerInstancesCount': 1,
                        'runningTasksCount': 1,
                        'pendingTasksCount': 1,
                        'activeServicesCount': 1,
                        'statistics': [
                            {
                                'name': 'test_statistics_name',
                                'value': 'test_statistics_name_value'
                            },
                        ]
                    },
                ],
            }

        self.cluster.describe_cluster_filter = {
            cluster.CLUSTERS: [
                'test_cluster_name'
            ]
        }
        self.cluster.client = self.make_client_function('describe_clusters',
                                                        return_value=response)

        self.assertEqual(
            self.cluster.properties[cluster.CLUSTER_RESOURCE_NAME],
            'test_cluster_name'
        )

    def test_class_status(self):
        response = {
            cluster.CLUSTERS: [
                {
                    'clusterArn': 'test_cluster_arn',
                    'clusterName': 'test_cluster_name',
                    'status': 'test_status',
                    'registeredContainerInstancesCount': 1,
                    'runningTasksCount': 1,
                    'pendingTasksCount': 1,
                    'activeServicesCount': 1,
                    'statistics': [
                        {
                            'name': 'test_statistics_name',
                            'value': 'test_statistics_name_value'
                        },
                    ]
                },
            ],
        }
        self.cluster.client = self.make_client_function('describe_clusters',
                                                        return_value=response)

        self.assertEqual(self.cluster.status, 'test_status')

    def test_class_status_empty(self):
        response = {cluster.CLUSTERS: [{}]}
        self.cluster.client = self.make_client_function('describe_clusters',
                                                        return_value=response)

        self.assertIsNone(self.cluster.status)

    def test_class_create(self):
        params = {cluster.CLUSTER_RESOURCE_NAME: 'test_cluster_name'}
        response = \
            {
                cluster.CLUSTER: {
                    'clusterArn': 'test_cluster_arn',
                    'clusterName': 'test_cluster_name',
                    'status': 'test_cluster_status',
                    'registeredContainerInstancesCount': 1,
                    'runningTasksCount': 1,
                    'pendingTasksCount': 1,
                    'activeServicesCount': 1,
                    'statistics': [
                        {
                            'name': 'test_statistics_name',
                            'value': 'test_statistics_name'
                        },
                    ]
                }
            }
        self.cluster.client = self.make_client_function(
            'create_cluster', return_value=response)

        self.assertEqual(
            self.cluster.create(params)[cluster.CLUSTER],
            response.get(cluster.CLUSTER))

    def test_class_delete(self):
        params = {cluster.CLUSTER: 'test_cluster_name'}
        response = \
            {
                cluster.CLUSTER: {
                    'clusterArn': 'test_cluster_arn',
                    'clusterName': 'test_cluster_name',
                    'status': 'test_cluster_status',
                    'registeredContainerInstancesCount': 0,
                    'runningTasksCount': 0,
                    'pendingTasksCount': 0,
                    'activeServicesCount': 0,
                    'statistics': [
                        {
                            'name': 'test_statistics_name',
                            'value': 'test_statistics_name'
                        },
                    ]
                }
            }

        self.cluster.client = self.make_client_function(
            'delete_cluster', return_value=response)

        self.assertEqual(self.cluster.delete(params), response)

    def test_prepare(self):
        ctx = self.get_mock_ctx("Cluster")
        cluster.prepare(ctx, 'config')
        self.assertEqual(
            ctx.instance.runtime_properties['resource_config'],
            'config')

    def test_create(self):
        ctx = self.get_mock_ctx("Cluster")
        config = {cluster.CLUSTER_RESOURCE_NAME: 'test_cluster_name'}
        iface = MagicMock()
        response = \
            {
                cluster.CLUSTER: {
                    'clusterArn': 'test_cluster_arn',
                    'clusterName': 'test_cluster_name',
                    'status': 'test_cluster_status',
                    'registeredContainerInstancesCount': 1,
                    'runningTasksCount': 1,
                    'pendingTasksCount': 1,
                    'activeServicesCount': 1,
                    'statistics': [
                        {
                            'name': 'test_statistics_name',
                            'value': 'test_statistics_name'
                        },
                    ]
                }
            }

        iface.create = self.mock_return(response)
        cluster.create(ctx, iface, config)
        self.assertEqual(
            ctx.instance.runtime_properties[constants.EXTERNAL_RESOURCE_ID],
            'test_cluster_name'
        )

    def test_delete(self):
        iface = MagicMock()
        cluster.delete({}, iface, {})
        self.assertTrue(iface.delete.called)


if __name__ == '__main__':
    unittest.main()

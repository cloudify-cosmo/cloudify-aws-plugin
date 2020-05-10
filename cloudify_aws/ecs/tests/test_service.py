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

from cloudify_aws.common._compat import reload_module
from cloudify_aws.common.tests.test_base import (
    TestBase,
    mock_decorator
)

# Local imports
from cloudify_aws.ecs.resources.service import ECSService
from cloudify_aws.ecs.resources import service


class TestECSService(TestBase):

    def setUp(self):
        super(TestECSService, self).setUp()

        self.service = ECSService("ctx_node", resource_id=True,
                                  client=True, logger=None)
        self.mock_resource = patch(
            'cloudify_aws.common.decorators.aws_resource', mock_decorator
        )
        self.mock_resource.start()
        reload_module(service)

    def tearDown(self):
        self.mock_resource.stop()

        super(TestECSService, self).tearDown()

    def test_class_properties(self):
        effect = self.get_client_error_exception(name=service.RESOURCE_TYPE)
        self.service.client = self.make_client_function('describe_services',
                                                        side_effect=effect)
        self.assertIsNone(self.service.properties)

        response = {
            service.SERVICES: [
                {
                    'serviceArn': 'test_service_arn',
                    'serviceName': 'test_service_name',
                    'clusterArn': 'test_cluster_arn',
                    'status': 'test_status',
                    'desiredCount': 1,
                    'runningCount': 1,
                    'pendingCount': 1,
                },
            ],
        }

        self.service.describe_cluster_filter = {
            service.CLUSTER: 'test_cluster_name',
            service.SERVICES: ['test_service_name']

        }
        self.service.client = self.make_client_function('describe_services',
                                                        return_value=response)

        self.assertEqual(
            self.service.properties[service.SERVICE_RESOURCE],
            'test_service_name'
        )

    def test_class_status(self):
        response = {
            service.SERVICES: [
                {
                    'serviceArn': 'test_service_arn',
                    'serviceName': 'test_service_name',
                    'clusterArn': 'test_cluster_arn',
                    'status': 'test_status',
                    'desiredCount': 1,
                    'runningCount': 1,
                    'pendingCount': 1,
                },
            ],
        }
        self.service.client = self.make_client_function('describe_services',
                                                        return_value=response)

        self.assertEqual(self.service.status, 'test_status')

    def test_class_create(self):
        params = {service.CLUSTER: 'test_cluster_name',
                  service.SERVICE_RESOURCE: 'test_service_name',
                  'taskDefinition': 'test_task_definition_name'}
        response = {
            service.SERVICE: {
                'serviceArn': 'test_service_arn',
                'serviceName': 'test_service_name',
                'clusterArn': 'test_cluster_arn',
                'status': 'test_status',
                'desiredCount': 1,
                'runningCount': 1,
                'pendingCount': 1,
            }
        }
        self.service.client = self.make_client_function(
            'create_service', return_value=response)

        self.assertEqual(self.service.create(params)[service.SERVICE],
                         response.get(service.SERVICE))

    def test_class_delete(self):
        params = {service.CLUSTER: 'test_cluster_name',
                  service.SERVICE: 'test_service_name'}
        response = \
            {
                service.SERVICE: {
                    'clusterArn': 'test_cluster_arn',
                    'clusterName': 'test_cluster_name',
                    'status': 'test_cluster_status',
                    'registeredContainerInstancesCount': 1,
                    'desiredCount': '0',
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

        self.service.client = self.make_client_function(
            'delete_service', return_value=response
        )

        mock_update_service = getattr(self.service.client, 'update_service')
        mock_update_service.return_value = response
        self.assertEqual(self.service.delete(params), response)

    def test_create(self):
        ctx = self.get_mock_ctx("Service")
        config = {service.CLUSTER: 'test_cluster_name',
                  service.SERVICE_RESOURCE: 'test_service_name',
                  'taskDefinition': 'test_task_definition_name'}
        iface = MagicMock()
        response = {
            service.SERVICE: {
                'serviceArn': 'test_service_arn',
                'serviceName': 'test_service_name',
                'clusterArn': 'test_cluster_arn',
                'status': 'test_status',
                'desiredCount': 1,
                'runningCount': 1,
                'pendingCount': 1,
            }
        }

        iface.create = self.mock_return(response)
        service.create(ctx, iface, config)
        self.assertEqual(
            ctx.instance.runtime_properties[service.SERVICE],
            'test_service_name'
        )

    def test_prepare(self):
        ctx = self.get_mock_ctx("Service")
        service.prepare(ctx, 'config')
        self.assertEqual(
            ctx.instance.runtime_properties['resource_config'],
            'config')

    @patch('cloudify_aws.ecs.resources.service.get_cluster_name',
           return_value='test_cluster_name')
    def test_delete(self, mock_function):
        iface = MagicMock()
        ctx = self.get_mock_ctx("Service")
        service.delete(ctx, iface, {})
        self.assertTrue(iface.delete.called)


if __name__ == '__main__':
    unittest.main()

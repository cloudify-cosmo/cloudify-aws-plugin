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
from cloudify_aws.ecs.resources.task_definition import ECSTaskDefinition
from cloudify_aws.ecs.resources import task_definition
from cloudify_aws.common import constants


class TestECSTaskDefinition(TestBase):

    def setUp(self):
        super(TestECSTaskDefinition, self).setUp()

        self.task_definition = ECSTaskDefinition(
            "ctx_node", resource_id=True, client=True, logger=None)

        self.mock_resource = patch(
            'cloudify_aws.common.decorators.aws_resource', mock_decorator
        )
        self.mock_resource.start()
        reload_module(task_definition)

    def tearDown(self):
        self.mock_resource.stop()
        super(TestECSTaskDefinition, self).tearDown()

    def test_class_properties(self):
        effect = self.get_client_error_exception(
            name=task_definition.RESOURCE_TYPE)

        self.task_definition.client = \
            self.make_client_function('describe_task_definition',
                                      side_effect=effect)
        self.assertIsNone(self.task_definition.properties)

        response = \
            {
                task_definition.TASK_DEFINITION: {
                    'taskDefinitionArn': 'test_task_definition_arn',
                    'containerDefinitions': [
                        {
                            'name': 'test_task_name',
                            'image': 'test_task_image',
                            'cpu': 1,
                            'memory': 123,
                            'memoryReservation': 1,
                            'hostname': 'test_hostname',
                            'user': 'test_user',
                            'workingDirectory': 'test',
                            'disableNetworking': True,
                            'privileged': True,
                            'readonlyRootFilesystem': True,
                        },
                    ],
                    'family': 'test_task_family',
                    'taskRoleArn': 'test_task_role_arn',
                    'cpu': 'test_task_cpu',
                    'memory': 'test_task_memory',
                    'status': 'test_status',
                }
            }

        self.task_definition.describe_cluster_filter = {
            task_definition.TASK_DEFINITION: 'test_task_family'
        }
        self.task_definition.client = self.make_client_function(
            'describe_task_definition', return_value=response)

        self.assertEqual(
            self.task_definition.properties[
                task_definition.TASK_DEFINITION_FAMILY],
            'test_task_family'
        )

    def test_class_status(self):
        response = \
            {
                task_definition.TASK_DEFINITION: {
                    'taskDefinitionArn': 'test_task_definition_arn',
                    'containerDefinitions': [
                        {
                            'name': 'test_task_name',
                            'image': 'test_task_image',
                            'cpu': 1,
                            'memory': 123,
                            'memoryReservation': 1,
                            'hostname': 'test_hostname',
                            'user': 'test_user',
                            'workingDirectory': 'test',
                            'disableNetworking': True,
                            'privileged': True,
                            'readonlyRootFilesystem': True,
                        },
                    ],
                    'family': 'test_task_family',
                    'taskRoleArn': 'test_task_role_arn',
                    'cpu': 'test_task_cpu',
                    'memory': 'test_task_memory',
                    'status': 'test_status',
                }
            }

        self.task_definition.client = \
            self.make_client_function('describe_task_definition',
                                      return_value=response)

        self.assertEqual(self.task_definition.status, 'test_status')

    def test_class_status_empty(self):
        response = {task_definition.TASK_DEFINITION: {}}

        self.task_definition.client = \
            self.make_client_function('describe_task_definition',
                                      return_value=response)

        self.assertIsNone(self.task_definition.status)

    def test_class_create(self):
        params = {
            task_definition.TASK_DEFINITION_FAMILY:
                'test_task_family',
            task_definition.TASK_DEFINITION: {
                'taskDefinitionArn': 'test_task_definition_arn',
                'containerDefinitions': [
                    {
                        'name': 'test_task_name',
                        'image': 'test_task_image',
                        'cpu': 1,
                        'memory': 123,
                        'memoryReservation': 1,
                        'hostname': 'test_hostname',
                        'user': 'test_user',
                        'workingDirectory': 'test',
                        'disableNetworking': True,
                        'privileged': True,
                        'readonlyRootFilesystem': True,
                    },
                ],
                'family': 'test_task_family',
                'taskRoleArn': 'test_task_role_arn',
                'cpu': 'test_task_cpu',
                'memory': 'test_task_memory',
                'status': 'test_status',
            }
        }
        response = \
            {
                task_definition.TASK_DEFINITION: {
                    'taskDefinitionArn': 'test_task_definition_arn',
                    'containerDefinitions': [
                        {
                            'name': 'test_task_name',
                            'image': 'test_task_image',
                            'cpu': 1,
                            'memory': 123,
                            'memoryReservation': 1,
                            'hostname': 'test_hostname',
                            'user': 'test_user',
                            'workingDirectory': 'test',
                            'disableNetworking': True,
                            'privileged': True,
                            'readonlyRootFilesystem': True,
                        },
                    ],
                    'family': 'test_task_family',
                    'taskRoleArn': 'test_task_role_arn',
                    'cpu': 'test_task_cpu',
                    'memory': 'test_task_memory',
                    'status': 'test_status',
                }
            }
        self.task_definition.client = self.make_client_function(
            'register_task_definition', return_value=response)

        self.assertEqual(
            self.task_definition.create(
                params)[task_definition.TASK_DEFINITION],
            response.get(task_definition.TASK_DEFINITION))

    def test_class_delete(self):
        params = {
            task_definition.TASK_DEFINITION:
                'test_task_family'
        }
        response = \
            {
                task_definition.TASK_DEFINITION: {
                    'taskDefinitionArn': 'test_task_definition_arn',
                    'containerDefinitions': [
                        {
                            'name': 'test_task_name',
                            'image': 'test_task_image',
                            'cpu': 1,
                            'memory': 123,
                            'memoryReservation': 1,
                            'hostname': 'test_hostname',
                            'user': 'test_user',
                            'workingDirectory': 'test',
                            'disableNetworking': True,
                            'privileged': True,
                            'readonlyRootFilesystem': True,
                        },
                    ],
                    'family': 'test_task_family',
                    'taskRoleArn': 'test_task_role_arn',
                    'cpu': 'test_task_cpu',
                    'memory': 'test_task_memory',
                    'status': 'test_status',
                }
            }
        self.task_definition.client = self.make_client_function(
            'deregister_task_definition', return_value=response)

        self.assertEqual(self.task_definition.delete(params),
                         response.get(task_definition.TASK_DEFINITION))

    def test_prepare(self):
        ctx = self.get_mock_ctx("TaskDefinition")
        task_definition.prepare(ctx, 'config')
        self.assertEqual(
            ctx.instance.runtime_properties['resource_config'],
            'config')

    def test_create(self):
        ctx = self.get_mock_ctx("TaskDefinition")
        config = {
            task_definition.TASK_DEFINITION_FAMILY:
                'test_task_family',
            task_definition.TASK_DEFINITION: {
                'taskDefinitionArn': 'test_task_definition_arn',
                'containerDefinitions': [
                    {
                        'name': 'test_task_name',
                        'image': 'test_task_image',
                        'cpu': 1,
                        'memory': 123,
                        'memoryReservation': 1,
                        'hostname': 'test_hostname',
                        'user': 'test_user',
                        'workingDirectory': 'test',
                        'disableNetworking': True,
                        'privileged': True,
                        'readonlyRootFilesystem': True,
                    },
                ],
                'family': 'test_task_family',
                'taskRoleArn': 'test_task_role_arn',
                'cpu': 'test_task_cpu',
                'memory': 'test_task_memory',
                'status': 'test_status',
            }
        }
        iface = MagicMock()
        response = \
            {
                task_definition.TASK_DEFINITION: {
                    'taskDefinitionArn': 'test_task_definition_arn',
                    'containerDefinitions': [
                        {
                            'name': 'test_task_name',
                            'image': 'test_task_image',
                            'cpu': 1,
                            'memory': 123,
                            'memoryReservation': 1,
                            'hostname': 'test_hostname',
                            'user': 'test_user',
                            'workingDirectory': 'test',
                            'disableNetworking': True,
                            'privileged': True,
                            'readonlyRootFilesystem': True,
                        },
                    ],
                    'family': 'test_task_family',
                    'taskRoleArn': 'test_task_role_arn',
                    'cpu': 'test_task_cpu',
                    'memory': 'test_task_memory',
                    'status': 'test_status',
                }
            }

        iface.create = self.mock_return(response)
        task_definition.create(ctx, iface, config)
        self.assertEqual(
            ctx.instance.runtime_properties[constants.EXTERNAL_RESOURCE_ID],
            'test_task_family'
        )

    def test_delete(self):
        iface = MagicMock()
        ctx = self.get_mock_ctx("TaskDefinition")
        task_definition.delete(ctx, iface, {})
        self.assertTrue(iface.delete.called)


if __name__ == '__main__':
    unittest.main()

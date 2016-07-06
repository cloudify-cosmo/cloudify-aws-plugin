########
# Copyright (c) 2015 GigaSpaces Technologies Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
#    * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    * See the License for the specific language governing permissions and
#    * limitations under the License.

# Stdlib imports

# Third party imports
import testtools
from mock import patch, Mock

# Cloudify imports
from cloudify.exceptions import NonRecoverableError

# This package imports
from cloudify_aws import constants
from cloudify_aws.ecs import service
from cloudify_aws.ecs.tests import (
    configure_mock_connection,
    make_node_context,
)


class FakeArnGetter(object):
    def __init__(self, task='task_arn', cluster='cluster_arn'):
        self.task_return = task
        self.cluster_return = cluster

    def __call__(self, relationships, from_relationship):
        if 'task' in from_relationship:
            return self.task_return
        elif 'cluster' in from_relationship:
            return self.cluster_return


class TestService(testtools.TestCase):

    def setUp(self):
        super(TestService, self).setUp()

    @patch('cloudify_aws.ecs.service.EC2ConnectionClient')
    @patch('cloudify_aws.ecs.service.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_get_relationship_target_not_present(self,
                                                 mock_ctx,
                                                 mock_ctx2,
                                                 mock_ctx3,
                                                 mock_conn):
        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            context.instance = mock_ctx.instance
            context.instance.relationships = []
        relationship = Mock()
        relationship.type = 'notright'
        relationships = [relationship]

        intended_relationship = 'right'

        self.assertIsNone(service.Service().get_relationship_target(
            relationships,
            intended_relationship,
        ))

    @patch('cloudify_aws.ecs.service.EC2ConnectionClient')
    @patch('cloudify_aws.ecs.service.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_get_relationship_target_present(self,
                                             mock_ctx,
                                             mock_ctx2,
                                             mock_ctx3,
                                             mock_conn):
        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            context.instance = mock_ctx.instance
            context.instance.relationships = []
        relationship = Mock()
        relationship.type = 'right'
        relationship.target = 'hello'
        relationships = [relationship]

        intended_relationship = 'right'

        self.assertEqual(
            service.Service().get_relationship_target(
                relationships,
                intended_relationship,
            ),
            relationship.target,
        )

    @patch('cloudify_aws.ecs.service.EC2ConnectionClient')
    @patch('cloudify_aws.ecs.service.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_get_relationship_target_multiple(self,
                                              mock_ctx,
                                              mock_ctx2,
                                              mock_ctx3,
                                              mock_conn):
        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            context.instance = mock_ctx.instance
            context.instance.relationships = []
        relationship = Mock()
        relationship.type = 'right'
        relationship.target = 'hello'

        wrong_relationship = Mock()
        relationships = [
            wrong_relationship,
            relationship,
            wrong_relationship,
        ]

        intended_relationship = 'right'

        self.assertEqual(
            service.Service().get_relationship_target(
                relationships,
                intended_relationship,
            ),
            relationship.target,
        )

    @patch('cloudify_aws.ecs.service.Service.get_relationship_target')
    @patch('cloudify_aws.ecs.service.EC2ConnectionClient')
    @patch('cloudify_aws.ecs.service.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_get_target_attribute_no_target(self,
                                            mock_ctx,
                                            mock_ctx2,
                                            mock_ctx3,
                                            mock_conn,
                                            mock_get_target):
        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            context.instance = mock_ctx.instance
            context.instance.relationships = []
        mock_get_target.return_value = None
        relationships = ['something']
        from_relationship = 'this one'
        desired_attribute = 'right attribute'

        self.assertIsNone(service.Service().get_target_attribute(
            relationships,
            from_relationship,
            desired_attribute,
        ))

    @patch('cloudify_aws.ecs.service.Service.get_relationship_target')
    @patch('cloudify_aws.ecs.service.EC2ConnectionClient')
    @patch('cloudify_aws.ecs.service.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_get_target_attribute_missing(self,
                                          mock_ctx,
                                          mock_ctx2,
                                          mock_ctx3,
                                          mock_conn,
                                          mock_get_target):
        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            context.instance = mock_ctx.instance
            context.instance.relationships = []
        no_runtime = Mock()
        no_runtime.instance.runtime_properties = {}
        mock_get_target.return_value = no_runtime
        relationships = ['something']
        from_relationship = 'this one'
        desired_attribute = 'right attribute'

        self.assertIsNone(service.Service().get_target_attribute(
            relationships,
            from_relationship,
            desired_attribute,
        ))

    @patch('cloudify_aws.ecs.service.Service.get_relationship_target')
    @patch('cloudify_aws.ecs.service.EC2ConnectionClient')
    @patch('cloudify_aws.ecs.service.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_get_target_attribute_success(self,
                                          mock_ctx,
                                          mock_ctx2,
                                          mock_ctx3,
                                          mock_conn,
                                          mock_get_target):
        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            context.instance = mock_ctx.instance
            context.instance.relationships = []
        expected = 'found'
        runtime = Mock()
        runtime.instance.runtime_properties = {
            'right attribute': expected,
        }
        mock_get_target.return_value = runtime
        relationships = ['something']
        from_relationship = 'this one'
        desired_attribute = 'right attribute'

        self.assertEqual(
            service.Service().get_target_attribute(
                relationships,
                from_relationship,
                desired_attribute,
            ),
            expected,
        )

    @patch('cloudify_aws.ecs.service.Service.get_relationship_target')
    @patch('cloudify_aws.ecs.service.EC2ConnectionClient')
    @patch('cloudify_aws.ecs.service.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_get_target_property_no_target(self,
                                           mock_ctx,
                                           mock_ctx2,
                                           mock_ctx3,
                                           mock_conn,
                                           mock_get_target):
        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            context.instance = mock_ctx.instance
            context.instance.relationships = []
        mock_get_target.return_value = None
        relationships = ['something']
        from_relationship = 'this one'
        desired_attribute = 'right attribute'

        self.assertIsNone(service.Service().get_target_property(
            relationships,
            from_relationship,
            desired_attribute,
        ))

    @patch('cloudify_aws.ecs.service.Service.get_relationship_target')
    @patch('cloudify_aws.ecs.service.EC2ConnectionClient')
    @patch('cloudify_aws.ecs.service.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_get_target_property_missing(self,
                                         mock_ctx,
                                         mock_ctx2,
                                         mock_ctx3,
                                         mock_conn,
                                         mock_get_target):
        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            context.instance = mock_ctx.instance
            context.instance.relationships = []
        no_properties = Mock()
        no_properties.node.properties = {}
        mock_get_target.return_value = no_properties
        relationships = ['something']
        from_relationship = 'this one'
        desired_attribute = 'right attribute'

        self.assertIsNone(service.Service().get_target_property(
            relationships,
            from_relationship,
            desired_attribute,
        ))

    @patch('cloudify_aws.ecs.service.Service.get_relationship_target')
    @patch('cloudify_aws.ecs.service.EC2ConnectionClient')
    @patch('cloudify_aws.ecs.service.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_get_target_property_success(self,
                                         mock_ctx,
                                         mock_ctx2,
                                         mock_ctx3,
                                         mock_conn,
                                         mock_get_target):
        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            context.instance = mock_ctx.instance
            context.instance.relationships = []
        expected = 'found'
        properties = Mock()
        properties.node.properties = {
            'right attribute': expected,
        }
        mock_get_target.return_value = properties
        relationships = ['something']
        from_relationship = 'this one'
        desired_attribute = 'right attribute'

        self.assertEqual(
            service.Service().get_target_property(
                relationships,
                from_relationship,
                desired_attribute,
            ),
            expected,
        )

    @patch('cloudify_aws.ecs.service.Service.get_target_attribute')
    @patch('cloudify_aws.ecs.service.EC2ConnectionClient')
    @patch('cloudify_aws.ecs.service.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_get_arn(self,
                     mock_ctx,
                     mock_ctx2,
                     mock_ctx3,
                     mock_conn,
                     mock_get_attribute):
        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            context.instance = mock_ctx.instance
            context.instance.relationships = []
        mock_get_attribute.return_value = 'my_arn'
        relationships = ['something']
        from_relationship = 'this one'
        desired_attribute = constants.EXTERNAL_RESOURCE_ID

        self.assertEqual(
            service.Service().get_arn(relationships, from_relationship),
            mock_get_attribute.return_value,
        )

        mock_get_attribute.assert_called_once_with(
            relationships=relationships,
            from_relationship=from_relationship,
            desired_attribute=desired_attribute,
        )

    @patch('cloudify_aws.ecs.service.Service.get_target_property')
    @patch('cloudify_aws.ecs.service.EC2ConnectionClient')
    @patch('cloudify_aws.ecs.service.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_get_related_elb_name(self,
                                  mock_ctx,
                                  mock_ctx2,
                                  mock_ctx3,
                                  mock_conn,
                                  mock_get_property):
        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            context.instance = mock_ctx.instance
            context.instance.relationships = []
        mock_get_property.return_value = 'my_elb'
        relationships = ['something']
        from_relationship = constants.SERVICE_LOAD_BALANCER_RELATIONSHIP
        desired_attribute = 'elb_name'

        self.assertEqual(
            service.Service().get_related_elb_name(relationships),
            mock_get_property.return_value,
        )

        mock_get_property.assert_called_once_with(
            relationships=relationships,
            from_relationship=from_relationship,
            desired_property=desired_attribute,
        )

    @patch('cloudify_aws.ecs.service.Service.get_target_attribute')
    @patch('cloudify_aws.ecs.service.EC2ConnectionClient')
    @patch('cloudify_aws.ecs.service.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_get_container_instance_count(self,
                                          mock_ctx,
                                          mock_ctx2,
                                          mock_ctx3,
                                          mock_conn,
                                          mock_get_attribute):
        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            context.instance = mock_ctx.instance
            context.instance.relationships = []
        mock_get_attribute.return_value = 42
        relationships = ['something']
        from_relationship = constants.SERVICE_CLUSTER_RELATIONSHIP
        desired_attribute = 'instances'

        self.assertEqual(
            service.Service().get_container_instance_count(
                relationships,
            ),
            mock_get_attribute.return_value,
        )

        mock_get_attribute.assert_called_once_with(
            relationships=relationships,
            from_relationship=from_relationship,
            desired_attribute=desired_attribute,
        )

    @patch('cloudify_aws.ecs.service.Service.get_target_attribute')
    @patch('cloudify_aws.ecs.service.EC2ConnectionClient')
    @patch('cloudify_aws.ecs.service.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_get_task_container_names(self,
                                      mock_ctx,
                                      mock_ctx2,
                                      mock_ctx3,
                                      mock_conn,
                                      mock_get_attribute):
        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            context.instance = mock_ctx.instance
            context.instance.relationships = []
        mock_get_attribute.return_value = ['groucho', 'harpo']
        relationships = ['something']
        from_relationship = constants.SERVICE_TASK_RELATIONSHIP
        desired_attribute = 'container_names'

        self.assertEqual(
            service.Service().get_task_container_names(
                relationships,
            ),
            mock_get_attribute.return_value,
        )

        mock_get_attribute.assert_called_once_with(
            relationships=relationships,
            from_relationship=from_relationship,
            desired_attribute=desired_attribute,
        )

    @patch('cloudify_aws.ecs.service.Service.get_container_instance_count')
    @patch('cloudify_aws.ecs.service.EC2ConnectionClient')
    @patch('cloudify_aws.ecs.service.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_instances_none_ready(self,
                                  mock_ctx,
                                  mock_ctx2,
                                  mock_ctx3,
                                  mock_conn,
                                  mock_container_count):
        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            make_node_context(
                context,
                node='ECSService',
                properties={
                    'name': 'myservice',
                },
            )
            context.instance = mock_ctx.instance
            context.instance.relationships = []
            context.operation = mock_ctx.operation
        mock_container_count.return_value = None

        client = configure_mock_connection(mock_conn)

        service.Service().create()

        mock_ctx.operation.retry.assert_called_once_with(
            'Waiting for cluster to have available instances.'
        )
        assert client.create_service.call_count == 0

    @patch('cloudify_aws.ecs.service.Service.get_container_instance_count')
    @patch('cloudify_aws.ecs.service.EC2ConnectionClient')
    @patch('cloudify_aws.ecs.service.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_instances_not_yet_ready(self,
                                     mock_ctx,
                                     mock_ctx2,
                                     mock_ctx3,
                                     mock_conn,
                                     mock_container_count):
        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            make_node_context(
                context,
                node='ECSService',
                properties={
                    'name': 'myservice',
                },
            )
            context.instance = mock_ctx.instance
            context.instance.relationships = []
            context.operation = mock_ctx.operation
        mock_container_count.return_value = []

        client = configure_mock_connection(mock_conn)

        service.Service().create()

        mock_ctx.operation.retry.assert_called_once_with(
            'Waiting for cluster to have available instances.'
        )
        assert client.create_service.call_count == 0

    @patch('cloudify_aws.ecs.service.Service.get_arn')
    @patch('cloudify_aws.ecs.service.Service.get_container_instance_count')
    @patch('cloudify_aws.ecs.service.EC2ConnectionClient')
    @patch('cloudify_aws.ecs.service.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_no_task(self,
                     mock_ctx,
                     mock_ctx2,
                     mock_ctx3,
                     mock_conn,
                     mock_container_count,
                     mock_arn_getter):
        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            make_node_context(
                context,
                node='ECSService',
                properties={
                    'name': 'service',
                },
            )
            context.instance = mock_ctx.instance
            context.instance.relationships = []
        mock_container_count.return_value = ['con1']

        mock_arn_getter.side_effect = FakeArnGetter(task=None)

        client = configure_mock_connection(mock_conn)
        client.describe_clusters.return_value = {
            'clusters': [{'clusterArn': 'returned'}],
        }

        self.assertRaises(
            NonRecoverableError,
            service.Service().create,
        )

        assert client.create_service.call_count == 0

    @patch('cloudify_aws.ecs.service.Service.get_arn')
    @patch('cloudify_aws.ecs.service.Service.get_container_instance_count')
    @patch('cloudify_aws.ecs.service.EC2ConnectionClient')
    @patch('cloudify_aws.ecs.service.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_no_cluster(self,
                        mock_ctx,
                        mock_ctx2,
                        mock_ctx3,
                        mock_conn,
                        mock_container_count,
                        mock_arn_getter):
        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            make_node_context(
                context,
                node='ECSService',
                properties={
                    'name': 'service',
                },
            )
            context.instance = mock_ctx.instance
            context.instance.relationships = []
        mock_container_count.return_value = ['con1']

        mock_arn_getter.side_effect = FakeArnGetter(cluster=None)

        client = configure_mock_connection(mock_conn)
        client.describe_clusters.return_value = {
            'clusters': [],
        }
        client.create_service.return_value = {
            'service': {'serviceArn': 'arn'},
        }

        self.assertRaises(
            NonRecoverableError,
            service.Service().create,
        )

        assert client.create_service.call_count == 0

    @patch('cloudify_aws.ecs.service.Service.get_related_elb_name')
    @patch('cloudify_aws.ecs.service.Service.get_arn')
    @patch('cloudify_aws.ecs.service.Service.get_container_instance_count')
    @patch('cloudify_aws.ecs.service.EC2ConnectionClient')
    @patch('cloudify_aws.ecs.service.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_no_elb(self,
                    mock_ctx,
                    mock_ctx2,
                    mock_ctx3,
                    mock_conn,
                    mock_container_count,
                    mock_arn_getter,
                    mock_get_elb):
        task_arn = 'task_arn'
        cluster_arn = 'cluster_arn'
        service_name = 'myservice'
        desired_count = 4
        service_arn = 'service_arn'

        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            make_node_context(
                context,
                node='ECSService',
                properties={
                    'name': service_name,
                    'desired_count': desired_count,
                },
            )
            context.instance = mock_ctx.instance
            context.instance.relationships = []
        mock_get_elb.return_value = None
        mock_container_count.return_value = ['con1']

        mock_arn_getter.side_effect = FakeArnGetter(
            task=task_arn,
            cluster=cluster_arn,
        )

        client = configure_mock_connection(mock_conn)
        client.create_service.return_value = {
            'service': {
                'serviceArn': service_arn,
            },
        }
        client.describe_clusters.return_value = {
            'clusters': [{'clusterArn': cluster_arn}],
        }

        service.Service().create()

        client.create_service.assert_called_once_with(
            cluster=cluster_arn,
            serviceName=service_name,
            desiredCount=desired_count,
            taskDefinition=task_arn,
        )

    @patch('cloudify_aws.ecs.service.Service.get_task_container_names')
    @patch('cloudify_aws.ecs.service.Service.get_related_elb_name')
    @patch('cloudify_aws.ecs.service.Service.get_arn')
    @patch('cloudify_aws.ecs.service.Service.get_container_instance_count')
    @patch('cloudify_aws.ecs.service.EC2ConnectionClient')
    @patch('cloudify_aws.ecs.service.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_elb_no_containers(self,
                               mock_ctx,
                               mock_ctx2,
                               mock_ctx3,
                               mock_conn,
                               mock_container_count,
                               mock_arn_getter,
                               mock_get_elb,
                               mock_get_container_names):
        task_arn = 'task_arn'
        cluster_arn = 'cluster_arn'
        service_name = 'myservice'
        desired_count = 4

        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            make_node_context(
                context,
                node='ECSService',
                properties={
                    'name': service_name,
                    'desired_count': desired_count,
                },
            )
            context.instance = mock_ctx.instance
            context.instance.relationships = []
        mock_get_elb.return_value = 'happy_elb'
        mock_container_count.return_value = ['con1']
        mock_get_container_names.return_value = []

        mock_arn_getter.side_effect = FakeArnGetter(
            task=task_arn,
            cluster=cluster_arn,
        )

        client = configure_mock_connection(mock_conn)
        client.describe_clusters.return_value = {
            'clusters': [{'clusterArn': 'returned'}],
        }

        self.assertRaises(
            NonRecoverableError,
            service.Service().create,
        )

        assert client.create_service.call_count == 0

    @patch('cloudify_aws.ecs.service.Service.get_task_container_names')
    @patch('cloudify_aws.ecs.service.Service.get_related_elb_name')
    @patch('cloudify_aws.ecs.service.Service.get_arn')
    @patch('cloudify_aws.ecs.service.Service.get_container_instance_count')
    @patch('cloudify_aws.ecs.service.EC2ConnectionClient')
    @patch('cloudify_aws.ecs.service.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_elb_many_containers(self,
                                 mock_ctx,
                                 mock_ctx2,
                                 mock_ctx3,
                                 mock_conn,
                                 mock_container_count,
                                 mock_arn_getter,
                                 mock_get_elb,
                                 mock_get_container_names):
        task_arn = 'task_arn'
        cluster_arn = 'cluster_arn'
        service_name = 'myservice'
        desired_count = 4

        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            make_node_context(
                context,
                node='ECSService',
                properties={
                    'name': service_name,
                    'desired_count': desired_count,
                },
            )
            context.instance = mock_ctx.instance
            context.instance.relationships = []
        mock_get_elb.return_value = 'happy_elb'
        mock_container_count.return_value = ['con1']
        mock_get_container_names.return_value = ['groucho', 'harpo']

        mock_arn_getter.side_effect = FakeArnGetter(
            task=task_arn,
            cluster=cluster_arn,
        )

        client = configure_mock_connection(mock_conn)
        client.describe_clusters.return_value = {
            'clusters': [{'clusterArn': 'returned'}],
        }

        self.assertRaises(
            NonRecoverableError,
            service.Service().create,
        )

        assert client.create_service.call_count == 0

    @patch('cloudify_aws.ecs.service.Service.get_task_container_names')
    @patch('cloudify_aws.ecs.service.Service.get_related_elb_name')
    @patch('cloudify_aws.ecs.service.Service.get_arn')
    @patch('cloudify_aws.ecs.service.Service.get_container_instance_count')
    @patch('cloudify_aws.ecs.service.EC2ConnectionClient')
    @patch('cloudify_aws.ecs.service.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_elb(self,
                 mock_ctx,
                 mock_ctx2,
                 mock_ctx3,
                 mock_conn,
                 mock_container_count,
                 mock_arn_getter,
                 mock_get_elb,
                 mock_get_container_names):
        elb_name = 'happy_elb'
        container_name = 'groucho'
        task_arn = 'task_arn'
        cluster_arn = 'cluster_arn'
        service_name = 'myservice'
        desired_count = 4
        service_arn = 'service_arn'
        listening_port = 42
        elb_management_role = 'PHB'

        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            make_node_context(
                context,
                node='ECSService',
                properties={
                    'name': service_name,
                    'desired_count': desired_count,
                    'container_listening_port': listening_port,
                    'lb_management_role': elb_management_role,
                },
            )
            context.instance = mock_ctx.instance
            context.instance.relationships = []

        mock_get_elb.return_value = elb_name
        mock_container_count.return_value = ['con1']
        mock_get_container_names.return_value = [container_name]

        mock_arn_getter.side_effect = FakeArnGetter(
            task=task_arn,
            cluster=cluster_arn,
        )

        client = configure_mock_connection(mock_conn)
        client.create_service.return_value = {
            'service': {
                'serviceArn': service_arn,
            },
        }
        client.describe_clusters.return_value = {
            'clusters': [{'clusterArn': cluster_arn}],
        }

        service.Service().create()

        client.create_service.assert_called_once_with(
            cluster=cluster_arn,
            serviceName=service_name,
            desiredCount=desired_count,
            taskDefinition=task_arn,
            role=elb_management_role,
            loadBalancers=[
                {
                    'loadBalancerName': elb_name,
                    'containerName': container_name,
                    'containerPort': listening_port,
                },
            ],
        )

    @patch('cloudify_aws.ecs.service.Service.get_arn')
    @patch('cloudify_aws.ecs.service.EC2ConnectionClient')
    @patch('cloudify_aws.ecs.service.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_delete_success(self,
                            mock_ctx,
                            mock_ctx2,
                            mock_ctx3,
                            mock_conn,
                            mock_arn_getter):
        cluster_arn = 'mycluster'
        service_name = 'myservice'
        service_arn = 'service_arn'

        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            make_node_context(
                context,
                node='ECSService',
                properties={
                    'name': service_name,
                },
                runtime_properties={
                    constants.EXTERNAL_RESOURCE_ID: service_arn,
                },
            )
            context.instance = mock_ctx.instance
            context.instance.relationships = []
        mock_arn_getter.side_effect = FakeArnGetter(
            cluster=cluster_arn,
        )

        client = configure_mock_connection(mock_conn)
        client.describe_clusters.return_value = {
            'clusters': [{'clusterArn': cluster_arn}],
        }

        service.Service().delete()

        client.update_service.assert_called_once_with(
            service=service_arn,
            cluster=cluster_arn,
            desiredCount=0,
        )
        client.delete_service.assert_called_once_with(
            service=service_arn,
            cluster=cluster_arn,
        )

    @patch('cloudify_aws.ecs.service.EC2ConnectionClient')
    @patch('cloudify_aws.ecs.service.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_get_service_arn_too_many_services_found(self,
                                                     mock_ctx,
                                                     mock_ctx2,
                                                     mock_ctx3,
                                                     mock_conn):
        name = 'something'
        cluster_arn = 'test'
        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            context.instance = mock_ctx.instance
            context.instance.relationships = []
        mock_client = configure_mock_connection(mock_conn)

        mock_client.describe_services.return_value = {'services': [
            {'serviceName': 1},
            {'serviceName': 2},
            {'serviceName': 3},
        ]}

        self.assertRaises(
            NonRecoverableError,
            service.Service().get_service_arn,
            name=name,
            cluster_arn=cluster_arn,
        )

        mock_client.describe_services.assert_called_once_with(
            cluster=cluster_arn,
            services=[name],
        )

    @patch('cloudify_aws.ecs.service.EC2ConnectionClient')
    @patch('cloudify_aws.ecs.service.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_get_service_arn_no_services_found(self,
                                               mock_ctx,
                                               mock_ctx2,
                                               mock_ctx3,
                                               mock_conn):
        name = 'something'
        cluster_arn = 'test'
        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            context.instance = mock_ctx.instance
            context.instance.relationships = []
        mock_client = configure_mock_connection(mock_conn)

        mock_client.describe_services.return_value = {'services': []}

        self.assertRaises(
            NonRecoverableError,
            service.Service().get_service_arn,
            name=name,
            cluster_arn=cluster_arn,
        )

        mock_client.describe_services.assert_called_once_with(
            cluster=cluster_arn,
            services=[name],
        )

    @patch('cloudify_aws.ecs.service.EC2ConnectionClient')
    @patch('cloudify_aws.ecs.service.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_get_service_arn(self,
                             mock_ctx,
                             mock_ctx2,
                             mock_ctx3,
                             mock_conn):
        name = 'something'
        cluster_arn = 'test'
        expected_result = 'yes'
        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            context.instance = mock_ctx.instance
            context.instance.relationships = []
        mock_client = configure_mock_connection(mock_conn)

        mock_client.describe_services.return_value = {'services': [
            {'serviceArn': expected_result},
        ]}

        result = service.Service().get_service_arn(
            name=name,
            cluster_arn=cluster_arn,
        )
        self.assertEqual(result, expected_result)

        mock_client.describe_services.assert_called_once_with(
            cluster=cluster_arn,
            services=[name],
        )

    @patch('cloudify_aws.ecs.service.EC2ConnectionClient')
    @patch('cloudify_aws.ecs.service.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_get_cluster_arn_too_many_clusters_found(self,
                                                     mock_ctx,
                                                     mock_ctx2,
                                                     mock_ctx3,
                                                     mock_conn):
        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            context.instance = mock_ctx.instance
            context.instance.relationships = []
        mock_client = configure_mock_connection(mock_conn)

        mock_client.describe_clusters.return_value = {'clusters': [
            {
                'clusterName': 1,
            },
            {
                'clusterName': 2,
            },
            {
                'clusterName': 3,
            },
        ]}

        self.assertRaises(
            NonRecoverableError,
            service.Service().get_cluster_arn,
            'acluster',
        )

    @patch('cloudify_aws.ecs.service.Service.get_service_arn')
    @patch('cloudify_aws.ecs.service.Service.get_arn')
    @patch('cloudify_aws.ecs.service.EC2ConnectionClient')
    @patch('cloudify_aws.ecs.service.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_get_resource(self,
                          mock_ctx,
                          mock_ctx2,
                          mock_ctx3,
                          mock_conn,
                          mock_get_arn,
                          mock_service_arn):
        expected_result = 'a good result'
        cluster_arn = 'something'
        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            context.instance = mock_ctx.instance
            context.instance.relationships = []

        mock_client = configure_mock_connection(mock_conn)
        mock_client.list_services.return_value = {
            'serviceArns': [
                expected_result,
            ],
        }

        mock_get_arn.return_value = cluster_arn
        mock_service_arn.return_value = expected_result

        result = service.Service().get_resource()

        self.assertEqual(result, expected_result)

        mock_client.list_services.assert_called_once_with(
            cluster=cluster_arn
        )

    @patch('cloudify_aws.ecs.service.Service.get_service_arn')
    @patch('cloudify_aws.ecs.service.Service.get_arn')
    @patch('cloudify_aws.ecs.service.EC2ConnectionClient')
    @patch('cloudify_aws.ecs.service.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_get_no_resource(self,
                             mock_ctx,
                             mock_ctx2,
                             mock_ctx3,
                             mock_conn,
                             mock_get_arn,
                             mock_service_arn):
        cluster_arn = 'something'
        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            context.instance = mock_ctx.instance
            context.instance.relationships = []

        mock_client = configure_mock_connection(mock_conn)
        mock_client.list_services.return_value = {
            'serviceArns': [],
        }

        mock_get_arn.return_value = cluster_arn
        mock_service_arn.return_value = 'no arn cake'

        result = service.Service().get_resource()

        self.assertIsNone(result)

        mock_client.list_services.assert_called_once_with(
            cluster=cluster_arn
        )

    @patch('cloudify_aws.ecs.service.Service')
    def test_create_calls_correct_method(self, mock_service):
        args = [1, 2, 3]
        expected = 'the right result'
        mock_service.return_value.created.return_value = expected

        result = service.create(args)

        self.assertEqual(result, expected)
        mock_service.return_value.created.assert_called_once_with(args)

    @patch('cloudify_aws.ecs.service.Service')
    def test_delete_calls_correct_method(self, mock_service):
        args = [1, 2, 3]
        expected = 'the right result'
        mock_service.return_value.deleted.return_value = expected

        result = service.delete(args)

        self.assertEqual(result, expected)
        mock_service.return_value.deleted.assert_called_once_with(args)

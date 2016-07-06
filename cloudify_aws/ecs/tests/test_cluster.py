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

# This package imports
from cloudify_aws import constants
from cloudify_aws.ecs import cluster
from cloudify_aws.ecs.tests import (
    configure_mock_connection,
    make_node_context,
)


class TestCluster(testtools.TestCase):

    def setUp(self):
        super(TestCluster, self).setUp()

    @patch('cloudify_aws.ecs.cluster.EC2ConnectionClient')
    @patch('cloudify_aws.ecs.cluster.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_create_successfully(self,
                                 mock_ctx,
                                 mock_ctx2,
                                 mock_ctx3,
                                 mock_conn):
        new_cluster_name = 'mycluster'
        new_cluster_arn = 'abc123'

        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            make_node_context(
                context,
                node='ECSCluster',
                properties={
                    'name': new_cluster_name,
                    'use_external_resource': False,
                },
            )
            context.instance = mock_ctx.instance
            context.instance.relationships = []

        client = configure_mock_connection(mock_conn)
        client.list_clusters.return_value = {
            'clusterArns': ['something']
        }
        client.describe_clusters.return_value = {
            'clusters': [
                {
                    'clusterArn': 'something',
                    'clusterName': 'default',
                },
            ],
        }
        client.create_cluster.return_value = {
            'cluster': {
                'clusterArn': new_cluster_arn,
            }
        }

        cluster.Cluster().create()

        client.create_cluster.assert_called_once_with(
            clusterName=new_cluster_name,
        )

        self.assertEqual(
            mock_ctx.instance.runtime_properties['instances'],
            [],
        )

    @patch('cloudify_aws.ecs.cluster.EC2ConnectionClient')
    @patch('cloudify_aws.ecs.cluster.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_delete_with_instances(self,
                                   mock_ctx,
                                   mock_ctx2,
                                   mock_ctx3,
                                   mock_conn):
        cluster_arn = 'abc123'
        instances = ['i1', 'i2', 'i3']

        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            make_node_context(
                context,
                node='ECSCluster',
                properties={
                    'name': 'mycluster',
                    'use_external_resource': False,
                },
                runtime_properties={
                    constants.EXTERNAL_RESOURCE_ID: cluster_arn,
                },
            )
            context.instance = mock_ctx.instance
            context.instance.relationships = []
            context.logger = mock_ctx.logger

        client = configure_mock_connection(mock_conn)

        client.list_container_instances.return_value = {
            'containerInstanceArns': instances,
        }

        cluster.Cluster().delete()

        for instance in instances:
            client.deregister_container_instance.assert_any_call(
                containerInstance=instance,
                cluster=cluster_arn,
            )
            logged_this_instance = False
            for args in mock_ctx.logger.warn.call_args_list:
                # Check whether the instance is in the first of the *args for
                # ctx.logger.warn for any of its calls
                if instance in args[0][0]:
                    logged_this_instance = True
                    break
            if not logged_this_instance:
                raise AssertionError(
                    'All instances being deregistered are expected to log '
                    'warnings.'
                )

        client.delete_cluster.assert_called_once_with(cluster=cluster_arn)

    @patch('cloudify_aws.ecs.cluster.EC2ConnectionClient')
    @patch('cloudify_aws.ecs.cluster.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_delete_without_instances(self,
                                      mock_ctx,
                                      mock_ctx2,
                                      mock_ctx3,
                                      mock_conn):
        cluster_arn = 'abc123'

        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            make_node_context(
                context,
                node='ECSCluster',
                properties={
                    'name': 'mycluster',
                    'use_external_resource': False,
                },
                runtime_properties={
                    constants.EXTERNAL_RESOURCE_ID: cluster_arn,
                },
            )
            context.instance = mock_ctx.instance
            context.instance.relationships = []

        client = configure_mock_connection(mock_conn)

        client.list_container_instances.return_value = {
            'containerInstanceArns': [],
        }

        cluster.Cluster().delete()

        assert client.deregister_container_instance.call_count == 0

        client.delete_cluster.assert_called_once_with(cluster=cluster_arn)

    @patch('cloudify_aws.ecs.cluster.EC2ConnectionClient')
    @patch('cloudify_aws.ecs.cluster.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_get_cluster_instance_arn_from_ec2_id_no_arns(self,
                                                          mock_ctx,
                                                          mock_ctx2,
                                                          mock_ctx3,
                                                          mock_conn):
        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            context.instance = mock_ctx.instance
            context.instance.relationships = []

        client = configure_mock_connection(mock_conn)

        ec2_id = 'myec2instance'
        cluster_arn = 'mycluster'
        container_instance_arns = []
        container_instances = []

        client.list_container_instances.return_value = {
            'containerInstanceArns': container_instance_arns,
        }
        client.describe_container_instances.return_value = {
            'containerInstances': container_instances,
        }

        self.assertIsNone(
            cluster.ClusterInstance()._get_container_instance_arn_from_ec2_id(
                ec2_id,
                cluster_arn,
            )
        )

    @patch('cloudify_aws.ecs.cluster.EC2ConnectionClient')
    @patch('cloudify_aws.ecs.cluster.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_get_cluster_instance_arn_from_ec2_id_missing(self,
                                                          mock_ctx,
                                                          mock_ctx2,
                                                          mock_ctx3,
                                                          mock_conn):
        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            context.instance = mock_ctx.instance
            context.instance.relationships = []

        client = configure_mock_connection(mock_conn)

        ec2_id = 'myec2instance'
        cluster_arn = 'mycluster'
        container_instance_arns = [
            'something',
        ]
        container_instances = [
            {
                'ec2InstanceId': 'nottherightinstance',
                'containerInstanceArn': 'something',
            },
        ]

        client.list_container_instances.return_value = {
            'containerInstanceArns': container_instance_arns,
        }
        client.describe_container_instances.return_value = {
            'containerInstances': container_instances,
        }

        self.assertIsNone(
            cluster.ClusterInstance()._get_container_instance_arn_from_ec2_id(
                ec2_id,
                cluster_arn,
            )
        )

    @patch('cloudify_aws.ecs.cluster.EC2ConnectionClient')
    @patch('cloudify_aws.ecs.cluster.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_get_cluster_instance_arn_from_ec2_id_success(self,
                                                          mock_ctx,
                                                          mock_ctx2,
                                                          mock_ctx3,
                                                          mock_conn):
        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            context.instance = mock_ctx.instance
            context.instance.relationships = []

        client = configure_mock_connection(mock_conn)

        ec2_id = 'myec2instance'
        expected_arn = 'other'
        cluster_arn = 'mycluster'
        container_instance_arns = [
            'something',
            expected_arn,
        ]
        container_instances = [
            {
                'ec2InstanceId': 'nottherightinstance',
                'containerInstanceArn': 'something',
            },
            {
                'ec2InstanceId': ec2_id,
                'containerInstanceArn': expected_arn,
            },
        ]

        client.list_container_instances.return_value = {
            'containerInstanceArns': container_instance_arns,
        }
        client.describe_container_instances.return_value = {
            'containerInstances': container_instances,
        }

        assert cluster.ClusterInstance(
        )._get_container_instance_arn_from_ec2_id(
            ec2_id,
            cluster_arn,
        ) == expected_arn

    def _make_container_relationship_ctx(self, ctx, ec2_instance_ctx,
                                         cluster_ctx):
        ctx.source = ec2_instance_ctx
        ctx.target = cluster_ctx
        return ctx

    @patch('cloudify_aws.ecs.cluster.ClusterInstance.'
           '_get_container_instance_arn_from_ec2_id')
    @patch('cloudify_aws.ecs.cluster.EC2ConnectionClient')
    @patch('cloudify_aws.ecs.cluster.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_associate_ec2_not_ready(self,
                                     mock_ctx,
                                     mock_ctx2,
                                     mock_ctx3,
                                     mock_conn,
                                     mock_get_arn):
        ec2_resource_id = 'myec2instance'
        cluster_arn = 'mycluster'
        ec2_instance_ctx = make_node_context(
            Mock(),
            node='Instance',
            properties={
                'image_id': 'test',
                'instance_type': 'test',
            },
            runtime_properties={
                constants.EXTERNAL_RESOURCE_ID: ec2_resource_id,
            },
        )
        cluster_ctx = make_node_context(
            Mock(),
            node='ECSCluster',
            properties={
                'name': 'clustername',
                'use_external_resource': False,
            },
            runtime_properties={
                constants.EXTERNAL_RESOURCE_ID: cluster_arn,
            },
        )

        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            self._make_container_relationship_ctx(
                context,
                ec2_instance_ctx,
                cluster_ctx,
            )
            context.instance = mock_ctx.instance
            context.instance.relationships = []
            context.operation = mock_ctx.operation

        mock_get_arn.return_value = None

        self.assertFalse(cluster.ClusterInstance().associate())

        mock_get_arn.assert_called_once_with(
            ec2_id=ec2_resource_id,
            cluster_arn=cluster_arn,
        )

    @patch('cloudify_aws.ecs.cluster.ClusterInstance.'
           '_get_container_instance_arn_from_ec2_id')
    @patch('cloudify_aws.ecs.cluster.EC2ConnectionClient')
    @patch('cloudify_aws.ecs.cluster.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_associate_first(self,
                             mock_ctx,
                             mock_ctx2,
                             mock_ctx3,
                             mock_conn,
                             mock_get_arn):
        ec2_resource_id = 'myec2instance'
        cluster_arn = 'mycluster'
        ec2_instance_ctx = make_node_context(
            Mock(),
            node='Instance',
            properties={
                'image_id': 'test',
                'instance_type': 'test',
            },
            runtime_properties={
                constants.EXTERNAL_RESOURCE_ID: ec2_resource_id,
            },
        )
        cluster_ctx = make_node_context(
            Mock(),
            node='ECSCluster',
            properties={
                'name': 'clustername',
                'use_external_resource': False,
            },
            runtime_properties={
                constants.EXTERNAL_RESOURCE_ID: cluster_arn,
                'instances': [],
            },
        )

        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            self._make_container_relationship_ctx(
                context,
                ec2_instance_ctx,
                cluster_ctx,
            )
            context.instance = mock_ctx.instance
            context.instance.relationships = []

        mock_get_arn.return_value = 'happy'

        cluster.ClusterInstance().associate()

        mock_get_arn.assert_called_once_with(
            ec2_id=ec2_resource_id,
            cluster_arn=cluster_arn,
        )

        assert cluster_ctx.instance.runtime_properties['instances'] == [
            ec2_resource_id,
        ]

    @patch('cloudify_aws.ecs.cluster.ClusterInstance.'
           '_get_container_instance_arn_from_ec2_id')
    @patch('cloudify_aws.ecs.cluster.EC2ConnectionClient')
    @patch('cloudify_aws.ecs.cluster.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_associate_more(self,
                            mock_ctx,
                            mock_ctx2,
                            mock_ctx3,
                            mock_conn,
                            mock_get_arn):
        ec2_resource_id = 'myec2instance'
        cluster_arn = 'mycluster'
        ec2_instance_ctx = make_node_context(
            Mock(),
            node='Instance',
            properties={
                'image_id': 'test',
                'instance_type': 'test',
            },
            runtime_properties={
                constants.EXTERNAL_RESOURCE_ID: ec2_resource_id,
            },
        )
        cluster_ctx = make_node_context(
            Mock(),
            node='ECSCluster',
            properties={
                'name': 'clustername',
                'use_external_resource': False,
            },
            runtime_properties={
                constants.EXTERNAL_RESOURCE_ID: cluster_arn,
                'instances': ['test'],
            },
        )

        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            self._make_container_relationship_ctx(
                context,
                ec2_instance_ctx,
                cluster_ctx,
            )
            context.instance = mock_ctx.instance
            context.instance.relationships = []

        mock_get_arn.return_value = 'happy'

        cluster.ClusterInstance().associate()

        mock_get_arn.assert_called_once_with(
            ec2_id=ec2_resource_id,
            cluster_arn=cluster_arn,
        )

        assert cluster_ctx.instance.runtime_properties['instances'] == [
            'test',
            ec2_resource_id,
        ]

    @patch('cloudify_aws.ecs.cluster.ClusterInstance.'
           '_get_container_instance_arn_from_ec2_id')
    @patch('cloudify_aws.ecs.cluster.EC2ConnectionClient')
    @patch('cloudify_aws.ecs.cluster.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_disassociate_missing(self,
                                  mock_ctx,
                                  mock_ctx2,
                                  mock_ctx3,
                                  mock_conn,
                                  mock_get_arn):
        # As registration of instances can take a long time, this ensures that
        # an instance that hasn't been registered can be forgotten about.
        client = configure_mock_connection(mock_conn)

        ec2_resource_id = 'myec2instance'
        cluster_arn = 'mycluster'
        ec2_instance_ctx = make_node_context(
            Mock(),
            node='Instance',
            properties={
                'image_id': 'test',
                'instance_type': 'test',
            },
            runtime_properties={
                constants.EXTERNAL_RESOURCE_ID: ec2_resource_id,
            },
        )
        cluster_ctx = make_node_context(
            Mock(),
            node='ECSCluster',
            properties={
                'name': 'clustername',
                'use_external_resource': False,
            },
            runtime_properties={
                constants.EXTERNAL_RESOURCE_ID: cluster_arn,
                'instances': ['other', ec2_resource_id],
            },
        )

        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            self._make_container_relationship_ctx(
                context,
                ec2_instance_ctx,
                cluster_ctx,
            )
            context.instance = mock_ctx.instance
            context.instance.relationships = []

        mock_get_arn.return_value = None

        cluster.ClusterInstance().disassociate()

        mock_get_arn.assert_called_once_with(
            ec2_id=ec2_resource_id,
            cluster_arn=cluster_arn,
        )

        self.assertEqual(
            cluster_ctx.instance.runtime_properties['instances'],
            ['other'],
        )
        self.assertEqual(
            client.deregister_container_instance.call_count,
            0,
        )

    @patch('cloudify_aws.ecs.cluster.ClusterInstance.'
           '_get_container_instance_arn_from_ec2_id')
    @patch('cloudify_aws.ecs.cluster.EC2ConnectionClient')
    @patch('cloudify_aws.ecs.cluster.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_disassociate_existing(self,
                                   mock_ctx,
                                   mock_ctx2,
                                   mock_ctx3,
                                   mock_conn,
                                   mock_get_arn):
        client = configure_mock_connection(mock_conn)

        ec2_resource_id = 'myec2instance'
        cluster_arn = 'mycluster'
        container_instance = 'happy'
        ec2_instance_ctx = make_node_context(
            Mock(),
            node='Instance',
            properties={
                'image_id': 'test',
                'instance_type': 'test',
            },
            runtime_properties={
                constants.EXTERNAL_RESOURCE_ID: ec2_resource_id,
            },
        )
        cluster_ctx = make_node_context(
            Mock(),
            node='ECSCluster',
            properties={
                'name': 'clustername',
                'use_external_resource': False,
            },
            runtime_properties={
                constants.EXTERNAL_RESOURCE_ID: cluster_arn,
                'instances': ['other', ec2_resource_id],
            },
        )

        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            self._make_container_relationship_ctx(
                context,
                ec2_instance_ctx,
                cluster_ctx,
            )
            context.instance = mock_ctx.instance
            context.instance.relationships = []

        mock_get_arn.return_value = container_instance

        cluster.ClusterInstance().disassociate()

        mock_get_arn.assert_called_once_with(
            ec2_id=ec2_resource_id,
            cluster_arn=cluster_arn,
        )

        client.deregister_container_instance.assert_called_once_with(
            cluster=cluster_arn,
            containerInstance=container_instance,
        )

        self.assertEqual(
            cluster_ctx.instance.runtime_properties['instances'],
            ['other'],
        )

    @patch('cloudify_aws.ecs.cluster.EC2ConnectionClient')
    @patch('cloudify_aws.ecs.cluster.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_get_resource_arn(self,
                              mock_ctx,
                              mock_ctx2,
                              mock_ctx3,
                              mock_conn):
        cluster_arn = 'floodland'
        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            make_node_context(
                context,
                node='ECSCluster',
                properties={
                    'name': 'mycluster',
                },
                runtime_properties={
                    constants.EXTERNAL_RESOURCE_ID: cluster_arn,
                },
            )
            context.instance = mock_ctx.instance
            context.instance.relationships = []

        mock_client = configure_mock_connection(mock_conn)
        mock_client.describe_clusters.return_value = {'clusters': [
            {
                'clusterArn': 'vision',
                'clusterName': 'thing',
            },
            {
                'clusterArn': cluster_arn,
                'clusterName': 'mycluster',
            },
        ]}

        result = cluster.Cluster().get_resource()

        self.assertEqual(result, cluster_arn)

    @patch('cloudify_aws.ecs.cluster.EC2ConnectionClient')
    @patch('cloudify_aws.ecs.cluster.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_get_resource_name(self,
                               mock_ctx,
                               mock_ctx2,
                               mock_ctx3,
                               mock_conn):
        cluster_name = 'lucretia'
        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            make_node_context(
                context,
                node='ECSCluster',
                properties={
                    'name': cluster_name,
                },
            )
            context.instance = mock_ctx.instance
            context.instance.relationships = []

        mock_client = configure_mock_connection(mock_conn)
        mock_client.describe_clusters.return_value = {'clusters': [
            {
                'clusterArn': 'vision',
                'clusterName': 'thing',
            },
            {
                'clusterArn': 'kgcop',
                'clusterName': cluster_name,
            },
        ]}

        result = cluster.Cluster().get_resource()

        self.assertEqual(result, cluster_name)

    @patch('cloudify_aws.ecs.cluster.EC2ConnectionClient')
    @patch('cloudify_aws.ecs.cluster.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_get_no_resource(self,
                             mock_ctx,
                             mock_ctx2,
                             mock_ctx3,
                             mock_conn):
        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            make_node_context(
                context,
                node='ECSCluster',
                properties={
                    'name': 'more',
                },
            )
            context.instance = mock_ctx.instance
            context.instance.relationships = []

        mock_client = configure_mock_connection(mock_conn)
        mock_client.describe_clusters.return_value = {'clusters': [
            {
                'clusterArn': 'vision',
                'clusterName': 'thing',
            },
        ]}

        result = cluster.Cluster().get_resource()

        self.assertIsNone(result)

    @patch('cloudify_aws.ecs.cluster.ClusterInstance.post_associate')
    @patch('cloudify_aws.ecs.cluster.ClusterInstance.associate')
    @patch('cloudify_aws.ecs.cluster.ClusterInstance.'
           'use_source_external_resource_naively')
    @patch('cloudify_aws.ecs.cluster.EC2ConnectionClient')
    @patch('cloudify_aws.ecs.cluster.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_associated_not_yet(self,
                                mock_ctx,
                                mock_ctx2,
                                mock_ctx3,
                                mock_conn,
                                mock_use_naive,
                                mock_associate,
                                mock_post):
        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            context.instance = mock_ctx.instance
            context.instance.relationships = []
            context.operation = mock_ctx.operation

        mock_use_naive.return_value = False
        mock_associate.return_value = False

        cluster.ClusterInstance().associated()

        mock_ctx.operation.retry.assert_called_once_with(
            message='Waiting for EC2 instance to register with cluster.',
        )
        mock_use_naive.assert_called_once_with()
        mock_associate.assert_called_once_with(None)
        self.assertEqual(mock_post.call_count, 0)

    @patch('cloudify_aws.ecs.cluster.ClusterInstance.post_associate')
    @patch('cloudify_aws.ecs.cluster.ClusterInstance.associate')
    @patch('cloudify_aws.ecs.cluster.ClusterInstance.'
           'use_source_external_resource_naively')
    @patch('cloudify_aws.ecs.cluster.EC2ConnectionClient')
    @patch('cloudify_aws.ecs.cluster.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_associated_external(self,
                                 mock_ctx,
                                 mock_ctx2,
                                 mock_ctx3,
                                 mock_conn,
                                 mock_use_naive,
                                 mock_associate,
                                 mock_post):
        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            context.instance = mock_ctx.instance
            context.instance.relationships = []
            context.operation = mock_ctx.operation

        mock_use_naive.return_value = True
        mock_associate.return_value = False

        cluster.ClusterInstance().associated()

        self.assertEqual(mock_ctx.operation.retry.call_count, 0)
        mock_use_naive.assert_called_once_with()
        self.assertEqual(mock_associate.call_count, 0)
        mock_post.assert_called_once_with()

    @patch('cloudify_aws.ecs.cluster.ClusterInstance.post_associate')
    @patch('cloudify_aws.ecs.cluster.ClusterInstance.associate')
    @patch('cloudify_aws.ecs.cluster.ClusterInstance.'
           'use_source_external_resource_naively')
    @patch('cloudify_aws.ecs.cluster.EC2ConnectionClient')
    @patch('cloudify_aws.ecs.cluster.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_associated_success(self,
                                mock_ctx,
                                mock_ctx2,
                                mock_ctx3,
                                mock_conn,
                                mock_use_naive,
                                mock_associate,
                                mock_post):
        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            context.instance = mock_ctx.instance
            context.instance.relationships = []
            context.operation = mock_ctx.operation

        mock_use_naive.return_value = False
        mock_associate.return_value = True

        cluster.ClusterInstance().associated()

        self.assertEqual(mock_ctx.operation.retry.call_count, 0)
        mock_use_naive.assert_called_once_with()
        mock_associate.assert_called_once_with(None)
        mock_post.assert_called_once_with()

    @patch('cloudify_aws.ecs.cluster.Cluster')
    def test_create_calls_correct_method(self, mock_cluster):
        args = [1, 2, 3]
        expected = 'the right result'
        mock_cluster.return_value.created.return_value = expected

        result = cluster.create(args)

        self.assertEqual(result, expected)
        mock_cluster.return_value.created.assert_called_once_with(args)

    @patch('cloudify_aws.ecs.cluster.Cluster')
    def test_delete_calls_correct_method(self, mock_cluster):
        args = [1, 2, 3]
        expected = 'the right result'
        mock_cluster.return_value.deleted.return_value = expected

        result = cluster.delete(args)

        self.assertEqual(result, expected)
        mock_cluster.return_value.deleted.assert_called_once_with(args)

    @patch('cloudify_aws.ecs.cluster.ClusterInstance')
    def test_associate_calls_correct_method(self, mock_cluster_instance):
        args = [1, 2, 3]
        expected = 'the right result'
        mock_cluster_instance.return_value.associated.return_value = (
            expected
        )

        result = cluster.add_container_instance(args)

        self.assertEqual(result, expected)
        mock_cluster_instance.return_value.associated.assert_called_once_with(
            args,
        )

    @patch('cloudify_aws.ecs.cluster.ClusterInstance')
    def test_disassociate_calls_correct_method(self, mock_cluster_instance):
        args = [1, 2, 3]
        expected = 'the right result'
        dis = mock_cluster_instance.return_value.disassociated
        dis.return_value = expected

        result = cluster.remove_container_instance(args)

        self.assertEqual(result, expected)
        dis.assert_called_once_with(args)

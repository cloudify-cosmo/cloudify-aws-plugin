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
from collections import OrderedDict

# Third party imports
import testtools
from mock import patch, Mock

# Cloudify imports
from cloudify.exceptions import NonRecoverableError

# This package imports
from cloudify_aws import constants
from cloudify_aws.ecs import task
from cloudify_aws.ecs.tests import (
    configure_mock_connection,
    make_node_context,
)


class TestTask(testtools.TestCase):

    def setUp(self):
        super(TestTask, self).setUp()

    @patch('cloudify_aws.ecs.task.EC2ConnectionClient')
    @patch('cloudify_aws.ecs.task.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_get_appropriate_relationship_targets_none(self,
                                                       mock_ctx,
                                                       mock_ctx2,
                                                       mock_ctx3,
                                                       mock_conn):
        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            context.instance = mock_ctx.instance
            context.instance.relationships = []
        self.assertEqual(
            task.Task().get_appropriate_relationship_targets(
                relationships=[],
                target_relationship='this_relationship',
                target_node='some_node',
            ),
            [],
        )

    @patch('cloudify_aws.ecs.task.EC2ConnectionClient')
    @patch('cloudify_aws.ecs.task.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_get_appropriate_relationship_targets_one(self,
                                                      mock_ctx,
                                                      mock_ctx2,
                                                      mock_ctx3,
                                                      mock_conn):
        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            context.instance = mock_ctx.instance
            context.instance.relationships = []
        right_relationship_type = 'this relationship'
        right_relationship_target = 'this target'

        right_relationship = Mock()
        right_relationship.type = right_relationship_type
        right_relationship.target.node.type = right_relationship_target

        relationships = [right_relationship]

        self.assertEqual(
            task.Task().get_appropriate_relationship_targets(
                relationships=relationships,
                target_relationship=right_relationship_type,
                target_node=right_relationship_target,
            ),
            [right_relationship.target.node],
        )

    @patch('cloudify_aws.ecs.task.EC2ConnectionClient')
    @patch('cloudify_aws.ecs.task.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_get_appropriate_relationship_targets_more(self,
                                                       mock_ctx,
                                                       mock_ctx2,
                                                       mock_ctx3,
                                                       mock_conn):
        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            context.instance = mock_ctx.instance
            context.instance.relationships = []
        right_relationship_type = 'this relationship'
        right_relationship_target = 'this target'

        right_relationship1 = Mock()
        right_relationship1.type = right_relationship_type
        right_relationship1.target.node.type = right_relationship_target

        right_relationship2 = Mock()
        right_relationship2.type = right_relationship_type
        right_relationship2.target.node.type = right_relationship_target

        relationships = [right_relationship1, right_relationship2]

        self.assertEqual(
            task.Task().get_appropriate_relationship_targets(
                relationships=relationships,
                target_relationship=right_relationship_type,
                target_node=right_relationship_target,
            ),
            [
                right_relationship1.target.node,
                right_relationship2.target.node,
            ],
        )

    @patch('cloudify_aws.ecs.task.EC2ConnectionClient')
    @patch('cloudify_aws.ecs.task.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_get_appropriate_relationship_targets_wrong(self,
                                                        mock_ctx,
                                                        mock_ctx2,
                                                        mock_ctx3,
                                                        mock_conn):
        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            context.instance = mock_ctx.instance
            context.instance.relationships = []
        right_relationship_type = 'this relationship'
        right_relationship_target = 'this target'

        wrong_relationship = Mock()
        wrong_relationship.type = 'something'
        wrong_relationship.target.node.type = 'else'

        relationships = [wrong_relationship]

        self.assertEqual(
            task.Task().get_appropriate_relationship_targets(
                relationships=relationships,
                target_relationship=right_relationship_type,
                target_node=right_relationship_target,
            ),
            [],
        )

    @patch('cloudify_aws.ecs.task.EC2ConnectionClient')
    @patch('cloudify_aws.ecs.task.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_get_appropriate_relationship_targets_mixed(self,
                                                        mock_ctx,
                                                        mock_ctx2,
                                                        mock_ctx3,
                                                        mock_conn):
        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            context.instance = mock_ctx.instance
            context.instance.relationships = []
        right_relationship_type = 'this relationship'
        right_relationship_target = 'this target'

        right_relationship = Mock()
        right_relationship.type = right_relationship_type
        right_relationship.target.node.type = right_relationship_target

        wrong_relationship = Mock()
        wrong_relationship.type = 'something'
        wrong_relationship.target.node.type = 'else'

        relationships = [right_relationship, wrong_relationship]

        self.assertEqual(
            task.Task().get_appropriate_relationship_targets(
                relationships=relationships,
                target_relationship=right_relationship_type,
                target_node=right_relationship_target,
            ),
            [right_relationship.target.node],
        )

    @patch('cloudify_aws.ecs.task.EC2ConnectionClient')
    @patch('cloudify_aws.ecs.task.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_get_appropriate_relationship_targets_wrong_target(self,
                                                               mock_ctx,
                                                               mock_ctx2,
                                                               mock_ctx3,
                                                               mock_conn):
        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            context.instance = mock_ctx.instance
            context.instance.relationships = []
        right_relationship_type = 'this relationship'
        right_relationship_target = 'this target'

        right_relationship = Mock()
        right_relationship.type = right_relationship_type
        right_relationship.target.node.type = right_relationship_target

        wrong_relationship = Mock()
        wrong_relationship.type = 'something'
        wrong_relationship.target.node.type = 'else'

        bad_relationship = Mock()
        bad_relationship.type = right_relationship_type
        bad_relationship.target.node.type = 'else'

        relationships = [
            right_relationship,
            wrong_relationship,
            bad_relationship,
        ]

        self.assertRaises(
            NonRecoverableError,
            task.Task().get_appropriate_relationship_targets,
            relationships=relationships,
            target_relationship=right_relationship_type,
            target_node=right_relationship_target,
        )

    @patch('cloudify_aws.ecs.task.Task.get_appropriate_relationship_targets')
    @patch('cloudify_aws.ecs.task.EC2ConnectionClient')
    @patch('cloudify_aws.ecs.task.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_construct_volume_definitions_none(self,
                                               mock_ctx,
                                               mock_ctx2,
                                               mock_ctx3,
                                               mock_conn,
                                               mock_get_targets):
        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            context.instance = mock_ctx.instance
            context.instance.relationships = []

        mock_get_targets.return_value = []

        self.assertEqual(
            task.Task().construct_volume_definitions(),
            [],
        )

        mock_get_targets.assert_called_once_with(
            relationships=mock_ctx.instance.relationships,
            target_relationship=constants.VOLUME_TASK_RELATIONSHIP,
            target_node='cloudify.aws.nodes.ECSVolume',
        )

    @patch('cloudify_aws.ecs.task.Task.get_appropriate_relationship_targets')
    @patch('cloudify_aws.ecs.task.EC2ConnectionClient')
    @patch('cloudify_aws.ecs.task.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_construct_volume_definitions_some(self,
                                               mock_ctx,
                                               mock_ctx2,
                                               mock_ctx3,
                                               mock_conn,
                                               mock_get_targets):
        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            context.instance = mock_ctx.instance
            context.instance.relationships = []

        name1 = 'first'
        name2 = 'second'

        first = Mock()
        second = Mock()
        first.properties = {'name': name1}
        second.properties = {'name': name2}

        mock_get_targets.return_value = [first, second]

        self.assertEqual(
            task.Task().construct_volume_definitions(),
            [
                {'name': name1},
                {'name': name2},
            ],
        )

        mock_get_targets.assert_called_once_with(
            relationships=mock_ctx.instance.relationships,
            target_relationship=constants.VOLUME_TASK_RELATIONSHIP,
            target_node='cloudify.aws.nodes.ECSVolume',
        )

    @patch('cloudify_aws.ecs.task.Task.get_appropriate_relationship_targets')
    @patch('cloudify_aws.ecs.task.EC2ConnectionClient')
    @patch('cloudify_aws.ecs.task.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_construct_container_definitions_none(self,
                                                  mock_ctx,
                                                  mock_ctx2,
                                                  mock_ctx3,
                                                  mock_conn,
                                                  mock_get_targets):
        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            context.instance = mock_ctx.instance
            context.instance.relationships = []

        mock_get_targets.return_value = []

        self.assertEqual(
            task.Task().construct_container_definitions(),
            [],
        )

        mock_get_targets.assert_called_once_with(
            relationships=mock_ctx.instance.relationships,
            target_relationship=constants.CONTAINER_TASK_RELATIONSHIP,
            target_node='cloudify.aws.nodes.ECSContainer',
        )

    @patch('cloudify_aws.ecs.task.Task.get_appropriate_relationship_targets')
    @patch('cloudify_aws.ecs.task.EC2ConnectionClient')
    @patch('cloudify_aws.ecs.task.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_construct_container_definitions_defaults(self,
                                                      mock_ctx,
                                                      mock_ctx2,
                                                      mock_ctx3,
                                                      mock_conn,
                                                      mock_get_targets):
        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            context.instance = mock_ctx.instance
            context.instance.relationships = []

        name = 'c1'
        image = 'myimage'
        memory = 4

        container1 = make_node_context(
            Mock(),
            node='ECSContainer',
            properties={
                'name': name,
                'image': image,
                'memory': memory,
            },
        )

        mock_get_targets.return_value = [
            container1.node,
        ]

        self.assertEqual(
            task.Task().construct_container_definitions(),
            [
                {
                    'name': name,
                    'image': image,
                    'memory': memory,
                    # Defaults- there must be at least one essential
                    'essential': True,
                    'readonlyRootFilesystem': False,
                    'privileged': False,
                },
            ],
        )

        mock_get_targets.assert_called_once_with(
            relationships=mock_ctx.instance.relationships,
            target_relationship=constants.CONTAINER_TASK_RELATIONSHIP,
            target_node='cloudify.aws.nodes.ECSContainer',
        )

    @patch('cloudify_aws.ecs.task.Task.get_appropriate_relationship_targets')
    @patch('cloudify_aws.ecs.task.EC2ConnectionClient')
    @patch('cloudify_aws.ecs.task.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_construct_container_definitions_two_defaults(self,
                                                          mock_ctx,
                                                          mock_ctx2,
                                                          mock_ctx3,
                                                          mock_conn,
                                                          mock_get_targets):
        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            context.instance = mock_ctx.instance
            context.instance.relationships = []

        name1 = 'c1'
        image1 = 'myimage'
        memory1 = 4

        name2 = 'c2'
        image2 = 'myimage2'
        memory2 = 5

        container1 = make_node_context(
            Mock(),
            node='ECSContainer',
            properties={
                'name': name1,
                'image': image1,
                'memory': memory1,
            },
        )

        container2 = make_node_context(
            Mock(),
            node='ECSContainer',
            properties={
                'name': name2,
                'image': image2,
                'memory': memory2,
            },
        )

        mock_get_targets.return_value = [
            container1.node,
            container2.node,
        ]

        self.assertEqual(
            task.Task().construct_container_definitions(),
            [
                {
                    'name': name1,
                    'image': image1,
                    'memory': memory1,
                    # Defaults- there must be at least one essential
                    'essential': True,
                    'readonlyRootFilesystem': False,
                    'privileged': False,
                },
                {
                    'name': name2,
                    'image': image2,
                    'memory': memory2,
                    # Defaults- there must be at least one essential
                    'essential': True,
                    'readonlyRootFilesystem': False,
                    'privileged': False,
                },
            ],
        )

        mock_get_targets.assert_called_once_with(
            relationships=mock_ctx.instance.relationships,
            target_relationship=constants.CONTAINER_TASK_RELATIONSHIP,
            target_node='cloudify.aws.nodes.ECSContainer',
        )

    @patch('cloudify_aws.ecs.task.Task.get_appropriate_relationship_targets')
    @patch('cloudify_aws.ecs.task.EC2ConnectionClient')
    @patch('cloudify_aws.ecs.task.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_construct_container_definitions_tcp(self,
                                                 mock_ctx,
                                                 mock_ctx2,
                                                 mock_ctx3,
                                                 mock_conn,
                                                 mock_get_targets):
        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            context.instance = mock_ctx.instance
            context.instance.relationships = []

        name = 'c1'
        image = 'myimage'
        memory = 4
        # All mappings tests use ordereddicts so that we can assert equality
        # on the result. The order should not actually matter, but this is
        # simpler than trying to hack around assertEqual in this case
        tcp_mappings = OrderedDict((
            (10, 20),
            (80, 8080),
        ))

        expected_mappings = [
            {
                'containerPort': 20,
                'hostPort': 10,
                'protocol': 'tcp',
            },
            {
                'containerPort': 8080,
                'hostPort': 80,
                'protocol': 'tcp',
            },
        ]

        container1 = make_node_context(
            Mock(),
            node='ECSContainer',
            properties={
                'name': name,
                'image': image,
                'memory': memory,
                'tcp_port_mappings': tcp_mappings,
            },
        )

        mock_get_targets.return_value = [
            container1.node,
        ]

        self.assertEqual(
            task.Task().construct_container_definitions(),
            [
                {
                    'name': name,
                    'image': image,
                    'memory': memory,
                    'essential': True,
                    'readonlyRootFilesystem': False,
                    'privileged': False,
                    'portMappings': expected_mappings,
                },
            ],
        )

        mock_get_targets.assert_called_once_with(
            relationships=mock_ctx.instance.relationships,
            target_relationship=constants.CONTAINER_TASK_RELATIONSHIP,
            target_node='cloudify.aws.nodes.ECSContainer',
        )

    @patch('cloudify_aws.ecs.task.Task.get_appropriate_relationship_targets')
    @patch('cloudify_aws.ecs.task.EC2ConnectionClient')
    @patch('cloudify_aws.ecs.task.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_construct_container_definitions_udp(self,
                                                 mock_ctx,
                                                 mock_ctx2,
                                                 mock_ctx3,
                                                 mock_conn,
                                                 mock_get_targets):
        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            context.instance = mock_ctx.instance
            context.instance.relationships = []

        name = 'c1'
        image = 'myimage'
        memory = 4
        # All mappings tests use ordereddicts so that we can assert equality
        # on the result. The order should not actually matter, but this is
        # simpler than trying to hack around assertEqual in this case
        udp_mappings = OrderedDict((
            (10, 20),
            (80, 8080),
        ))

        expected_mappings = [
            {
                'containerPort': 20,
                'hostPort': 10,
                'protocol': 'udp',
            },
            {
                'containerPort': 8080,
                'hostPort': 80,
                'protocol': 'udp',
            },
        ]

        container1 = make_node_context(
            Mock(),
            node='ECSContainer',
            properties={
                'name': name,
                'image': image,
                'memory': memory,
                'udp_port_mappings': udp_mappings,
            },
        )

        mock_get_targets.return_value = [
            container1.node,
        ]

        self.assertEqual(
            task.Task().construct_container_definitions(),
            [
                {
                    'name': name,
                    'image': image,
                    'memory': memory,
                    'essential': True,
                    'readonlyRootFilesystem': False,
                    'privileged': False,
                    'portMappings': expected_mappings,
                },
            ],
        )

        mock_get_targets.assert_called_once_with(
            relationships=mock_ctx.instance.relationships,
            target_relationship=constants.CONTAINER_TASK_RELATIONSHIP,
            target_node='cloudify.aws.nodes.ECSContainer',
        )

    @patch('cloudify_aws.ecs.task.Task.get_appropriate_relationship_targets')
    @patch('cloudify_aws.ecs.task.EC2ConnectionClient')
    @patch('cloudify_aws.ecs.task.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_construct_container_definitions_tcp_and_udp(self,
                                                         mock_ctx,
                                                         mock_ctx2,
                                                         mock_ctx3,
                                                         mock_conn,
                                                         mock_get_targets):
        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            context.instance = mock_ctx.instance
            context.instance.relationships = []

        name = 'c1'
        image = 'myimage'
        memory = 4
        # All mappings tests use ordereddicts so that we can assert equality
        # on the result. The order should not actually matter, but this is
        # simpler than trying to hack around assertEqual in this case
        tcp_mappings = OrderedDict((
            (30, 40),
            (90, 1024),
        ))
        udp_mappings = OrderedDict((
            (10, 20),
            (80, 8080),
        ))

        expected_mappings = [
            {
                'containerPort': 40,
                'hostPort': 30,
                'protocol': 'tcp',
            },
            {
                'containerPort': 1024,
                'hostPort': 90,
                'protocol': 'tcp',
            },
            {
                'containerPort': 20,
                'hostPort': 10,
                'protocol': 'udp',
            },
            {
                'containerPort': 8080,
                'hostPort': 80,
                'protocol': 'udp',
            },
        ]

        container1 = make_node_context(
            Mock(),
            node='ECSContainer',
            properties={
                'name': name,
                'image': image,
                'memory': memory,
                'tcp_port_mappings': tcp_mappings,
                'udp_port_mappings': udp_mappings,
            },
        )

        mock_get_targets.return_value = [
            container1.node,
        ]

        self.assertEqual(
            task.Task().construct_container_definitions(),
            [
                {
                    'name': name,
                    'image': image,
                    'memory': memory,
                    'essential': True,
                    'readonlyRootFilesystem': False,
                    'privileged': False,
                    'portMappings': expected_mappings,
                },
            ],
        )

        mock_get_targets.assert_called_once_with(
            relationships=mock_ctx.instance.relationships,
            target_relationship=constants.CONTAINER_TASK_RELATIONSHIP,
            target_node='cloudify.aws.nodes.ECSContainer',
        )

    @patch('cloudify_aws.ecs.task.Task.get_appropriate_relationship_targets')
    @patch('cloudify_aws.ecs.task.EC2ConnectionClient')
    @patch('cloudify_aws.ecs.task.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_construct_container_definitions_cpu(self,
                                                 mock_ctx,
                                                 mock_ctx2,
                                                 mock_ctx3,
                                                 mock_conn,
                                                 mock_get_targets):
        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            context.instance = mock_ctx.instance
            context.instance.relationships = []

        name = 'c1'
        image = 'myimage'
        memory = 4
        cpu_units = 1024

        container1 = make_node_context(
            Mock(),
            node='ECSContainer',
            properties={
                'name': name,
                'image': image,
                'memory': memory,
                'cpu_units': cpu_units,
            },
        )

        mock_get_targets.return_value = [
            container1.node,
        ]

        self.assertEqual(
            task.Task().construct_container_definitions(),
            [
                {
                    'name': name,
                    'image': image,
                    'memory': memory,
                    'essential': True,
                    'readonlyRootFilesystem': False,
                    'privileged': False,
                    'cpu': cpu_units,
                },
            ],
        )

        mock_get_targets.assert_called_once_with(
            relationships=mock_ctx.instance.relationships,
            target_relationship=constants.CONTAINER_TASK_RELATIONSHIP,
            target_node='cloudify.aws.nodes.ECSContainer',
        )

    @patch('cloudify_aws.ecs.task.Task.get_appropriate_relationship_targets')
    @patch('cloudify_aws.ecs.task.EC2ConnectionClient')
    @patch('cloudify_aws.ecs.task.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_construct_container_definitions_entrypoint(self,
                                                        mock_ctx,
                                                        mock_ctx2,
                                                        mock_ctx3,
                                                        mock_conn,
                                                        mock_get_targets):
        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            context.instance = mock_ctx.instance
            context.instance.relationships = []

        name = 'c1'
        image = 'myimage'
        memory = 4
        entrypoint = ['hello']

        container1 = make_node_context(
            Mock(),
            node='ECSContainer',
            properties={
                'name': name,
                'image': image,
                'memory': memory,
                'entrypoint': entrypoint,
            },
        )

        mock_get_targets.return_value = [
            container1.node,
        ]

        self.assertEqual(
            task.Task().construct_container_definitions(),
            [
                {
                    'name': name,
                    'image': image,
                    'memory': memory,
                    'essential': True,
                    'readonlyRootFilesystem': False,
                    'privileged': False,
                    'entryPoint': entrypoint,
                },
            ],
        )

        mock_get_targets.assert_called_once_with(
            relationships=mock_ctx.instance.relationships,
            target_relationship=constants.CONTAINER_TASK_RELATIONSHIP,
            target_node='cloudify.aws.nodes.ECSContainer',
        )

    @patch('cloudify_aws.ecs.task.Task.get_appropriate_relationship_targets')
    @patch('cloudify_aws.ecs.task.EC2ConnectionClient')
    @patch('cloudify_aws.ecs.task.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_construct_container_definitions_command(self,
                                                     mock_ctx,
                                                     mock_ctx2,
                                                     mock_ctx3,
                                                     mock_conn,
                                                     mock_get_targets):
        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            context.instance = mock_ctx.instance
            context.instance.relationships = []

        name = 'c1'
        image = 'myimage'
        memory = 4
        command = ['hello']

        container1 = make_node_context(
            Mock(),
            node='ECSContainer',
            properties={
                'name': name,
                'image': image,
                'memory': memory,
                'command': command,
            },
        )

        mock_get_targets.return_value = [
            container1.node,
        ]

        self.assertEqual(
            task.Task().construct_container_definitions(),
            [
                {
                    'name': name,
                    'image': image,
                    'memory': memory,
                    'essential': True,
                    'readonlyRootFilesystem': False,
                    'privileged': False,
                    'command': command,
                },
            ],
        )

        mock_get_targets.assert_called_once_with(
            relationships=mock_ctx.instance.relationships,
            target_relationship=constants.CONTAINER_TASK_RELATIONSHIP,
            target_node='cloudify.aws.nodes.ECSContainer',
        )

    @patch('cloudify_aws.ecs.task.Task.get_appropriate_relationship_targets')
    @patch('cloudify_aws.ecs.task.EC2ConnectionClient')
    @patch('cloudify_aws.ecs.task.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_construct_container_definitions_workdir(self,
                                                     mock_ctx,
                                                     mock_ctx2,
                                                     mock_ctx3,
                                                     mock_conn,
                                                     mock_get_targets):
        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            context.instance = mock_ctx.instance
            context.instance.relationships = []

        name = 'c1'
        image = 'myimage'
        memory = 4
        workdir = 'hello'

        container1 = make_node_context(
            Mock(),
            node='ECSContainer',
            properties={
                'name': name,
                'image': image,
                'memory': memory,
                'workdir': workdir,
            },
        )

        mock_get_targets.return_value = [
            container1.node,
        ]

        self.assertEqual(
            task.Task().construct_container_definitions(),
            [
                {
                    'name': name,
                    'image': image,
                    'memory': memory,
                    'essential': True,
                    'readonlyRootFilesystem': False,
                    'privileged': False,
                    'workingDirectory': workdir,
                },
            ],
        )

        mock_get_targets.assert_called_once_with(
            relationships=mock_ctx.instance.relationships,
            target_relationship=constants.CONTAINER_TASK_RELATIONSHIP,
            target_node='cloudify.aws.nodes.ECSContainer',
        )

    @patch('cloudify_aws.ecs.task.Task.get_appropriate_relationship_targets')
    @patch('cloudify_aws.ecs.task.EC2ConnectionClient')
    @patch('cloudify_aws.ecs.task.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_construct_container_definitions_env_vars(self,
                                                      mock_ctx,
                                                      mock_ctx2,
                                                      mock_ctx3,
                                                      mock_conn,
                                                      mock_get_targets):
        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            context.instance = mock_ctx.instance
            context.instance.relationships = []

        name = 'c1'
        image = 'myimage'
        memory = 4
        # As for port mappings, this helps with assertEqual
        env_vars = OrderedDict((
            ('say', 'hello'),
            ('wave', 'goodbye'),
        ))

        expected_env = [
            {
                'name': 'say',
                'value': 'hello',
            },
            {
                'name': 'wave',
                'value': 'goodbye',
            },
        ]

        container1 = make_node_context(
            Mock(),
            node='ECSContainer',
            properties={
                'name': name,
                'image': image,
                'memory': memory,
                'env_vars': env_vars,
            },
        )

        mock_get_targets.return_value = [
            container1.node,
        ]

        self.assertEqual(
            task.Task().construct_container_definitions(),
            [
                {
                    'name': name,
                    'image': image,
                    'memory': memory,
                    'essential': True,
                    'readonlyRootFilesystem': False,
                    'privileged': False,
                    'environment': expected_env,
                },
            ],
        )

        mock_get_targets.assert_called_once_with(
            relationships=mock_ctx.instance.relationships,
            target_relationship=constants.CONTAINER_TASK_RELATIONSHIP,
            target_node='cloudify.aws.nodes.ECSContainer',
        )

    @patch('cloudify_aws.ecs.task.Task.get_appropriate_relationship_targets')
    @patch('cloudify_aws.ecs.task.EC2ConnectionClient')
    @patch('cloudify_aws.ecs.task.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_construct_container_definitions_no_net(self,
                                                    mock_ctx,
                                                    mock_ctx2,
                                                    mock_ctx3,
                                                    mock_conn,
                                                    mock_get_targets):
        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            context.instance = mock_ctx.instance
            context.instance.relationships = []

        name = 'c1'
        image = 'myimage'
        memory = 4
        disable_networking = False

        container1 = make_node_context(
            Mock(),
            node='ECSContainer',
            properties={
                'name': name,
                'image': image,
                'memory': memory,
                'disable_networking': disable_networking,
            },
        )

        mock_get_targets.return_value = [
            container1.node,
        ]

        self.assertEqual(
            task.Task().construct_container_definitions(),
            [
                {
                    'name': name,
                    'image': image,
                    'memory': memory,
                    'essential': True,
                    'readonlyRootFilesystem': False,
                    'privileged': False,
                    'disableNetworking': disable_networking,
                },
            ],
        )

        mock_get_targets.assert_called_once_with(
            relationships=mock_ctx.instance.relationships,
            target_relationship=constants.CONTAINER_TASK_RELATIONSHIP,
            target_node='cloudify.aws.nodes.ECSContainer',
        )

    @patch('cloudify_aws.ecs.task.Task.get_appropriate_relationship_targets')
    @patch('cloudify_aws.ecs.task.EC2ConnectionClient')
    @patch('cloudify_aws.ecs.task.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_construct_container_definitions_links(self,
                                                   mock_ctx,
                                                   mock_ctx2,
                                                   mock_ctx3,
                                                   mock_conn,
                                                   mock_get_targets):
        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            context.instance = mock_ctx.instance
            context.instance.relationships = []

        name = 'c1'
        image = 'myimage'
        memory = 4
        links = ['left']

        container1 = make_node_context(
            Mock(),
            node='ECSContainer',
            properties={
                'name': name,
                'image': image,
                'memory': memory,
                'links': links,
            },
        )

        mock_get_targets.return_value = [
            container1.node,
        ]

        self.assertEqual(
            task.Task().construct_container_definitions(),
            [
                {
                    'name': name,
                    'image': image,
                    'memory': memory,
                    'essential': True,
                    'readonlyRootFilesystem': False,
                    'privileged': False,
                    'links': links,
                },
            ],
        )

        mock_get_targets.assert_called_once_with(
            relationships=mock_ctx.instance.relationships,
            target_relationship=constants.CONTAINER_TASK_RELATIONSHIP,
            target_node='cloudify.aws.nodes.ECSContainer',
        )

    @patch('cloudify_aws.ecs.task.Task.get_appropriate_relationship_targets')
    @patch('cloudify_aws.ecs.task.EC2ConnectionClient')
    @patch('cloudify_aws.ecs.task.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_construct_container_definitions_hostname(self,
                                                      mock_ctx,
                                                      mock_ctx2,
                                                      mock_ctx3,
                                                      mock_conn,
                                                      mock_get_targets):
        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            context.instance = mock_ctx.instance
            context.instance.relationships = []

        name = 'c1'
        image = 'myimage'
        memory = 4
        hostname = 'happyhost'

        container1 = make_node_context(
            Mock(),
            node='ECSContainer',
            properties={
                'name': name,
                'image': image,
                'memory': memory,
                'hostname': hostname,
            },
        )

        mock_get_targets.return_value = [
            container1.node,
        ]

        self.assertEqual(
            task.Task().construct_container_definitions(),
            [
                {
                    'name': name,
                    'image': image,
                    'memory': memory,
                    'essential': True,
                    'readonlyRootFilesystem': False,
                    'privileged': False,
                    'hostname': hostname,
                },
            ],
        )

        mock_get_targets.assert_called_once_with(
            relationships=mock_ctx.instance.relationships,
            target_relationship=constants.CONTAINER_TASK_RELATIONSHIP,
            target_node='cloudify.aws.nodes.ECSContainer',
        )

    @patch('cloudify_aws.ecs.task.Task.get_appropriate_relationship_targets')
    @patch('cloudify_aws.ecs.task.EC2ConnectionClient')
    @patch('cloudify_aws.ecs.task.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_construct_container_definitions_dns_servers(self,
                                                         mock_ctx,
                                                         mock_ctx2,
                                                         mock_ctx3,
                                                         mock_conn,
                                                         mock_get_targets):
        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            context.instance = mock_ctx.instance
            context.instance.relationships = []

        name = 'c1'
        image = 'myimage'
        memory = 4
        dns_servers = [1, 2, 3, 4]

        container1 = make_node_context(
            Mock(),
            node='ECSContainer',
            properties={
                'name': name,
                'image': image,
                'memory': memory,
                'dns_servers': dns_servers,
            },
        )

        mock_get_targets.return_value = [
            container1.node,
        ]

        self.assertEqual(
            task.Task().construct_container_definitions(),
            [
                {
                    'name': name,
                    'image': image,
                    'memory': memory,
                    'essential': True,
                    'readonlyRootFilesystem': False,
                    'privileged': False,
                    'dnsServers': dns_servers,
                },
            ],
        )

        mock_get_targets.assert_called_once_with(
            relationships=mock_ctx.instance.relationships,
            target_relationship=constants.CONTAINER_TASK_RELATIONSHIP,
            target_node='cloudify.aws.nodes.ECSContainer',
        )

    @patch('cloudify_aws.ecs.task.Task.get_appropriate_relationship_targets')
    @patch('cloudify_aws.ecs.task.EC2ConnectionClient')
    @patch('cloudify_aws.ecs.task.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_construct_container_definitions_dns_domains(self,
                                                         mock_ctx,
                                                         mock_ctx2,
                                                         mock_ctx3,
                                                         mock_conn,
                                                         mock_get_targets):
        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            context.instance = mock_ctx.instance
            context.instance.relationships = []

        name = 'c1'
        image = 'myimage'
        memory = 4
        dns_search_domains = ['local']

        container1 = make_node_context(
            Mock(),
            node='ECSContainer',
            properties={
                'name': name,
                'image': image,
                'memory': memory,
                'dns_search_domains': dns_search_domains,
            },
        )

        mock_get_targets.return_value = [
            container1.node,
        ]

        self.assertEqual(
            task.Task().construct_container_definitions(),
            [
                {
                    'name': name,
                    'image': image,
                    'memory': memory,
                    'essential': True,
                    'readonlyRootFilesystem': False,
                    'privileged': False,
                    'dnsSearchDomains': dns_search_domains,
                },
            ],
        )

        mock_get_targets.assert_called_once_with(
            relationships=mock_ctx.instance.relationships,
            target_relationship=constants.CONTAINER_TASK_RELATIONSHIP,
            target_node='cloudify.aws.nodes.ECSContainer',
        )

    @patch('cloudify_aws.ecs.task.Task.get_appropriate_relationship_targets')
    @patch('cloudify_aws.ecs.task.EC2ConnectionClient')
    @patch('cloudify_aws.ecs.task.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_construct_container_definitions_hosts_entries(self,
                                                           mock_ctx,
                                                           mock_ctx2,
                                                           mock_ctx3,
                                                           mock_conn,
                                                           mock_get_targets):
        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            context.instance = mock_ctx.instance
            context.instance.relationships = []

        name = 'c1'
        image = 'myimage'
        memory = 4
        # As with mappings, work better with assertEqual
        hosts_entries = OrderedDict((
            ('me', '192.0.2.15'),
            ('xp', '192.0.2.90'),
        ))

        expected_hosts_entries = [
            {
                'hostname': 'me',
                'ipAddress': '192.0.2.15',
            },
            {
                'hostname': 'xp',
                'ipAddress': '192.0.2.90',
            },
        ]

        container1 = make_node_context(
            Mock(),
            node='ECSContainer',
            properties={
                'name': name,
                'image': image,
                'memory': memory,
                'extra_hosts_entries': hosts_entries,
            },
        )

        mock_get_targets.return_value = [
            container1.node,
        ]

        self.assertEqual(
            task.Task().construct_container_definitions(),
            [
                {
                    'name': name,
                    'image': image,
                    'memory': memory,
                    'essential': True,
                    'readonlyRootFilesystem': False,
                    'privileged': False,
                    'extraHosts': expected_hosts_entries,
                },
            ],
        )

        mock_get_targets.assert_called_once_with(
            relationships=mock_ctx.instance.relationships,
            target_relationship=constants.CONTAINER_TASK_RELATIONSHIP,
            target_node='cloudify.aws.nodes.ECSContainer',
        )

    @patch('cloudify_aws.ecs.task.Task.get_appropriate_relationship_targets')
    @patch('cloudify_aws.ecs.task.EC2ConnectionClient')
    @patch('cloudify_aws.ecs.task.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_construct_container_definitions_mounts(self,
                                                    mock_ctx,
                                                    mock_ctx2,
                                                    mock_ctx3,
                                                    mock_conn,
                                                    mock_get_targets):
        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            context.instance = mock_ctx.instance
            context.instance.relationships = []

        name = 'c1'
        image = 'myimage'
        memory = 4
        mount_points = ['a', 'b', 'c']

        container1 = make_node_context(
            Mock(),
            node='ECSContainer',
            properties={
                'name': name,
                'image': image,
                'memory': memory,
                'mount_points': mount_points,
            },
        )

        mock_get_targets.return_value = [
            container1.node,
        ]

        self.assertEqual(
            task.Task().construct_container_definitions(),
            [
                {
                    'name': name,
                    'image': image,
                    'memory': memory,
                    'essential': True,
                    'readonlyRootFilesystem': False,
                    'privileged': False,
                    'mountPoints': mount_points,
                },
            ],
        )

        mock_get_targets.assert_called_once_with(
            relationships=mock_ctx.instance.relationships,
            target_relationship=constants.CONTAINER_TASK_RELATIONSHIP,
            target_node='cloudify.aws.nodes.ECSContainer',
        )

    @patch('cloudify_aws.ecs.task.Task.get_appropriate_relationship_targets')
    @patch('cloudify_aws.ecs.task.EC2ConnectionClient')
    @patch('cloudify_aws.ecs.task.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_construct_container_definitions_volumes(self,
                                                     mock_ctx,
                                                     mock_ctx2,
                                                     mock_ctx3,
                                                     mock_conn,
                                                     mock_get_targets):
        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            context.instance = mock_ctx.instance
            context.instance.relationships = []

        name = 'c1'
        image = 'myimage'
        memory = 4
        volumes_from = ['b', 'a', 't']

        container1 = make_node_context(
            Mock(),
            node='ECSContainer',
            properties={
                'name': name,
                'image': image,
                'memory': memory,
                'volumes_from': volumes_from,
            },
        )

        mock_get_targets.return_value = [
            container1.node,
        ]

        self.assertEqual(
            task.Task().construct_container_definitions(),
            [
                {
                    'name': name,
                    'image': image,
                    'memory': memory,
                    'essential': True,
                    'readonlyRootFilesystem': False,
                    'privileged': False,
                    'volumesFrom': volumes_from,
                },
            ],
        )

        mock_get_targets.assert_called_once_with(
            relationships=mock_ctx.instance.relationships,
            target_relationship=constants.CONTAINER_TASK_RELATIONSHIP,
            target_node='cloudify.aws.nodes.ECSContainer',
        )

    @patch('cloudify_aws.ecs.task.Task.get_appropriate_relationship_targets')
    @patch('cloudify_aws.ecs.task.EC2ConnectionClient')
    @patch('cloudify_aws.ecs.task.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_construct_container_definitions_non_essential(self,
                                                           mock_ctx,
                                                           mock_ctx2,
                                                           mock_ctx3,
                                                           mock_conn,
                                                           mock_get_targets):
        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            context.instance = mock_ctx.instance
            context.instance.relationships = []

        name = 'c1'
        image = 'myimage'
        memory = 4
        essential = False

        container1 = make_node_context(
            Mock(),
            node='ECSContainer',
            properties={
                'name': name,
                'image': image,
                'memory': memory,
                'essential': essential,
            },
        )

        mock_get_targets.return_value = [
            container1.node,
        ]

        self.assertEqual(
            task.Task().construct_container_definitions(),
            [
                {
                    'name': name,
                    'image': image,
                    'memory': memory,
                    'essential': False,
                    'readonlyRootFilesystem': False,
                    'privileged': False,
                },
            ],
        )

        mock_get_targets.assert_called_once_with(
            relationships=mock_ctx.instance.relationships,
            target_relationship=constants.CONTAINER_TASK_RELATIONSHIP,
            target_node='cloudify.aws.nodes.ECSContainer',
        )

    @patch('cloudify_aws.ecs.task.Task.get_appropriate_relationship_targets')
    @patch('cloudify_aws.ecs.task.EC2ConnectionClient')
    @patch('cloudify_aws.ecs.task.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_construct_container_definitions_privileged(self,
                                                        mock_ctx,
                                                        mock_ctx2,
                                                        mock_ctx3,
                                                        mock_conn,
                                                        mock_get_targets):
        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            context.instance = mock_ctx.instance
            context.instance.relationships = []

        name = 'c1'
        image = 'myimage'
        memory = 4
        privileged = True

        container1 = make_node_context(
            Mock(),
            node='ECSContainer',
            properties={
                'name': name,
                'image': image,
                'memory': memory,
                'privileged': privileged,
            },
        )

        mock_get_targets.return_value = [
            container1.node,
        ]

        self.assertEqual(
            task.Task().construct_container_definitions(),
            [
                {
                    'name': name,
                    'image': image,
                    'memory': memory,
                    'essential': True,
                    'readonlyRootFilesystem': False,
                    'privileged': True,
                },
            ],
        )

        mock_get_targets.assert_called_once_with(
            relationships=mock_ctx.instance.relationships,
            target_relationship=constants.CONTAINER_TASK_RELATIONSHIP,
            target_node='cloudify.aws.nodes.ECSContainer',
        )

    @patch('cloudify_aws.ecs.task.Task.get_appropriate_relationship_targets')
    @patch('cloudify_aws.ecs.task.EC2ConnectionClient')
    @patch('cloudify_aws.ecs.task.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_construct_container_definitions_read_only(self,
                                                       mock_ctx,
                                                       mock_ctx2,
                                                       mock_ctx3,
                                                       mock_conn,
                                                       mock_get_targets):
        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            context.instance = mock_ctx.instance
            context.instance.relationships = []

        name = 'c1'
        image = 'myimage'
        memory = 4
        read_only = True

        container1 = make_node_context(
            Mock(),
            node='ECSContainer',
            properties={
                'name': name,
                'image': image,
                'memory': memory,
                'read_only_root_filesystem': read_only,
            },
        )

        mock_get_targets.return_value = [
            container1.node,
        ]

        self.assertEqual(
            task.Task().construct_container_definitions(),
            [
                {
                    'name': name,
                    'image': image,
                    'memory': memory,
                    'essential': True,
                    'readonlyRootFilesystem': True,
                    'privileged': False,
                },
            ],
        )

        mock_get_targets.assert_called_once_with(
            relationships=mock_ctx.instance.relationships,
            target_relationship=constants.CONTAINER_TASK_RELATIONSHIP,
            target_node='cloudify.aws.nodes.ECSContainer',
        )

    @patch('cloudify_aws.ecs.task.Task.get_appropriate_relationship_targets')
    @patch('cloudify_aws.ecs.task.EC2ConnectionClient')
    @patch('cloudify_aws.ecs.task.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_construct_container_definitions_log_driver(self,
                                                        mock_ctx,
                                                        mock_ctx2,
                                                        mock_ctx3,
                                                        mock_conn,
                                                        mock_get_targets):
        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            context.instance = mock_ctx.instance
            context.instance.relationships = []

        name = 'c1'
        image = 'myimage'
        memory = 4
        log_driver = 'jumberlack'

        container1 = make_node_context(
            Mock(),
            node='ECSContainer',
            properties={
                'name': name,
                'image': image,
                'memory': memory,
                'log_driver': log_driver,
            },
        )

        mock_get_targets.return_value = [
            container1.node,
        ]

        self.assertEqual(
            task.Task().construct_container_definitions(),
            [
                {
                    'name': name,
                    'image': image,
                    'memory': memory,
                    'essential': True,
                    'readonlyRootFilesystem': False,
                    'privileged': False,
                    'logConfiguration': {
                        'logDriver': log_driver,
                    },
                },
            ],
        )

        mock_get_targets.assert_called_once_with(
            relationships=mock_ctx.instance.relationships,
            target_relationship=constants.CONTAINER_TASK_RELATIONSHIP,
            target_node='cloudify.aws.nodes.ECSContainer',
        )

    @patch('cloudify_aws.ecs.task.Task.get_appropriate_relationship_targets')
    @patch('cloudify_aws.ecs.task.EC2ConnectionClient')
    @patch('cloudify_aws.ecs.task.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_construct_container_definitions_log_options(self,
                                                         mock_ctx,
                                                         mock_ctx2,
                                                         mock_ctx3,
                                                         mock_conn,
                                                         mock_get_targets):
        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            context.instance = mock_ctx.instance
            context.instance.relationships = []

        name = 'c1'
        image = 'myimage'
        memory = 4
        log_driver = 'jumberlack'
        log_driver_options = ['yes', 'no']

        container1 = make_node_context(
            Mock(),
            node='ECSContainer',
            properties={
                'name': name,
                'image': image,
                'memory': memory,
                'log_driver': log_driver,
                'log_driver_options': log_driver_options,
            },
        )

        mock_get_targets.return_value = [
            container1.node,
        ]

        self.assertEqual(
            task.Task().construct_container_definitions(),
            [
                {
                    'name': name,
                    'image': image,
                    'memory': memory,
                    'essential': True,
                    'readonlyRootFilesystem': False,
                    'privileged': False,
                    'logConfiguration': {
                        'logDriver': log_driver,
                        'options': log_driver_options,
                    },
                },
            ],
        )

        mock_get_targets.assert_called_once_with(
            relationships=mock_ctx.instance.relationships,
            target_relationship=constants.CONTAINER_TASK_RELATIONSHIP,
            target_node='cloudify.aws.nodes.ECSContainer',
        )

    @patch('cloudify_aws.ecs.task.Task.get_appropriate_relationship_targets')
    @patch('cloudify_aws.ecs.task.EC2ConnectionClient')
    @patch('cloudify_aws.ecs.task.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_construct_container_definitions_username(self,
                                                      mock_ctx,
                                                      mock_ctx2,
                                                      mock_ctx3,
                                                      mock_conn,
                                                      mock_get_targets):
        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            context.instance = mock_ctx.instance
            context.instance.relationships = []

        name = 'c1'
        image = 'myimage'
        memory = 4
        user = 'george'

        container1 = make_node_context(
            Mock(),
            node='ECSContainer',
            properties={
                'name': name,
                'image': image,
                'memory': memory,
                'user': user,
            },
        )

        mock_get_targets.return_value = [
            container1.node,
        ]

        self.assertEqual(
            task.Task().construct_container_definitions(),
            [
                {
                    'name': name,
                    'image': image,
                    'memory': memory,
                    'essential': True,
                    'readonlyRootFilesystem': False,
                    'privileged': False,
                    'username': user,
                },
            ],
        )

        mock_get_targets.assert_called_once_with(
            relationships=mock_ctx.instance.relationships,
            target_relationship=constants.CONTAINER_TASK_RELATIONSHIP,
            target_node='cloudify.aws.nodes.ECSContainer',
        )

    @patch('cloudify_aws.ecs.task.Task.get_appropriate_relationship_targets')
    @patch('cloudify_aws.ecs.task.EC2ConnectionClient')
    @patch('cloudify_aws.ecs.task.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_construct_container_definitions_security(self,
                                                      mock_ctx,
                                                      mock_ctx2,
                                                      mock_ctx3,
                                                      mock_conn,
                                                      mock_get_targets):
        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            context.instance = mock_ctx.instance
            context.instance.relationships = []

        name = 'c1'
        image = 'myimage'
        memory = 4
        security_options = ['disable_apt', 'ignore_ddos', 'be_safe_not_sorry']

        container1 = make_node_context(
            Mock(),
            node='ECSContainer',
            properties={
                'name': name,
                'image': image,
                'memory': memory,
                'security_options': security_options,
            },
        )

        mock_get_targets.return_value = [
            container1.node,
        ]

        self.assertEqual(
            task.Task().construct_container_definitions(),
            [
                {
                    'name': name,
                    'image': image,
                    'memory': memory,
                    'essential': True,
                    'readonlyRootFilesystem': False,
                    'privileged': False,
                    'dockerSecurityOptions': security_options,
                },
            ],
        )

        mock_get_targets.assert_called_once_with(
            relationships=mock_ctx.instance.relationships,
            target_relationship=constants.CONTAINER_TASK_RELATIONSHIP,
            target_node='cloudify.aws.nodes.ECSContainer',
        )

    @patch('cloudify_aws.ecs.task.Task.get_appropriate_relationship_targets')
    @patch('cloudify_aws.ecs.task.EC2ConnectionClient')
    @patch('cloudify_aws.ecs.task.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_construct_container_definitions_ulimits(self,
                                                     mock_ctx,
                                                     mock_ctx2,
                                                     mock_ctx3,
                                                     mock_conn,
                                                     mock_get_targets):
        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            context.instance = mock_ctx.instance
            context.instance.relationships = []

        name = 'c1'
        image = 'myimage'
        memory = 4
        ulimits = ['something', 'somethingelse', 'yes']

        container1 = make_node_context(
            Mock(),
            node='ECSContainer',
            properties={
                'name': name,
                'image': image,
                'memory': memory,
                'ulimits': ulimits,
            },
        )

        mock_get_targets.return_value = [
            container1.node,
        ]

        self.assertEqual(
            task.Task().construct_container_definitions(),
            [
                {
                    'name': name,
                    'image': image,
                    'memory': memory,
                    'essential': True,
                    'readonlyRootFilesystem': False,
                    'privileged': False,
                    'ulimits': ulimits,
                },
            ],
        )

        mock_get_targets.assert_called_once_with(
            relationships=mock_ctx.instance.relationships,
            target_relationship=constants.CONTAINER_TASK_RELATIONSHIP,
            target_node='cloudify.aws.nodes.ECSContainer',
        )

    @patch('cloudify_aws.ecs.task.Task.get_appropriate_relationship_targets')
    @patch('cloudify_aws.ecs.task.EC2ConnectionClient')
    @patch('cloudify_aws.ecs.task.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_construct_container_definitions_labels(self,
                                                    mock_ctx,
                                                    mock_ctx2,
                                                    mock_ctx3,
                                                    mock_conn,
                                                    mock_get_targets):
        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            context.instance = mock_ctx.instance
            context.instance.relationships = []

        name = 'c1'
        image = 'myimage'
        memory = 4
        docker_labels = ['do', 'not', 'label', 'docker']

        container1 = make_node_context(
            Mock(),
            node='ECSContainer',
            properties={
                'name': name,
                'image': image,
                'memory': memory,
                'docker_labels': docker_labels,
            },
        )

        mock_get_targets.return_value = [
            container1.node,
        ]

        self.assertEqual(
            task.Task().construct_container_definitions(),
            [
                {
                    'name': name,
                    'image': image,
                    'memory': memory,
                    'essential': True,
                    'readonlyRootFilesystem': False,
                    'privileged': False,
                    'dockerLabels': docker_labels,
                },
            ],
        )

        mock_get_targets.assert_called_once_with(
            relationships=mock_ctx.instance.relationships,
            target_relationship=constants.CONTAINER_TASK_RELATIONSHIP,
            target_node='cloudify.aws.nodes.ECSContainer',
        )

    @patch('cloudify_aws.ecs.task.Task.construct_volume_definitions')
    @patch('cloudify_aws.ecs.task.Task.construct_container_definitions')
    @patch('cloudify_aws.ecs.task.EC2ConnectionClient')
    @patch('cloudify_aws.ecs.task.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_create(self,
                    mock_ctx,
                    mock_ctx2,
                    mock_ctx3,
                    mock_conn,
                    mock_containers,
                    mock_volumes):
        expected_arn = 'arn-e'
        expected_name = 'task1'
        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            make_node_context(
                context,
                node='ECSTask',
                properties={
                    'name': expected_name,
                },
            )
            context.instance = mock_ctx.instance
            context.instance.relationships = []
        expected_containers = [
            {
                'name': 'yes',
            },
            {
                'name': 'no',
            },
        ]
        expected_container_names = [c['name'] for c in expected_containers]
        expected_volumes = ['some', 'volumes']

        mock_containers.return_value = expected_containers
        mock_volumes.return_value = expected_volumes

        mock_client = configure_mock_connection(mock_conn)
        mock_client.register_task_definition.return_value = {
            'taskDefinition': {
                'taskDefinitionArn': expected_arn,
            },
        }

        task.Task().create()

        mock_client.register_task_definition.assert_called_once_with(
            family=expected_name,
            containerDefinitions=expected_containers,
            volumes=expected_volumes,
        )

        self.assertEqual(
            mock_ctx.instance.runtime_properties['container_names'],
            expected_container_names,
        )

    @patch('cloudify_aws.ecs.task.EC2ConnectionClient')
    @patch('cloudify_aws.ecs.task.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_delete_success(self,
                            mock_ctx,
                            mock_ctx2,
                            mock_ctx3,
                            mock_conn):
        expected_arn = 'myarn'
        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            make_node_context(
                context,
                node='ECSTask',
                properties={
                    'name': 'mytask',
                },
                runtime_properties={
                    constants.EXTERNAL_RESOURCE_ID: expected_arn,
                },
            )
            context.instance = mock_ctx.instance
            context.instance.relationships = []

        mock_client = configure_mock_connection(mock_conn)

        task.Task().delete()

        mock_client.deregister_task_definition.assert_called_once_with(
            taskDefinition=expected_arn,
        )

    @patch('cloudify_aws.ecs.task.EC2ConnectionClient')
    @patch('cloudify_aws.ecs.task.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_get_resource(self,
                          mock_ctx,
                          mock_ctx2,
                          mock_ctx3,
                          mock_conn):
        expected_name = 'cake'
        expected_cluster = 'carrot'
        expected_result = ['cream cheese']
        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            make_node_context(
                context,
                node='ECSTask',
                properties={
                    'name': expected_name,
                },
            )
            context.instance = mock_ctx.instance
            context.instance.relationships = []

        mock_client = configure_mock_connection(mock_conn)
        mock_client.list_clusters.return_value = {
            'clusterArns': [expected_cluster],
        }
        mock_client.list_tasks.return_value = {
            'taskArns': expected_result,
        }

        result = task.Task().get_resource()

        self.assertEqual(result, expected_result)

        mock_client.list_clusters.assert_called_once_with()
        mock_client.list_tasks.assert_called_once_with(
            cluster=expected_cluster,
            family=expected_name,
        )

    @patch('cloudify_aws.ecs.task.EC2ConnectionClient')
    @patch('cloudify_aws.ecs.task.ctx')
    @patch('cloudify_aws.base.ctx')
    @patch('cloudify_aws.utils.ctx')
    def test_get_no_resource(self,
                             mock_ctx,
                             mock_ctx2,
                             mock_ctx3,
                             mock_conn):
        expected_name = 'no cake'
        expected_result = []
        for context in (mock_ctx, mock_ctx2, mock_ctx3):
            make_node_context(
                context,
                node='ECSTask',
                properties={
                    'name': expected_name,
                },
            )
            context.instance = mock_ctx.instance
            context.instance.relationships = []

        mock_client = configure_mock_connection(mock_conn)
        mock_client.list_clusters.return_value = {'clusterArns': []}

        result = task.Task().get_resource()

        self.assertEqual(result, expected_result)

        mock_client.list_clusters.assert_called_once_with()
        self.assertEqual(mock_client.list_tasks.call_count, 0)

    @patch('cloudify_aws.ecs.task.Task')
    def test_create_calls_correct_method(self, mock_task):
        args = [1, 2, 3]
        expected = 'the right result'
        mock_task.return_value.created.return_value = expected

        result = task.create(args)

        self.assertEqual(result, expected)
        mock_task.return_value.created.assert_called_once_with(args)

    @patch('cloudify_aws.ecs.task.Task')
    def test_delete_calls_correct_method(self, mock_task):
        args = [1, 2, 3]
        expected = 'the right result'
        mock_task.return_value.deleted.return_value = expected

        result = task.delete(args)

        self.assertEqual(result, expected)
        mock_task.return_value.deleted.assert_called_once_with(args)

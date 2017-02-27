########
# Copyright (c) 2017 GigaSpaces Technologies Ltd. All rights reserved
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

# Built-in Imports
import testtools
from cloudify.state import current_ctx
from boto.exception import EC2ResponseError
from boto.ec2.ec2object import TaggedEC2Object

# Third Party Imports
import mock
from moto import mock_ec2
from cloudify_aws.vpc import routetable
from cloudify_aws import constants, connection
from cloudify_aws.base import AwsBase, AwsBaseNode, AwsBaseRelationship, \
    RouteMixin
from cloudify.mocks import MockCloudifyContext, MockContext
from cloudify.exceptions import NonRecoverableError, RecoverableError


class TestCloudifyAwsBase(testtools.TestCase):

    states = [{'name': 'create',
               'success': ['available'],
               'waiting': ['pending'],
               'failed': ['error']}]

    def get_mock_ctx(self, test_name, retry_number=0):
        """ Creates a mock context for the base
            tests
        """
        test_node_id = test_name
        test_properties = {
            constants.AWS_CONFIG_PROPERTY: {},
            'use_external_resource': False,
            'resource_id': '{0}'.format(test_name)
        }

        operation = {
            'retry_number': retry_number
        }
        ctx = MockCloudifyContext(
                node_id=test_node_id,
                deployment_id=test_name,
                properties=test_properties,
                operation=operation,
                provider_context={'resources': {}}
        )
        ctx.node.type_hierarchy = ['cloudify.nodes.Root']
        return ctx

    def mock_relationship_context(self, testname):

        source_context = MockContext({
            'node': MockContext({
                'properties': {
                    constants.AWS_CONFIG_PROPERTY: {},
                    'use_external_resource': False,
                    'resource_id': ''
                }
            }),
            'instance': MockContext({
                'runtime_properties': {
                    'aws_resource_id': 'r-abc1234'
                }
            })
        })

        target_context = MockContext({
            'node': MockContext({
                'properties': {
                    constants.AWS_CONFIG_PROPERTY: {},
                    'use_external_resource': False,
                    'resource_id': 'r-abc12345'
                }
            }),
            'instance': MockContext({
                'runtime_properties': {
                    'aws_resource_id': 'r-abc12346',
                    'relationships':
                        'cloudify.aws.relationships.root_connected_to_root'
                }
            })
        })

        relationship_context = MockCloudifyContext(
                node_id=testname, source=source_context,
                target=target_context)

        setattr(relationship_context.source.node,
                'type_hierarchy',
                ['cloudify.nodes.Root', 'cloudify.nodes.Root']
                )

        return relationship_context

    def create_vpc_client(self):
        return connection.VPCConnection()

    @mock_ec2
    def test_base_operation_functions(self):
        """ Tests that the base operations
            create, start, stop, delete
            returns False.
        """
        ctx = self.get_mock_ctx('test_base_operation_functions')
        current_ctx.set(ctx=ctx)
        resource = AwsBaseNode('root', [], resource_states=[])
        # testing operations
        for operation in ('create', 'start', 'stop', 'delete'):
            function = getattr(resource, operation)
            output = function()
            self.assertEquals(False, output)

    @mock_ec2
    def test_base_operation_handler_functions(self):
        """ Tests that the base operation helpers
            create_helper, start_helper, stop_helper, delete_helper
            calls cloudify_resource_state_change_handler function
            and run as expected.
        """
        ctx = self.get_mock_ctx('test_base_operation_handler_functions')
        current_ctx.set(ctx=ctx)
        resource = AwsBaseNode('root', [], resource_states=[])

        with mock.patch('cloudify_aws.base.AwsBaseNode'
                        '.get_and_filter_resources_by_matcher') \
                as mock_get_and_filter_resources_by_matcher:
            mock_get_and_filter_resources_by_matcher.return_value = []

            for operation in ('create', 'start', 'stop', 'delete'):
                ctx.operation._operation_context['name'] = operation
                with mock.patch('cloudify_aws.base.AwsBaseNode.{0}'
                                .format(operation)) as mock_operation:
                    function = getattr(resource, '{0}_helper'
                                       .format(operation))
                    output = function()
                    if operation in ('create_helper', 'start_helper',
                                     'modify_helper', 'stop_helper'):
                        self.assertIsNone(output)
                    elif operation == 'delete_helper':
                        self.assertEqual(output, True)

                    mock_operation.return_value = False
                    function = getattr(resource, '{0}_helper'
                                       .format(operation))
                    with self.assertRaisesRegexp(
                            NonRecoverableError,
                            'Neither external resource, nor Cloudify '
                            'resource'):
                        function()

            with mock.patch('cloudify_aws.base.AwsBaseNode.modify_attributes',
                            return_value=True):
                ctx.operation._operation_context['name'] = 'modify'
                function = getattr(resource, 'modify_helper')
                self.assertEqual(True, function({'key': 'value'}))

    @mock_ec2
    def test_tag_resource_raises_error(self):
        """ Tests that when add_tags fails
            tag_resource raises the right error.
        """
        ctx = self.get_mock_ctx('test_tag_resource_raises_error')
        current_ctx.set(ctx=ctx)
        resource = AwsBaseNode('root', [], resource_states=[])
        ctx.node.properties['name'] = 'root'
        test_resource = TaggedEC2Object()
        tags = []
        with mock.patch(
                'boto.ec2.ec2object.TaggedEC2Object.add_tags') \
                as mock_add_tags:
            mock_add_tags.side_effect = EC2ResponseError(
                    mock.Mock(return_value={'status': 404}),
                    'error')
            ex = self.assertRaises(
                    NonRecoverableError,
                    resource._tag_resource,
                    test_resource,
                    tags)
            self.assertIn(
                    'unable to tag resource name', ex.message)

    @mock_ec2
    def test_get_all_matching(self):
        """ Tests that get_all_matching
            returns the right matched resources.
        """
        ctx = self.get_mock_ctx('test_get_all_matching')
        current_ctx.set(ctx=ctx)
        ec2_client = connection.EC2ConnectionClient().client()
        resource = AwsBaseNode('root', [], ec2_client, resource_states=[])
        reservation = ec2_client.run_instances(
                'ami-e214778a', instance_type='t1.micro')
        instance_id = reservation.instances[0].id
        list_of_ids = [instance_id]
        resource.get_all_handler['function'] = \
            resource.client.get_all_reservations
        resource.get_all_handler['argument'] = 'instance_ids'
        self.assertEqual(reservation.id,
                         resource.get_all_matching(list_of_ids)[0].id)

    @mock_ec2
    def test_delete_external_resource_naively(self):
        """ Tests that delete_external_resource_naively
            returns True when the resource is external.
        """
        ctx = self.get_mock_ctx('test_delete_external_resource_naively')
        current_ctx.set(ctx=ctx)
        resource = AwsBaseNode('root', [], resource_states=[])
        resource.is_external_resource = True
        self.assertEqual(True, resource.delete_external_resource_naively())

    @mock_ec2
    @mock.patch('cloudify_aws.base.AwsBaseNode.get_resource')
    def test_use_external_resource_naively(self, *_):
        """ Tests that use_external_resource_naively
            returns True when the resource is external.
        """
        ctx = self.get_mock_ctx('test_use_external_resource_naively')
        current_ctx.set(ctx=ctx)
        resource = AwsBaseNode('root', [], resource_states=[])
        resource.is_external_resource = True
        self.assertEqual(True, resource.use_external_resource_naively())

    @mock_ec2
    def test_cloudify_operation_exit_handler(self):
        """ Tests that operation_exit_handler
            behaves as expected in each state.
        """
        ctx = self.get_mock_ctx('test_cloudify_operation_exit_handler')
        current_ctx.set(ctx=ctx)
        resource = AwsBaseNode('root', [], resource_states=self.states)
        self.assertEqual(True, resource.cloudify_operation_exit_handler(
                'available', 'create'))
        self.assertIsNone(resource.cloudify_operation_exit_handler('pending',
                                                                   'create'))
        with self.assertRaisesRegexp(
                NonRecoverableError,
                'Resource is in failed state'):
            resource.cloudify_operation_exit_handler('error', 'create')
        with self.assertRaisesRegexp(
                RecoverableError,
                'The resource is not in state'):
            resource.cloudify_operation_exit_handler('nonvalid', 'create')

    @mock_ec2
    @mock.patch('cloudify_aws.base.AwsBaseNode.get_resource',
                return_value=None)
    @mock.patch('cloudify_aws.utils.validate_node_property')
    def test_creation_validation_external_doesnt_exists(self, *_):
        """ Tests that creation_validation raises the right error
            when the resource is external but doesn't exists.
        """
        ctx = self.get_mock_ctx(
                'test_creation_validation_external_doesnt_exists')
        current_ctx.set(ctx=ctx)
        resource = AwsBaseNode('root', [], resource_states=[])
        resource.required_properties = ['description']
        resource.is_external_resource = True
        with self.assertRaisesRegexp(
                NonRecoverableError,
                'External resource, but the supplied'):
            resource.creation_validation()

    @mock_ec2
    @mock.patch('cloudify_aws.base.AwsBaseNode.get_resource')
    @mock.patch('cloudify_aws.utils.validate_node_property')
    def test_creation_validation_not_external_exists(self, *_):
        """ Tests that creation_validation raises the right error
            when the resource is not external but does exists.
        """
        ctx = self.get_mock_ctx(
                'test_creation_validation_not_external_exists')
        current_ctx.set(ctx=ctx)
        resource = AwsBaseNode('root', [], resource_states=[])
        resource.required_properties = ['description']
        with self.assertRaisesRegexp(
                NonRecoverableError,
                'Not external resource'):
            resource.creation_validation()

    @mock_ec2
    @mock.patch('cloudify_aws.base.AwsBaseRelationship'
                '.filter_for_single_resource', return_value='r-1234abcd')
    def test_get_source_resource(self, *_):
        """ Tests that get_source_resource
            gets the right resource.
        """
        ctx = self.mock_relationship_context('test_get_source_resource')
        current_ctx.set(ctx=ctx)
        relation = AwsBaseRelationship()
        ctx.source.instance.runtime_properties['aws_resource_id'] = \
            relation.source_resource_id
        resource_id = 'r-1234abcd'
        self.assertEqual(resource_id, relation.get_source_resource())

    @mock_ec2
    @mock.patch('cloudify_aws.base.AwsBaseRelationship.get_source_resource')
    def test_disassociate_external_resource_naively(self, *_):
        """ Tests that disassociate_external_resource_naively
            returns True when the resource is external.
        """
        ctx = self.mock_relationship_context(
                'test_disassociate_external_resource_naively')
        current_ctx.set(ctx=ctx)
        relation = AwsBaseRelationship()
        relation.source_is_external_resource = True
        self.assertEqual(True,
                         relation.disassociate_external_resource_naively())

    @mock_ec2
    def test_relationship_operation_functions(self):
        """ Tests that the base relationship operations
            associate, disassociate
            returns False.
        """
        ctx = self.mock_relationship_context(
                'test_relationship_operation_functions')
        current_ctx.set(ctx=ctx)
        relation = AwsBaseRelationship()
        # testing operations
        for operation in ('associate', 'disassociate'):
            function = getattr(relation, operation)
            output = function()
            self.assertEquals(False, output)

    @mock_ec2
    def test_relationship_operation_handler_functions(self):
        """ Tests that the base relationship operation helpers
            associate_helper, disassociate_helper
            runs as expected.
        """
        ctx = self.mock_relationship_context(
                'test_relationship_operation_handler_functions')
        current_ctx.set(ctx=ctx)
        relation = AwsBaseRelationship()
        for operation in ('associate', 'disassociate'):
            with mock.patch('cloudify_aws.base.AwsBaseRelationship.{0}'
                            .format(operation)) as mock_operation:
                function = getattr(relation, '{0}_helper'
                                   .format(operation))
                output = function()
                self.assertEqual(output, True)
                mock_operation.return_value = False
                function = getattr(relation, '{0}_helper'
                                   .format(operation))
            with self.assertRaisesRegexp(
                    NonRecoverableError,
                    'Source is neither external resource, '
                    'nor Cloudify resource'):
                function()

    @mock_ec2
    def test_use_source_external_resource_naively(self):
        """ Tests that use_source_external_resource_naively
            returns True when the resource is external
            or calls raise_forbidden_external_resource.
        """
        ctx = self.mock_relationship_context(
                'test_use_source_external_resource_naively')
        current_ctx.set(ctx=ctx)
        relation = AwsBaseRelationship()
        relation.source_is_external_resource = True
        with mock.patch('cloudify_aws.base.AwsBaseRelationship'
                        '.get_source_resource') as mock_get_source_resource:
            self.assertEqual(True,
                             relation.use_source_external_resource_naively())
            mock_get_source_resource._mock_return_value = None
            with self.assertRaisesRegexp(
                NonRecoverableError,
                    'is not in this account'):
                relation.use_source_external_resource_naively()

    @mock_ec2
    def test_get_target_ids_of_relationship_type(self):
        """ Tests that get_target_ids_of_relationship_type
            returns the right target id.
        """
        ctx = self.mock_relationship_context(
                'test_get_target_ids_of_relationship_type')
        current_ctx.set(ctx=ctx)
        relation = AwsBaseRelationship()
        relationship_type = ctx.target.instance.runtime_properties[
            'relationships']
        with mock.patch('cloudify_aws.base.AwsBase'
                        '.get_related_targets_and_types') \
                as mock_get_related_targets_and_types:
            resource_id = 'r-1234abcd'
            mock_get_related_targets_and_types.return_value = {
                'cloudify.aws.relationships.root_connected_to_root':
                    resource_id}
            relationships = relation.get_related_targets_and_types(
                    relationship_type)
            self.assertIn(resource_id,
                          relation.get_target_ids_of_relationship_type(
                                  relationship_type, relationships))

    @mock_ec2
    def test_get_related_targets_and_types(self):
        """ Tests that get_related_targets_and_types
            returns the right targets_and_types.
        """
        ctx = self.mock_relationship_context(
                'test_get_related_targets_and_types')
        current_ctx.set(ctx=ctx)
        relation = AwsBaseRelationship()
        relationships = []
        self.assertEqual({}, relation.get_related_targets_and_types(
                relationships))

    @mock_ec2
    def test_get_and_filter_resources_by_matcher(self):
        """ Tests that get_and_filter_resources_by_matcher
            returns the right targets_and_types.
        """
        ctx = self.get_mock_ctx('test_get_and_filter_resources_by_matcher')
        current_ctx.set(ctx=ctx)
        ec2_client = connection.EC2ConnectionClient().client()
        resource = AwsBase(client=ec2_client)
        reservation = ec2_client.run_instances(
                'ami-e214778a', instance_type='t1.micro')
        instance_id = reservation.instances[0].id
        list_of_ids = [instance_id]
        filter_function = resource.client.get_all_reservations
        filters = {'instance_ids': list_of_ids}
        self.assertEqual(reservation.id,
                         resource.get_and_filter_resources_by_matcher(
                                 filter_function, filters)[0].id)

    @mock_ec2
    def test_get_and_filter_resources_by_matcher_response_error(self):
        """ Tests that get_and_filter_resources_by_matcher
            returns raises an error when tje resource
            does not exists.
        """
        ctx = self.get_mock_ctx(
                'test_get_and_filter_resources_by_matcher_response_error')
        current_ctx.set(ctx=ctx)
        ec2_client = connection.EC2ConnectionClient().client()
        resource = AwsBase(client=ec2_client)
        list_of_ids = ['i-3333333']
        filter_function = resource.client.get_all_reservations
        filters = {'instance_ids': list_of_ids}
        ex = self.assertRaises(
                NonRecoverableError,
                resource.get_and_filter_resources_by_matcher,
                filter_function,
                filters,
                'error')
        self.assertIn(
                'does not exist', ex.message)

    @mock_ec2
    def test_execute(self):
        """ Tests that execute runs and
            returns the expected return value.
        """
        ctx = self.get_mock_ctx('test_execute')
        current_ctx.set(ctx=ctx)
        ec2_client = connection.EC2ConnectionClient().client()
        resource = AwsBase(client=ec2_client)
        output = resource.execute(resource.client.run_instances,
                                  dict(image_id='ami-e214778a',
                                       instance_type='t1.micro'))
        reservation = resource.client.get_all_reservations()
        self.assertEqual(output.id, reservation[0].id)

    @mock_ec2
    def test_execute_response_error(self):
        """ Tests that execute raises
            an error when the execution fails.
        """
        ctx = self.get_mock_ctx('test_execute_response_error')
        current_ctx.set(ctx=ctx)
        ec2_client = connection.EC2ConnectionClient().client()
        resource = AwsBase(client=ec2_client)
        with mock.patch(
                'boto.ec2.connection.EC2Connection.run_instances') \
                as mock_run_instances:
            mock_run_instances.side_effect = \
                EC2ResponseError(
                        mock.Mock(return_value={'status': 404}),
                        'error')
            ex = self.assertRaises(
                    NonRecoverableError,
                    resource.execute,
                    resource.client.run_instances,
                    dict(image_id='ami-e214778a',
                         instance_type='t1.micro'))
            self.assertIn(
                    'error', ex.message)

    @mock_ec2
    def test_execute_raise_on_falsy(self):
        """ Tests that execute return False
            when the execution failed
            and raise_on_falsy flag is True.
        """
        ctx = self.get_mock_ctx('test_execute_raise_on_falsy')
        current_ctx.set(ctx=ctx)
        ec2_client = connection.EC2ConnectionClient().client()
        resource = AwsBase(client=ec2_client)
        with mock.patch(
                'boto.ec2.connection.EC2Connection.run_instances') \
                as mock_run_instances:
            mock_run_instances.return_value = None
            ex = self.assertRaises(
                    NonRecoverableError,
                    resource.execute,
                    resource.client.run_instances,
                    dict(image_id='ami-e214778a',
                         instance_type='t1.micro'),
                    raise_on_falsy=True)
            self.assertIn(
                    'returned False', ex.message)

    @mock_ec2
    def test_create_and_delete_route(self):
        """ Tests that create_route
            creates route with each input
            and delete_route deletes the route.
        """
        ctx = self.get_mock_ctx('test_create_and_delete_route')
        ctx.node.properties['name'] = 'test_create_and_delete_route'
        current_ctx.set(ctx=ctx)
        vpc_client = self.create_vpc_client()
        vpc = vpc_client.create_vpc('10.10.10.0/16')
        new_route_table = vpc_client.create_route_table(vpc.id)
        route_table_id = new_route_table.id
        ctx.instance.runtime_properties['aws_resource_id'] = route_table_id
        ctx.operation._operation_context['name'] = 'start'
        routetable.start_route_table(ctx=ctx)
        route_gw = dict(
                destination_cidr_block='0.0.0.0/0',
                gateway_id=ctx.instance.runtime_properties[
                    constants.EXTERNAL_RESOURCE_ID]
        )
        route_instance = dict(
                destination_cidr_block='0.0.0.0/0',
                instance_id=''
        )
        route_cidr = dict(
                destination_cidr_block='0.0.0.0/0',
                interface_id=''
        )
        route_vpc = dict(
                destination_cidr_block='0.0.0.0/0',
                vpc_peering_connection_id=''
        )
        route_error = dict(
                destination_cidr_block='0.0.0.0/0'
        )
        resource = RouteMixin()
        resource.client = vpc_client
        self.assertEqual(True, resource.create_route(route_table_id,
                                                     route_gw))
        self.assertEqual(True, resource.create_route(route_table_id,
                                                     route_instance))
        self.assertEqual(True, resource.create_route(route_table_id,
                                                     route_cidr))
        self.assertEqual(True, resource.create_route(route_table_id,
                                                     route_vpc))
        ex = self.assertRaises(
                NonRecoverableError,
                resource.create_route,
                route_table_id,
                route_error)
        self.assertIn(
                'Unable to create provided route', ex.message)

        self.assertEqual(True, resource.delete_route(route_table_id,
                                                     route_gw))
        self.assertEqual(True, resource.delete_route(route_table_id,
                                                     route_instance))
        self.assertEqual(True, resource.delete_route(route_table_id,
                                                     route_cidr))
        self.assertEqual(True, resource.delete_route(route_table_id,
                                                     route_vpc))

    @mock_ec2
    def test_create_route_exists(self):
        """ Tests that create_route
            raises an error when the
            route already exists.
        """
        ctx = self.get_mock_ctx('test_create_route_exists')
        ctx.node.properties['name'] = 'test_create_route'
        current_ctx.set(ctx=ctx)
        vpc_client = self.create_vpc_client()
        vpc = vpc_client.create_vpc('10.10.10.0/16')
        new_route_table = vpc_client.create_route_table(vpc.id)
        route_table_id = new_route_table.id
        ctx.instance.runtime_properties['aws_resource_id'] = route_table_id
        ctx.operation._operation_context['name'] = 'start'
        routetable.start_route_table(ctx=ctx)
        route = dict(
                destination_cidr_block='0.0.0.0/0',
                gateway_id=ctx.instance.runtime_properties[
                    constants.EXTERNAL_RESOURCE_ID]
        )
        resource = RouteMixin()
        resource.client = vpc_client
        with mock.patch(
                'moto.ec2.models.RouteBackend.create_route') \
                as mock_create_route:
            mock_create_route.side_effect = \
                EC2ResponseError(
                        mock.Mock(return_value={'status': 404}),
                        '<Code>RouteAlreadyExists</Code>')
            self.assertEqual(True, resource.create_route(route_table_id,
                                                         route, ctx.instance))
            mock_create_route.side_effect = \
                EC2ResponseError(
                        mock.Mock(return_value={'status': 404}),
                        'some error')
            self.assertRaises(
                    RecoverableError,
                    resource.create_route,
                    route_table_id,
                    route)

    @mock_ec2
    def test_add_and_remove_route_runtime_properties(self):
        """ Tests that add_route_to_runtime_properties
            assigns route to runtime_properties
            and that remove_route_from_runtime_properties
            removes the route from runtime_properties.
        """
        ctx = self.get_mock_ctx('test_add_and_remove_route_runtime_properties')
        ctx.node.properties['name'] = 'test_create_route'
        current_ctx.set(ctx=ctx)
        vpc_client = self.create_vpc_client()
        vpc = vpc_client.create_vpc('10.10.10.0/16')
        new_route_table = vpc_client.create_route_table(vpc.id)
        route_table_id = new_route_table.id
        ctx.instance.runtime_properties['aws_resource_id'] = route_table_id
        ctx.operation._operation_context['name'] = 'start'
        routetable.start_route_table(ctx=ctx)
        route = dict(
                destination_cidr_block='0.0.0.0/0',
                gateway_id=ctx.instance.runtime_properties[
                    constants.EXTERNAL_RESOURCE_ID]
        )
        resource = RouteMixin()
        self.assertEqual(None,
                         resource.add_route_to_runtime_properties(
                                 ctx.instance, route))
        self.assertIn(route, ctx.instance.runtime_properties['routes'])

        self.assertEqual(None,
                         resource.remove_route_from_runtime_properties(
                                 ctx.instance, route))
        self.assertEqual([], ctx.instance.runtime_properties['routes'])

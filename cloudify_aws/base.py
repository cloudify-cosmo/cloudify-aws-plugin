#########
# Copyright (c) 2015 GigaSpaces Technologies Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
#  * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  * See the License for the specific language governing permissions and
#  * limitations under the License.

import uuid

# Third-party Imports
from boto import exception

# Cloudify imports
from . import utils, constants, connection
from cloudify.exceptions import NonRecoverableError, RecoverableError
from cloudify import ctx


class AwsBase(object):

    def __init__(self,
                 client=None
                 ):
        self.client = \
            client if client else connection.EC2ConnectionClient().client()

    def execute(self, fn, args=None, raise_on_falsy=False):

        try:
            output = fn(**args) if args else fn()
        except (exception.EC2ResponseError,
                exception.BotoServerError) as e:
            raise NonRecoverableError('{0}'.format(str(e)))

        if raise_on_falsy and not output:
            raise NonRecoverableError(
                'Function {0} returned False.'.format(fn))

        return output

    def get_and_filter_resources_by_matcher(
            self, filter_function, filters,
            not_found_token='NotFound'):

        try:
            list_of_matching_resources = filter_function(**filters)
        except exception.EC2ResponseError as e:
            if not_found_token in str(e):
                return []
            raise NonRecoverableError('{0}'.format(str(e)))
        except exception.BotoServerError as e:
            raise NonRecoverableError('{0}'.format(str(e)))

        return list_of_matching_resources

    def filter_for_single_resource(self, filter_function,
                                   filters,
                                   not_found_token='NotFound'):

        resources = self.get_and_filter_resources_by_matcher(
            filter_function, filters, not_found_token)

        if resources:
            for resource in resources:
                if resource.id == filters.values()[0]:
                    return resource

        return None

    def get_related_targets_and_types(self, relationships):
        """

        :param relationships: should be ctx.instance.relationships
        or ctx.source/target.instance.relationships
        :return: targets_and_types a dict of structure
        relationship-type: relationship_target_id
        """

        targets_by_relationship_type = dict()

        if len(relationships) > 0:

            for relationship in relationships:
                targets_by_relationship_type.update(
                    {
                        relationship.type:
                            relationship.target.instance
                            .runtime_properties.get(
                                constants.EXTERNAL_RESOURCE_ID)
                    }
                )

        return targets_by_relationship_type

    def get_target_ids_of_relationship_type(
            self, relationship_type,
            targets_by_relationship_type):

        target_ids = []

        for current_relationship_type, current_target_id in \
                targets_by_relationship_type.items():

            if relationship_type in current_relationship_type:
                target_ids.append(current_target_id)

        return target_ids

    def raise_forbidden_external_resource(self, resource_id):
        raise NonRecoverableError(
            'Cannot use_external_resource because resource {0} '
            'is not in this account.'.format(resource_id))


class AwsBaseRelationship(AwsBase):

    def __init__(self, client=None):
        super(AwsBaseRelationship, self).__init__(client)
        self.source_resource_id = \
            ctx.source.instance.runtime_properties.get(
                constants.EXTERNAL_RESOURCE_ID, None) if \
            constants.EXTERNAL_RESOURCE_ID in \
            ctx.source.instance.runtime_properties.keys() else \
            ctx.source.node.properties['resource_id']
        self.target_resource_id = ctx.target.instance.runtime_properties.get(
            constants.EXTERNAL_RESOURCE_ID, None) if \
            constants.EXTERNAL_RESOURCE_ID in \
            ctx.target.instance.runtime_properties.keys() else \
            ctx.target.node.properties['resource_id']
        self.source_is_external_resource = \
            ctx.source.node.properties['use_external_resource']
        self.source_get_all_handler = {'function': None, 'argument': ''}

    def associate(self, args=None):
        return False

    def associate_helper(self, args=None):

        ctx.logger.info(
            'Attempting to associate {0} with {1}.'
            .format(self.source_resource_id,
                    self.target_resource_id))

        if self.use_source_external_resource_naively() \
                or self.associate(args):
            return self.post_associate()

        raise NonRecoverableError(
            'Source is neither external resource, '
            'nor Cloudify resource, unable to associate {0} with {1}.'
            .format(self.source_resource_id,
                    self.target_resource_id))

    def use_source_external_resource_naively(self):

        if not self.source_is_external_resource:
            return False

        resource = self.get_source_resource()

        if resource is None:
            self.raise_forbidden_external_resource(
                self.source_resource_id)

        if hasattr(resource, 'id'):
            ctx.logger.info(
                'Assuming {0} is external, because the user '
                'specified use_external_resource. '
                'Not associating it with {1}.'
                .format(resource.id, self.target_resource_id))
        else:
            ctx.logger.info(
                'Assuming resource is external, because the user '
                'specified use_external_resource. '
                'Not associating it with {0}.'
                .format(self.target_resource_id))

        return True

    def disassociate(self, args=None):
        return False

    def disassociate_helper(self, args=None):

        ctx.logger.info(
            'Attempting to disassociate {0} from {1}.'
            .format(self.source_resource_id, self.target_resource_id))

        if self.disassociate_external_resource_naively() \
                or self.disassociate(args):
            return self.post_disassociate()

        raise NonRecoverableError(
            'Source is neither external resource, '
            'nor Cloudify resource, unable to disassociate {0} from {1}.'
            .format(self.source_resource_id, self.target_resource_id))

    def disassociate_external_resource_naively(self):

        if not self.source_is_external_resource:
            return False

        resource = self.get_source_resource()

        if hasattr(resource, 'id'):
            ctx.logger.info(
                'Assuming {0} is external, because the user specified '
                'use_external_resource. Not disassociating it with {1}.'
                .format(resource.id, self.target_resource_id))
        else:
            ctx.logger.info(
                'Assuming resource is external, because the user '
                'specified use_external_resource. '
                'Not disassociating it with {0}.'
                .format(self.target_resource_id))

        return True

    def post_associate(self):
        ctx.logger.info(
            'Associated {0} with {1}.'
            .format(self.source_resource_id,
                    self.target_resource_id))
        return True

    def post_disassociate(self):
        ctx.logger.info(
            'Disassociated {0} from {1}.'
            .format(self.source_resource_id,
                    self.target_resource_id))
        return True

    def get_source_resource(self):

        resource = self.filter_for_single_resource(
            self.source_get_all_handler['function'],
            {
                self.source_get_all_handler['argument']:
                self.source_resource_id
            },
        )

        return resource


class State(object):
    def __init__(self, **kwargs):
        for kw in kwargs.keys():
            setattr(self, kw, kwargs.get(kw))


class AwsResourceStates(object):
    def __init__(self, states):
        if not isinstance(states, list):
            raise TypeError('AwsResourceStates takes a list.')
        for state in states:
            name = state.get('name')
            if name:
                setattr(self, name, State(**state))


class AwsBaseNode(AwsBase):

    def __init__(self,
                 aws_resource_type,
                 required_properties,
                 client=None,
                 resource_states=None
                 ):
        super(AwsBaseNode, self).__init__(client)

        self.aws_resource_type = aws_resource_type
        self.cloudify_node_instance_id = ctx.instance.id
        self.resource_id = ctx.instance.runtime_properties.get(
            constants.EXTERNAL_RESOURCE_ID, None) if \
            constants.EXTERNAL_RESOURCE_ID in \
            ctx.instance.runtime_properties.keys() else \
            ctx.node.properties['resource_id']
        self.is_external_resource = \
            ctx.node.properties['use_external_resource']
        self.required_properties = required_properties
        self.get_all_handler = {'function': basestring, 'argument': ''}
        self.not_found_error = ''
        self.state_attribute = 'state'
        self.states = AwsResourceStates(resource_states)

    def creation_validation(self):
        """ This validates all Nodes before bootstrap.
        """

        resource = self.get_resource()

        for property_key in self.required_properties:
            utils.validate_node_property(
                property_key, ctx.node.properties)

        if self.is_external_resource and not resource:
            raise NonRecoverableError(
                'External resource, but the supplied {0} '
                'does not exist in the account.'
                .format(self.aws_resource_type))

        if not self.is_external_resource and resource:
            raise NonRecoverableError(
                'Not external resource, but the supplied {0}'
                'exists in the account.'
                .format(self.aws_resource_type))

    def cloudify_operation_exit_handler(self,
                                        resource_state,
                                        operation_name):
        """
        This function decides whether to allow the Cloudify
        Operation to succeed. It does this by getting the state of
        the AWS Resource (if possible) and determining if it is a
        valid state for the current Cloudify Operation.

        :param resource_state: The resource current resource state.
            This is usually received from self.get_resource_state().
        :param operation_name: The Cloudify Lifecyle Operation Name.
            This is usually provided by ctx.operations.name.
        :return: True if successful or cloudify.operation.retry if waiting.
        :raises: NonRecoverableError if state is failed.
                 RecoverableError if state is indeterminate.
        """

        # Get the list of valid states for the current operation.
        # Usually received from constants.RESOURCE_TYPE_NAME['STATES']
        operation_states = getattr(self.states, operation_name, None)

        # This is not a no-go. Most likely the AWS resource doesnt
        # provide one, so we do not care. But just in case there is
        # an error we log a warning.
        if operation_states is None:
            ctx.logger.debug(
                'AWS type {0} has no state-validation '
                'reference for {1} sequence. Exit sequence.'
                .format(self.aws_resource_type, operation_name))
            return

        ctx.logger.info(
            'AWS {0} ID# {1} '
            'verified to be in -{2}- state.'
            .format(self.aws_resource_type,
                    self.resource_id,
                    resource_state)
        )

        # Return to Cloudify Workflow either a success
        # a failure, or a retry.
        if resource_state in operation_states.success:
            return True
        elif resource_state in operation_states.failed:
            raise NonRecoverableError('Resource is in failed state.')
        elif resource_state in operation_states.waiting:
            _message = \
                'Waiting to verify that {0} {1} is in desired state.' \
                .format(self.aws_resource_type, self.resource_id)
            return ctx.operation.retry(message=_message)

        # This is potentially a serious issue.
        # Either AWS Failed and could possible recover.
        # OR this plugin has a bug.
        raise RecoverableError(
            'The resource is not in state '
            'that is recognized as success, failed, or waiting.')

    # Methods related to handling external resources
    def use_external_resource_naively(self):

        if not self.is_external_resource:
            return False

        ctx.logger.info('AWS {0} ID# {1} is user-provided.'
                        .format(self.aws_resource_type,
                                self.resource_id))

        if not self.get_resource():
            self.raise_forbidden_external_resource(self.resource_id)

        ctx.logger.info(
            'Verified that AWS resource ID# {0} exists. '
            .format(self.resource_id))

        return True

    def delete_external_resource_naively(self):

        if not self.is_external_resource:
            return False

        ctx.logger.info('AWS {0} ID# {1} is user-provided '
                        '- superficial deletion only.'
                        .format(self.aws_resource_type,
                                self.resource_id))

        return True

    def cloudify_resource_state_change_handler(self, args=None):
        """
        Take steps to create a desired resource state.
        If the operation is a retry do not try to call the state change again.

        :return:
        """

        full_operation_name = ctx.operation.name
        short_operation_name = full_operation_name.split('.').pop()
        internal_resource_function = getattr(self,
                                             short_operation_name)
        post_operation_funtion = getattr(self,
                                         'post_{0}'.format(
                                             short_operation_name))

        if 'delete' in short_operation_name:
            external_resource_function = self.delete_external_resource_naively
        else:
            external_resource_function = self.use_external_resource_naively

        if ctx.operation.retry_number == 0:
            ctx.logger.info(
                'Initializing AWS {0}-{1} sequence.'
                .format(self.aws_resource_type, short_operation_name))

            ret = \
                external_resource_function() \
                or internal_resource_function(args)

            if ret is False:
                raise NonRecoverableError(
                    'Neither external resource, nor Cloudify resource, '
                    'unable to {0} this resource.'
                    .format(short_operation_name))
            post_operation_funtion()
            ctx.logger.info(
                'AWS {0}-{1}: primary stage complete.'
                .format(self.aws_resource_type, short_operation_name))
        resource = self.get_resource()
        if not resource and 'delete' in short_operation_name:
            ctx.logger.info('AWS {0} ID# {1} no longer extant.'
                            .format(self.aws_resource_type,
                                    self.resource_id))
            return True
        resource_state = self.get_resource_state(resource=resource)
        ctx.instance.runtime_properties['aws_resource_state'] = resource_state
        if not resource_state:
            ctx.logger.info(
                'Unable to verify AWS {0} ID# {1} state.'
                .format(self.aws_resource_type, self.resource_id))
        return self.cloudify_operation_exit_handler(resource_state,
                                                    short_operation_name)

    # Cloudify workflow operation helpers
    def create_helper(self, args=None):
        return self.cloudify_resource_state_change_handler(args)

    def start_helper(self, args=None):
        return self.cloudify_resource_state_change_handler(args)

    def stop_helper(self, args=None):
        return self.cloudify_resource_state_change_handler(args)

    def delete_helper(self, args=None):
        return self.cloudify_resource_state_change_handler(args)

    def modify_helper(self, new_attributes):
        ctx.logger.info(
            'Attempting to modify instance attributes {0} {1}.'
            .format(self.aws_resource_type,
                    self.cloudify_node_instance_id))
        if self.modify_attributes(new_attributes):
            return self.post_modify()

    # generic resource related methods
    def get_all_matching(self, list_of_ids=None):
        matches = self.get_and_filter_resources_by_matcher(
            self.get_all_handler['function'],
            {self.get_all_handler['argument']: list_of_ids},
            not_found_token=self.not_found_error
        )
        return matches

    def get_resource(self):
        resource = self.filter_for_single_resource(
            self.get_all_handler['function'],
            {self.get_all_handler['argument']: self.resource_id},
            not_found_token=self.not_found_error
        )
        return resource

    def get_resource_state(self, resource=None):
        resource = resource or self.get_resource()
        return getattr(resource, self.state_attribute, None)

    def tag_resource(self, resource):

        tags = ctx.node.properties.get('tags', {})
        name = ctx.node.properties.get('name', '')
        deployment_id = ctx.deployment.id

        if not tags and not name:
            return

        if 'Name' not in tags.keys() and name:
            tags.update({'Name': name})
        else:
            tags.update({'Name': uuid.uuid4()})

        if 'resource_id' not in tags.keys():
            tags.update({'resource_id': ctx.instance.id})

        if deployment_id and 'deployment_id' not in tags.keys():
            tags.update({'deployment_id': deployment_id})

        self._tag_resource(resource, tags)

    def _tag_resource(self, resource, tags):

        try:
            output = resource.add_tags(tags)
        except (exception.EC2ResponseError,
                exception.BotoServerError) as e:
            raise NonRecoverableError(
                'unable to tag resource name: {0}'.format(str(e)))

        return output

    # Abstract methods for API calls
    def create(self, args=None):
        return False

    def start(self, args=None):
        return False

    def stop(self, args=None):
        return False

    def delete(self, args=None):
        return False

    def modify_attributes(self, new_attributes):
        return False

    # Generic methods run after the API call
    def post_create(self):
        utils.set_external_resource_id(self.resource_id, ctx.instance)
        return True

    def post_start(self):
        resource = self.get_resource()
        self.tag_resource(resource)
        return True

    def post_stop(self):
        return True

    def post_delete(self):
        utils.unassign_runtime_properties_from_resource(
            constants.RUNTIME_PROPERTIES, ctx.instance)
        return True

    def post_modify(self):

        ctx.logger.info(
            'Modified {0} {1}.'
            .format(self.aws_resource_type, self.resource_id))
        return True


class RouteMixin(object):

    def create_route(self, route_table_id,
                     route, route_table_ctx_instance=None):

        route_to_create = dict(
            route_table_id=route_table_id,
            destination_cidr_block=route['destination_cidr_block'],
        )

        if 'gateway_id' in route:
            route_to_create['gateway_id'] = route['gateway_id']
        elif 'instance_id' in route:
            route_to_create['instance_id'] = route['instance_id']
        elif 'interface_id' in route:
            route_to_create['interface_id'] = \
                route['interface_id']
        elif 'vpc_peering_connection_id' in route:
            route_to_create['vpc_peering_connection_id'] = \
                route['vpc_peering_connection_id']
        else:
            raise NonRecoverableError(
                'Unable to create provided route. '
                'Missing valid values: {0}'.format(route)
            )

        try:
            output = self.client.create_route(**route_to_create)
        except exception.EC2ResponseError as e:
            if '<Code>RouteAlreadyExists</Code>' in str(e):
                if route_table_ctx_instance:
                    self.add_route_to_runtime_properties(
                        route_table_ctx_instance,
                        route_to_create)
                return True
            else:
                raise RecoverableError('{0}'.format(str(e)))

        if 'output' not in locals() or not output:
            raise NonRecoverableError(
                'create_route failed and no exception was thrown. '
                'route: {0}'.format(route_to_create)
            )

        if route_table_ctx_instance:
            self.add_route_to_runtime_properties(route_table_ctx_instance,
                                                 route_to_create)
        return True

    def add_route_to_runtime_properties(self,
                                        route_table_ctx_instance, route):
        if 'routes' not in \
                route_table_ctx_instance.runtime_properties.keys():
            route_table_ctx_instance.runtime_properties['routes'] = []
        route_table_ctx_instance.runtime_properties['routes'].append(route)

    def delete_route(self, route_table_id,
                     route, route_table_ctx_instance=None):
        args = dict(
            route_table_id=route_table_id,
            destination_cidr_block=route['destination_cidr_block']
        )

        try:
            output = self.client.delete_route(**args)
        except exception.EC2ResponseError as e:
            if constants.ROUTE_NOT_FOUND_ERROR in str(e):
                ctx.logger.info(
                    'Could not delete route: {0} route not '
                    'found on route_table.'
                    .format(route, route_table_id))
                return True
            raise NonRecoverableError('{0}'.format(str(e)))

        if output:
            if route_table_ctx_instance:
                self.remove_route_from_runtime_properties(
                    route_table_ctx_instance, route)
            return True
        return False

    def remove_route_from_runtime_properties(
            self, route_table_ctx_instance, route):
        if route in route_table_ctx_instance.runtime_properties['routes']:
            route_table_ctx_instance.runtime_properties[
                'routes'].remove(route)

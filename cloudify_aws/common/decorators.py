# #######
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
#    * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    * See the License for the specific language governing permissions and
#    * limitations under the License.

"""
    Common.Decorators
    ~~~~~~~~~~~~~~~~~
    AWS decorators
"""

# Standard Imports
import sys

# Third party imports
from cloudify.exceptions import (OperationRetry, NonRecoverableError)
from cloudify.utils import exception_to_error_cause
from botocore.exceptions import ClientError

# Local imports
from cloudify_aws.common import utils
from cloudify_aws.common.constants import (
    EXTERNAL_RESOURCE_ARN as EXT_RES_ARN,
    EXTERNAL_RESOURCE_ID as EXT_RES_ID,
    SWIFT_NODE_PREFIX,
    SWIFT_ERROR_TOKEN_CODE)


def aws_relationship(class_decl=None,
                     resource_type='AWS Resource'):
    '''AWS resource decorator'''
    def wrapper_outer(function):
        '''Outer function'''
        def wrapper_inner(**kwargs):
            '''Inner, worker function'''
            ctx = kwargs['ctx']
            # Add new operation arguments
            kwargs['resource_type'] = resource_type
            kwargs['iface'] = class_decl(
                ctx.source.node, logger=ctx.logger,
                resource_id=utils.get_resource_id(
                    node=ctx.source.node,
                    instance=ctx.source.instance,
                    raise_on_missing=True)) if class_decl else None
            kwargs['resource_config'] = kwargs.get('resource_config') or dict()
            # Check if using external
            if ctx.source.node.properties.get('use_external_resource', False):
                resource_id = utils.get_resource_id(
                    node=ctx.source.node, instance=ctx.source.instance)
                ctx.logger.info('%s ID# "%s" is user-provided.'
                                % (resource_type, resource_id))
                force_op = kwargs.get('force_operation', False)
                old_target = ctx.target.node.properties.get(
                    'use_external_resource', False)
                if not force_op and not old_target:
                    ctx.logger.info(
                        '%s ID# "%s" does not have force_operation '
                        'set but target ID "%s" is new, therefore '
                        'execution relationship operation.' % (
                            resource_type,
                            ctx.target.instance.runtime_properties[EXT_RES_ID],
                            resource_id))
                elif not kwargs.get('force_operation', False):
                    return
                ctx.logger.warn('%s ID# "%s" has force_operation set.'
                                % (resource_type, resource_id))
            # Execute the function
            ret = function(**kwargs)
            # When modifying nested runtime properties, the internal
            # "dirty checking" mechanism will not know of our changes.
            # This forces the internal tracking to mark the properties as
            # dirty and will be refreshed on next query.
            # pylint: disable=W0212
            ctx.source.instance.runtime_properties._set_changed()
            ctx.target.instance.runtime_properties._set_changed()
            return ret
        return wrapper_inner
    return wrapper_outer


def aws_resource(class_decl=None,
                 resource_type='AWS Resource',
                 ignore_properties=False):
    '''AWS resource decorator'''
    def wrapper_outer(function):
        '''Outer function'''
        def wrapper_inner(**kwargs):
            '''Inner, worker function'''
            ctx = kwargs['ctx']
            _, _, _, operation_name = ctx.operation.name.split('.')
            props = ctx.node.properties
            runtime_instance_properties = ctx.instance.runtime_properties
            # Override the resource ID if needed
            resource_id = kwargs.get(EXT_RES_ID)
            if resource_id and not \
                    ctx.instance.runtime_properties.get(EXT_RES_ID):
                ctx.instance.runtime_properties[EXT_RES_ID] = resource_id
            if resource_id and not \
                    ctx.instance.runtime_properties.get(EXT_RES_ARN):
                ctx.instance.runtime_properties[EXT_RES_ARN] = resource_id
            # Override any runtime properties if needed
            runtime_properties = kwargs.get('runtime_properties') or dict()
            for key, val in runtime_properties.iteritems():
                ctx.instance.runtime_properties[key] = val
            # Add new operation arguments
            kwargs['resource_type'] = resource_type

            # Check if "aws_config" is provided
            # if "client_config" is empty, then the current node is a swift
            # node and the "aws_config" will be taken as "aws_config" for
            # boto3 config in order to use the S3 API
            aws_config = ctx.instance.runtime_properties.get('aws_config')
            aws_config_kwargs = kwargs.get('aws_config')

            # Attribute needed for AWS resource class
            class_decl_attr = {
                'ctx_node': ctx.node,
                'logger': ctx.logger,
                'resource_id': utils.get_resource_id(node=ctx.node,
                                                     instance=ctx.instance),
            }

            # Check if "aws_config" is set and has a valid "dict" type because
            #  the expected data type for "aws_config" must be "dict"
            if aws_config:
                if type(aws_config) is dict:
                    class_decl_attr.update({'aws_config': aws_config})
                else:
                    # Raise an error if the provided "aws_config" is not a
                    # valid dict data type
                    raise NonRecoverableError(
                        'aws_config is invalid type: {0}, it must be '
                        'valid dict type'.format(type(aws_config)))

            # Check the value of "aws_config" which could be part of "kwargs"
            # and it has to be the same validation for the above "aws_config"
            elif aws_config_kwargs:
                if type(aws_config_kwargs) is dict:
                    class_decl_attr.update({'aws_config': aws_config_kwargs})
                else:
                    # Raise an error if the provided "aws_config_kwargs"
                    # is not a valid dict data type
                    raise NonRecoverableError(
                        'aws_config is invalid type: {0}, it must be '
                        'valid dict type'.format(type(aws_config)))

            kwargs['iface'] =\
                class_decl(**class_decl_attr) if class_decl else None

            resource_config = None
            if not ignore_properties:
                # Normalize resource_config property
                resource_config = props.get('resource_config') or dict()
                resource_config_kwargs = \
                    resource_config.get('kwargs') or dict()
                if 'kwargs' in resource_config:
                    del resource_config['kwargs']
                resource_config.update(resource_config_kwargs)
                # Update the argument
                kwargs['resource_config'] = kwargs.get('resource_config') or \
                    resource_config or dict()

                # ``resource_config`` could be part of the runtime instance
                # properties, If ``resource_config`` is empty then check if it
                # exists on runtime instance properties
                if not resource_config and runtime_instance_properties \
                        and runtime_instance_properties.get('resource_config'):
                    kwargs['resource_config'] =\
                        runtime_instance_properties['resource_config']
                    resource_config = kwargs['resource_config']
            resource_id = utils.get_resource_id(
                node=ctx.node,
                instance=ctx.instance)
            # Check if using external
            if ctx.node.properties.get('use_external_resource', False):
                ctx.logger.info('%s ID# "%s" is user-provided.'
                                % (resource_type, resource_id))
                if not kwargs.get('force_operation', False):
                    # If "force_operation" is not set then we need to make
                    # sure that runtime properties for node instance are
                    # setting correctly
                    # Set "resource_config" and "EXT_RES_ID"
                    ctx.instance.runtime_properties[
                        'resource_config'] = resource_config
                    ctx.instance.runtime_properties[EXT_RES_ID] = resource_id
                    if operation_name not in ['delete', 'create'] and \
                            not kwargs['iface'].verify_resource_exists():
                        raise NonRecoverableError(
                            'Resource type {0} resource_id '
                            '{1} not found.'.format(
                                kwargs['resource_type'],
                                kwargs['iface'].resource_id))
                    return
                ctx.logger.warn('%s ID# "%s" has force_operation set.'
                                % (resource_type, resource_id))
            return function(**kwargs)
        return wrapper_inner
    return wrapper_outer


def wait_for_status(status_good=None,
                    status_pending=None,
                    fail_on_missing=True):
    '''AWS resource decorator'''
    def wrapper_outer(function):
        '''Outer function'''
        def wrapper_inner(**kwargs):
            '''Inner, worker function'''
            ctx = kwargs['ctx']
            _, _, _, operation_name = ctx.operation.name.split('.')
            resource_type = kwargs.get('resource_type', 'AWS Resource')
            iface = kwargs['iface']
            # Run the operation if this is the first pass
            if ctx.operation.retry_number == 0:
                function(**kwargs)
                # issue 128 and issue 129
                # by updating iface object with actual details from the
                # AWS response assuming that actual state is available
                # at ctx.instance.runtime_properties['create_response']
                # and ctx.instance.runtime_properties[EXT_RES_ID]
                # correctly updated after creation

                # At first let's verify was a new AWS resource
                # really created
                if iface.resource_id != \
                        ctx.instance.runtime_properties.get(EXT_RES_ID):
                    # Assuming new resource was really created,
                    # so updating iface object
                    iface.resource_id = \
                        ctx.instance.runtime_properties.get(EXT_RES_ID)
                    # If sequence of install -> uninstall workflows was
                    # executed, we should remove '__deleted'
                    # flag set in the decorator wait_for_delete below
                    if '__deleted' in ctx.instance.runtime_properties:
                        del ctx.instance.runtime_properties['__deleted']

            # Get a resource interface and query for the status
            status = iface.status
            ctx.logger.debug('%s ID# "%s" reported status: %s'
                             % (resource_type, iface.resource_id, status))
            if status_pending and status in status_pending:
                raise OperationRetry(
                    '%s ID# "%s" is still in a pending state.'
                    % (resource_type, iface.resource_id))

            elif status_good and status in status_good:
                if operation_name in ['create', 'configure']:
                    ctx.instance.runtime_properties['create_response'] = \
                        utils.JsonCleanuper(iface.properties).to_dict()

            elif not status and fail_on_missing:
                raise NonRecoverableError(
                    '%s ID# "%s" no longer exists but "fail_on_missing" set'
                    % (resource_type, iface.resource_id))
            elif status_good and status not in status_good and fail_on_missing:
                raise NonRecoverableError(
                    '%s ID# "%s" reported an unexpected status: "%s"'
                    % (resource_type, iface.resource_id, status))
        return wrapper_inner
    return wrapper_outer


def wait_for_delete(status_deleted=None, status_pending=None):
    '''AWS resource decorator'''
    def wrapper_outer(function):
        '''Outer function'''
        def wrapper_inner(**kwargs):
            '''Inner, worker function'''
            ctx = kwargs['ctx']
            resource_type = kwargs.get('resource_type', 'AWS Resource')
            iface = kwargs['iface']
            # Run the operation if this is the first pass
            if not ctx.instance.runtime_properties.get('__deleted', False):
                function(**kwargs)
                ctx.instance.runtime_properties['__deleted'] = True
            # Get a resource interface and query for the status
            status = iface.status
            ctx.logger.debug('%s ID# "%s" reported status: %s'
                             % (resource_type, iface.resource_id, status))
            if not status or (status_deleted and status in status_deleted):
                for key in [EXT_RES_ARN, EXT_RES_ID, 'resource_config']:
                    if key in ctx.instance.runtime_properties:
                        del ctx.instance.runtime_properties[key]
                return
            elif status_pending and status in status_pending:
                raise OperationRetry(
                    '%s ID# "%s" is still in a pending state.'
                    % (resource_type, iface.resource_id))
            raise NonRecoverableError(
                '%s ID# "%s" reported an unexpected status: "%s"'
                % (resource_type, iface.resource_id, status))
        return wrapper_inner
    return wrapper_outer


def check_swift_resource(func):
    def wrapper(**kwargs):
        ctx = kwargs['ctx']
        node_type = ctx.node.type
        if node_type and node_type.startswith(SWIFT_NODE_PREFIX):
            response = None
            swift_config = ctx.node.properties.get('swift_config')

            username = swift_config.get('swift_username')
            password = swift_config.get('swift_password')
            auth_url = swift_config.get('swift_auth_url')
            region_name = swift_config.get('swift_region_name')

            aws_config = {}
            # Only Generate the token if it is not generated before
            if not ctx.instance.runtime_properties.get('aws_config'):
                endpoint_url, token = \
                    utils.generate_swift_access_config(auth_url,
                                                       username,
                                                       password)

                aws_config['aws_access_key_id'] = username
                aws_config['aws_secret_access_key'] = token
                aws_config['region_name'] = region_name
                aws_config['endpoint_url'] = endpoint_url
                ctx.instance.runtime_properties['aws_config'] = aws_config

            try:
                kwargs['aws_config'] = aws_config
                kwargs['ctx'] = ctx
                response = func(**kwargs)
            except ClientError as err:
                _, _, tb = sys.exc_info()
                error = err.response.get('Error')
                error_code = error.get('Code', 'Unknown')
                if error_code == SWIFT_ERROR_TOKEN_CODE:
                    endpoint_url, token = \
                        utils.generate_swift_access_config(auth_url,
                                                           username,
                                                           password)
                    # Reset the old "aws_config" and generate new one
                    del ctx.instance.runtime_properties['aws_config']

                    aws_config = {}
                    aws_config['aws_access_key_id'] = username
                    aws_config['aws_secret_access_key'] = token
                    aws_config['region_name'] = region_name
                    aws_config['endpoint_url'] = endpoint_url
                    ctx.instance.runtime_properties['aws_config'] =\
                        aws_config

                    raise OperationRetry(
                        'Re-try the operation and generate new token'
                        ' and endpoint url for swift connection',
                        retry_after=10,
                        causes=[exception_to_error_cause(error, tb)])
            except Exception as error:
                error_traceback = utils.get_traceback_exception()
                raise NonRecoverableError('{0}'.format(str(error)),
                                          causes=[error_traceback])
            return response

        return func(**kwargs)
    return wrapper


def tag_resources(fn):
    def wrapper(**kwargs):
        result = fn(**kwargs)
        ctx = kwargs.get('ctx')
        iface = kwargs.get('iface')
        resource_id = utils.get_resource_id(
            node=ctx.node,
            instance=ctx.instance)
        tags = utils.get_tags_list(
            ctx.node.properties.get('Tags'),
            ctx.instance.runtime_properties.get('Tags'),
            kwargs.get('Tags'))
        if iface and tags and resource_id:
            iface.tag({
                'Tags': tags,
                'Resources': [resource_id]})
        return result
    return wrapper


def untag_resources(fn):
    def wrapper(**kwargs):
        ctx = kwargs.get('ctx')
        iface = kwargs.get('iface')
        resource_id = utils.get_resource_id(
            node=ctx.node,
            instance=ctx.instance)
        tags = utils.get_tags_list(
            ctx.node.properties.get('Tags'),
            ctx.instance.runtime_properties.get('Tags'),
            kwargs.get('Tags'))
        if iface and tags and resource_id:
            iface.untag({
                'Tags': tags,
                'Resources': [resource_id]})
        return fn(**kwargs)
    return wrapper

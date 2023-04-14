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

"""
    Common.Decorators
    ~~~~~~~~~~~~~~~~~
    AWS decorators
"""

# Standard Imports
import sys
from time import sleep

# Third party imports
from botocore.exceptions import ClientError

from cloudify import ctx
from cloudify.decorators import operation
from cloudify.utils import exception_to_error_cause
from cloudify.exceptions import OperationRetry, NonRecoverableError
from cloudify_common_sdk.utils import \
    skip_creative_or_destructive_operation as skip
from cloudify_common_sdk.utils import (
    v1_gteq_v2,
    get_cloudify_version,
)
# Local imports
from .constants import SUPPORT_DRIFT
from cloudify_aws.eks import EKSBase
from cloudify_aws.elb import ELBBase
from cloudify_aws.common import utils
from cloudify_aws.common._compat import text_type
from cloudify_common_sdk.utils import get_ctx_instance
from cloudify_aws.common.constants import (
    SWIFT_NODE_PREFIX,
    SWIFT_ERROR_TOKEN_CODE,
    EXTERNAL_RESOURCE_ID as EXT_RES_ID,
    EXTERNAL_RESOURCE_ARN as EXT_RES_ARN,
    EXTERNAL_RESOURCE_ID_MULTIPLE as MULTI_ID
)


def _wait_for_status(kwargs,
                     _ctx,
                     _operation,
                     function,
                     status_pending,
                     status_good,
                     fail_on_missing):
    """
    @param kwargs:
    @param _ctx:
    @param _operation:
    @param function:
    @param status_pending:
    @param status_good: the desirable status or nothing
    @param fail_on_missing:
    @return:
    """
    status_good = status_good or []
    status_pending = status_pending or []

    resource_type = kwargs.get('resource_type', 'AWS Resource')

    operation_name = _operation.name.split(
        'cloudify.interfaces.lifecycle.')[-1]
    creation_phase = operation_name in [
        'precreate', 'create', 'configure']
    resource_id = kwargs['iface'].resource_id

    # Run the operation if this is the resource has not been created yet
    result = None

    ctx.logger.debug('Resource %s ID# "%s"' % (resource_type, resource_id))
    ctx_instance = get_ctx_instance()
    if (creation_phase and _ctx.operation.retry_number == 0) \
            or not resource_id:
        if not creation_phase:
            ctx.logger.error(
                'The resource should exist, but does not have a resource ID.')
        try:
            result = function(**kwargs)
        except utils.SkipWaitingOperation:
            return
        ctx.logger.debug("The function result is %s" % result)
        iface_resource_id = kwargs['iface'].resource_id
        runtime_resource_id = utils.get_resource_id(ctx.node, ctx_instance)
        if iface_resource_id != runtime_resource_id:
            if not iface_resource_id and runtime_resource_id:
                kwargs['iface'].update_resource_id(runtime_resource_id)
                resource_id = runtime_resource_id
            elif not runtime_resource_id and iface_resource_id:
                utils.update_resource_id(ctx_instance, iface_resource_id)
                resource_id = iface_resource_id
            elif iface_resource_id and runtime_resource_id:
                raise NonRecoverableError(
                    'There are multiple resource IDs for the same resource. '
                    'This indicates the operation may have run more than once '
                    'and created multiple resources.'
                    ' Please check your aws account.')
            else:
                raise OperationRetry("Resource not created, trying again...")
        else:
            kwargs['iface'].update_resource_id(runtime_resource_id)
            resource_id = runtime_resource_id

    ctx.logger.debug('Requesting ID# "%s" status.' % resource_id)

    status = kwargs['iface'].status

    # Get a resource interface and query for the status
    ctx.logger.info('%s ID# "%s" reported status: %s.' % (
        resource_type, resource_id, status))

    if kwargs['iface'].wait_for_status():
        return

    if status in status_good:
        ctx_instance.runtime_properties['create_response'] = \
            utils.JsonCleanuper(kwargs['iface'].properties).to_dict()
        return result

    elif status in status_pending:
        raise OperationRetry(
            '%s ID# "%s" is still in a pending state.'
            % (resource_type, kwargs['iface'].resource_id))

    elif not status and fail_on_missing:
        sleep(0.5)
        if kwargs['iface'].status:
            return _wait_for_status(kwargs,
                                    _ctx,
                                    _operation,
                                    function,
                                    status_pending,
                                    status_good,
                                    fail_on_missing)

        raise NonRecoverableError(
            '%s ID# "%s" no longer exists but "fail_on_missing" set.'
            % (resource_type, kwargs['iface'].resource_id))

    elif not status:
        raise OperationRetry('Waiting for operation to succeed')

    # TODO: Is it always "failed"?
    elif status in ['failed']:
        raise NonRecoverableError(
            'Resource {r} ID# {n} is in a failed state.'.format(
                r=resource_type, n=resource_id))

    elif status not in status_good + status_pending:
        try:
            result = function(**kwargs)
        except utils.SkipWaitingOperation:
            return
        ctx.logger.debug("The function result is %s" % result)
        raise OperationRetry('Waiting for operation to succeed...')

    elif status not in status_good and fail_on_missing:
        raise NonRecoverableError(
            '%s ID# "%s" reported an unexpected status: "%s"'
            % (resource_type, kwargs['iface'].resource_id, status))

    ctx.logger.warn("Resource was created but no good status reached.")
    return result


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
            iface = kwargs.get('iface')
            if not iface and class_decl:
                kwargs['iface'] = class_decl(
                    ctx.source.node, logger=ctx.logger,
                    resource_id=utils.get_resource_id(
                        node=ctx.source.node,
                        instance=ctx.source.instance,
                        raise_on_missing=True))
            else:
                kwargs['iface'] = iface
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

    return operation(func=wrapper_outer, resumable=True)


def aws_params(resource_name, params_priority=True):
    '''AWS resource decorator'''

    def wrapper_outer(function):
        '''Outer function'''

        def wrapper_inner(*argc, **kwargs):
            ctx = kwargs.get('ctx')
            iface = kwargs['iface']
            resource_config = kwargs.get('resource_config')

            # Create a copy of the resource config for clean manipulation.
            params = utils.clean_params(
                dict() if not resource_config else resource_config.copy())
            if params_priority:
                # params value will overwrite other resources id
                resource_id = params.get(resource_name)
                if not resource_id:
                    resource_id = \
                        iface.resource_id or \
                        utils.get_resource_id(
                            ctx.node,
                            ctx.instance,
                            use_instance_id=True)
                    params[resource_name] = resource_id
            else:
                # resource id from runtime has priority over params
                resource_id = \
                    iface.resource_id or \
                    utils.get_resource_id(
                        ctx.node,
                        ctx.instance,
                        params.get(resource_name),
                        use_instance_id=True)
                params[resource_name] = resource_id
                ctx.instance.runtime_properties[resource_name] = \
                    resource_id

            utils.update_resource_id(ctx.instance, resource_id)
            kwargs['params'] = params
            return function(*argc, **kwargs)

        return wrapper_inner

    return wrapper_outer


def get_special_condition(external,
                          node_type,
                          op_name,
                          create_op,
                          stop_op,
                          delete_op,
                          force,
                          waits_for_status):
    if 'cloudify.nodes.aws.ec2.Instances' in node_type and \
            op_name == 'poststart':
        return True
    elif external and 'cloudify.nodes.aws.ec2.Image' in node_type and \
            op_name == 'precreate':
        return True
    elif external and 'cloudify.nodes.aws.ec2.Image' in node_type and \
            op_name == 'delete':
        return False
    elif waits_for_status and not external:
        return True
    elif create_op and 'cloudify.nodes.aws.ec2.VpcPeeringRequest' in node_type:
        return True
    elif 'cloudify.relationships.aws.iam.login_profile' \
            in node_type and op_name == 'establish':
        return True
    elif 'cloudify.relationships.aws.iam.access_key.connected_to' \
            in node_type and op_name == 'establish':
        return True
    elif stop_op and (external and not force):
        return False
    return not create_op and not delete_op or force


def get_create_op(op_name):
    """ Determine if we are dealing with a creation operation.
    Normally we just do the logic in the last return. However, we may want
    special behavior for some types.

    :param op_name: ctx.operation.name.split('.')[-1].
    :return: bool
    """
    return 'create' == op_name
    # return 'create' in op or 'configure' in op


def get_stop_operation(op_name):
    """ Determine if we are dealing with a stop operation.
    Normally we just do the logic in the last return. However, we may want
    special behavior for some types.

    :param op_name: ctx.operation.name.split('.')[-1].
    :return: bool
    """
    return 'stop' == op_name


def get_delete_op(op_name):
    """ Determine if we are dealing with a deletion operation.
    Normally we just do the logic in the last return. However, we may want
    special behavior for some types.

    :param op_name: ctx.operation.name.split('.')[-1].
    :return: bool
    """
    return 'delete' == op_name


def _put_resource_id_in_runtime_props(resource_id, runtime_props):
    if resource_id and not runtime_props.get(EXT_RES_ID):
        runtime_props[EXT_RES_ID] = resource_id
    if resource_id and not runtime_props.get(EXT_RES_ARN):
        runtime_props[EXT_RES_ARN] = resource_id


def _put_values_from_kwargs_in_runtime_props(from_kwargs, runtime_props):
    # Override any runtime properties if needed
    for key, val in from_kwargs.items():
        runtime_props[key] = val


def _put_aws_config_in_class_decl(aws_config,
                                  class_decl_attr,
                                  aws_config_kwargs):
    # Check if "aws_config" is set and has a valid "dict" type because
    #  the expected data type for "aws_config" must be "dict"
    if aws_config:
        if isinstance(aws_config, dict):
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
        if isinstance(aws_config_kwargs, dict):
            class_decl_attr.update({'aws_config': aws_config_kwargs})
        else:
            # Raise an error if the provided "aws_config_kwargs"
            # is not a valid dict data type
            raise NonRecoverableError(
                'The aws_config is invalid type: {0}, it must be '
                'valid dict type'.format(type(aws_config)))


def _get_resource_config_if_not_ignore_properties(
        kwargs, props, runtime_instance_properties):
    # Normalize resource_config property
    resource_config = props.get('resource_config') or dict()
    resource_config_kwargs = resource_config.get('kwargs') or dict()
    if 'kwargs' in resource_config:
        del resource_config['kwargs']
    resource_config.update(resource_config_kwargs)
    # Update the argument
    kwargs['resource_config'] = utils.clean_params(
        kwargs.get('resource_config') or resource_config or dict())

    # ``resource_config`` could be part of the runtime instance
    # properties, If ``resource_config`` is empty then check if it
    # exists on runtime instance properties
    if not resource_config \
            and runtime_instance_properties \
            and runtime_instance_properties.get('resource_config'):
        kwargs['resource_config'] = \
            runtime_instance_properties['resource_config']
        resource_config = kwargs['resource_config']
    return resource_config


def _log_assume_role(aws_config, aws_config_kwargs, ctx):
    assume_role = None
    if aws_config:
        assume_role = aws_config.get('assume_role')
    elif aws_config_kwargs:
        assume_role = aws_config_kwargs.get('assume_role')
    if assume_role:
        ctx.logger.info('Assuming provided role: {}'.format(assume_role))


def _aws_resource(function,
                  class_decl,
                  resource_type,
                  ignore_properties,
                  **kwargs):
    ctx = kwargs['ctx']
    operation_name = ctx.operation.name.split(
        'cloudify.interfaces.lifecycle.')[-1]
    create_operation = get_create_op(operation_name)
    stop_operation = get_stop_operation(operation_name)
    delete_operation = get_delete_op(operation_name)
    if create_operation and '__deleted' in ctx.instance.runtime_properties:
        del ctx.instance.runtime_properties['__deleted']
    props = ctx.node.properties
    runtime_instance_properties = ctx.instance.runtime_properties
    # Override the resource ID if needed
    resource_id = kwargs.get(EXT_RES_ID)
    _put_resource_id_in_runtime_props(
        resource_id, ctx.instance.runtime_properties)
    runtime_props_from_kwargs = kwargs.get('runtime_properties') or dict()
    _put_values_from_kwargs_in_runtime_props(
        runtime_props_from_kwargs, ctx.instance.runtime_properties)

    # Add new operation arguments
    kwargs['resource_type'] = resource_type

    # Check if "aws_config" is provided
    # if "client_config" is empty, then the current node is a swift
    # node and the "aws_config" will be taken as "aws_config" for
    # boto3 config in order to use the S3 API
    aws_config = ctx.instance.runtime_properties.get('aws_config')
    aws_config_kwargs = kwargs.get('aws_config', {})
    if 'aws_session_token' in aws_config_kwargs and not \
            aws_config_kwargs['session_token']:
        aws_config_kwargs.pop('aws_session_token')

    resource_name = None
    if 'cloudify.nodes.aws.elb.LoadBalancer' in ctx.node.type_hierarchy:
        resource_name = ctx.node.properties.get(
            'resource_config', {}).get('Name')

    # Attribute needed for AWS resource class
    class_decl_attr = {
        'ctx_node': ctx.node,
        'logger': ctx.logger,
        'resource_id': utils.get_resource_id(
            node=ctx.node,
            instance=ctx.instance,
            resource_name=resource_name),
    }

    _put_aws_config_in_class_decl(
        aws_config, class_decl_attr, aws_config_kwargs)
    _log_assume_role(aws_config, aws_config_kwargs, ctx)
    kwargs['iface'] = class_decl(**class_decl_attr) if class_decl else None

    if not ignore_properties:
        resource_config = _get_resource_config_if_not_ignore_properties(
            kwargs, props, runtime_instance_properties)
    else:
        resource_config = None

    resource_id = utils.get_resource_id(node=ctx.node, instance=ctx.instance)

    iface = kwargs.get('iface')
    if iface and ctx.node.type in SUPPORT_DRIFT:
        iface.initial_configuration = resource_config
        iface.import_configuration(
            resource_config, runtime_instance_properties)

    try:
        if iface.status in [None, {}]:
            exists = False
        else:
            exists = True
    except (AttributeError, NotImplementedError):
        exists = False
        special_condition = True
    else:
        special_condition = get_special_condition(
            props.get('use_external_resource'),
            ctx.node.type_hierarchy,
            operation_name,
            create_operation,
            stop_operation,
            delete_operation,
            kwargs.get('force_operation'),
            kwargs.pop('waits_for_status', False))

    result = None
    if not skip(
            resource_type=resource_type,
            resource_id=getattr(kwargs['iface'], 'resource_id', resource_id),
            _ctx_node=ctx.node,
            exists=exists,
            special_condition=special_condition,
            create_operation=create_operation,
            delete_operation=delete_operation):
        result = function(**kwargs)
    else:
        ctx.instance.runtime_properties['resource_config'] = resource_config
        ctx.instance.runtime_properties[EXT_RES_ID] = resource_id
        if iface:
            iface.populate_resource(ctx)
            kwargs['iface'] = iface
    if create_operation and iface:
        iface.populate_resource(ctx)
        kwargs['iface'] = iface
    if delete_operation:
        # cleanup runtime after delete
        keys = list(ctx.instance.runtime_properties.keys())
        for key in keys:
            if key != '__deleted':
                del ctx.instance.runtime_properties[key]
    if operation_name == 'poststart' and \
            ctx.node.type in SUPPORT_DRIFT:
        utils.assign_previous_configuration(
            iface, ctx.instance.runtime_properties)
    return result


def aws_resource(class_decl=None,
                 resource_type='AWS Resource',
                 ignore_properties=False,
                 waits_for_status=True):
    '''AWS resource decorator'''

    def wrapper_outer(function):
        '''Outer function'''

        def wrapper_inner(**kwargs):
            '''Inner, worker function'''
            kwargs['waits_for_status'] = waits_for_status
            return _aws_resource(
                function,
                class_decl,
                resource_type,
                ignore_properties,
                **kwargs)

        return wrapper_inner

    return operation(func=wrapper_outer, resumable=True)


def multiple_aws_resource(class_decl=None,
                          resource_type='AWS Resource',
                          ignore_properties=False):
    '''AWS resource decorator'''

    def wrapper_outer(function):
        '''Outer function'''

        def wrapper_inner(**kwargs):
            '''Inner, worker function'''
            ctx = kwargs['ctx']
            ids = ctx.instance.runtime_properties.get(MULTI_ID, [])
            if not ids and EXT_RES_ID in ctx.instance.runtime_properties:
                ids.append(ctx.instance.runtime_properties[EXT_RES_ID])
            for resource_id in ids:
                kwargs_runtime_properties = kwargs.get('runtime_properties')
                if not isinstance(kwargs_runtime_properties, dict):
                    kwargs_runtime_properties = {}
                kwargs_runtime_properties.update({EXT_RES_ID: resource_id})
                kwargs['runtime_properties'] = kwargs_runtime_properties
                utils.update_resource_id(ctx.instance, resource_id)
                kwargs['ctx'] = ctx
                _aws_resource(function,
                              class_decl,
                              resource_type,
                              ignore_properties,
                              **kwargs)

        return wrapper_inner

    return operation(func=wrapper_outer, resumable=True)


def wait_for_status(status_good=None,
                    status_pending=None,
                    fail_on_missing=True):
    '''AWS resource decorator'''

    def wrapper_outer(function):
        '''Outer function'''

        def wrapper_inner(**kwargs):
            '''Inner, worker function'''
            _ctx = kwargs['ctx']
            _operation = _ctx.operation
            _wait_for_status(kwargs,
                             _ctx,
                             _operation,
                             function,
                             status_pending,
                             status_good,
                             fail_on_missing)

        return wrapper_inner

    return wrapper_outer


def wait_on_relationship_unlink(status_deleted=None,
                                status_pending=None):
    '''AWS resource decorator'''

    def wrapper_outer(function):
        '''Outer function'''

        def wrapper_inner(**kwargs):
            '''Inner, worker function'''
            _ctx = kwargs['ctx']
            _operation = _ctx.operation
            _wait_for_delete(kwargs,
                             _ctx,
                             _operation,
                             function,
                             status_pending,
                             status_deleted)

        return wrapper_inner

    return wrapper_outer


def wait_on_relationship_status(status_good=None,
                                status_pending=None,
                                fail_on_missing=True):
    '''AWS resource decorator'''

    def wrapper_outer(function):
        '''Outer function'''

        def wrapper_inner(**kwargs):
            '''Inner, worker function'''
            _ctx = kwargs['ctx']
            _operation = _ctx.operation
            _wait_for_status(kwargs,
                             _ctx.source,
                             _operation,
                             function,
                             status_pending,
                             status_good,
                             fail_on_missing)

        return wrapper_inner

    return wrapper_outer


def wait_for_delete(status_deleted=None,
                    status_pending=None,
                    status_not_deleted=None):
    '''AWS resource decorator'''

    status_deleted = status_deleted or []
    status_pending = status_pending or []
    status_not_deleted = status_not_deleted or []

    def wrapper_outer(function):
        '''Outer function'''

        def wrapper_inner(**kwargs):
            '''Inner, worker function'''
            _ctx = kwargs['ctx']
            _operation = _ctx.operation
            _wait_for_delete(kwargs,
                             _ctx,
                             _operation,
                             function,
                             status_pending,
                             status_deleted,
                             status_not_deleted)

        return wrapper_inner

    return wrapper_outer


def _wait_for_delete(kwargs,
                     ctx,
                     operation,
                     function,
                     status_pending,
                     status_deleted,
                     status_not_deleted=None):
    status_not_deleted = status_not_deleted or []
    resource_type = kwargs.get('resource_type', 'AWS Resource')
    iface = kwargs['iface']
    ctx_instance = get_ctx_instance()
    # Run the operation if this is the first pass
    delete_operation = 'delete' == operation.name.split(
        'cloudify.interfaces.lifecycle.')[-1]
    deleted_already = ctx_instance.runtime_properties.get(
        '__deleted', False)
    if delete_operation and not deleted_already or not delete_operation:
        function(**kwargs)
        # flag will be removed after first call without any exceptions
        ctx_instance.runtime_properties['__deleted'] = True
    # Get a resource interface and query for the status
    status = iface.status
    ctx.logger.debug('%s ID# "%s" reported status: %s'
                     % (resource_type, iface.resource_id, status))
    if not status or status in status_deleted:
        if delete_operation:
            for key in [EXT_RES_ARN, EXT_RES_ID, 'resource_config']:
                if key in ctx_instance.runtime_properties:
                    del ctx_instance.runtime_properties[key]
        return
    elif status in status_pending:
        raise OperationRetry(
            '%s ID# "%s" is still in a pending state.'
            % (resource_type, iface.resource_id))
    elif status in status_not_deleted:
        ctx_instance.runtime_properties['__deleted'] = False
        raise OperationRetry(
            '%s ID# "%s" is still in a pending state.'
            % (resource_type, iface.resource_id))
    raise NonRecoverableError(
        '%s ID# "%s" reported an unexpected status: "%s"'
        % (resource_type, iface.resource_id, status))


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
                    ctx.instance.runtime_properties['aws_config'] = \
                        aws_config

                    raise OperationRetry(
                        'Re-try the operation and generate new token'
                        ' and endpoint url for swift connection',
                        retry_after=10,
                        causes=[exception_to_error_cause(error, tb)])
            except Exception as error:
                error_traceback = utils.get_traceback_exception()
                raise NonRecoverableError('{0}'.format(text_type(error)),
                                          causes=[error_traceback])
            return response

        return func(**kwargs)

    return operation(func=wrapper, resumable=True)


def tag_resources(fn):
    def wrapper(**kwargs):
        result = fn(**kwargs)
        ctx = kwargs.get('ctx')
        iface = kwargs.get('iface')
        if len(ctx.instance.runtime_properties.get(MULTI_ID, [])) > 1:
            resource_ids = ctx.instance.runtime_properties[MULTI_ID]
            iface.update_resource_id(resource_ids[0])
        else:
            if not iface.resource_id:
                resource_id = utils.get_resource_id(
                    node=ctx.node,
                    instance=ctx.instance)
                iface.update_resource_id(resource_id)
            resource_ids = [iface.resource_id]
        if ctx.node.properties.get('cloudify_tagging', False):
            try:
                add_default_tag(ctx, iface)
            except ClientError:
                raise OperationRetry(
                    'Waiting for {} to be provisioned before tagging.'.format(
                        iface.resource_id))
        else:
            ctx.logger.info("Not adding default Cloudify tags.")
        tags = utils.get_tags_list(
            ctx.node.properties.get('Tags'),
            ctx.instance.runtime_properties.get('Tags'),
            kwargs.get('Tags'))
        if iface and tags and resource_ids:
            iface.tag({
                'Tags': tags,
                'Resources': resource_ids})
        return result

    return wrapper


def untag_resources(fn):
    def wrapper(**kwargs):
        ctx = kwargs.get('ctx')
        iface = kwargs.get('iface')
        if len(ctx.instance.runtime_properties.get(MULTI_ID, [])) > 1:
            resource_ids = ctx.instance.runtime_properties[MULTI_ID]
            iface.update_resource_id(resource_ids[0])
        else:
            resource_ids = [utils.get_resource_id(
                node=ctx.node,
                instance=ctx.instance)]
        tags = utils.get_tags_list(
            ctx.node.properties.get('Tags'),
            ctx.instance.runtime_properties.get('Tags'),
            kwargs.get('Tags'))
        if isinstance(iface, (ELBBase, EKSBase)):
            can_be_deleted = False
        else:
            can_be_deleted = utils.delete_will_succeed(fn=fn, params=kwargs)
        if iface and tags and resource_ids and can_be_deleted:
            iface.untag({
                'Tags': tags,
                'Resources': resource_ids})
        return fn(**kwargs)

    return wrapper


def add_default_tag(_ctx, iface):
    ctx.logger.info("Adding default cloudify_tagging.")
    special_tags = {}
    if v1_gteq_v2(get_cloudify_version(), "6.3.1"):
        ctx.logger.info("Adding tags using resource_tags.")
        special_tags.update(ctx.deployment.resource_tags)
    for key in special_tags:
        iface.tag(
            {
                'Tags': [
                    {
                        'Key': key,
                        'Value': "{}".format(
                            special_tags[key])
                    }
                ],
                'Resources': [iface.resource_id]
            }
        )
    iface.tag(
        {
            'Tags':
                [
                    {'Key': 'CreatedBy', 'Value': "{}-{}-{}".format(
                        _ctx.tenant_name,
                        _ctx.deployment.id,
                        _ctx.instance.id)}],
            'Resources': [iface.resource_id]
        }
    )
    iface.tag(
        {
            'Tags': [
                {'Key': 'Name', 'Value': "{}_{}".format(
                    _ctx.node.name,
                    _ctx.instance.id)}],
            'Resources': [iface.resource_id]
        }
    )
    ctx.logger.info("Added default cloudify_tagging.")

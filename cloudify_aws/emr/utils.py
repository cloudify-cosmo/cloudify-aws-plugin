# #######
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
'''
    EMR.Utils
    ~~~~~~~~~
    AWS EMR helper utilities
'''
try:
    from cloudify import ctx as base_ctx
except RuntimeError:
    from cloudify.workflows import ctx as base_ctx
from cloudify.workflows.workflow_context import CloudifyWorkflowContext
from cloudify import manager
from cloudify.exceptions import NonRecoverableError
from cloudify_aws import constants


def get_resource_id(node=None, node_instance=None,
                    raise_on_missing=False,
                    raise_exception=NonRecoverableError,
                    logger=None):
    '''
        Gets the (external) resource ID of a Cloudify context. This
        is a very flexible method that allows for either normal
        `CloudifyContext` node(-instance) objects as well as those
        from `CloudifyWorkflowContext` and imposes sensible defaults
        depending on the environment available.

    :param `cloudify.context.NodeContext` node:
        Cloudify node.
    :param `cloudify.context.NodeInstanceContext` node_instance:
        Cloudify node instance.
    :param boolean raise_on_missing: If True, causes this method to raise
        an exception if the resource ID is not found.
    :param `Exception` raise_exception: An exception class that will
        be raised if `raise_on_missing` is set.
    :raises: :exc:`cloudify.exceptions.NonRecoverableError`
    '''
    node = node or (base_ctx.node if base_ctx else None)
    node_instance = node_instance or (base_ctx.instance if base_ctx else None)
    props = node.properties if node else {}
    # Get runtime properties (if possible)
    logger.info('type(ctx): %s' % type(base_ctx))
    if isinstance(base_ctx, CloudifyWorkflowContext) and not base_ctx.local:
        node_instance = manager.NodeInstance(node_instance.id, node.id)
    runtime_props = node_instance.runtime_properties if node_instance else {}
    # Search instance runtime properties first, then the node properties
    resource_id = runtime_props.get(
        constants.EXTERNAL_RESOURCE_ID, props.get('resource_id'))
    if not resource_id and raise_on_missing:
        raise raise_exception('Missing resource ID!')
    return resource_id

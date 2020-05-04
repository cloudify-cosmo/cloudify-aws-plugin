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
    CloudFormation.stack
    ~~~~~~~~~~~~~~
    AWS CloudFormation Stack interface
"""
# Standard imports
import json
from datetime import datetime

# Cloudify imports
from cloudify._compat import text_type

# Third party imports
from botocore.exceptions import ClientError

# Local imports
from cloudify_aws.common import decorators, utils
from cloudify_aws.common.constants import EXTERNAL_RESOURCE_ID
from cloudify_aws.cloudformation import AWSCloudFormationBase

RESOURCE_TYPE = 'CloudFormation Stack'
RESOURCE_NAME = 'StackName'
RESOURCE_NAMES = 'StackNames'
STACKS = 'Stacks'
TEMPLATEBODY = 'TemplateBody'
STATUS = 'StackStatus'


class CloudFormationStack(AWSCloudFormationBase):
    """
        AWS CloudFormation Stack interface
    """
    def __init__(self, ctx_node, resource_id=None, client=None, logger=None):
        AWSCloudFormationBase.__init__(self, ctx_node, resource_id, client,
                                       logger)
        self.type_name = RESOURCE_TYPE

    @property
    def properties(self):
        """Gets the properties of an external resource"""
        params = {RESOURCE_NAME: self.resource_id}
        try:
            resources = \
                self.client.describe_stacks(**params)
        except ClientError:
            pass
        else:
            return resources.get(STACKS, [None])[0]

    @property
    def status(self):
        """Gets the status of an external resource"""
        props = self.properties
        if not props:
            return None
        return props.get(STATUS)

    def create(self, params):
        """
            Create a new AWS CloudFormation Stack.
        """
        return self.make_client_call('create_stack', params)

    def delete(self, params=None):
        """
            Deletes an existing AWS CloudFormation Stack.
        """
        self.logger.debug('Deleting %s with parameters: %s'
                          % (self.type_name, params))
        res = self.client.delete_stack(**params)
        self.logger.debug('Response: %s' % res)
        return res


@decorators.aws_resource(resource_type=RESOURCE_TYPE)
def prepare(ctx, resource_config, **_):
    """Prepares an AWS CloudFormation Stack"""
    # Save the parameters
    ctx.instance.runtime_properties['resource_config'] = resource_config


@decorators.aws_resource(CloudFormationStack, RESOURCE_TYPE)
@decorators.wait_for_status(
    status_good=['CREATE_COMPLETE'],
    status_pending=['CREATE_IN_PROGRESS'])
def create(ctx, iface, resource_config, **_):
    """Creates an AWS CloudFormation Stack"""
    # Create a copy of the resource config for clean manipulation.
    params = dict() if not resource_config else resource_config.copy()
    resource_id = \
        iface.resource_id or \
        utils.get_resource_id(
            ctx.node,
            ctx.instance,
            params.get(RESOURCE_NAME),
            use_instance_id=True)
    params[RESOURCE_NAME] = resource_id
    utils.update_resource_id(ctx.instance, resource_id)

    template_body = params.get(TEMPLATEBODY, {})
    if template_body and not isinstance(template_body, text_type):
        params[TEMPLATEBODY] = json.dumps(template_body)
    if not iface.resource_id:
        setattr(iface, 'resource_id', params.get(RESOURCE_NAME))
    # Actually create the resource
    iface.create(params)


@decorators.aws_resource(CloudFormationStack, RESOURCE_TYPE)
def start(ctx, iface, **_):
    """Update Runtime Properties an AWS CloudFormation Stack"""

    def test(_value):
        if isinstance(_value, datetime):
            return str(_value)
        elif isinstance(_value, list):
            for _value_item in _value:
                i = _value.index(_value_item)
                _value[i] = test(_value_item)
            return _value
        elif isinstance(_value, dict):
            for _value_key, _value_item in _value.items():
                _value[_value_key] = test(_value_item)
            return _value
        else:
            return _value

    if not iface.resource_id:
        iface.update_resource_id(
            ctx.instance.runtime_properties[EXTERNAL_RESOURCE_ID])

    props = iface.properties
    for key, value in props.items():
        tested_value = test(value)
        ctx.instance.runtime_properties[key] = tested_value


@decorators.aws_resource(CloudFormationStack, RESOURCE_TYPE,
                         ignore_properties=True)
@decorators.wait_for_delete(
    status_deleted=['DELETE_COMPLETE'],
    status_pending=['DELETE_IN_PROGRESS'])
def delete(iface, resource_config, **_):
    """Deletes an AWS CloudFormation Stack"""
    # Create a copy of the resource config for clean manipulation.
    params = \
        dict() if not resource_config else resource_config.copy()
    name = params.get(RESOURCE_NAME)
    if not name:
        name = iface.resource_id
    iface.delete({RESOURCE_NAME: name})

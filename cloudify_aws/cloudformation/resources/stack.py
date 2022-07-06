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
import time
import json
from datetime import datetime

# Third party imports
from botocore.exceptions import ClientError
from cloudify.exceptions import NonRecoverableError

# Local imports
from cloudify_aws.common._compat import text_type
from cloudify_aws.common import decorators, utils
from cloudify_aws.cloudformation import AWSCloudFormationBase
from cloudify_aws.common.constants import EXTERNAL_RESOURCE_ID

RESOURCE_TYPE = 'CloudFormation Stack'
RESOURCE_NAME = 'StackName'
RESOURCE_NAMES = 'StackNames'
STACKS = 'Stacks'
TEMPLATEBODY = 'TemplateBody'
STATUS = 'StackStatus'
STACK_RESOURCES = 'StackResourceSummaries'
STACK_RESOURCES_DRIFTS = 'StackResourceDrifts'
STACK_DRIFT_DETECTION_ID = 'StackDriftDetectionId'
DRIFT_STATUS_FILTERS = 'StackResourceDriftStatusFilters'
STACK_RESOURCES_RUNTIME_PROP = 'state'
STACK_DETECTION_STATUS = 'DetectionStatus'
SAVED_PROPERTIES = 'saved_properties_keys'
IS_DRIFTED = 'is_drifted'
DRIFTED_STATUS = 'DRIFTED'
DRIFT_INFO = 'DriftInformation'
STACK_DRIFT_STATUS = 'StackDriftStatus'


class CloudFormationStack(AWSCloudFormationBase):
    """
        AWS CloudFormation Stack interface
    """

    def __init__(self, ctx_node, resource_id=None, client=None, logger=None):
        AWSCloudFormationBase.__init__(self, ctx_node, resource_id, client,
                                       logger)
        self.type_name = RESOURCE_TYPE
        self._properties = {}
        self._describe_call = 'describe_stacks'

    @property
    def properties(self):
        '''Gets the properties of an external resource'''
        if not self.resource_id:
            return
        if not self._properties:
            res = self.get_describe_result({RESOURCE_NAME: self.resource_id})
            if STACKS in res:
                for stack in res[STACKS]:
                    if self.resource_id == stack[RESOURCE_NAME]:
                        self._properties = stack
        return self._properties

    @property
    def status(self):
        '''Gets the status of an external resource'''
        return self.properties.get(STATUS)

    @property
    def exists(self):
        """
            Check if Stack exists.
        """
        return True if self.properties else False

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

    def list_resources(self):
        """
            List resources of AWS CloudFormation Stack.
        """
        params = {RESOURCE_NAME: self.resource_id}
        try:
            resources = \
                self.client.list_stack_resources(**params)
        except ClientError:
            return []
        else:
            return resources.get(STACK_RESOURCES, [])

    def detect_stack_drifts(self):
        """
            Invoke Drifts detection of AWS CloudFormation Stack.
        """
        params = {RESOURCE_NAME: self.resource_id}
        try:
            stack_drift_detection_id = \
                self.client.detect_stack_drift(**params).get(
                    STACK_DRIFT_DETECTION_ID)
            detection_status_response = \
                self.client.describe_stack_drift_detection_status(
                    StackDriftDetectionId=stack_drift_detection_id)
            # Wait for drift detections to end.
            while detection_status_response[STACK_DETECTION_STATUS] == \
                    'DETECTION_IN_PROGRESS':
                time.sleep(1)
                detection_status_response = \
                    self.client.describe_stack_drift_detection_status(
                        StackDriftDetectionId=stack_drift_detection_id)
        except ClientError:
            pass
        else:
            return detection_status_response[STACK_DETECTION_STATUS]

    def resources_drifts(self):
        """
        Returns drift information for the resources that have been checked for
        drift in the stack.
        Will return only resources with drift status MODIFIED, DELETED.
        """
        params = {RESOURCE_NAME: self.resource_id,
                  DRIFT_STATUS_FILTERS: ['DELETED', 'MODIFIED']
                  }
        try:
            resources = \
                self.client.describe_stack_resource_drifts(**params)
        except ClientError:
            return []
        else:
            return resources.get(STACK_RESOURCES_DRIFTS, [])


@decorators.aws_resource(CloudFormationStack, RESOURCE_TYPE)
def prepare(ctx, resource_config, **_):
    """Prepares an AWS CloudFormation Stack"""
    # Save the parameters
    ctx.instance.runtime_properties['resource_config'] = resource_config


@decorators.aws_resource(CloudFormationStack, RESOURCE_TYPE)
@decorators.wait_for_status(
    status_good=['CREATE_COMPLETE', 'UPDATE_COMPLETE'],
    status_pending=['CREATE_IN_PROGRESS',
                    'REVIEW_IN_PROGRESS',
                    'UPDATE_IN_PROGRESS'])
def create(ctx, iface, resource_config, minimum_wait_time=None, **_):
    """Creates an AWS CloudFormation Stack"""
    resource_id = \
        iface.resource_id or \
        utils.get_resource_id(
            ctx.node,
            ctx.instance,
            resource_config.get(RESOURCE_NAME),
            use_instance_id=True)
    resource_config[RESOURCE_NAME] = resource_id
    utils.update_resource_id(ctx.instance, resource_id)

    template_body = resource_config.get(TEMPLATEBODY, {})
    if template_body and not isinstance(template_body, text_type):
        resource_config[TEMPLATEBODY] = json.dumps(template_body)
    if not iface.resource_id:
        setattr(iface, 'resource_id', resource_config.get(RESOURCE_NAME))

    # Our status is not configured for failing on create,
    # so this is handled here.
    if not iface.exists:
        # Actually create the resource
        iface.create(resource_config)
    elif iface.exists and iface.status in ['CREATE_COMPLETE',
                                           'UPDATE_COMPLETE',
                                           'CREATE_IN_PROGRESS',
                                           'UPDATE_IN_PROGRESS',
                                           'REVIEW_IN_PROGRESS',
                                           'UPDATE_COMPLETE_'
                                           'CLEANUP_IN_PROGRESS']:
        raise NonRecoverableError(
            'Stack deployment failed in status {}, reason: {}'.format(
                iface.resource_id, iface.status, iface.properties.get(
                    'StackStatusReason')))

    if minimum_wait_time is not None and minimum_wait_time > 0:
        arrived_at_min_wait_time(ctx, minimum_wait_time)


def test(_value):
    if isinstance(_value, datetime):
        return text_type(_value)
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


@decorators.aws_resource(CloudFormationStack, RESOURCE_TYPE)
def start(ctx, iface, **_):
    """Update Runtime Properties an AWS CloudFormation Stack"""

    if not iface.resource_id:
        iface.update_resource_id(
            ctx.instance.runtime_properties[EXTERNAL_RESOURCE_ID])

    # Pull stack details and store in runtime properties.
    _pull(ctx, iface)


@decorators.aws_resource(CloudFormationStack, RESOURCE_TYPE,
                         ignore_properties=True)
@decorators.wait_for_delete(
    status_deleted=['DELETE_COMPLETE'],
    status_pending=['DELETE_IN_PROGRESS'],
    status_not_deleted=['CREATE_COMPLETE',
                        'REVIEW_IN_PROGRESS',
                        'UPDATE_COMPLETE',
                        'ROLLBACK_FAILED'])
def delete(ctx, iface, resource_config, minimum_wait_time=None, **_):
    """Deletes an AWS CloudFormation Stack"""
    name = resource_config.get(RESOURCE_NAME)
    if not name:
        name = iface.resource_id
    iface.delete({RESOURCE_NAME: name})

    if minimum_wait_time is not None and minimum_wait_time > 0:
        arrived_at_min_wait_time(ctx, minimum_wait_time)


@decorators.aws_resource(CloudFormationStack, RESOURCE_TYPE)
def pull(ctx, iface, **_):
    _pull(ctx, iface)


def _pull(ctx, iface):
    if not iface.exists:
        ctx.instance.runtime_properties[STACK_RESOURCES_RUNTIME_PROP] = []
        delete_stack_info_runtime_properties(ctx)
        # If the stack was deleted so it drifted.
        ctx.instance.runtime_properties[IS_DRIFTED] = True
        return
    ctx.logger.debug(
        "Detecting stack {stack_id} drifts.".format(
            stack_id=iface.resource_id))
    iface.detect_stack_drifts()
    update_runtime_properties_with_stack_info(ctx, iface)
    resources = iface.list_resources()
    ctx.logger.debug("Updating stack resources state.")
    ctx.instance.runtime_properties[STACK_RESOURCES_RUNTIME_PROP] = test(
        resources)
    drifts = iface.resources_drifts()
    ctx.instance.runtime_properties[STACK_RESOURCES_DRIFTS] = test(
        drifts)
    ctx.logger.debug("Updating stack resources drifts.")
    ctx.instance.runtime_properties.get(
        SAVED_PROPERTIES).append(STACK_RESOURCES_DRIFTS)


def delete_stack_info_runtime_properties(ctx):
    # delete runtime properties
    for runtime_property in ctx.instance.runtime_properties.get(
            SAVED_PROPERTIES, []):
        try:
            del ctx.instance.runtime_properties[runtime_property]
        except KeyError:
            pass
    ctx.instance.runtime_properties[SAVED_PROPERTIES] = []


def update_runtime_properties_with_stack_info(ctx, iface):
    props = iface.properties or {}
    # store saved runtime properties keys for deleting/updating
    # them during pull workflow.
    saved_keys = []
    ctx.logger.info(
        "Updating runtime properties with stack {id} details.".format(
            id=iface.resource_id))
    for key, value in props.items():
        tested_value = test(value)
        ctx.instance.runtime_properties[key] = tested_value
        saved_keys.append(key)

    set_is_drifted_runtime_property(ctx, props)
    # Special handling for outputs: they're provided by the stack
    # as a list of key-value pairs, which makes it impossible to
    # use them via intrinsic functions. So, create a dictionary out
    # of them.
    if 'Outputs' in props:
        outputs_items = {}
        for output in props['Outputs']:
            outputs_items[output['OutputKey']] = output['OutputValue']
        ctx.instance.runtime_properties['outputs_items'] = outputs_items
        saved_keys.append('outputs_items')
    ctx.instance.runtime_properties[SAVED_PROPERTIES] = saved_keys


def set_is_drifted_runtime_property(ctx, props):
    if props.get(DRIFT_INFO, {}).get(STACK_DRIFT_STATUS) == DRIFTED_STATUS:
        ctx.instance.runtime_properties[IS_DRIFTED] = True
    else:
        ctx.instance.runtime_properties[IS_DRIFTED] = False


# min_wait_time should be in seconds.
def arrived_at_min_wait_time(ctx, minimum_wait_time):
    ctx.logger.info('Minimum wait time provided: {}'.format(minimum_wait_time))
    count = 0
    ten_sec_to_sleep = 10
    while count < minimum_wait_time:
        time.sleep(ten_sec_to_sleep)
        count += ten_sec_to_sleep
        ctx.logger.info('The time elapsed is: {}'.format(count))

    ctx.logger.info('Minimum wait time elapsed.')

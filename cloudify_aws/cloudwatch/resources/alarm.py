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
    Cloudwatch.alarm
    ~~~~~~~~~~~~~~
    AWS Cloudwatch Alarm interface
"""
# Third party imports
from botocore.exceptions import ClientError, ParamValidationError

# Local imports
from cloudify_aws.common import decorators, utils
from cloudify_aws.cloudwatch import AWSCloudwatchBase

RESOURCE_TYPE = 'Cloudwatch Alarm'
RESOURCE_NAME = 'AlarmName'
RESOURCE_NAMES = 'AlarmNames'
METRIC_ALARMS = 'MetricAlarms'


class CloudwatchAlarm(AWSCloudwatchBase):
    """
        AWS Cloudwatch Alarm interface
    """
    def __init__(self, ctx_node, resource_id=None, client=None, logger=None):
        AWSCloudwatchBase.__init__(self, ctx_node, resource_id, client, logger)
        self.type_name = RESOURCE_TYPE

    @property
    def properties(self):
        """Gets the properties of an external resource"""
        if not self.resource_id:
            return
        params = {RESOURCE_NAMES: [self.resource_id]}
        try:
            resources = \
                self.client.describe_alarms(**params)
        except (ParamValidationError, ClientError):
            pass
        else:
            return resources.get(METRIC_ALARMS, [None])[0]

    @property
    def status(self):
        """Gets the status of an external resource"""
        return None

    def create(self, params):
        """
            Create a new AWS Cloudwatch Alarm.
        """
        return self.make_client_call('put_metric_alarm', params)

    def delete(self, params=None):
        """
            Deletes an existing AWS Cloudwatch Alarm.
        """
        self.logger.debug('Deleting %s with parameters: %s'
                          % (self.type_name, params))
        res = self.client.delete_alarms(**params)
        self.logger.debug('Response: %s' % res)
        return res


@decorators.aws_resource(CloudwatchAlarm, RESOURCE_TYPE)
def prepare(ctx, resource_config, **_):
    """Prepares an AWS Cloudwatch Alarm"""
    # Save the parameters
    ctx.instance.runtime_properties['resource_config'] = resource_config


@decorators.aws_resource(CloudwatchAlarm, RESOURCE_TYPE)
def create(ctx, iface, resource_config, **_):
    """Creates an AWS Cloudwatch Alarm"""
    resource_id = \
        iface.resource_id or \
        utils.get_resource_id(
            ctx.node,
            ctx.instance,
            resource_config.get(RESOURCE_NAME),
            use_instance_id=True)
    resource_config[RESOURCE_NAME] = resource_id
    utils.update_resource_id(ctx.instance, resource_id)
    if not iface.resource_id:
        setattr(iface, 'resource_id', resource_config.get(RESOURCE_NAME))

    # Actually create the resource
    iface.create(resource_config)


@decorators.aws_resource(CloudwatchAlarm, RESOURCE_TYPE,
                         ignore_properties=True)
def delete(iface, resource_config, **_):
    """Deletes an AWS Cloudwatch Alarm"""
    if RESOURCE_NAMES not in resource_config:
        resource_config.update({RESOURCE_NAMES: [iface.resource_id]})
    iface.delete(resource_config)

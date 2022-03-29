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
    Autoscaling.Notification Configuration
    ~~~~~~~~~~~~~~
    AWS Autoscaling Group Notification Configuration interface
"""
# Cloudify
from cloudify_aws.common import decorators, utils
from cloudify_aws.autoscaling import AutoscalingBase
# Boto
from botocore.exceptions import ClientError, ParamValidationError

RESOURCE_TYPE = 'AutoScaling Group Notification Configuration'
DESCRIBE_KEY = 'AutoScalingGroupNames'
RESOURCE_KEY = 'NotificationConfigurations'
AUTOSCALING_GROUP_TARGET = 'AutoScalingGroupName'
TOPIC_TARGET = 'TopicARN'
AUTOSCALING_TYPE = 'cloudify.nodes.aws.autoscaling.Group'
TOPIC_TYPE = 'cloudify.nodes.aws.SNS.Topic'


class AutoscalingNotification(AutoscalingBase):
    """
        Autoscaling Group Notification Configuration
    """
    def __init__(self, ctx_node, resource_id=None, client=None, logger=None):
        AutoscalingBase.__init__(self, ctx_node, resource_id, client, logger)
        self.type_name = RESOURCE_TYPE

    @property
    def properties(self):
        """Gets the properties of an external resource"""
        if not self.resource_id:
            return
        params = {DESCRIBE_KEY: [self.resource_id]}
        try:
            resources = \
                self.client.describe_notification_configurations(**params)
        except (ParamValidationError, ClientError):
            return []
        else:
            return resources.get(RESOURCE_KEY, [None])

    @property
    def status(self):
        """Gets the status of an external resource"""
        return None

    def create(self, params=None):
        """
            Create a new AWS Autoscaling Group Notification Configuration.
        """
        return self.make_client_call('put_notification_configuration', params)

    def delete(self, params=None):
        """
            Deletes an existing Autoscaling Group Notification Configuration.
        """
        self.logger.debug('Deleting %s with parameters: %s'
                          % (self.type_name, params))
        res = self.client.delete_notification_configuration(**params)
        self.logger.debug('Response: %s' % res)
        return res


@decorators.aws_resource(AutoscalingNotification, RESOURCE_TYPE)
def prepare(ctx, resource_config, **_):
    """Prepares an AWS Autoscaling Group Notification Configuration"""
    # Save the parameters
    ctx.instance.runtime_properties['resource_config'] = resource_config


@decorators.aws_resource(AutoscalingNotification, RESOURCE_TYPE)
def create(ctx, iface, resource_config, **_):
    """Creates an AWS Autoscaling Group Notification Configuration"""
    autoscaling_group = resource_config.get(AUTOSCALING_GROUP_TARGET)
    if not autoscaling_group:
        autoscaling_group = \
            utils.find_resource_id_by_type(ctx.instance, AUTOSCALING_TYPE)
        resource_config[AUTOSCALING_GROUP_TARGET] = autoscaling_group

    topic_arn = resource_config.get(TOPIC_TARGET)
    if not topic_arn:
        topic_arn = utils.find_resource_arn_by_type(ctx.instance, TOPIC_TYPE)
        resource_config[TOPIC_TARGET] = topic_arn

    # Actually create the resource
    iface.create(resource_config)


@decorators.aws_resource(AutoscalingNotification, RESOURCE_TYPE,
                         ignore_properties=True)
def delete(ctx, iface, resource_config, **_):
    """Deletes an AWS Autoscaling Group Notification Configuration"""
    autoscaling_group = resource_config.get(AUTOSCALING_GROUP_TARGET)
    if not autoscaling_group:
        autoscaling_group = \
            utils.find_resource_id_by_type(ctx.instance, AUTOSCALING_TYPE)
        resource_config[AUTOSCALING_GROUP_TARGET] = autoscaling_group

    topic_arn = resource_config.get(TOPIC_TARGET)
    if not topic_arn:
        topic_arn = \
            utils.find_resource_arn_by_type(ctx.instance, TOPIC_TYPE)
        resource_config[TOPIC_TARGET] = topic_arn

    iface.delete(resource_config)

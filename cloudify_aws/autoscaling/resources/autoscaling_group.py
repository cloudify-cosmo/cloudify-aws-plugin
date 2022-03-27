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
    Autoscaling.Group
    ~~~~~~~~~~~~~~
    AWS Autoscaling Group interface

"""

# Third party imports
from cloudify.exceptions import OperationRetry, NonRecoverableError

from cloudify_aws.common import decorators, utils
from cloudify_aws.autoscaling import AutoscalingBase

# Boto
from botocore.exceptions import ClientError, ParamValidationError

RESOURCE_TYPE = 'Autoscaling Group'
GROUPS = 'AutoScalingGroups'
RESOURCE_NAMES = 'AutoScalingGroupNames'
RESOURCE_NAME = 'AutoScalingGroupName'
GROUP_ARN = 'AutoScalingGroupARN'
LC_NAME = 'LaunchConfigurationName'
LC_TYPE = 'cloudify.nodes.aws.autoscaling.LaunchConfiguration'
INSTANCE_ID = 'InstanceId'
INSTANCE_IDS = 'InstanceIds'
INSTANCE_TYPE = 'cloudify.aws.nodes.Instance'
INSTANCES = 'Instances'
SUBNET_LIST = 'VPCZoneIdentifier'
SUBNET_TYPE = 'cloudify.nodes.aws.ec2.Subnet'
SUBNET_TYPE_DEPRECATED = 'cloudify.aws.nodes.Subnet'


class AutoscalingGroup(AutoscalingBase):
    """
        Autoscaling Group interface
    """
    def __init__(self, ctx_node, resource_id=None, client=None, logger=None):
        AutoscalingBase.__init__(self, ctx_node, resource_id, client, logger)
        self.type_name = RESOURCE_TYPE

    @property
    def properties(self):
        """Gets the properties of an external resource"""
        if not self.resource_id:
            return
        params = {RESOURCE_NAMES: [self.resource_id]}
        try:
            resources = \
                self.client.describe_auto_scaling_groups(**params)
        except (ParamValidationError, ClientError):
            pass
        else:
            return resources.get(GROUPS, [None])[0]

    @property
    def status(self):
        """Gets the status of an external resource"""
        props = self.properties
        if not props:
            return None
        return props.get('Status')

    def create(self, params):
        """
            Create a new AWS Autoscaling Group.
        """
        return self.make_client_call('create_auto_scaling_group', params)

    def delete(self, params=None):
        """
            Deletes an existing AWS Autoscaling Group.
        """
        self.logger.debug('Deleting %s with parameters: %s'
                          % (self.type_name, params))
        res = self.client.delete_auto_scaling_group(**params)
        self.logger.debug('Response: %s' % res)
        return res

    def update(self, params=None):
        """
            Updates an existing AWS Autoscaling Group.
        """
        self.logger.debug('Updating %s with parameters: %s'
                          % (self.type_name, params))
        res = self.client.update_auto_scaling_group(**params)
        self.logger.debug('Response: %s' % res)
        return res

    def remove_instances(self, params=None):
        """
            Deletes an existing AWS Autoscaling Group.
        """
        self.logger.debug('Removing %s with parameters: %s'
                          % (self.type_name, params))
        try:
            res = self.client.detach_instances(**params)
        except ClientError:
            pass
        else:
            self.logger.debug('Response: %s' % res)
            return res


@decorators.aws_resource(AutoscalingGroup, RESOURCE_TYPE)
def prepare(ctx, resource_config, **_):
    """Prepares an AWS Autoscaling Group"""
    # Save the parameters
    ctx.instance.runtime_properties['resource_config'] = resource_config


@decorators.aws_resource(AutoscalingGroup, RESOURCE_TYPE)
@decorators.aws_params(RESOURCE_NAME)
def create(ctx, iface, resource_config, params, **_):
    """Creates an AWS Autoscaling Group"""
    # Try to populate the Launch Configuration field
    # with a relationship
    lc_name = params.get(LC_NAME)
    instance_id = params.get(INSTANCE_ID)

    if not lc_name and not instance_id:
        lc_name = \
            utils.find_resource_id_by_type(
                ctx.instance,
                LC_TYPE)
        if lc_name:
            params.update({LC_NAME: lc_name})

    # If no LC_NAME, try to populate the
    # InstanceId field with a relationship.
    if not lc_name:
        instance_id = \
            utils.find_resource_id_by_type(
                ctx.instance,
                INSTANCE_TYPE)
        params[INSTANCE_ID] = instance_id

    get_subnet_list(ctx.instance, params)

    # Actually create the resource
    if not iface.resource_id:
        setattr(iface, 'resource_id', params.get(RESOURCE_NAME))
    iface.create(params)
    iface.update_resource_id(iface.properties.get(RESOURCE_NAME))
    utils.update_resource_id(
        ctx.instance, iface.properties.get(RESOURCE_NAME))
    utils.update_resource_arn(
        ctx.instance, iface.properties.get(GROUP_ARN))


@decorators.aws_resource(AutoscalingGroup, RESOURCE_TYPE)
def stop(iface, resource_config, **_):
    """Stops all instances associated with Autoscaling group."""

    autoscaling_group = iface.properties

    instances = autoscaling_group.get(INSTANCES, [])
    minsize = autoscaling_group.get('MinSize')
    maxsize = autoscaling_group.get('MaxSize')
    desired_cap = autoscaling_group.get('DesiredCapacity')

    # If rules would allow scaling
    if minsize != 0 and desired_cap != 0 and maxsize != 0:
        stop_parameters = {
            RESOURCE_NAME: iface.resource_id,
            'MinSize': 0,
            'MaxSize': 0,
            'DesiredCapacity': 0
        }
        iface.update(stop_parameters)
        raise OperationRetry(
            'Updating %s ID# "%s" parameters before deletion.'
            % (iface.type_name, iface.resource_id))

    # Retry until there are no instances.
    if len(instances) > 0:
        raise OperationRetry(
            '%s ID# "%s" is deleting associated instances.'
            % (iface.type_name, iface.resource_id))


@decorators.aws_resource(AutoscalingGroup, RESOURCE_TYPE,
                         ignore_properties=True)
def delete(iface, resource_config, **_):
    """Deletes an AWS Autoscaling Group"""
    if RESOURCE_NAME not in resource_config:
        resource_config.update({RESOURCE_NAME: iface.resource_id})

    autoscaling_group = iface.properties
    instances = autoscaling_group.get(INSTANCES)
    iface.remove_instances(
        {RESOURCE_NAME: resource_config.get(RESOURCE_NAME),
         'ShouldDecrementDesiredCapacity': False,
         INSTANCE_IDS:
             [instance.get(INSTANCE_ID) for instance in instances]})

    iface.delete(resource_config)


def get_subnet_list(ctx_instance, params):
    subnet_list = params.get(SUBNET_LIST)
    subnet_list = subnet_list or []
    if not isinstance(subnet_list, list):
        raise NonRecoverableError(
            'The provided {} is not a list, '
            'please reformat. Provided value: {}'.format(
                SUBNET_LIST, subnet_list))

    subnet_list = \
        utils.add_resources_from_rels(
            ctx_instance,
            SUBNET_TYPE,
            subnet_list)
    subnet_list = \
        utils.add_resources_from_rels(
            ctx_instance,
            SUBNET_TYPE_DEPRECATED,
            subnet_list)
    if subnet_list:
        # Remove any duplicate items from subnet list
        subnet_list = list(set(subnet_list))
        params[SUBNET_LIST] = ', '.join(subnet_list)

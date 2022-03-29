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
    Autoscaling.Policy
    ~~~~~~~~~~~~~~
    AWS Autoscaling Policy interface
"""
# Third part imports
from botocore.exceptions import ClientError, ParamValidationError

# Local imports
from cloudify_aws.common import decorators, utils
from cloudify_aws.autoscaling import AutoscalingBase

RESOURCE_TYPE = 'Autoscaling Policy'
GROUP_NAME = 'AutoScalingGroupName'
SCALING_POLICIES = 'ScalingPolicies'
RESOURCE_NAMES = 'PolicyNames'
RESOURCE_NAME = 'PolicyName'
POLICY_ARN = 'PolicyARN'
POLICY_TYPES = 'PolicyTypes'
GROUP_TYPE = 'cloudify.nodes.aws.autoscaling.Group'


class AutoscalingPolicy(AutoscalingBase):
    """
        Autoscaling Autoscaling Policy interface
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
                self.client.describe_policies(**params)
        except (ParamValidationError, ClientError):
            pass
        else:
            return resources.get(SCALING_POLICIES, [None])[0]

    @property
    def status(self):
        """Gets the status of an external resource"""
        return None

    def create(self, params):
        """
            Create a new AWS Autoscaling Autoscaling Policy.
        """
        return self.make_client_call('put_scaling_policy', params)

    def delete(self, params=None):
        """
            Deletes an existing AWS Autoscaling Policy.
        """
        self.logger.debug('Deleting %s with parameters: %s'
                          % (self.type_name, params))
        res = self.client.delete_policy(**params)
        self.logger.debug('Response: %s' % res)
        return res


@decorators.aws_resource(AutoscalingPolicy, RESOURCE_TYPE)
def prepare(ctx, resource_config, **_):
    """Prepares an AWS Autoscaling Autoscaling Policy"""
    # Save the parameters
    ctx.instance.runtime_properties['resource_config'] = resource_config


@decorators.aws_resource(AutoscalingPolicy, RESOURCE_TYPE)
@decorators.aws_params(RESOURCE_NAME)
def create(ctx, iface, resource_config, params, **_):
    """Creates an AWS Autoscaling Autoscaling Policy"""

    # Ensure the $GROUP_NAME parameter is populated.
    autoscaling_group = params.get(GROUP_NAME)
    if not autoscaling_group:
        autoscaling_group = \
            utils.find_resource_id_by_type(ctx.instance, GROUP_TYPE)
        params[GROUP_NAME] = autoscaling_group
    ctx.instance.runtime_properties[GROUP_NAME] = autoscaling_group

    # Actually create the resource
    if not iface.resource_id:
        setattr(iface, 'resource_id', params.get(RESOURCE_NAME))
    resource_arn = iface.create(params)[POLICY_ARN]
    utils.update_resource_arn(
        ctx.instance, resource_arn)


@decorators.aws_resource(AutoscalingPolicy, RESOURCE_TYPE,
                         ignore_properties=True)
def delete(ctx, iface, resource_config, **_):
    """Deletes an AWS Autoscaling Autoscaling Policy"""
    # Ensure the $GROUP_NAME parameter is populated.
    autoscaling_group = resource_config.get(GROUP_NAME)
    if not autoscaling_group:
        autoscaling_group = ctx.instance.runtime_properties[GROUP_NAME]
        resource_config.update({GROUP_NAME: autoscaling_group})

    if RESOURCE_NAME not in resource_config:
        resource_config.update({RESOURCE_NAME: iface.resource_id})

    iface.delete(resource_config)

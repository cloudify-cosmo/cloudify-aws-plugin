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
    Autoscaling.LaunchConfiguration
    ~~~~~~~~~~~~~~
    AWS Autoscaling Launch Configuration interface
"""
# Third party imports
from botocore.exceptions import ClientError, ParamValidationError

# Cloudify imports
from cloudify.exceptions import NonRecoverableError

# Local imports
from cloudify_aws.common._compat import text_type
from cloudify_aws.common import decorators, utils
from cloudify_aws.autoscaling import AutoscalingBase

RESOURCE_TYPE = 'Autoscaling Launch Configuration'
LCS = 'LaunchConfigurations'
RESOURCE_NAMES = 'LaunchConfigurationNames'
RESOURCE_NAME = 'LaunchConfigurationName'
IAM_INSTANCE_PROFILE = 'IamInstanceProfile'
LC_ARN = 'LaunchConfigurationARN'
IMAGEID = 'ImageId'
INSTANCEID = 'InstanceId'
INSTANCE_TYPE = 'cloudify.aws.nodes.Instance'
INSTANCE_TYPE_NEW = 'cloudify.nodes.aws.ec2.Instances'
INSTANCE_TYPE_PROPERTY = 'InstanceType'
INSTANCE_TYPE_PROPERTY_DEPRECATED = 'instance_type'
SECGROUPS = 'SecurityGroups'
SECGROUP_TYPE = 'cloudify.aws.nodes.SecurityGroup'


class AutoscalingLaunchConfiguration(AutoscalingBase):
    """
        Autoscaling Autoscaling Launch Configuration interface
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
                self.client.describe_launch_configurations(**params)
        except (ParamValidationError, ClientError):
            pass
        else:
            return resources.get(LCS, [None])[0]

    @property
    def status(self):
        """Gets the status of an external resource"""
        return None

    def create(self, params):
        """
            Create a new AWS Autoscaling Autoscaling Launch Configuration.
        """
        return self.make_client_call('create_launch_configuration', params)

    def delete(self, params=None):
        """
            Deletes an existing AWS Autoscaling Autoscaling
            Launch Configuration.
        """
        self.logger.debug('Deleting %s with parameters: %s'
                          % (self.type_name, params))
        res = self.client.delete_launch_configuration(**params)
        self.logger.debug('Response: %s' % res)
        return res


@decorators.aws_resource(AutoscalingLaunchConfiguration, RESOURCE_TYPE)
def prepare(ctx, resource_config, **_):
    """Prepares an AWS Autoscaling Autoscaling Launch Configuration"""
    # Save the parameters
    ctx.instance.runtime_properties['resource_config'] = resource_config


@decorators.aws_resource(AutoscalingLaunchConfiguration, RESOURCE_TYPE)
@decorators.aws_params(RESOURCE_NAME)
def create(ctx, iface, resource_config, params, **_):
    """Creates an AWS Autoscaling Autoscaling Launch Configuration"""

    # Check if the "IamInstanceProfile" is passed or not and then update it
    iam_instance_profile = params.get(IAM_INSTANCE_PROFILE)
    if iam_instance_profile:
        if isinstance(iam_instance_profile, text_type):
            iam_instance_profile = iam_instance_profile.strip()
            params[IAM_INSTANCE_PROFILE] = text_type(iam_instance_profile)
        else:
            raise NonRecoverableError(
                'Invalid {0} data type for {1}'
                ''.format(type(iam_instance_profile), IAM_INSTANCE_PROFILE))

    # Add Security Groups
    secgroups_list = params.get(SECGROUPS, [])
    params[SECGROUPS] = \
        utils.add_resources_from_rels(
            ctx.instance,
            SECGROUP_TYPE,
            secgroups_list)

    image_id = params.get(IMAGEID)

    # Add Instance and Instance Type
    instance_id = params.get(INSTANCEID)
    instance_type = params.get(INSTANCE_TYPE_PROPERTY)
    if not image_id and not instance_id:
        instance_id = utils.find_resource_id_by_type(
            ctx.instance,
            INSTANCE_TYPE_NEW) or \
            utils.find_resource_id_by_type(
                ctx.instance,
                INSTANCE_TYPE)
        params.update({INSTANCEID: instance_id})
    if instance_id and not instance_type:
        targ = utils.find_rel_by_node_type(
            ctx.instance,
            INSTANCE_TYPE_NEW) or \
            utils.find_rel_by_node_type(
                ctx.instance,
                INSTANCE_TYPE)
        if targ:
            instance_type = \
                targ.target.instance.runtime_properties.get(
                    'resource_config', {}).get(
                        INSTANCE_TYPE_PROPERTY) or \
                targ.target.node.properties.get(
                    INSTANCE_TYPE_PROPERTY_DEPRECATED)
        params.update({INSTANCE_TYPE_PROPERTY: instance_type})

    utils.update_resource_id(
        ctx.instance, params.get(RESOURCE_NAME))
    iface.update_resource_id(params.get(RESOURCE_NAME))
    # Actually create the resource
    if not iface.resource_id:
        setattr(iface, 'resource_id', params.get(RESOURCE_NAME))
    iface.create(params)
    resource_arn = iface.properties[LC_ARN]
    utils.update_resource_arn(
        ctx.instance, resource_arn)


@decorators.aws_resource(AutoscalingLaunchConfiguration, RESOURCE_TYPE,
                         ignore_properties=True)
def delete(iface, resource_config, **_):
    """Deletes an AWS Autoscaling Autoscaling Launch Configuration"""
    if RESOURCE_NAME not in resource_config:
        resource_config.update({RESOURCE_NAME: iface.resource_id})
    utils.handle_response(iface, 'delete', resource_config, ['not found'])

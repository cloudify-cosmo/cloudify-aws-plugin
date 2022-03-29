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
    Cloudwatch.target
    ~~~~~~~~~~~~~~
    AWS Cloudwatch Target interface
"""
# Cloudify
from cloudify_aws.common import decorators, utils
from cloudify_aws.cloudwatch import AWSCloudwatchBase
from cloudify_aws.common.connection import Boto3Connection
from cloudify_aws.common.constants import EXTERNAL_RESOURCE_ARN

RESOURCE_TYPE = 'Cloudwatch Target'
TARGETS = 'Targets'
IDS = 'Ids'
ID = 'Id'
ARN = 'Arn'
RULE = 'Rule'
RULE_TYPE = 'cloudify.nodes.aws.cloudwatch.Rule'


class CloudwatchTarget(AWSCloudwatchBase):
    """
        AWS Cloudwatch Target interface
    """
    def __init__(self, ctx_node, resource_id=None, client=None, logger=None):
        AWSCloudwatchBase.__init__(
            self,
            ctx_node,
            resource_id,
            client or Boto3Connection(ctx_node).client('events'),
            logger)
        self.type_name = RESOURCE_TYPE

    @property
    def properties(self):
        """Gets the properties of an external resource"""
        return None

    @property
    def status(self):
        """Gets the status of an external resource"""
        return None

    def create(self, params):
        """
            Create a new AWS Cloudwatch Target.
        """
        return self.make_client_call('put_targets', params)

    def delete(self, params=None):
        """
            Deletes an existing AWS Cloudwatch Target.
        """
        self.logger.debug('Deleting %s with parameters: %s'
                          % (self.type_name, params))
        res = self.client.remove_targets(**params)
        self.logger.debug('Response: %s' % res)
        return res


@decorators.aws_resource(CloudwatchTarget, RESOURCE_TYPE)
def prepare(ctx, resource_config, **_):
    """Prepares an AWS Cloudwatch Alarm"""
    # Save the parameters
    ctx.instance.runtime_properties['resource_config'] = resource_config


@decorators.aws_resource(CloudwatchTarget, RESOURCE_TYPE)
def create(ctx, iface, resource_config, **_):
    """Creates an AWS Cloudwatch Target"""
    rule = resource_config.get(RULE)
    if not rule:
        rule = utils.find_resource_id_by_type(
            ctx.instance, RULE_TYPE)
        resource_config[RULE] = rule

    targets = resource_config.get(TARGETS, [])
    for target in targets:
        target_arn = target.get(ARN, '')
        if not utils.validate_arn(target_arn):
            targs = \
                utils.find_rels_by_node_name(
                    ctx.instance,
                    target_arn)
            if targs:
                target_arn = \
                    targs[0].target.instance.runtime_properties.get(
                        EXTERNAL_RESOURCE_ARN, target_arn)
        targets.remove(target)
        target[ARN] = target_arn
        targets.append(target)

    # Actually create the resource
    iface.create(resource_config)


@decorators.aws_resource(CloudwatchTarget, RESOURCE_TYPE)
def delete(ctx, iface, resource_config, **_):
    """Deletes an AWS Cloudwatch Target"""

    rule = resource_config.get(RULE)
    if not rule:
        rule = utils.find_resource_id_by_type(ctx.instance, RULE_TYPE)
        resource_config[RULE] = rule

    resource_config[IDS] = \
        [target.get(ID) for target in resource_config.pop(TARGETS)]

    iface.delete(resource_config)

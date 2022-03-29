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
    SQS.queue
    ~~~~~~~~
    AWS SQS Queue interface
"""
# Standard imports
import json

# Third party imports
from botocore.exceptions import ClientError, ParamValidationError

# Local imports
from cloudify_aws.common._compat import text_type
from cloudify_aws.common import decorators, utils
from cloudify_aws.sqs import SQSBase

RESOURCE_TYPE = 'SQS Queue'
RESOURCE_NAME = 'QueueName'
QUEUE_URL = 'QueueUrl'
QUEUE_URLS = 'QueueUrls'
QUEUE_ARN = 'QueueArn'
POLICY = 'Policy'


class SQSQueue(SQSBase):
    """
        AWS SQS Queue interface
    """
    def __init__(self, ctx_node, resource_id=None, client=None, logger=None):
        SQSBase.__init__(self, ctx_node, resource_id, client, logger)
        self.type_name = RESOURCE_TYPE

    @property
    def properties(self):
        """Gets the properties of an external resource"""
        if not self.resource_id:
            return
        try:
            resource = \
                self.client.list_queues(
                    QueueNamePrefix=self.resource_id)
        except (ParamValidationError, ClientError):
            pass
        else:
            return resource.get(QUEUE_URLS, [None])[0]
        return None

    @property
    def status(self):
        """Gets the status of an external resource"""
        return None

    def create(self, params):
        """
            Create a new AWS SQS Queue.
        """
        return self.make_client_call('create_queue', params)

    def delete(self, params=None):
        """
            Deletes an existing AWS SQS Queue.
        """
        self.logger.debug('Deleting %s with parameters: %s'
                          % (self.type_name, params))
        self.client.delete_queue(**params)


@decorators.aws_resource(SQSQueue, RESOURCE_TYPE)
def prepare(ctx, resource_config, **_):
    """Prepares an AWS SQS Queue"""
    # Save the parameters
    ctx.instance.runtime_properties['resource_config'] = resource_config


@decorators.aws_resource(SQSQueue, RESOURCE_TYPE)
def create(ctx, iface, resource_config, **_):
    """Creates an AWS SQS Queue"""
    resource_id = \
        utils.get_resource_id(
            ctx.node,
            ctx.instance,
            resource_config.get(RESOURCE_NAME),
            use_instance_id=True
        )
    resource_config[RESOURCE_NAME] = resource_id
    utils.update_resource_id(ctx.instance, resource_id)

    queue_attributes = resource_config.get('Attributes', {})
    queue_attributes_policy = queue_attributes.get('Policy')
    if not isinstance(queue_attributes_policy, text_type):
        queue_attributes[POLICY] = json.dumps(queue_attributes_policy)

    # Actually create the resource
    create_response = iface.create(resource_config)
    # Attempt to retrieve the ARN.
    try:
        resource_attributes = iface.client.get_queue_attributes(
            QueueUrl=create_response[QUEUE_URL],
            AttributeNames=[QUEUE_ARN])
    except ClientError:
        utils.update_resource_arn(
            ctx.instance,
            None)
    else:
        utils.update_resource_arn(
            ctx.instance,
            resource_attributes.get('Attributes', {}).get(QUEUE_ARN))
    utils.update_resource_id(ctx.instance, create_response[QUEUE_URL])


@decorators.aws_resource(SQSQueue, RESOURCE_TYPE,
                         ignore_properties=True)
def delete(iface, resource_config, **_):
    """Deletes an AWS SQS Queue"""
    # Add the required QueueUrl parameter.
    if QUEUE_URL not in resource_config:
        resource_config.update({QUEUE_URL: iface.resource_id})

    # Actually delete the resource
    iface.delete(resource_config)

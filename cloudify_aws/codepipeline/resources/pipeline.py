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
    CodePipeline.Pipeline
    ~~~~~~~~~~~~~~
    AWS pipeline interface
"""
# Third party imports
from botocore.exceptions import ClientError, ParamValidationError

# Cloudify
from cloudify.decorators import operation
from cloudify.exceptions import OperationRetry
from cloudify_aws.common import decorators, utils
from cloudify_aws.codepipeline import CodePipelineBase

RESOURCE_TYPE = 'CodePipeline pipeline'
RESOURCE_NAME = 'name'
CREATED_STATUS = 'Created'


class CodePipelinePipeline(CodePipelineBase):
    """
        AWS CodePipeline pipeline interface
    """

    def __init__(self, ctx_node, resource_id=None, client=None, logger=None):
        CodePipelineBase.__init__(self, ctx_node, resource_id, client, logger)
        self.type_name = RESOURCE_TYPE

    @property
    def properties(self):
        """Gets the properties of an external resource"""
        if not self.resource_id:
            return
        resource = None
        try:
            resource = self.client.get_pipeline_state(
                name=self.resource_id)
        except (ParamValidationError, ClientError):
            pass
        return resource

    @property
    def status(self):
        """Gets the status of an external resource"""
        props = self.properties
        if props:
            if props.get('created'):
                return CREATED_STATUS

    def create(self, params):
        """
            Create a new Pipeline .
        """
        return self.make_client_call('create_pipeline', params)

    def delete(self, params=None):
        """
            Deletes an existing Pipeline.
        """
        self.logger.debug('Deleting {resource_type} with parameters:'
                          ' {params}'.format(resource_type=self.type_name,
                                             params=params))
        self.client.delete_pipeline(**params)

    def execute(self, name=None, clientRequestToken=None):
        """
            start execution of an existing Pipeline.
        """
        params = {'name': name if name else self.resource_id}
        if clientRequestToken:
            params.update({"clientRequestToken": clientRequestToken})
        self.logger.debug('Executing {resource_type} with parameters:'
                          ' {params}'.format(resource_type=self.type_name,
                                             params=params))

        return self.client.start_pipeline_execution(**params)


@decorators.aws_resource(CodePipelinePipeline, RESOURCE_TYPE)
def prepare(ctx, resource_config, **_):
    # Save the parameters
    ctx.instance.runtime_properties['resource_config'] = resource_config


@decorators.aws_resource(CodePipelinePipeline, RESOURCE_TYPE)
@decorators.wait_for_delete()
def delete(ctx, iface, resource_config, **_):
    """Deletes a Pipeline"""
    # Add the required name parameter.
    if RESOURCE_NAME not in resource_config:
        params = {RESOURCE_NAME: iface.resource_id}
    else:
        params = {RESOURCE_NAME: resource_config.get(RESOURCE_NAME)}
    ctx.logger.info("delete params {}".format(params))
    iface.delete(params)


@decorators.aws_resource(CodePipelinePipeline, RESOURCE_TYPE)
@decorators.wait_for_status(status_good=[CREATED_STATUS])
@decorators.aws_params(RESOURCE_NAME)
def create(ctx, iface, params, **_):
    # Actually create the resource
    ctx.logger.debug("create params: {params}".format(params=params))
    params.pop(RESOURCE_NAME)
    create_response = iface.create(params)
    resource_id = create_response['pipeline']['name']
    iface.update_resource_id(resource_id)
    utils.update_resource_id(ctx.instance, resource_id)


@operation
@decorators.aws_resource(CodePipelinePipeline, RESOURCE_TYPE)
def execute(ctx, iface, name=None, clientRequestToken=None, **_):
    try:
        execute_response = iface.execute(name, clientRequestToken)
        ctx.instance.runtime_properties[
            'execute_pipeline_response'] = execute_response
    except ClientError:
        error_traceback = utils.get_traceback_exception()
        raise OperationRetry(
            'Re-try start_pipeline_execution operation.',
            retry_after=2,
            causes=[error_traceback])

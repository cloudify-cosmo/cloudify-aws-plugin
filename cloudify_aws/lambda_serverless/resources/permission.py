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
'''
    Lambda.Permission
    ~~~~~~~~~~~~~~~~~
    AWS Lambda Permission interface
'''
# Standard imports
import json
from uuid import uuid4

# Local imports
from cloudify_aws.common._compat import text_type
from cloudify_aws.common import decorators, utils
from cloudify_aws.lambda_serverless import LambdaBase

RESOURCE_TYPE = 'Lambda Permission'
STATEMENT_ID = 'StatementId'
FUNCTION_NAME = 'FunctionName'
FUNCTION_TYPE = 'cloudify.nodes.aws.lambda.Function'


class LambdaPermission(LambdaBase):
    '''
        AWS Lambda Permission interface
    '''
    def __init__(self, ctx_node, resource_id=None, client=None, logger=None):
        LambdaBase.__init__(self, ctx_node, resource_id, client, logger)
        self.type_name = RESOURCE_TYPE

    @property
    def properties(self):
        '''Gets the properties of an external resource'''
        raise NotImplementedError('permission')

    @property
    def status(self):
        '''Gets the status of an external resource'''
        raise NotImplementedError('permission')

    def create(self, params):
        '''
            Create a new AWS Lambda Permission.
        '''
        return self.make_client_call('add_permission', params)

    def delete(self, params=None):
        '''
            Deletes an existing AWS Lambda Permission.
        '''
        params = params or dict()
        params.update(dict(StatementId=self.resource_id))
        self.logger.debug('Deleting %s with parameters: %s'
                          % (self.type_name, params))
        self.client.remove_permission(**params)


@decorators.aws_resource(LambdaPermission, RESOURCE_TYPE)
def prepare(ctx, resource_config, **_):
    '''Prepares an AWS Lambda Permission'''
    # Save the parameters
    if not utils.get_resource_id():
        if resource_config.get('StatementId'):
            utils.update_resource_id(
                ctx.instance, resource_config['StatementId'])
        else:
            utils.update_resource_id(ctx.instance, text_type(uuid4()))
    ctx.instance.runtime_properties['resource_config'] = resource_config


@decorators.aws_resource(LambdaPermission, RESOURCE_TYPE)
def create(ctx, iface, resource_config, **_):
    '''Creates an AWS Lambda Permission'''
    function_rels = \
        utils.find_rels_by_node_type(
            ctx.instance, FUNCTION_TYPE)

    lambda_function = None if len(function_rels) != 1 else function_rels[0]
    if lambda_function:
        resource_config[FUNCTION_NAME] = utils.get_resource_id(
            node=lambda_function.target.node,
            instance=lambda_function.target.instance,
            raise_on_missing=False)

    if STATEMENT_ID not in resource_config and iface.resource_id:
        resource_config.update({'StatementId': iface.resource_id})

    create_response = iface.create(resource_config)

    statement = create_response.get('Statement')
    # The actual value for key "statement" is not a python dict type,
    # so it is required to check if it is "unicode" and then convert it back
    # as python dict type

    if statement:
        if isinstance(statement, text_type):
            statement = json.loads(statement)

        resource_id = statement['Sid'] if statement.get('Sid') else None
        iface.update_resource_id(resource_id)
        utils.update_resource_id(ctx.instance, resource_id)
        utils.update_resource_arn(ctx.instance, resource_id)


@decorators.aws_resource(LambdaPermission, RESOURCE_TYPE,
                         ignore_properties=True)
def delete(ctx, iface, resource_config, **_):
    '''Deletes an AWS Lambda Permission'''
    # Build API params
    resource_config.update(dict(
        FunctionName=ctx.instance.runtime_properties[
            'resource_config'].get('FunctionName')))
    iface.delete(resource_config)


@decorators.aws_relationship(LambdaPermission, RESOURCE_TYPE)
def prepare_assoc(ctx, iface, resource_config, **_):
    '''Prepares to associate an Lambda Permission to something else'''
    assert iface is None or iface is not None  # qa
    assert resource_config is None or resource_config is not None  # qa
    _prepare_assoc(ctx.source, ctx.target)


def _prepare_assoc(ctx_source, ctx_target):
    if utils.is_node_type(ctx_target.node,
                          'cloudify.nodes.aws.lambda.Function'):
        ctx_source.instance.runtime_properties[
            'resource_config']['FunctionName'] = utils.get_resource_arn(
                node=ctx_target.node,
                instance=ctx_target.instance,
                raise_on_missing=True)


@decorators.aws_relationship(LambdaPermission, RESOURCE_TYPE)
def detach_from(ctx, iface, resource_config, **_):
    '''Detaches an Lambda Permission from something else'''
    pass

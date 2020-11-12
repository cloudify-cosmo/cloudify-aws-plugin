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
    Serverless.Function
    ~~~~~~~~~~~~~~~~~~~
    AWS Lambda Function interface
'''
import json

from os import remove as os_remove
from os.path import exists as path_exists
# Cloudify
from cloudify_aws.common import decorators, utils
from cloudify_aws.lambda_serverless import LambdaBase
# Boto
from botocore.exceptions import ClientError

RESOURCE_ID = 'FunctionName'
RESOURCE_TYPE = 'Lambda Function'
SUBNET_TYPE = 'cloudify.nodes.aws.ec2.Subnet'
SUBNET_TYPE_DEPRECATED = 'cloudify.aws.nodes.Subnet'
SECGROUP_TYPE = 'cloudify.nodes.aws.ec2.SecurityGroup'
SECGROUP_TYPE_DEPRECATED = 'cloudify.aws.nodes.SecurityGroup'


class LambdaFunction(LambdaBase):
    '''
        AWS Lambda Function interface
    '''
    def __init__(self, ctx_node, resource_id=None, client=None, logger=None):
        LambdaBase.__init__(self, ctx_node, resource_id, client, logger)
        self.type_name = RESOURCE_TYPE

    @property
    def properties(self):
        '''Gets the properties of an external resource'''
        resource = None
        try:
            resource = self.client.get_function(FunctionName=self.resource_id)
        except ClientError:
            pass
        if not resource or not resource.get('Configuration', dict()):
            return None
        return resource['Configuration']

    @property
    def status(self):
        '''Gets the status of an external resource'''
        if self.properties:
            return 'available'
        return None

    def create(self, params):
        '''
            Create a new AWS Lambda Function.
        '''
        return self.make_client_call('create_function', params)

    def delete(self, params=None):
        '''
            Deletes an existing AWS Lambda Function.
        '''
        params = params or dict()
        params.update(dict(FunctionName=self.resource_id))
        self.logger.debug('Deleting %s with parameters: %s'
                          % (self.type_name, params))
        self.client.delete_function(**params)

    def invoke(self, params):
        '''
            Invokes an AWS Lambda Function.
        '''
        invoke_params = dict()
        invoke_params.update(params)
        invoke_params.update(dict(FunctionName=self.resource_id))
        if invoke_params.get('Payload'):
            invoke_params['Payload'] = _encode_payload(
                invoke_params['Payload'])
        self.logger.debug('Invoking %s with parameters: %s'
                          % (self.type_name, invoke_params))
        res = self.client.invoke(**invoke_params)
        if res and res.get('Payload'):
            try:
                res['Payload'] = res['Payload'].read()
                res['Payload'] = json.loads(res['Payload'].decode('utf-8'))
                if res['Payload'].get('body'):
                    res['Payload']['body'] = json.loads(res['Payload']['body'])
            except json.JSONDecodeError:
              pass
        self.logger.debug('Response: %s' % res)
        return res

def _encode_payload(payload):
    if isinstance(payload, dict):
        payload = json.dumps(payload)
    if isinstance(payload, str):
        return payload.encode('utf-8')
    return payload

def _get_subnets_to_attach(ctx, vpc_config):
    # Attach a Subnet Group if it exists
    subnet_ids = vpc_config.get('SubnetIds', list())

    subnet_rels = \
        utils.find_rels_by_node_type(
            ctx.instance, SUBNET_TYPE) or \
        utils.find_rels_by_node_type(
            ctx.instance, SUBNET_TYPE)

    for rel in subnet_rels:
        subnet_ids.append(utils.get_resource_id(
            node=rel.target.node,
            instance=rel.target.instance,
            raise_on_missing=True))
    return subnet_ids


def _get_security_groups_to_attach(ctx, vpc_config):
    security_groups = vpc_config.get('SecurityGroupIds', list())

    sg_rels = \
        utils.find_rels_by_node_type(
            ctx.instance, SECGROUP_TYPE) or \
        utils.find_rels_by_node_type(
            ctx.instance, SECGROUP_TYPE_DEPRECATED)

    for rel in sg_rels:
        security_groups.append(
            utils.get_resource_id(
                node=rel.target.node,
                instance=rel.target.instance,
                raise_on_missing=True))
    return security_groups


def _get_iam_role_to_attach(ctx):
    role_arn = None
    iam_role = utils.find_rel_by_node_type(
        ctx.instance, 'cloudify.nodes.aws.iam.Role')
    if iam_role:
        role_arn = utils.get_resource_arn(
            node=iam_role.target.node,
            instance=iam_role.target.instance,
            raise_on_missing=True)
    return role_arn


@decorators.aws_resource(LambdaFunction, RESOURCE_TYPE)
def create(ctx, iface, resource_config, **_):
    '''Creates an AWS Lambda Function'''
    # Build API params
    params = utils.clean_params(
        dict() if not resource_config else resource_config.copy())
    if RESOURCE_ID not in params:
        params[RESOURCE_ID] = iface.resource_id
    vpc_config = params.get('VpcConfig', dict())

    # Attach a Subnet Group if it exists
    subnet_ids = _get_subnets_to_attach(ctx, vpc_config)
    if subnet_ids:
        vpc_config['SubnetIds'] = subnet_ids

    # Attach any security groups if they exist
    security_groups = _get_security_groups_to_attach(ctx, vpc_config)
    if security_groups:
        vpc_config['SecurityGroupIds'] = security_groups

    params['VpcConfig'] = vpc_config
    # Attach an IAM Role if it exists
    iam_role = _get_iam_role_to_attach(ctx)
    if iam_role:
        params['Role'] = iam_role

    # Handle user-profided code ZIP file
    if params.get('Code', dict()).get('ZipFile'):
        codezip = params['Code']['ZipFile']
        ctx.logger.debug('ZipFile: "%s" (%s)' % (codezip, type(codezip)))
        if not path_exists(codezip):
            codezip = ctx.download_resource(codezip)
            ctx.logger.debug('Downloaded resource: "%s"' % codezip)
            with open(codezip, mode='rb') as _file:
                params['Code']['ZipFile'] = _file.read()
            ctx.logger.debug('Deleting resource: "%s"' % codezip)
            os_remove(codezip)
        else:
            with open(codezip, mode='rb') as _file:
                params['Code']['ZipFile'] = _file.read()
    # Actually create the resource
    create_response = iface.create(params)
    resource_id = create_response['FunctionName']
    utils.update_resource_id(ctx.instance, resource_id)
    utils.update_resource_arn(
        ctx.instance, create_response['FunctionArn'])

    # Save vpc_config to be used later on when remove eni created by invoke
    # function
    if vpc_config and create_response.get('VpcConfig'):
        ctx.instance.runtime_properties['vpc_config'] =\
            create_response['VpcConfig']


@decorators.aws_resource(LambdaFunction, RESOURCE_TYPE,
                         ignore_properties=True)
@decorators.wait_for_delete()
def delete(iface, resource_config, **_):
    '''Deletes an AWS Lambda Function'''
    iface.delete(resource_config)

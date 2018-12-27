# #######
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
#    * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    * See the License for the specific language governing permissions and
#    * limitations under the License.
'''
    Serverless.Function
    ~~~~~~~~~~~~~~~~~~~
    AWS Lambda Function interface
'''
from os import remove as os_remove
from os.path import exists as path_exists
# Cloudify
from cloudify_aws.common import decorators, utils
from cloudify_aws.lambda_serverless import LambdaBase
# Boto
from botocore.exceptions import ClientError

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
        params = params or dict()
        params.update(dict(FunctionName=self.resource_id))
        self.logger.debug('Invoking %s with parameters: %s'
                          % (self.type_name, params))
        res = self.client.invoke(**params)
        if res and res.get('Payload'):
            res['Payload'] = res['Payload'].read()
        self.logger.debug('Response: %s' % res)
        return res


@decorators.aws_resource(LambdaFunction, RESOURCE_TYPE)
def create(ctx, iface, resource_config, **_):
    '''Creates an AWS Lambda Function'''
    # Build API params
    params = resource_config
    params.update(dict(FunctionName=iface.resource_id))
    vpc_config = params.get('VpcConfig', dict())
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
    vpc_config['SubnetIds'] = subnet_ids
    # Attach any security groups if they exist
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
    vpc_config['SecurityGroupIds'] = security_groups
    params['VpcConfig'] = vpc_config
    # Attach an IAM Role if it exists
    iam_role = utils.find_rel_by_node_type(
        ctx.instance, 'cloudify.nodes.aws.iam.Role')
    if iam_role:
        params['Role'] = utils.get_resource_arn(
            node=iam_role.target.node,
            instance=iam_role.target.instance,
            raise_on_missing=True)
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

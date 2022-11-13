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
    Serverless.Invoke
    ~~~~~~~~~~~~~~~~~
    AWS Lambda Function invocation interface
'''
# Cloudify
from cloudify_aws.common import decorators, utils
from cloudify_aws.lambda_serverless.resources.function import LambdaFunction
from cloudify_aws.ec2.resources import eni

RESOURCE_TYPE = 'Lambda Function Invocation'


@decorators.aws_resource(None, RESOURCE_TYPE)
def configure(ctx, resource_config, **_):
    '''Configures an AWS Lambda Invoke'''
    # Save the parameters
    ctx.instance.runtime_properties['resource_config'] = resource_config


@decorators.aws_relationship(None, RESOURCE_TYPE)
def attach_to(ctx, resource_config, **_):
    '''Attaches an Lambda Invoke to something else'''
    rtprops = ctx.source.instance.runtime_properties
    resource_encoding = \
        ctx.source.instance.runtime_properties.get('resource_encoding') or \
        ctx.source.node.properties.get('resource_encoding')
    if utils.is_node_type(ctx.target.node,
                          'cloudify.nodes.aws.lambda.Function'):
        lambda_fn = LambdaFunction(
            ctx.target.node, logger=ctx.logger,
            resource_encoding=resource_encoding,
            resource_id=utils.get_resource_id(
                node=ctx.target.node,
                instance=ctx.target.instance,
                raise_on_missing=True))
        result = lambda_fn.invoke(resource_config or rtprops.get(
            'resource_config'))
        ctx.source.instance.runtime_properties['output'] = result


@decorators.aws_relationship(None, RESOURCE_TYPE)
def detach_from(ctx, **_):
    '''Detaches an Lambda Invoke from something else'''
    props = ctx.target.instance.runtime_properties
    function_name = props.get('aws_resource_id')
    vpc_config = props.get('vpc_config')

    # Check to see if the invoked function is placed in vpc or not so that we
    # can remove the eni created by invoke method
    if vpc_config:
        eni_instance = eni.EC2NetworkInterface(
            ctx_node=ctx.target.node,
            logger=ctx.logger
        )

        eni_filter = [
            {
                'Name': 'vpc-id',
                'Values': [vpc_config['VpcId']]
            },
            {
                'Name': 'group-id',
                'Values': [
                    group_id for group_id in
                    vpc_config['SecurityGroupIds']
                ]
            },
            {
                'Name': 'description',
                'Values': ['AWS Lambda VPC ENI:*']
            },
            {
                'Name': 'requester-id',
                'Values': ['*:{0}*'.format(function_name)]
            }
        ]

        eni_interfaces = eni_instance.list_network_interfaces(eni_filter)
        if eni_interfaces:
            eni_interface = eni_interfaces[0]
            eni_id = eni_interface['NetworkInterfaceId']
            attachment = eni_interface.get('Attachment')
            if attachment:
                eni_attachment_id = attachment.get('AttachmentId')
                params = {
                    eni.ATTACHMENT_ID: eni_attachment_id
                }
                eni_instance.detach(params)

            params = dict()
            params[eni.NETWORKINTERFACE_ID] = eni_id
            eni_instance.delete(params)

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
    EC2.InternetGateway
    ~~~~~~~~~~~~~~
    AWS EC2 Internet interface
'''
from time import sleep


# Cloudify
from cloudify_aws.common import decorators, utils
from cloudify_aws.ec2 import EC2Base
from cloudify_aws.common.constants import (EXTERNAL_RESOURCE_ID,
                                           TAG_SPECIFICATIONS_KWARG)
from cloudify.exceptions import OperationRetry

RESOURCE_TYPE = 'EC2 Internet Gateway'
INTERNETGATEWAYS = 'InternetGateways'
INTERNETGATEWAY_ID = 'InternetGatewayId'
INTERNETGATEWAY_IDS = 'InternetGatewayIds'
VPC_ID = 'VpcId'
VPC_TYPE = 'cloudify.nodes.aws.ec2.Vpc'
VPC_TYPE_DEPRECATED = 'cloudify.aws.nodes.Vpc'


class EC2InternetGateway(EC2Base):
    '''
        EC2 Internet Gateway interface
    '''
    def __init__(self, ctx_node, resource_id=None, client=None, logger=None):
        EC2Base.__init__(self, ctx_node, resource_id, client, logger)
        self.type_name = RESOURCE_TYPE
        self._describe_call = 'describe_internet_gateways'
        self._type_key = INTERNETGATEWAYS
        self._ids_key = INTERNETGATEWAY_IDS
        self._id_key = INTERNETGATEWAY_ID

    @property
    def status(self):
        '''Gets the status of an external resource'''
        self.logger.error(
            'Improvements are needed to Internet Gateway status property.')
        try:
            return self.properties['Attachments'][0]['State']
        except (IndexError, KeyError, TypeError):
            return None

    @property
    def check_status(self):
        if self.status in ['available', 'attached']:
            return 'OK'
        return 'NOT OK'

    def create(self, params):
        '''
            Create a new AWS EC2 Internet Gateway.
        '''
        return self.make_client_call('create_internet_gateway', params)

    def delete(self, params=None):
        '''
            Deletes an existing AWS EC2 Internet Gateway.
        '''
        self.logger.debug('Deleting %s with parameters: %s'
                          % (self.type_name, params))
        res = self.client.delete_internet_gateway(**params)
        self.logger.debug('Response: %s' % res)
        return res

    def attach(self, params):
        '''
            Attach an AWS EC2 Internet Gateway to a VPC.
        '''
        self.logger.debug('Attaching %s with: %s'
                          % (self.type_name, params.get(VPC_ID, None)))
        res = self.client.attach_internet_gateway(**params)
        self.logger.debug('Response: %s' % res)
        return res

    def detach(self, params):
        '''
            Detach an AWS EC2 Internet Gateway from a VPC.
        '''
        self.logger.debug('Detaching %s from: %s'
                          % (self.type_name, params.get(VPC_ID, None)))
        res = self.client.detach_internet_gateway(**params)
        self.logger.debug('Response: %s' % res)
        return res


@decorators.aws_resource(EC2InternetGateway,
                         RESOURCE_TYPE,
                         waits_for_status=False)
def prepare(ctx, resource_config, **_):
    '''Prepares an AWS EC2 Internet Gateway'''
    # Save the parameters
    ctx.instance.runtime_properties['resource_config'] = resource_config


@decorators.aws_resource(EC2InternetGateway,
                         RESOURCE_TYPE,
                         waits_for_status=False)
@decorators.tag_resources
def create(ctx, iface, resource_config, **_):
    '''Creates an AWS EC2 Internet Gateway'''
    if iface.resource_id and not iface.properties:
        raise OperationRetry("Create did not succeed, trying again ")
    elif iface.resource_id:
        return
    create_response = iface.create(resource_config)['InternetGateway']
    ctx.instance.runtime_properties['create_response'] = \
        utils.JsonCleanuper(create_response).to_dict()
    utils.update_resource_id(ctx.instance,
                             create_response.get(INTERNETGATEWAY_ID))
    max_wait = 5
    counter = 0
    while not iface.properties:
        ctx.logger.debug('Waiting for Internet Gateway to be created.')
        sleep(5)
        if max_wait > counter:
            break
        counter += 1


@decorators.aws_resource(EC2InternetGateway,
                         RESOURCE_TYPE,
                         ignore_properties=True,
                         waits_for_status=False)
@decorators.untag_resources
def delete(iface, resource_config, dry_run=False, **_):
    '''Deletes an AWS EC2 Internet Gateway'''
    resource_config['DryRun'] = dry_run
    internet_gateway_id = resource_config.get(INTERNETGATEWAY_ID)
    if not internet_gateway_id:
        internet_gateway_id = iface.resource_id

    resource_config.update({INTERNETGATEWAY_ID: internet_gateway_id})
    iface.delete(resource_config)


@decorators.aws_resource(EC2InternetGateway,
                         RESOURCE_TYPE,
                         waits_for_status=False)
def attach(ctx, iface, resource_config, **_):
    '''Attach an AWS EC2 Internet Gateway to a VPC'''
    internet_gateway_id = resource_config.get(INTERNETGATEWAY_ID)
    if not internet_gateway_id:
        internet_gateway_id = \
            iface.resource_id or \
            ctx.instance.runtime_properties.get(EXTERNAL_RESOURCE_ID)

    resource_config.update({INTERNETGATEWAY_ID: internet_gateway_id})

    vpc_id = resource_config.get(VPC_ID)
    if not vpc_id:
        targ = \
            utils.find_rel_by_node_type(ctx.instance, VPC_TYPE) or \
            utils.find_rel_by_node_type(ctx.instance, VPC_TYPE_DEPRECATED)

        # Attempt to use the VPC ID from parameters.
        # Fallback to connected VPC.
        resource_config[VPC_ID] = \
            vpc_id or \
            targ.target.instance.runtime_properties.get(EXTERNAL_RESOURCE_ID)

    # Actually create the resource
    attach_params = resource_config.copy()
    attach_params.pop(TAG_SPECIFICATIONS_KWARG, None)
    # TODO: Handle conditionally if already attached.
    iface.attach(attach_params)


@decorators.aws_resource(EC2InternetGateway,
                         RESOURCE_TYPE,
                         ignore_properties=True,
                         waits_for_status=False)
def detach(ctx, iface, resource_config, **_):
    '''Detach an AWS EC2 Internet Gateway from a VPC'''
    internet_gateway_id = resource_config.get(INTERNETGATEWAY_ID)
    if not internet_gateway_id:
        internet_gateway_id = iface.resource_id
    if not internet_gateway_id:
        internet_gateway_id = utils.get_resource_id(ctx.node, ctx.instance)

    resource_config.update({INTERNETGATEWAY_ID: internet_gateway_id})

    vpc_id = resource_config.get(VPC_ID)
    if not vpc_id:
        targ = \
            utils.find_rel_by_node_type(ctx.instance, VPC_TYPE) or \
            utils.find_rel_by_node_type(ctx.instance, VPC_TYPE_DEPRECATED)

        # Attempt to use the VPC ID from parameters.
        # Fallback to connected VPC.
        resource_config[VPC_ID] = \
            vpc_id or \
            targ.target.instance.runtime_properties.get(EXTERNAL_RESOURCE_ID)

    return utils.exit_on_substring(iface,
                                   'detach',
                                   resource_config,
                                   ['Gateway.NotAttached',
                                    'InvalidInternetGatewayID.NotFound'])


interface = EC2InternetGateway

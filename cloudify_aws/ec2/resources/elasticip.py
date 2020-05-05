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
    EC2.ElasticIP
    ~~~~~~~~~~~~~~
    AWS EC2 ElasticIP interface
"""
# Boto
from botocore.exceptions import ClientError

from cloudify._compat import text_type

# Cloudify
from cloudify.exceptions import OperationRetry
from cloudify_aws.common import decorators, utils
from cloudify_aws.ec2 import EC2Base
from cloudify_aws.common.constants import EXTERNAL_RESOURCE_ID

RESOURCE_TYPE = 'EC2 Elastic IP'
ADDRESSES = 'Addresses'
ELASTICIP_ID = 'PublicIp'
ELASTICIP_IDS = 'PublicIps'
INSTANCE_ID = 'InstanceId'
INSTANCE_TYPE_DEPRECATED = 'cloudify.aws.nodes.Instance'
NETWORKINTERFACE_ID = 'NetworkInterfaceId'
NETWORKINTERFACE_TYPE = 'cloudify.nodes.aws.ec2.Interface'
NETWORKINTERFACE_TYPE_DEPRECATED = 'cloudify.aws.nodes.Interface'
ALLOCATION_ID = 'AllocationId'


class EC2ElasticIP(EC2Base):
    """
        EC2 EC2ElasticIP interface
    """
    def __init__(self, ctx_node, resource_id=None, client=None, logger=None):
        EC2Base.__init__(self, ctx_node, resource_id, client, logger)
        self.type_name = RESOURCE_TYPE

    @property
    def properties(self):
        """Gets the properties of an external resource"""
        params = {ELASTICIP_IDS: [self.resource_id]}
        try:
            resources = \
                self.client.describe_addresses(**params)
        except ClientError:
            pass
        else:
            return resources.get(ADDRESSES)[0] if resources else None

    def create(self, params):
        """
            Create a new AWS EC2 EC2ElasticIP.
        """
        return self.make_client_call('allocate_address', params)

    def delete(self, params=None):
        """
            Deletes an existing AWS EC2 ElasticIP.
        """
        self.logger.debug('Deleting %s with parameters: %s'
                          % (self.type_name, params))
        res = self.client.release_address(**params)
        self.logger.debug('Response: %s' % res)
        return res

    def attach(self, params):
        '''
            Attach an AWS EC2 ElasticIP to an Instance or a NetworkInterface.
        '''
        self.logger.debug('Attaching %s with: %s'
                          % (self.resource_id, params.get(INSTANCE_ID) or
                             params.get(NETWORKINTERFACE_ID)))
        res = self.client.associate_address(**params)
        self.logger.debug('Response: %s' % res)
        return res

    def detach(self, params):
        '''
            Detach an AWS EC2 ElasticIP from an Instance or a NetworkInterface.
        '''
        self.logger.debug('Detaching %s from: %s'
                          % (self.resource_id, params.get(INSTANCE_ID) or
                             params.get(NETWORKINTERFACE_ID)))
        res = self.client.disassociate_address(**params)
        self.logger.debug('Response: %s' % res)
        return res


@decorators.aws_resource(resource_type=RESOURCE_TYPE)
def prepare(ctx, resource_config, **_):
    """Prepares an AWS EC2 ElasticIP"""
    # Save the parameters
    ctx.instance.runtime_properties['resource_config'] = resource_config


@decorators.aws_resource(EC2ElasticIP, RESOURCE_TYPE)
def create(ctx, iface, resource_config, **_):
    """Creates an AWS EC2 ElasticIP"""

    # Create a copy of the resource config for clean manipulation.
    params = utils.clean_params(
        dict() if not resource_config else resource_config.copy())

    # Actually create the resource
    create_response = iface.create(params)
    ctx.instance.runtime_properties['create_response'] = \
        utils.JsonCleanuper(create_response).to_dict()
    elasticip_id = create_response.get(ELASTICIP_ID, '')
    iface.update_resource_id(elasticip_id)
    utils.update_resource_id(ctx.instance, elasticip_id)
    ctx.instance.runtime_properties['allocation_id'] = \
        create_response.get(ALLOCATION_ID)


@decorators.aws_resource(EC2ElasticIP, RESOURCE_TYPE,
                         ignore_properties=True)
def delete(ctx, iface, resource_config, **_):
    """Deletes an AWS EC2 ElasticIP"""

    # Create a copy of the resource config for clean manipulation.
    params = \
        dict() if not resource_config else resource_config.copy()

    allocation_id = params.get(ALLOCATION_ID)
    if not allocation_id:
        allocation_id = \
            ctx.instance.runtime_properties.get(
                'allocation_id')

    elasticip_id = params.get(ELASTICIP_ID)
    if not elasticip_id:
        elasticip_id = iface.resource_id

    if allocation_id:
        params[ALLOCATION_ID] = allocation_id
        try:
            del params[ELASTICIP_ID]
        except KeyError:
            pass
    elif elasticip_id:
        params[ELASTICIP_ID] = elasticip_id
        try:
            del params[ALLOCATION_ID]
        except KeyError:
            pass

    try:
        iface.delete(params)
    except ClientError as e:
        if 'AuthFailure' is text_type(e):
            raise OperationRetry('Address has not released yet.')
        else:
            pass


@decorators.aws_resource(EC2ElasticIP, RESOURCE_TYPE)
def attach(ctx, iface, resource_config, **_):
    '''Attaches an AWS EC2 ElasticIP to an Instance or a NetworkInterface'''
    params = dict() if not resource_config else resource_config.copy()

    allocation_id = params.get(ALLOCATION_ID)
    elasticip_id = params.get(ELASTICIP_ID)

    if not allocation_id:
        allocation_id = \
            ctx.instance.runtime_properties.get(
                'allocation_id', iface.properties.get('AllocationId'))
        params[ALLOCATION_ID] = allocation_id

    if not elasticip_id and not allocation_id:
        params[ELASTICIP_ID] = \
            iface.resource_id

    instance_id = params.get(INSTANCE_ID)
    eni_id = params.get(NETWORKINTERFACE_ID)

    if not instance_id and not eni_id:
        resource = \
            utils.find_rel_by_node_type(
                ctx.instance,
                INSTANCE_TYPE_DEPRECATED)

        if resource:
            params[INSTANCE_ID] = \
                resource.\
                target.instance.runtime_properties.get(EXTERNAL_RESOURCE_ID)
        else:
            resource = \
                utils.find_rel_by_node_type(
                    ctx.instance,
                    NETWORKINTERFACE_TYPE) or \
                utils.find_rel_by_node_type(
                    ctx.instance,
                    NETWORKINTERFACE_TYPE_DEPRECATED)

            if resource:
                params[NETWORKINTERFACE_ID] = \
                    eni_id or \
                    resource.target.instance.runtime_properties\
                    .get(EXTERNAL_RESOURCE_ID)
            else:
                return

    # Make sure that Domain is not sent to attach call.
    try:
        del params['Domain']
    except KeyError:
        pass

    # Actually attach the resources
    association_id = iface.attach(params)
    ctx.instance.runtime_properties['association_id'] = \
        association_id.get('AssociationId')


@decorators.aws_resource(EC2ElasticIP, RESOURCE_TYPE,
                         ignore_properties=True)
def detach(ctx, iface, resource_config, **_):
    '''Detach an AWS EC2 Elasticip from an Instance or NetworkInterface'''
    params = dict() if not resource_config else resource_config.copy()

    association_id = \
        params.get('AssociationId') or \
        ctx.instance.runtime_properties.get('association_id')
    elasticip_id = params.get(ELASTICIP_ID)

    if not elasticip_id:
        elasticip_id = iface.resource_id
        params[ELASTICIP_ID] = elasticip_id

    if not association_id:
        return

    if association_id and elasticip_id:
        del params[ELASTICIP_ID]

    params['AssociationId'] = association_id

    iface.detach(params)

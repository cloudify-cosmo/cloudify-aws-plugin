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
from botocore.exceptions import ClientError, ParamValidationError

from cloudify.exceptions import OperationRetry

# Cloudify
from cloudify_aws.common._compat import text_type
from cloudify_aws.common import decorators, utils
from cloudify_aws.ec2 import EC2Base
from cloudify_aws.common.constants import (
    EXTERNAL_RESOURCE_ID,
    TAG_SPECIFICATIONS_KWARG
)

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
        self.allocation_id = None
        self._describe_call = 'describe_addresses'
        self._type_key = ADDRESSES
        self._ids_key = ELASTICIP_IDS
        self._id_key = ELASTICIP_ID

    def get(self, params=None):
        try:
            if params:
                resources = self.client.describe_addresses(**params)
            else:
                resources = self.client.describe_addresses()
        except (ParamValidationError, ClientError):
            return {}
        return resources.get(ADDRESSES, {})

    def update_allocation_id(self, allocation_id):
        self.allocation_id = allocation_id

    def tag(self, params):
        params['Resources'] = [self.allocation_id]
        super(EC2ElasticIP, self).tag(params)

    @property
    def properties(self):
        """Gets the properties of an external resource"""
        if not self.resource_id:
            return {}
        params = {ELASTICIP_IDS: [self.resource_id]}
        if not self._properties:
            self._properties = self.get(params)
        return self._properties[0] if self._properties else {}

    @property
    def status(self):
        '''Gets the status of an external resource'''
        props = self.properties
        if not props:
            return None
        return bool(props.get('AssociationId', False))

    @property
    def check_status(self):
        if self.status:
            return 'OK'
        return 'NOT OK'

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


def get_already_allocated_ip(address_list):
    for create_response in address_list:
        if not create_response.get('AssociationId'):
            return create_response


@decorators.aws_resource(EC2ElasticIP, resource_type=RESOURCE_TYPE)
def prepare(ctx, resource_config, **_):
    """Prepares an AWS EC2 ElasticIP"""
    # Save the parameters
    ctx.instance.runtime_properties['resource_config'] = resource_config


@decorators.aws_resource(EC2ElasticIP, RESOURCE_TYPE)
@decorators.tag_resources
def create(ctx, iface, resource_config, **_):
    """Creates an AWS EC2 ElasticIP"""

    # Actually create the resource
    create_response = None
    if ctx.node.properties.get('use_unassociated_addresses', False):
        create_response = get_already_allocated_ip(iface.get())
    if not create_response:
        create_response = iface.create(resource_config)
    else:
        ctx.instance.runtime_properties['unassociated_address'] = \
            create_response.get(ELASTICIP_ID)
    ctx.instance.runtime_properties['create_response'] = \
        utils.JsonCleanuper(create_response).to_dict()
    elasticip_id = create_response.get(ELASTICIP_ID, '')
    iface.update_resource_id(elasticip_id)
    utils.update_resource_id(ctx.instance, elasticip_id)
    allocation_id = create_response.get(ALLOCATION_ID)
    iface.update_allocation_id(allocation_id)
    ctx.instance.runtime_properties['allocation_id'] = allocation_id


@decorators.aws_resource(EC2ElasticIP, RESOURCE_TYPE,
                         ignore_properties=True)
def delete(ctx, iface, resource_config, **_):
    """Deletes an AWS EC2 ElasticIP"""

    allocation_id = resource_config.get(ALLOCATION_ID)
    if not allocation_id:
        allocation_id = \
            ctx.instance.runtime_properties.get(
                'allocation_id')

    elasticip_id = resource_config.get(ELASTICIP_ID)
    if not elasticip_id:
        elasticip_id = iface.resource_id

    if allocation_id:
        resource_config[ALLOCATION_ID] = allocation_id
        try:
            del resource_config[ELASTICIP_ID]
        except KeyError:
            pass
    elif elasticip_id:
        resource_config[ELASTICIP_ID] = elasticip_id
        try:
            del resource_config[ALLOCATION_ID]
        except KeyError:
            pass

    if ctx.node.properties.get('use_unassociated_addresses', False):
        address = ctx.instance.runtime_properties.pop(
            'unassociated_address', None)
        if address:
            ctx.logger.info('Not deleting address {address}'.format(
                address=address))
            return

    try:
        iface.delete(resource_config)
    except ClientError as e:
        if 'AuthFailure' is text_type(e):
            raise OperationRetry('Address has not released yet.')
        else:
            pass


@decorators.aws_resource(EC2ElasticIP, RESOURCE_TYPE)
def attach(ctx, iface, resource_config, **_):
    '''Attaches an AWS EC2 ElasticIP to an Instance or a NetworkInterface'''
    allocation_id = resource_config.get(ALLOCATION_ID)
    elasticip_id = resource_config.get(ELASTICIP_ID)

    if not allocation_id:
        allocation_id = \
            ctx.instance.runtime_properties.get(
                'allocation_id', iface.properties.get('AllocationId'))
        resource_config[ALLOCATION_ID] = allocation_id

    if not elasticip_id and not allocation_id:
        resource_config[ELASTICIP_ID] = \
            iface.resource_id

    instance_id = resource_config.get(INSTANCE_ID)
    eni_id = resource_config.get(NETWORKINTERFACE_ID)

    if not instance_id and not eni_id:
        resource = \
            utils.find_rel_by_node_type(
                ctx.instance,
                INSTANCE_TYPE_DEPRECATED)

        if resource:
            resource_config[INSTANCE_ID] = \
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
                resource_config[NETWORKINTERFACE_ID] = \
                    eni_id or \
                    resource.target.instance.runtime_properties\
                    .get(EXTERNAL_RESOURCE_ID)
            else:
                return

    # Make sure that Domain and TagSpecifications are not sent to attach call.
    for arg_name in ['Domain', TAG_SPECIFICATIONS_KWARG]:
        resource_config.pop(arg_name, None)

    skip_attach = ctx.node.properties.get('use_external_resource', False) and \
        not ctx.node.properties.get('attach_existing_address', False)

    if skip_attach:
        return
    # Actually attach the resources
    association_id = iface.attach(resource_config)
    ctx.instance.runtime_properties['association_id'] = \
        association_id.get('AssociationId')


@decorators.aws_resource(EC2ElasticIP, RESOURCE_TYPE,
                         ignore_properties=True)
def detach(ctx, iface, resource_config, **_):
    '''Detach an AWS EC2 Elasticip from an Instance or NetworkInterface'''

    association_id = \
        resource_config.get('AssociationId') or \
        ctx.instance.runtime_properties.get('association_id')
    elasticip_id = resource_config.get(ELASTICIP_ID)

    if not elasticip_id:
        elasticip_id = iface.resource_id
        resource_config[ELASTICIP_ID] = elasticip_id

    if not association_id:
        return

    if association_id and elasticip_id:
        del resource_config[ELASTICIP_ID]

    resource_config['AssociationId'] = association_id
    resource_config.pop(TAG_SPECIFICATIONS_KWARG, None)

    skip_attach = ctx.node.properties.get('use_external_resource', False) and \
        not ctx.node.properties.get('attach_existing_address', False)

    if skip_attach:
        return
    iface.detach(resource_config)


interface = EC2ElasticIP

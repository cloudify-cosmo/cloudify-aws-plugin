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
    EC2.TransitGateway
    ~~~~~~~~~~~~~~
    AWS EC2 Transit Gateway interface
'''

# Third Party imports
from botocore.exceptions import ClientError
from cloudify.exceptions import NonRecoverableError, OperationRetry

# Local imports
from cloudify_aws.ec2 import EC2Base
from cloudify_aws.common import constants, decorators, utils

RESOURCE_TYPE = 'EC2 Transit Gateway'
TRANSIT_GATEWAY = 'TransitGateway'
TRANSIT_GATEWAYS = 'TransitGateways'
TRANSIT_GATEWAY_ID = 'TransitGatewayId'
TRANSIT_GATEWAY_IDS = 'TransitGatewayIds'

TRANSIT_GATEWAY_ATTACHMENT = 'TransitGatewayVpcAttachment'
TRANSIT_GATEWAY_ATTACHMENTS = 'TransitGatewayVpcAttachments'
TRANSIT_GATEWAY_ATTACHMENT_ID = 'TransitGatewayAttachmentId'
TRANSIT_GATEWAY_ATTACHMENT_IDS = 'TransitGatewayAttachmentIds'

PENDING = ['initiatingRequest', 'pending', 'modifying']
AVAILABLE = ['available', 'pendingAcceptance']
UNAVAILABLE = ['deleted',
               'deleting',
               'rollingBack',
               'rejected',
               'rejecting']
FAILED = ['failed', 'failing']


class EC2TransitGateway(EC2Base):
    '''
        EC2 Transit Gateway
    '''
    def __init__(self, ctx_node, resource_id=None, client=None, logger=None):
        EC2Base.__init__(self, ctx_node, resource_id, client, logger)
        self.type_name = RESOURCE_TYPE

    @property
    def properties(self):
        '''Gets the properties of an external resource'''
        params = {TRANSIT_GATEWAY_IDS: [self.resource_id]}
        try:
            resources = \
                self.client.describe_transit_gateways(**params)
        except ClientError:
            pass
        else:
            return None if not resources else resources.get(
                TRANSIT_GATEWAYS, [None])[0]
        return None

    @property
    def status(self):
        '''Gets the status of an external resource'''
        props = self.properties
        if not props:
            return None
        return props['State']

    def create(self, params):
        '''
            Create a new AWS EC2 Transit Gateway.
        '''
        return self.make_client_call('create_transit_gateway', params)

    def delete(self, params=None):
        '''
            Deletes an existing AWS EC2 Transit Gateway.
        '''
        self.logger.debug('Deleting %s with parameters: %s'
                          % (self.type_name, params))
        res = self.client.delete_transit_gateway(**params)
        self.logger.debug('Response: %s' % res)
        return res


class EC2TransitGatewayAttachment(EC2Base):

    '''
        EC2 Transit Gateway Attachment
    '''

    def __init__(self, ctx_node, resource_id=None, client=None, logger=None):
        EC2Base.__init__(self, ctx_node, resource_id, client, logger)
        self.type_name = RESOURCE_TYPE

    @property
    def properties(self):
        '''Gets the properties of an external resource'''
        params = {TRANSIT_GATEWAY_ATTACHMENT_IDS: [self.resource_id]}
        try:
            resources = \
                self.client.describe_transit_gateway_vpc_attachments(**params)
        except ClientError:
            pass
        else:
            return None if not resources else resources.get(
                TRANSIT_GATEWAY_ATTACHMENTS, [None])[0]
        return None

    @property
    def status(self):
        '''Gets the status of an external resource'''
        props = self.properties
        if not props:
            return None
        return props['State']

    def create(self, params):
        '''
            Create a new AWS EC2 Transit Gateway Attachment.
        '''
        return self.make_client_call(
            'create_transit_gateway_vpc_attachment', params)

    def accept(self, params):
        '''
            Create a new AWS EC2 Transit Gateway Attachment.
        '''
        return self.make_client_call(
            'accept_transit_gateway_vpc_attachment', params)

    def delete(self, params=None):
        '''
            Deletes an existing AWS EC2 Transit Gateway Attachment.
        '''
        return self.make_client_call(
            'delete_transit_gateway_vpc_attachment', params)


@decorators.aws_resource(EC2TransitGateway, resource_type=RESOURCE_TYPE)
def prepare(ctx, iface, resource_config, **_):
    '''Prepares an AWS EC2 Transit Gateway'''
    # Save the parameters
    ctx.instance.runtime_properties['resource_config'] = resource_config


@decorators.aws_resource(EC2TransitGateway, RESOURCE_TYPE)
@decorators.wait_for_status(status_good=['available'],
                            status_pending=['pending'])
@decorators.tag_resources
def create(ctx, iface, resource_config, **_):
    '''Creates an AWS EC2 Transit Gateway'''
    params = utils.clean_params(
        dict() if not resource_config else resource_config.copy())

    # Actually create the resource
    create_response = iface.create(params)[TRANSIT_GATEWAY]
    ctx.instance.runtime_properties['create_response'] = \
        utils.JsonCleanuper(create_response).to_dict()

    transit_gateway_id = create_response.get(TRANSIT_GATEWAY_ID, '')
    iface.update_resource_id(transit_gateway_id)
    utils.update_resource_id(ctx.instance, transit_gateway_id)


@decorators.aws_resource(EC2TransitGateway, RESOURCE_TYPE,
                         ignore_properties=True)
@decorators.untag_resources
def delete(iface, resource_config, **_):
    '''Deletes an AWS EC2 Transit Gateway'''

    params = dict() if not resource_config else resource_config.copy()

    if TRANSIT_GATEWAY_ID not in params:
        params.update({TRANSIT_GATEWAY_ID: iface.resource_id})

    iface.delete(params)


@decorators.aws_relationship(EC2TransitGatewayAttachment, RESOURCE_TYPE)
def request_vpc_attachment(ctx,
                           iface,
                           transit_gateway_id=None,
                           vpc_id=None,
                           **_):

    transit_gateway_id = \
        transit_gateway_id or ctx.source.instance.runtime_properties.get(
            constants.EXTERNAL_RESOURCE_ID)
    vpc_id = vpc_id or ctx.target.instance.runtime_properties.get(
        constants.EXTERNAL_RESOURCE_ID)

    if not transit_gateway_id or not vpc_id:
        raise NonRecoverableError(
            'The "cloudify.relationships.aws.ec2.'
            'attach_transit_gateway_to_vpc" relationship operation did not '
            'receive a value for transit_gateway_id '
            '({tgi}) or for vpc_id ({vi}).'.format(
                tgi=transit_gateway_id, vi=vpc_id))

    if TRANSIT_GATEWAY_ATTACHMENTS in ctx.source.instance.runtime_properties:
        if vpc_id in ctx.source.instance.runtime_properties[
                TRANSIT_GATEWAY_ATTACHMENTS]:
            transit_gateway_attachment_id = get_attachment_id(
                ctx.source.instance.runtime_properties)
            iface = EC2TransitGatewayAttachment(
                ctx.source.node,
                transit_gateway_attachment_id,
                iface.client,
                ctx.logger)
            if iface.status in PENDING:
                raise OperationRetry(
                    'The {r} creation request '
                    'has been received and is processing. State: {s}.'.format(
                        r=TRANSIT_GATEWAY_ATTACHMENT, s=iface.status))
            elif iface.status in UNAVAILABLE + FAILED:
                raise NonRecoverableError(
                    'The {r} creation request '
                    'results in a fatal error: {s}'.format(
                        r=TRANSIT_GATEWAY_ATTACHMENT,
                        s=iface.status))
            else:
                return
    else:
        ctx.source.instance.runtime_properties[
            TRANSIT_GATEWAY_ATTACHMENTS] = {}

    request = {
        TRANSIT_GATEWAY_ID: transit_gateway_id,
        'VpcId': vpc_id
    }

    response = iface.create(request)
    ctx.logger.info('Sent the {r} creation request.'.format(
        r=TRANSIT_GATEWAY_ATTACHMENT))
    ctx.source.instance.runtime_properties[
        TRANSIT_GATEWAY_ATTACHMENTS][vpc_id] = response


@decorators.aws_relationship(EC2TransitGatewayAttachment, RESOURCE_TYPE)
def accept_vpc_attachment(ctx, iface, transit_gateway_attachment_id=None, **_):
    transit_gateway_attachment_id = \
        transit_gateway_attachment_id or \
        get_attachment_id(ctx.source.instance.runtime_properties)
    if not transit_gateway_attachment_id:
        raise OperationRetry('Waiting for {r} creation request.'.format(
            r=TRANSIT_GATEWAY_ATTACHMENT))
    iface = EC2TransitGatewayAttachment(
        ctx.source.node,
        transit_gateway_attachment_id,
        iface.client,
        ctx.logger)
    request = {
        TRANSIT_GATEWAY_ATTACHMENT_ID: transit_gateway_attachment_id
    }
    iface.accept(request)
    raise OperationRetry('Sent the {r} acceptance request.'.format(
        r=TRANSIT_GATEWAY_ATTACHMENT))


@decorators.aws_relationship(EC2TransitGatewayAttachment, RESOURCE_TYPE)
def delete_vpc_attachment(ctx, iface, transit_gateway_attachment_id=None, **_):
    transit_gateway_attachment_id = \
        transit_gateway_attachment_id or \
        get_attachment_id(ctx.source.instance.runtime_properties)
    iface = EC2TransitGatewayAttachment(
        ctx.source.node,
        transit_gateway_attachment_id,
        iface.client,
        ctx.logger)
    request = {
        TRANSIT_GATEWAY_ATTACHMENT_ID: transit_gateway_attachment_id
    }
    if iface.status == 'deleting':
        raise OperationRetry(
            'The {r} deletion request has been received and is processing. '
            'State: {s}.'.format(r=TRANSIT_GATEWAY_ATTACHMENT, s=iface.state))
    elif iface.status in UNAVAILABLE:
        ctx.logger.info('The {r} has been deleted.'.format(
            r=TRANSIT_GATEWAY_ATTACHMENT))
        return
    iface.delete(request)
    raise OperationRetry(
        'Sent the {r} deletion request.'.format(r=TRANSIT_GATEWAY_ATTACHMENT))


def get_attachment_id(props):
    attachment = props.get(TRANSIT_GATEWAY_ATTACHMENT, {})
    return attachment.get(TRANSIT_GATEWAY_ATTACHMENT_ID)

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
    EC2.NetworkInterface
    ~~~~~~~~~~~~~~
    AWS EC2 NetworkInterface interface
"""

from cloudify import ctx as _ctx
from cloudify.exceptions import OperationRetry

# Cloudify
from cloudify_aws.ec2 import EC2Base
from cloudify_aws.common import decorators, utils
from cloudify_aws.common.constants import EXTERNAL_RESOURCE_ID

RESOURCE_TYPE = 'EC2 Network Interface'
NETWORKINTERFACES = 'NetworkInterfaces'
NETWORKINTERFACE_ID = 'NetworkInterfaceId'
NETWORKINTERFACE_IDS = 'NetworkInterfaceIds'
INSTANCE_ID = 'InstanceId'
INSTANCE_TYPE_DEPRECATED = 'cloudify.aws.nodes.Instance'
SUBNET_ID = 'SubnetId'
SUBNET_TYPE = 'cloudify.nodes.aws.ec2.Subnet'
SUBNET_TYPE_DEPRECATED = 'cloudify.aws.nodes.Subnet'
SEC_GROUP_TYPE = 'cloudify.nodes.aws.ec2.SecurityGroup'
SEC_GROUPS = 'Groups'
ATTACHMENT_ID = 'AttachmentId'


class EC2NetworkInterface(EC2Base):
    """
        EC2 NetworkInterface interface
    """
    def __init__(self, ctx_node, resource_id=None, client=None, logger=None):
        EC2Base.__init__(self, ctx_node, resource_id, client, logger)
        self.type_name = RESOURCE_TYPE
        self._describe_call = 'describe_network_interfaces'
        self._ids_key = NETWORKINTERFACE_IDS
        self._type_key = NETWORKINTERFACES
        self._id_key = NETWORKINTERFACE_ID

    @property
    def status(self):
        '''Gets the status of an external resource'''
        return self.properties.get('Status')

    @property
    def check_status(self):
        if self.status in ['available', 'associated', 'in-use']:
            return 'OK'
        return 'NOT OK'

    @property
    def attachment(self):
        props = self.properties
        if not props:
            return {}
        try:
            return props['Attachment']
        except KeyError:
            return {}

    def list_network_interfaces(self, filters=None):
        params = dict()
        if filters:
            params['Filters'] = filters

        resources = self.client.describe_network_interfaces(**params)
        return resources.get(NETWORKINTERFACES) if resources else []

    def create(self, params):
        """
            Create a new AWS EC2 NetworkInterface.
        """
        self.create_response = self.make_client_call(
            'create_network_interface', params)
        self.update_resource_id(
            self.create_response['NetworkInterface'].get(
                NETWORKINTERFACE_ID, ''))

    def delete(self, params=None):
        """
            Deletes an existing AWS EC2 NetworkInterface.
        """
        self.logger.debug('Deleting %s with parameters: %s'
                          % (self.type_name, params))
        res = self.client.delete_network_interface(**params)
        self.logger.debug('Response: %s' % res)
        return res

    def attach(self, params):
        '''
            Attach an AWS EC2 NetworkInterface to a Subnet.
        '''
        self.logger.debug('Attaching %s with: %s'
                          % (self.type_name, params.get(SUBNET_ID, None)))
        res = self.client.attach_network_interface(**params)
        self.logger.debug('Response: %s' % res)
        return res

    def detach(self, params):
        '''
            Detach an AWS EC2 NetworkInterface from a Subnet.
        '''
        self.logger.debug('Detaching %s from: %s'
                          % (self.type_name, params.get(SUBNET_ID, None)))
        self.logger.debug('Attaching default %s'
                          % (self.type_name))
        res = self.client.detach_network_interface(**params)
        self.logger.debug('Response: %s' % res)
        return res

    def modify_network_interface_attribute(self, params):
        '''
            Modify an AWS EC2 NetworkInterface attribute.
        '''
        self.logger.debug('Modifying %s with: %s'
                          % (self.type_name, params))
        res = self.client.modify_network_interface_attribute(**params)
        self.logger.debug('Response: %s' % res)
        return res


@decorators.aws_resource(EC2NetworkInterface, resource_type=RESOURCE_TYPE)
def prepare(ctx, resource_config, **_):
    """Prepares an AWS EC2 NetworkInterface"""
    # Save the parameters
    ctx.instance.runtime_properties['resource_config'] = resource_config


@decorators.aws_resource(EC2NetworkInterface, RESOURCE_TYPE)
@decorators.wait_for_status(status_good=['available'])
@decorators.tag_resources
def create(ctx, iface, resource_config, **_):
    """Creates an AWS EC2 NetworkInterface"""

    # Create a copy of the resource config for clean manipulation.
    resource_config = _create_eni_params(resource_config, ctx.instance)
    _create(iface, resource_config, ctx.instance)
    _modify_attribute(iface, _.get('modify_network_interface_attribute_args'))


@decorators.aws_resource(EC2NetworkInterface, RESOURCE_TYPE,
                         ignore_properties=True)
@decorators.untag_resources
def delete(ctx, iface, resource_config, dry_run=False, **_):
    """Deletes an AWS EC2 NetworkInterface"""

    resource_config['DryRun'] = dry_run
    # Create a copy of the resource config for clean manipulation.
    eni_id = resource_config.get(NETWORKINTERFACE_ID)

    if not eni_id:
        resource_config[NETWORKINTERFACE_ID] = \
            iface.resource_id or \
            ctx.instance.runtime_properties.get(EXTERNAL_RESOURCE_ID)

    iface.delete(resource_config)


@decorators.aws_resource(EC2NetworkInterface, RESOURCE_TYPE)
def attach(ctx, iface, resource_config, **_):
    '''Attaches an AWS EC2 NetworkInterface to a Subnet'''
    eni_id = resource_config.get(NETWORKINTERFACE_ID)
    if not eni_id:
        eni_id = iface.resource_id

    device_index = resource_config.get(
        'DeviceIndex') or ctx.instance.runtime_properties.get(
        'device_index', 1)
    ctx.instance.runtime_properties['device_index'] = device_index

    resource_config.update({NETWORKINTERFACE_ID: eni_id})
    resource_config.update({'DeviceIndex': device_index})
    instance_id = get_attached_instance_id(resource_config)
    if not instance_id:
        return
    resource_config[INSTANCE_ID] = instance_id
    if SUBNET_ID in resource_config:
        del resource_config[SUBNET_ID]

    # Actually attach the resources
    eni_attachment_id = iface.attach(resource_config)
    ctx.instance.runtime_properties['attachment_id'] = \
        eni_attachment_id[ATTACHMENT_ID]


@decorators.aws_resource(EC2NetworkInterface, RESOURCE_TYPE,
                         ignore_properties=True)
def detach(ctx, iface, resource_config, **_):
    '''Detach an AWS EC2 NetworkInterface from a Subnet'''
    attachment_id = ctx.instance.runtime_properties.get('attachment_id', None)
    if not attachment_id:
        try:
            attachment_id = iface.attachment['AttachmentId']
        except (TypeError, KeyError):
            ctx.logger.warn(
                'Detach operation requires an attachment ID. '
                'No attachment_id runtime property was found and the '
                'AWS API did not return an attachment for {i}.'.format(
                    i=iface.resource_id))
            return

    resource_config.update({ATTACHMENT_ID: attachment_id})
    if iface.attachment['Status'] == 'detached':
        return
    iface.detach(resource_config)
    raise OperationRetry(
        'Waiting for {i} attachment to be detached.'.format(
            i=iface.resource_id))


@decorators.aws_resource(EC2NetworkInterface, RESOURCE_TYPE)
def modify_network_interface_attribute(ctx, iface, resource_config, **_):
    eni_id = \
        ctx.instance.runtime_properties.get(
            NETWORKINTERFACE_ID, iface.resource_id)
    resource_config[NETWORKINTERFACE_ID] = eni_id
    iface.modify_network_interface_attribute(resource_config)


def get_attached_instance_id(params):
    # Maybe the user passed an instance ID.
    instance_id = params.get(INSTANCE_ID)
    if not instance_id:
        targ = \
            utils.find_rel_by_node_type(_ctx.instance,
                                        INSTANCE_TYPE_DEPRECATED)
        if targ:
            return targ.target.instance.runtime_properties.get(
                EXTERNAL_RESOURCE_ID)

    # Maybe the we have a started EC2 Instance
    instances = utils.get_node_instances_by_type_related_to_node_name(
        _ctx.node.id,
        'cloudify.nodes.aws.ec2.Instances',
        _ctx.deployment.id
    )

    if len(instances) == 1:
        if instances[0]['node_instance'].state == 'started':
            instance_id = instances[0]['node_instance'].runtime_properties.get(
                EXTERNAL_RESOURCE_ID)
        elif instances[0]['node'].properties['use_external_resource']:
            instance_id = instances[0]['node'].properties.get('resource_id')
        if instance_id:
            _ctx.logger.info(
                'A single EC2 Instance node instance '
                'is connected to the nic and is in started state. '
                'Attaching instance_id {instance} to ENI.'.format(
                    instance=instance_id)
            )
            return instance_id

    _ctx.logger.error('No instance ID provided in resource config, '
                      'no relationship to EC2 instance provided, '
                      'and no single existing EC2 Instance has a relationship '
                      'to the current ENI node. '
                      'Not performing attach operation.')


@decorators.aws_resource(class_decl=EC2NetworkInterface,
                         resource_type=RESOURCE_TYPE,
                         waits_for_status=False)
def check_drift(ctx, iface=None, **_):
    return utils.check_drift(RESOURCE_TYPE, iface, ctx.logger)


def _create_eni_params(params, ctx_instance):
    subnet_id = params.get(SUBNET_ID)
    if not subnet_id:
        targ = \
            utils.find_rel_by_node_type(ctx_instance, SUBNET_TYPE) or \
            utils.find_rel_by_node_type(ctx_instance, SUBNET_TYPE_DEPRECATED)

        # Attempt to use the VPC ID from parameters.
        # Fallback to connected VPC.
        params[SUBNET_ID] = \
            subnet_id or \
            targ.target.instance.runtime_properties.get(EXTERNAL_RESOURCE_ID)

    groups = params.get(SEC_GROUPS, [])
    for targ in utils.find_rels_by_node_type(ctx_instance, SEC_GROUP_TYPE):
        group_id = \
            targ.target.instance.runtime_properties.get(
                EXTERNAL_RESOURCE_ID)
        if group_id and group_id not in groups:
            groups.append(group_id)
    params[SEC_GROUPS] = groups
    return params


def _create(iface, params, ctx_instance):
    iface.create(params)
    utils.update_resource_id(ctx_instance, iface.resource_id)
    ctx_instance.runtime_properties['device_index'] = \
        iface.create_response['NetworkInterface'].get(
            'Attachment', {}).get(
            'DeviceIndex',
            ctx_instance.runtime_properties.get('device_index'))


def _modify_attribute(iface,  modify_network_interface_attribute_args):
    if modify_network_interface_attribute_args:
        modify_network_interface_attribute_args[NETWORKINTERFACE_ID] = \
            iface.resource_id
        iface.modify_network_interface_attribute(
            modify_network_interface_attribute_args)


@decorators.aws_resource(EC2NetworkInterface, RESOURCE_TYPE)
def poststart(ctx, iface, *_, **__):
    '''Stores AWS EC2 Instances Details'''
    utils.update_expected_configuration(iface, ctx.instance.runtime_properties)


interface = EC2NetworkInterface

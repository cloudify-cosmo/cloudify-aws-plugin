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
    EC2.Instances
    ~~~~~~~~~~~~~~~
    AWS EC2 Instances interface
'''

# Standard Imports
import os
import json
from base64 import b64encode
from collections import defaultdict

# Third Party imports
from Crypto.PublicKey import RSA

# Cloudify
from cloudify import ctx
from cloudify import compute
from cloudify.exceptions import NonRecoverableError, OperationRetry

# local imports
from cloudify_aws.ec2 import EC2Base
from cloudify_aws.common._compat import text_type
from cloudify_aws.common import decorators, utils
from cloudify_aws.ec2.decrypt import decrypt_password
from cloudify_aws.common.constants import (
    EXTERNAL_RESOURCE_ID,
    EXTERNAL_RESOURCE_ID_MULTIPLE as MULTI_ID)

PENDING = 0
RUNNING = 16
STOPPED = 80
STOPPING = 64
TERMINATED = 48
SHUTTING_DOWN = 32
USERDATA = 'UserData'
SUBNET_ID = 'SubnetId'
INSTANCES = 'Instances'
PS_OPEN = '<powershell>'
PS_CLOSE = '</powershell>'
TAGS = 'TagSpecifications'
INSTANCE_ID = 'InstanceId'
INSTANCE_IDS = 'InstanceIds'
DEVICE_INDEX = 'DeviceIndex'
NIC_ID = 'NetworkInterfaceId'
RESERVATIONS = 'Reservations'
GROUPIDS = 'SecurityGroupIds'
RESOURCE_TYPE = 'EC2 Instances'
NETWORK_INTERFACES = 'NetworkInterfaces'
KEY_TYPE = 'cloudify.nodes.aws.ec2.Keypair'
SUBNET_TYPE = 'cloudify.nodes.aws.ec2.Subnet'
GROUP_TYPE = 'cloudify.nodes.aws.ec2.SecurityGroup'
NETWORK_INTERFACE_TYPE = 'cloudify.nodes.aws.ec2.Interface'


class EC2Instances(EC2Base):
    '''
        EC2 Instances interface
    '''
    def __init__(self, ctx_node, resource_id=None, client=None, logger=None):
        EC2Base.__init__(self, ctx_node, resource_id, client, logger)
        self.type_name = RESOURCE_TYPE
        self._describe_call = 'describe_instances'
        self._ids_key = INSTANCE_IDS
        self._type_key = INSTANCES
        self._id_key = INSTANCE_ID

    def prepare_instance_ids_request(self, params=None):
        params = params or {}
        return {INSTANCE_IDS: params.get(INSTANCE_IDS, [self.resource_id])}

    @property
    def instance_ids_request(self):
        return self.prepare_instance_ids_request()

    @property
    def properties(self):
        '''Gets the properties of an external resource'''
        if not self._properties:
            reservations = self.get(self.instance_ids_request)
            for res in reservations:
                if self._type_key in res:
                    for instance in res[self._type_key]:
                        if instance[self._id_key] == self.resource_id:
                            self._properties = instance
        return self._properties

    def get(self, request):
        resources = self.describe(request)
        return resources.get(RESERVATIONS, [{}])

    @property
    def status(self):
        '''Gets the status of an external resource'''
        if not self.properties:
            return
        return self.properties.get('State', {}).get('Code')

    @property
    def check_status(self):
        if self.status in [RUNNING]:
            return 'OK'
        return 'NOT OK'

    def describe(self, params):
        try:
            return self.make_client_call('describe_instances', params)
        except NonRecoverableError:
            return {}

    def create(self, params):
        '''
            Create AWS EC2 Instances.
        '''
        return self.make_client_call('run_instances', params)

    def start(self, params):
        '''
            Start Instances.
        '''
        return self.make_client_call('start_instances', params)

    def stop(self, params):
        '''
            Stop AWS EC2 Instances.
        '''
        return self.make_client_call('stop_instances', params)

    def delete(self, params):
        '''
            Delete AWS EC2 Instances.
        '''
        return self.make_client_call('terminate_instances', params)

    def modify_instance_attribute(self, params):
        '''
            Modify attribute of AWS EC2 Instances.
        '''
        return self.make_client_call('modify_instance_attribute', params)

    def get_password(self, params):
        '''
            Modify attribute of AWS EC2 Instances.
        '''
        return self.make_client_call('get_password_data', params)


@decorators.aws_resource(EC2Instances, resource_type=RESOURCE_TYPE)
def prepare(ctx, iface, resource_config, **_):
    '''Prepares AWS EC2 Instances'''
    # Save the parameters
    ctx.instance.runtime_properties['resource_config'] = resource_config


@decorators.aws_resource(EC2Instances, RESOURCE_TYPE)
@decorators.tag_resources
@decorators.wait_for_status(
    status_good=[RUNNING, PENDING],
    fail_on_missing=False)
def create(ctx, iface, resource_config, **kwargs):
    '''Creates AWS EC2 Instances'''

    handle_userdata(resource_config)
    assign_subnet_param(resource_config)
    assign_groups_param(resource_config)
    assign_nics_param(resource_config)
    handle_tags(resource_config)

    validate_multiple_vm_per_node_instance(resource_config)

    create_response = iface.create(resource_config)
    ctx.instance.runtime_properties['create_response'] = \
        utils.JsonCleanuper(create_response).to_dict()
    if MULTI_ID not in ctx.instance.runtime_properties:
        ctx.instance.runtime_properties[MULTI_ID] = []
    if len(create_response[INSTANCES]) == 1:
        instance_id = create_response[INSTANCES][0].get(INSTANCE_ID, '')
        iface.update_resource_id(instance_id)
        utils.update_resource_id(ctx.instance, instance_id)
        do_modify_instance_attribute(
            iface,
            kwargs.get('modify_instance_attribute_args', {}))
        ctx.instance.runtime_properties[MULTI_ID] = [instance_id]
    else:
        for instance in create_response[INSTANCES]:
            instance_id = instance.get(INSTANCE_ID, '')
            ctx.instance.runtime_properties[MULTI_ID].append(
                instance_id)
            iface.update_resource_id(instance_id)
            do_modify_instance_attribute(
                iface,
                kwargs.get('modify_instance_attribute_args', {}))


@decorators.multiple_aws_resource(EC2Instances, RESOURCE_TYPE)
def start(ctx, iface, resource_config, **_):
    '''Starts AWS EC2 Instances'''
    if iface.status in [RUNNING] and ctx.operation.retry_number > 0:
        assign_ip_properties(ctx, iface.properties)
        if not _handle_password(iface):
            raise OperationRetry(
                'Waiting for {0} ID# {1} password.'.format(
                    iface.type_name, iface.resource_id))
        return
    elif ctx.operation.retry_number == 0:
        try:
            iface.start(iface.prepare_instance_ids_request(resource_config))
        except NonRecoverableError as e:
            if 'UnsupportedOperation' not in str(e):
                raise
            ctx.logger.info(
                'Skipping start, because the operation is not supported.')

    raise OperationRetry(
        '{0} ID# {1} is still in a pending state {2}.'.format(
            iface.type_name, iface.resource_id, iface.status))


@decorators.multiple_aws_resource(EC2Instances, RESOURCE_TYPE)
def poststart(ctx, iface, *_, **__):
    '''Stores AWS EC2 Instances Details'''
    ctx.instance.runtime_properties['resource'] = utils.JsonCleanuper(
        iface.properties).to_dict()
    utils.update_expected_configuration(iface, ctx.instance.runtime_properties)
    node_instance_ids = [
        ni.target.instance.id for ni in ctx.instance.relationships]
    utils.post_start_related_nodes(node_instance_ids, ctx.deployment.id)


@decorators.multiple_aws_resource(EC2Instances, RESOURCE_TYPE)
@decorators.wait_for_status(
    status_good=[STOPPED],
    status_pending=[PENDING, STOPPING, SHUTTING_DOWN])
def stop(ctx, iface, resource_config, **_):
    '''Stops AWS EC2 Instances'''

    if MULTI_ID in ctx.instance.runtime_properties:
        resource_config[INSTANCE_IDS] = \
            ctx.instance.runtime_properties[MULTI_ID]
    try:
        iface.stop(iface.prepare_instance_ids_request(resource_config))
    except NonRecoverableError as e:
        if 'UnsupportedOperation' not in str(e):
            raise
        raise utils.SkipWaitingOperation('Unsupported operation.')


@decorators.multiple_aws_resource(EC2Instances, RESOURCE_TYPE)
@decorators.untag_resources
@decorators.wait_for_delete(
    status_deleted=[TERMINATED],
    status_pending=[PENDING, STOPPING, STOPPED, SHUTTING_DOWN])
def delete(iface, resource_config, dry_run=False, **_):
    '''Deletes AWS EC2 Instances'''
    resource_config['DryRun'] = dry_run
    if MULTI_ID in ctx.instance.runtime_properties:
        resource_config[INSTANCE_IDS] = \
            ctx.instance.runtime_properties[MULTI_ID]
    iface.delete(iface.prepare_instance_ids_request(resource_config))


@decorators.multiple_aws_resource(EC2Instances, RESOURCE_TYPE)
def modify_instance_attribute(ctx, iface, resource_config, **_):
    do_modify_instance_attribute(iface, resource_config)


def extract_powershell_content(string_with_powershell):
    """We want to filter user data for powershell scripts.
    However, AWS EC2 allows only one segment that is Powershell.
    So we have to concat separate Powershell scripts into one.
    First we separate all Powershell scripts without their tags.
    Later we will add the tags back.
    """

    split_string = string_with_powershell.splitlines()

    if not split_string:
        return ''

    if split_string[0] == '#ps1_sysnative' or \
            split_string[0] == '#ps1_x86':
        split_string.pop(0)

    if PS_OPEN not in split_string:
        script_start = -1  # Because we join at +1.
    else:
        script_start = split_string.index(PS_OPEN)

    if PS_CLOSE not in split_string:
        script_end = len(split_string)
    else:
        script_end = split_string.index(PS_CLOSE)

    # Return everything between Powershell back as a string.
    return '\n'.join(split_string[script_start + 1:script_end])


def handle_userdata(params, encode=False):
    existing_userdata = params.get(USERDATA, '')
    if existing_userdata is None:
        existing_userdata = ''
    elif isinstance(existing_userdata, dict) or \
            isinstance(existing_userdata, list):
        existing_userdata = json.dumps(existing_userdata)
    elif not isinstance(existing_userdata, text_type):
        existing_userdata = text_type(existing_userdata)

    install_agent_userdata = ctx.agent.init_script()
    os_family = ctx.node.properties['os_family']

    if not (existing_userdata or install_agent_userdata):
        return ''

    # Windows instances require no more than one
    # Powershell script, which must be surrounded by
    # Powershell tags.
    if install_agent_userdata and os_family == 'windows':

        # Get the powershell content from install_agent_userdata
        install_agent_userdata = \
            extract_powershell_content(install_agent_userdata)

        # Get the powershell content from existing_userdata
        # (If it exists.)
        existing_userdata_powershell = \
            extract_powershell_content(existing_userdata)

        # Combine the powershell content from two sources.
        install_agent_userdata = \
            '#ps1_sysnative\n{0}\n{1}\n{2}\n{3}\n'.format(
                PS_OPEN,
                existing_userdata_powershell,
                install_agent_userdata,
                PS_CLOSE)

        # Additional work on the existing_userdata.
        # Remove duplicate Powershell content.
        # Get rid of unnecessary newlines.
        existing_userdata = \
            existing_userdata.replace(
                existing_userdata_powershell,
                '').replace(
                    PS_OPEN,
                    '').replace(
                        PS_CLOSE,
                        '').strip()

    if not existing_userdata or existing_userdata.isspace():
        final_userdata = install_agent_userdata
    elif not install_agent_userdata:
        final_userdata = existing_userdata
    else:
        final_userdata = compute.create_multi_mimetype_userdata(
            [existing_userdata, install_agent_userdata])

    if encode:
        final_userdata = b64encode(final_userdata.encode()).decode("ascii")

    params[USERDATA] = final_userdata


def _handle_password(iface):
    if not ctx.node.properties.get('use_password'):
        return True
    # Get agent key data.
    key_data = ctx.node.properties['agent_config'].get('key')
    # If no key_data yet, check to see if
    # a Key pair attached via relationship.
    if not key_data:
        rel = utils.find_rel_by_node_type(ctx.instance, KEY_TYPE)
        if rel:
            key_data = \
                rel.target.instance.runtime_properties.get(
                    'create_response', {}).get('KeyMaterial')
    if not key_data:
        raise NonRecoverableError(
            "'use_password' is 'true', however private key was not specified; "
            "please specify it either by using the 'key' field under "
            "'agent_config' or by a relationship to a "
            "'cloudify.nodes.aws.ec2.Keypair' node template")
    if os.path.exists(key_data):
        with open(key_data) as outfile:
            key_data = outfile.read()
    password_data = iface.get_password(
        {
            'InstanceId': ctx.instance.runtime_properties[EXTERNAL_RESOURCE_ID]
        }
    )
    if not isinstance(password_data, dict):
        return False
    encrypted_password = password_data.get('PasswordData')
    if not encrypted_password:
        ctx.logger.error('password_data is {0}'.format(password_data))
        return False
    key = RSA.importKey(key_data)
    password = decrypt_password(key, encrypted_password)
    ctx.instance.runtime_properties['password'] = \
        password
    return True


def sort_devices(devices):
    """Sort network interfaces according to index and assign indices to
    those with missing value `DeviceIndex` key.

    :param devices: A list of dicts,
        e.g. [{NetworkInterfaceId: 'foo', 'DeviceIndex': None}]
    :return:
    """
    # Get a list of those devices that have an index.
    indexed = [dev for dev in devices if isinstance(dev[DEVICE_INDEX], int)]
    # Sort by index
    indexed = sorted(indexed, key=lambda lb: lb.get(DEVICE_INDEX))
    # Get a list of those devices that have a None value for index.
    # Also provide default value based in dict index in list.
    unindexed = [{NIC_ID: dev[NIC_ID], DEVICE_INDEX: i} for i, dev in
                 enumerate(devices) if dev[DEVICE_INDEX] is None]

    def insert_from_unindexed(index):
        # This is how we remove unindexed devices and intersperse
        # them among indexed devices.
        dev = unindexed.pop(0)
        if index == 0:
            dev[DEVICE_INDEX] = index
            indexed.insert(index, dev)
        else:
            dev[DEVICE_INDEX] = indexed[index][DEVICE_INDEX] + 1
            try:
                indexed[index + 1] = dev
            except IndexError:
                indexed.append(dev)

    # If there are no devices in the indexed list, return the unindexed list.
    if not indexed:
        return unindexed
    # Make sure that we have a primary device if one is not specified.
    elif 0 not in [value[DEVICE_INDEX] for value in indexed]:
        insert_from_unindexed(0)
    # Go through all of the indexed devices and if there are indices between
    # assigned indices, fill them with unindexed devices and provide new index.
    for n in range(0, len(indexed + unindexed)):
        try:
            spare = indexed[n + 1][DEVICE_INDEX] - \
                indexed[n][DEVICE_INDEX] > 1
        except (IndexError, TypeError):
            if unindexed:
                insert_from_unindexed(n)
                continue
            spare = False
        if spare:
            insert_from_unindexed(n)

    return indexed


def assign_subnet_param(params):
    subnet_id = params.get(SUBNET_ID)
    if not subnet_id:
        relationship = utils.find_rel_by_node_type(ctx.instance,
                                                   SUBNET_TYPE)
        if relationship:
            target = relationship
            if target:
                subnet_id = \
                    target.target.instance.runtime_properties.get(
                        EXTERNAL_RESOURCE_ID)
    if subnet_id:
        params[SUBNET_ID] = subnet_id


def assign_groups_param(params):
    # Add security groups from relationships if provided.
    group_ids = get_groups_from_rels(params.get(GROUPIDS, []))
    if group_ids:
        params[GROUPIDS] = group_ids


def get_groups_from_rels(group_ids=None):
    group_ids = group_ids or []
    relationships = utils.find_rels_by_node_type(ctx.instance, GROUP_TYPE)
    for relationship in relationships:
        target = relationship
        if target is not None:
            group_id = \
                target.target.instance.runtime_properties.get(
                    EXTERNAL_RESOURCE_ID)
            if group_id not in group_ids:
                group_ids.append(group_id)
            del group_id
        del target, relationship
    return group_ids


def get_nics_from_rels(nics_from_rels=None):
    nics_from_rels = nics_from_rels or []
    relationships = utils.find_rels_by_node_type(
        ctx.instance, NETWORK_INTERFACE_TYPE)
    for relationship in relationships:
        target = relationship
        if target is not None:
            prop = target.target.instance.runtime_properties
            rel_nic_id = prop.get(EXTERNAL_RESOURCE_ID)
            rel_device_index = prop.get('device_index')
            rel_nic = {
                NIC_ID: rel_nic_id,
                DEVICE_INDEX: rel_device_index
            }
            if 'Description' in prop['resource_config']:
                rel_nic['Description'] = prop['resource_config']['Description']
            nics_from_rels.append(rel_nic)
        del target, rel_nic_id, rel_device_index, rel_nic
    return nics_from_rels


def assign_nics_param(params):
    # Get all nics from relationships.
    nics_from_rels = get_nics_from_rels()

    # Get all nics from the resource_config dict.
    nics_from_params = params.get(NETWORK_INTERFACES, [])

    # Merge the two lists.
    merged_nics = []
    nics = defaultdict(dict)
    for nic in (nics_from_rels, nics_from_params):
        for i in nic:
            nics[i[NIC_ID]].update(i)
            merged_nics = list(nics.values())
    sorted_devices = sort_devices(merged_nics)
    if sorted_devices:
        params[NETWORK_INTERFACES] = sorted_devices


def do_modify_instance_attribute(iface,
                                 modify_instance_attribute_args=None):
    if modify_instance_attribute_args:
        modify_instance_attribute_args[INSTANCE_ID] = iface.resource_id
        iface.modify_instance_attribute(modify_instance_attribute_args)


def assign_ip_properties(_ctx, current_properties):

    nics = current_properties.get('NetworkInterfaces', [])
    ipv4_addresses = \
        _ctx.instance.runtime_properties.get('ipv4_addresses', [])
    ipv6_addresses = \
        _ctx.instance.runtime_properties.get('ipv6_addresses', [])

    for nic in nics:
        nic_ipv4 = nic.get('PrivateIpAddresses', [])
        for _nic_ipv4 in nic_ipv4:
            _private_ip = _nic_ipv4.get('PrivateIpAddress')
            if _nic_ipv4.get('Primary', False):
                _ctx.instance.runtime_properties['ipv4_address'] = _private_ip
                _ctx.instance.runtime_properties['private_ip_address'] = \
                    _private_ip
            if _private_ip not in ipv4_addresses:
                ipv4_addresses.append(_private_ip)
        nic_ipv6 = nic.get('Ipv6Addresses', [])
        for _nic_ipv6 in nic_ipv6:
            if _nic_ipv6 not in ipv6_addresses:
                ipv6_addresses.append(_nic_ipv6)

    _ctx.instance.runtime_properties['ipv4_addresses'] = ipv4_addresses
    ipv6_addr_list = []
    for ipv6_addr in ipv6_addresses:
        if isinstance(ipv6_addr, dict) and ipv6_addr.get('Ipv6Address'):
            ipv6_addr_list.append(ipv6_addr['Ipv6Address'])
    _ctx.instance.runtime_properties['ipv6_addresses'] = ipv6_addr_list
    ipv6_addresses = ipv6_addr_list

    if len(ipv4_addresses) > 0 and \
            not _ctx.instance.runtime_properties.get('ipv4_address'):
        _ctx.instance.runtime_properties['ipv4_address'] = ipv4_addresses[0]

    if len(ipv6_addresses) > 0 and \
            not _ctx.instance.runtime_properties.get('ipv6_address'):
        _ctx.instance.runtime_properties['ipv6_address'] = ipv6_addresses[0]

    pip = current_properties.get('PublicIpAddress')
    ip = current_properties.get('PrivateIpAddress')

    if ctx.node.properties['use_public_ip']:
        _ctx.instance.runtime_properties['ip'] = pip
        _ctx.instance.runtime_properties['public_ip_address'] = pip
    elif ctx.node.properties.get('use_ipv6_ip', False) and ipv6_addresses:
        _ctx.instance.runtime_properties['ip'] = ipv6_addresses[0]
        _ctx.instance.runtime_properties['public_ip_address'] = pip
    else:
        _ctx.instance.runtime_properties['ip'] = ip
        _ctx.instance.runtime_properties['public_ip_address'] = pip

    _ctx.instance.runtime_properties['private_ip_address'] = ip


def validate_multiple_vm_per_node_instance(params):
    max_count = params.get('MaxCount', 1)
    min_count = params.get('MinCount', 1)
    if min_count > 1 or max_count > 1:
        ctx.logger.error(
            'The parameters MinCount and MaxCount may cause problems '
            'with Cloudify\'s implementation of EC2 Instances. '
            'For example, if you provided a relationship to a ENI or '
            'other resource, then EC2 instance provisioning will fail '
            'due to previously attached ENI.'
            'Also, Cloudify Agent node instance will require a one to one '
            'relationship to a Virtual machine node instance. If '
            'multiple virtual machines are contained in a single node '
            'instance, then Cloudify Agent installation will fail. '
            'Only use MinCount and MaxCount if your deployment does '
            'not require a Cloudify node instance. Otherwise, set both '
            'MinCount and MaxCount to 1 and control multiple instances '
            'with a scaling policy: https://docs.cloudify.co/latest/'
            'developer/blueprints/spec-policies/')
        agent_config = ctx.node.properties.get('agent_config', {})
        if agent_config.get('install_method') == 'remote':
            raise NonRecoverableError(
                'Configuration not supported. '
                'Cloudify agent_config property.install_method is '
                '\'remote\' and MinCount or MaxCount > 1.')
        elif ctx.node.properties.get('install_agent'):
            ctx.logger.warn(
                'The node property install_agent is deprecated and may '
                'lead to failed deployments.')


def handle_tags(params):
    for cnt, tags_spec in enumerate(params.get(TAGS, [])):
        if 'ResourceType' not in tags_spec:
            params[TAGS][cnt]['ResourceType'] = 'instance'


@decorators.aws_resource(class_decl=EC2Instances,
                         resource_type=RESOURCE_TYPE,
                         waits_for_status=False)
def check_drift(ctx, iface=None, **_):
    return utils.check_drift(RESOURCE_TYPE, iface, ctx.logger)


interface = EC2Instances

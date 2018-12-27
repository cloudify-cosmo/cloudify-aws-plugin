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
    EC2.Instances
    ~~~~~~~~~~~~~~~
    AWS EC2 Instances interface
'''

# Common
from Crypto.PublicKey import RSA
from collections import defaultdict
import json
import os

# Boto
from botocore.exceptions import ClientError

# Cloudify
from cloudify import compute
from cloudify import ctx
from cloudify.exceptions import NonRecoverableError, OperationRetry
from cloudify_aws.common import decorators, utils
from cloudify_aws.common.constants import EXTERNAL_RESOURCE_ID
from cloudify_aws.ec2 import EC2Base
from cloudify_aws.ec2.decrypt import decrypt_password

RESOURCE_TYPE = 'EC2 Instances'
RESERVATIONS = 'Reservations'
INSTANCES = 'Instances'
PENDING = 0
RUNNING = 16
SHUTTING_DOWN = 32
TERMINATED = 48
STOPPING = 64
STOPPED = 80
PS_OPEN = '<powershell>'
PS_CLOSE = '</powershell>'
GROUP_TYPE = 'cloudify.nodes.aws.ec2.SecurityGroup'
NETWORK_INTERFACE_TYPE = 'cloudify.nodes.aws.ec2.Interface'
SUBNET_TYPE = 'cloudify.nodes.aws.ec2.Subnet'
KEY_TYPE = 'cloudify.nodes.aws.ec2.Keypair'
GROUPIDS = 'SecurityGroupIds'
NETWORK_INTERFACES = 'NetworkInterfaces'
SUBNET_ID = 'SubnetId'
INSTANCE_ID = 'InstanceId'
INSTANCE_IDS = 'InstanceIds'
DEVICE_INDEX = 'DeviceIndex'
NIC_ID = 'NetworkInterfaceId'


class EC2Instances(EC2Base):
    '''
        EC2 Instances interface
    '''
    def __init__(self, ctx_node, resource_id=None, client=None, logger=None):
        EC2Base.__init__(self, ctx_node, resource_id, client, logger)
        self.type_name = RESOURCE_TYPE

    @property
    def properties(self):
        '''Gets the properties of an external resource'''
        params = {INSTANCE_IDS: [self.resource_id]}
        try:
            resources = \
                self.client.describe_instances(**params)
        except ClientError:
            pass
        else:
            reservations = resources.get(RESERVATIONS, [])
            instances = []
            for r in reservations:
                for i in r.get(INSTANCES, []):
                    instances.append(i)
            if len(instances) == 1:
                return instances[0]
        return None

    @property
    def status(self):
        '''Gets the status of an external resource'''
        props = self.properties
        if not props:
            return None
        return props['State']['Code']

    def create(self, params):
        '''
            Create AWS EC2 Instances.
        '''
        return self.make_client_call('run_instances', params)

    def start(self, params):
        '''
            Start Instances.
        '''
        self.logger.debug(
            'Starting {0} with parameters: {1}'.format(
                self.type_name, params))
        res = self.client.start_instances(**params)
        self.logger.debug('Response: {0}'.format(res))
        return res

    def stop(self, params):
        '''
            Stop AWS EC2 Instances.
        '''
        self.logger.debug(
            'Stopping {0} with parameters: {1}'.format(
                self.type_name, params))
        res = self.client.stop_instances(**params)
        self.logger.debug('Response: {0}'.format(res))
        return res

    def delete(self, params):
        '''
            Delete AWS EC2 Instances.
        '''
        self.logger.debug(
            'Deleting {0} with parameters: {1}'.format(
                self.type_name, params))
        res = self.client.terminate_instances(**params)
        self.logger.debug('Response: {0}'.format(res))
        return res

    def modify_instance_attribute(self, params):
        '''
            Modify attribute of AWS EC2 Instances.
        '''
        self.logger.debug(
            'Modifying {0} attribute with parameters: {1}'.format(
                self.type_name, params))
        res = self.client.modify_instance_attribute(**params)
        self.logger.debug('Response: {0}'.format(res))
        return res

    def get_password(self, params):
        '''
            Modify attribute of AWS EC2 Instances.
        '''
        self.logger.debug(
            'Getting {0} password with parameters: {1}'.format(
                self.type_name, params))
        res = self.client.get_password_data(**params)
        self.logger.debug('Response: {0}'.format(res))
        return res


@decorators.aws_resource(EC2Instances, resource_type=RESOURCE_TYPE)
def prepare(ctx, iface, resource_config, **_):
    '''Prepares AWS EC2 Instances'''
    # Save the parameters
    ctx.instance.runtime_properties['resource_config'] = resource_config


@decorators.aws_resource(EC2Instances, RESOURCE_TYPE)
@decorators.wait_for_status(
    status_good=[RUNNING, PENDING],
    fail_on_missing=False)
@decorators.tag_resources
def create(ctx, iface, resource_config, **_):
    '''Creates AWS EC2 Instances'''

    params = \
        dict() if not resource_config else resource_config.copy()

    params['UserData'] = _handle_userdata(params.get('UserData', ''))

    # Add subnet from relationship if provided.
    subnet_id = params.get(SUBNET_ID)
    if not subnet_id:
        relationship = utils.find_rel_by_node_type(ctx.instance, SUBNET_TYPE)
        if relationship:
            target = relationship
            if target:
                params[SUBNET_ID] = \
                    target.target.instance.runtime_properties.get(
                        EXTERNAL_RESOURCE_ID)
            del subnet_id, target, relationship

    # Add security groups from relationships if provided.
    group_ids = params.get(GROUPIDS, [])
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
    params[GROUPIDS] = group_ids

    # Get all nics from relationships.
    nics_from_rels = []
    relationships = utils.find_rels_by_node_type(
        ctx.instance, NETWORK_INTERFACE_TYPE)
    for relationship in relationships:
        target = relationship
        if target is not None:
            rel_nic_id = \
                target.target.instance.runtime_properties.get(
                    EXTERNAL_RESOURCE_ID)
            rel_device_index = target.target.instance.runtime_properties.get(
                'device_index')
            rel_nic = {
                NIC_ID: rel_nic_id,
                DEVICE_INDEX: rel_device_index
            }
            nics_from_rels.append(rel_nic)
        del target, rel_nic_id, rel_device_index, rel_nic

    # Get all nics from the resource_config dict.
    nics_from_params = params.get(NETWORK_INTERFACES, [])

    # Merge the two lists.
    merged_nics = []
    nics = defaultdict(dict)
    for nic in (nics_from_rels, nics_from_params):
        for i in nic:
            nics[i[NIC_ID]].update(i)
            merged_nics = nics.values()
    del nic, nics

    for counter, nic in enumerate(
            sorted(merged_nics,
                   key=lambda k: k.get(DEVICE_INDEX))):
        if not nic[DEVICE_INDEX]:
            nic[DEVICE_INDEX] = counter
    params[NETWORK_INTERFACES] = merged_nics

    create_response = iface.create(params)
    ctx.instance.runtime_properties['create_response'] = \
        utils.JsonCleanuper(create_response).to_dict()
    try:
        instance = create_response[INSTANCES][0]
    except (KeyError, IndexError) as e:
        raise NonRecoverableError(
            'Error {0}: create response has no instances: {1}'.format(
                e.message, create_response))
    instance_id = instance.get(INSTANCE_ID, '')
    iface.update_resource_id(instance_id)
    utils.update_resource_id(ctx.instance, instance_id)

    modify_instance_attribute_args = \
        _.get('modify_instance_attribute_args')
    if modify_instance_attribute_args:
        modify_instance_attribute_args[INSTANCE_ID] = \
            instance_id
        iface.modify_instance_attribute(
            modify_instance_attribute_args)


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


@decorators.aws_resource(EC2Instances, RESOURCE_TYPE)
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
        params = \
            dict() if not resource_config else resource_config.copy()
        iface.start(
            {INSTANCE_IDS: params.get(
                INSTANCE_IDS, [iface.resource_id])})

    raise OperationRetry(
        '{0} ID# {1} is still in a pending state.'.format(
            iface.type_name, iface.resource_id))


@decorators.aws_resource(EC2Instances, RESOURCE_TYPE)
@decorators.wait_for_status(
    status_good=[STOPPED],
    status_pending=[PENDING, RUNNING, STOPPING, SHUTTING_DOWN])
def stop(ctx, iface, resource_config, **_):
    '''Stops AWS EC2 Instances'''

    params = \
        dict() if not resource_config else resource_config.copy()
    iface.stop({INSTANCE_IDS: params.get(INSTANCE_IDS, [iface.resource_id])})


@decorators.aws_resource(EC2Instances, RESOURCE_TYPE)
@decorators.wait_for_delete(
    status_deleted=[TERMINATED],
    status_pending=[PENDING, STOPPING, SHUTTING_DOWN])
@decorators.untag_resources
def delete(iface, resource_config, **_):
    '''Deletes AWS EC2 Instances'''

    params = \
        dict() if not resource_config else resource_config.copy()
    iface.delete({INSTANCE_IDS: params.get(INSTANCE_IDS, [iface.resource_id])})
    for prop in ['ip',
                 'private_ip_address',
                 'public_ip_address',
                 'create_response']:
        try:
            del ctx.instance.runtime_properties[prop]
        except KeyError:
            pass


@decorators.aws_resource(EC2Instances, RESOURCE_TYPE)
def modify_instance_attribute(ctx, iface, resource_config, **_):
    params = \
        dict() if not resource_config else resource_config.copy()
    instance_id = \
        ctx.instance.runtime_properties.get(
            INSTANCE_ID, iface.resource_id)
    params[INSTANCE_ID] = instance_id
    iface.modify_instance_attribute(params)


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


def _handle_userdata(existing_userdata):

    if existing_userdata is None:
        existing_userdata = ''
    elif isinstance(existing_userdata, dict) or \
            isinstance(existing_userdata, list):
        existing_userdata = json.dumps(existing_userdata)
    elif not isinstance(existing_userdata, basestring):
        existing_userdata = str(existing_userdata)

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

    return final_userdata


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
            'No key_data was provided in agent config property or rel.')
    if os.path.exists(key_data):
        with open(key_data, 'r') as outfile:
            key_data = outfile.readlines()
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

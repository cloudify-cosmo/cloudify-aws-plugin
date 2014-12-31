########
# Copyright (c) 2014 GigaSpaces Technologies Ltd. All rights reserved
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

# built-in package
import time

# other packages
from boto.ec2 import EC2Connection as EC2
from boto.exception import EC2ResponseError

# ctx packages
from cloudify import ctx
from cloudify.exceptions import NonRecoverableError, RecoverableError
from cloudify.decorators import operation

# EC2 Instance States
INSTANCE_PENDING = 0
INSTANCE_RUNNING = 16
INSTANCE_SHUTTING_DOWN = 32
INSTANCE_TERMINATED = 48
INSTANCE_STOPPING = 64
INSTANCE_STOPPED = 80

# Timeouts
CREATION_TIMEOUT = 15 * 60
START_TIMEOUT = 15 * 30
STOP_TIMEOUT = 3 * 60
TERMINATION_TIMEOUT = 3 * 60

# EC2 Method Arguments
RUN_INSTANCES_DEFAULTS = {
    'key_name': None,
    'security_groups': None,
    'user_data': None,
    'addressing_type': None,
    'placement': None,
    'kernel_id': None,
    'ramdisk_id': None,
    'monitoring_enabled': False,
    'subnet_id': None,
    'block_device_map': None,
    'disable_api_termination': False,
    'instance_initiated_shutdown_behavior': None,
    'private_ip_address': None,
    'placement_group': None,
    'client_token': None,
    'security_group_ids': None,
    'additional_info': None,
    'instance_profile_name': None,
    'instance_profile_arn': None,
    'tenancy': None,
    'ebs_optimized': False,
    'network_interfaces': None
}

RUN_INSTANCES_UNSUPPORTED = {
    'min_count': 1,
    'max_count': 1,
    'dry_run': False
}


def build_arg_dict(user_supplied, defaults, unsupported):

    arguments = defaults.copy()
    for pair in user_supplied.iteritems():
        arguments['{0}'.format(pair[0])] = pair[1]
    for pair in unsupported.iteritems():
        arguments['{0}'.format(pair[0])] = pair[1]
    return arguments


@operation
def create(**kwargs):
    """ Creates an AWS Instance from an (AMI) image_id and an instance_type.
    """

    arguments = build_arg_dict(ctx.node.properties['attributes'].copy(),
                               RUN_INSTANCES_DEFAULTS, RUN_INSTANCES_UNSUPPORTED)
    arguments['image_id'] = ctx.node.properties['image_id']
    arguments['instance_type'] = ctx.node.properties['instance_type']

    try:
        reservation = EC2().run_instances(**arguments)
    except EC2ResponseError:
        raise NonRecoverableError(EC2ResponseError.body)

    instance_id = reservation.instances[0].id

    if _state_validation(instance_id, INSTANCE_RUNNING, CREATION_TIMEOUT):
        ctx.instance.runtime_properties['instance_id'] = instance_id
    else:
        raise NonRecoverableError('Instance did not create within specified timeout: {0}.'
                                  .format(CREATION_TIMEOUT))


@operation
def start(**kwargs):

    instance_id = ctx.instance.runtime_properties['instance_id']

    try:
        EC2().start_instances(instance_id)
    except EC2ResponseError:
        raise NonRecoverableError(EC2ResponseError.body)

    if _state_validation(instance_id, INSTANCE_RUNNING, START_TIMEOUT):
        pass
    elif _state_validation(instance_id, INSTANCE_RUNNING, 15):
        raise RecoverableError('Instance still starting, but didn\'t stop within specified timeout: {0}.'
                               .format(START_TIMEOUT))
    else:
        raise RecoverableError('Instance not started.'
                               .format(START_TIMEOUT))


@operation
def stop(**kwargs):

    instance_id = ctx.instance.runtime_properties['instance_id']

    try:
        EC2().stop_instances(instance_id)
    except EC2ResponseError:
        raise NonRecoverableError(EC2ResponseError.body)

    if _state_validation(instance_id, INSTANCE_STOPPED, STOP_TIMEOUT):
        pass
    elif _state_validation(instance_id, INSTANCE_STOPPING, 15):
        raise RecoverableError('Instance still shutting down, but didn\'t stop within specified timeout: {0}.'
                               .format(STOP_TIMEOUT))
    else:
        raise RecoverableError('Instance not stopped.'
                               .format(STOP_TIMEOUT))


@operation
def terminate(**kwargs):

    instance_id = ctx.instance.runtime_properties['instance_id']

    try:
        EC2().terminate_instances(instance_id)
    except EC2ResponseError:
        raise NonRecoverableError(EC2ResponseError.body)

    if _state_validation(instance_id, INSTANCE_TERMINATED, TERMINATION_TIMEOUT):
        pass
    else:
        raise RecoverableError('Instance did not terminate within specified timeout: {0}.'
                               .format(TERMINATION_TIMEOUT))


def _state_validation(instance_id, state, timeout_len):

    timeout = time.time() + timeout_len

    while True:
        instance_state = EC2().get_all_instance_status(instance_ids=instance_id)[0]
        if state == int(instance_state.state_code):
            return True
        elif time.time() > timeout:
            return False
        else:
            time.sleep(15)


@operation
def creation_validation(**kwargs):
    instance_id = ctx.instance.runtime_properties['instance_id']
    state = INSTANCE_RUNNING
    timeout_len = CREATION_TIMEOUT

    if _state_validation(instance_id, state, timeout_len):
        pass
    else:
        raise NonRecoverableError('Instance not running.')

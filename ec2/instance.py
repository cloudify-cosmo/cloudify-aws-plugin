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

# general imports
import time

# ctx is imported and used in operations
from cloudify import ctx
from cloudify.exceptions import NonRecoverableError

# put the operation decorator on any function that is a task
from cloudify.decorators import operation

# boto imports
from boto.ec2 import EC2Connection as EC2
from boto.exception import EC2ResponseError

# EC2 Instance States
INSTANCE_PENDING = 0
INSTANCE_RUNNING = 16
INSTANCE_SHUTTING_DOWN = 32
INSTANCE_TERMINATED = 48
INSTANCE_STOPPING = 64
INSTANCE_STOPPED = 80


@operation
def run(**kwargs):
    """
    :return: reservation object
    """

    ami_image_id = ctx.node.properties['ami_image_id']
    instance_type = ctx.node.propertes['instance_type']

    try:
        reservation = EC2().run_instances(image_id=ami_image_id, instance_type=instance_type)
        ctx.node.runtime_properties['reservation'] = reservation
        return True
    except EC2ResponseError as e:
        raise NonRecoverableError(e.body)


def start():
    return True


def stop():
    return True


def terminate():
    return True


def creation_validation():
    return True

def set_instance_state(instance):
    """
    :param instance: an instance in reservation.instances
    :return:
    """

    state = EC2().get_all_instance_status(instance_ids=instance.id)[0]
    ctx.node.runtime_properties['{0}_state_name'.format(instance.id)] = state.state_name
    ctx.node.runtime_properties['{0}_state_code'.format(instance.id)] = state.state_code


def set_instance_states():
    """ The above method for many instances.
    :return:
    """
    reservation = ctx.node.runtime_properties['reservation']
    for instance in reservation.instances:
        set_instance_state(instance)


def state_equals_state(instance, state):
    """
    :param instance: an instance in reservation.instances
    :param state: a state from EC2 Instance States
    :return: True if the states are equal, otherwise False.
    """
    instance_state = ctx.node.runtime_properties['{0}_state_code'.format(instance.id)]

    if instance_state == state:
        return True
    else:
        return False

def poll_for_state(instance, state=INSTANCE_RUNNING, timeout=30):
    """
    :param instance: an instance in reservation.instances
    :param state: a state from the EC2 Instance States
    :param timeout: How long you want to try for (in secs).
    :return:
    """

    outcome = False

    while True:
        set_instance_state(instance)
        if state_equals_state(instance, state):
            outcome = True
            break
        elif time.time() > timeout:
            break

    return outcome

def poll_for_states(state=INSTANCE_RUNNING, timeout=30):
    """ The above method for many instances.
    :param state: a state from the EC2 Instance States
    :param timeout: How long you want to try for (in secs).
    :return:
    """
    reservation = ctx.node.runtime_properties['reservation']
    for instance in reservation.instances:
        poll_for_state(instance, state, timeout)
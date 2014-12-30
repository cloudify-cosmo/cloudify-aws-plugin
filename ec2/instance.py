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

CREATION_TIMEOUT = 15 * 60


@operation
def create(**kwargs):
    """
    :return: reservation object
    """

    ami_image_id = ctx.node.properties['ami_image_id']
    instance_type = ctx.node.properties['instance_type']

    try:
        reservation = EC2().run_instances(image_id=ami_image_id, instance_type=instance_type)
    except EC2ResponseError as e:
        raise NonRecoverableError(e.body)

    if state_validation(reservation.instances[0].id, INSTANCE_RUNNING, CREATION_TIMEOUT):
        pass
    else:
        raise NonRecoverableError('Instance id {0} did not create within specified timeout: {1}.'
                                  .format(reservation.instances[0].id, CREATION_TIMEOUT))


def start():
    pass


def stop():
    pass


def terminate():
    pass


def state_validation(instance_id, state, timeout_len):

    timeout = time.time() + timeout_len

    while True:
        instance_state = EC2().get_all_instance_status(instance_ids=instance_id)[0]
        if state == int(instance_state.state_code):
            return True
        elif time.time() > timeout:
            return False
        else:
            time.sleep(15)

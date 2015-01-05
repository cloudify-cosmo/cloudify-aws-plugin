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

# built-in import
import time

# other import
from boto.ec2 import EC2Connection as EC2


class Utility():

    def state_validation(self, instance_id, state,
                         timeout_length, check_interval):
        """ Check if an EC2 instance is in a particular state.

        :param instance_id: The ID of a EC2 instance.
        :param state: The state code (pending = 0, running = 16,
            shutting down = 32, terminated = 48, stopping = 64, stopped = 80
        :param timeout_length: How long to wait for a positive answer
            before we stop checking.
        :param check_interval: How long to wait between checks.
        :return: bool (True the desired state was reached, False, it was not.)
        """

        timeout = time.time() + timeout_length
        while True:
            instance_state = EC2().get_all_instance_status(
                instance_ids=instance_id)[0]
            if state == int(instance_state.state_code):
                return True
            elif time.time() > timeout:
                return False
            else:
                time.sleep(check_interval)

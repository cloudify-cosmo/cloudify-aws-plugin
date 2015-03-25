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

import os
import json
import fabric.api
from ec2 import configure
from ec2 import constants

def upload_credentials(config_path):
    temp = configure.BotoConfig().get_temp_file()
    fabric.api.put(temp, config_path)

def set_provider_context(agents_security_group, agents_keypair):

    provider_context_json = {
        "agents_keypair": agents_keypair,
        "agents_security_group": agents_security_group
    }

    os.environ['agents_keypair'] = agents_keypair
    os.environ['agents_security_group'] = agents_security_group

    with open(
            os.path.expanduser(constants.AWS_CONFIG_PATH), 'w') \
        as provider_context_file:
            json.dump(provider_context_json, provider_context_file)

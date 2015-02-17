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

# Built-in Imports:
import os
import tempfile

# Third Party Imports
from boto import config


class BotoConfig(object):

    def get_temp_config(self):
        temp_config = tempfile.mktemp()
        config = self._get_config()
        with open(temp_config, 'w') as temp_config_file:
            temp_config_file.write(config)
        return temp_config

    def _get_config(self):
        config = '[{}]\n' \
                 'aws_access_key_id = {}\n' \
                 'aws_secret_access_key = {}'.format(
                     self._get_aws_credentials_name(),
                     self._get_aws_access_key_id(),
                     self._get_aws_secret_access_key)
        return config

    def _get_aws_credentials_name(self):
        return config.get_value('Credentials', '__name__')

    def _get_aws_access_key_id(self):
        return config.get('Credentials', 'aws_access_key_id')

    def _get_aws_secret_access_key(self):
        return config.get('Credentials', 'aws_secret_access_key')

    def _get_path_to_boto_configuration(self):
        home = os.path.expanduser('~')
        path_to_boto_configuration = os.path.join(home, '.boto')
        return path_to_boto_configuration

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
import tempfile

# Third Party Imports
from boto import config

# Cloudify Imports


class BotoConfig(object):

    def get_temp_file(self):
        temp_config = tempfile.mktemp()
        config = self.get_config()
        with open(temp_config, 'w') as temp_config_file:
            temp_config_file.write(config)
        return temp_config

    def get_config(self, path=None, profile_name='Credentials'):
        credentials = self._load_credentials_from_path(path, profile_name)
        return '[{0}]\n' \
               'aws_access_key_id = {1}\n' \
               'aws_secret_access_key = {2}'.format(
                   credentials['profile_name'],
                   credentials['aws_access_key_id'],
                   credentials['aws_secret_access_key'])

    def _get_aws_credentials_name(self, credentials='Credentials'):
        return config.get_value(credentials, '__name__')

    def _get_aws_access_key_id(self, credentials='Credentials'):
        return config.get(credentials, 'aws_access_key_id')

    def _get_aws_secret_access_key(self, credentials='Credentials'):
        return config.get(credentials, 'aws_secret_access_key')

    def _load_credentials_from_path(self, path, profile_name):
        if path:
            config.load_from_path(path)

        return {
            'profile_name': self._get_aws_credentials_name(
                credentials=profile_name),
            'aws_access_key_id': self._get_aws_access_key_id(
                credentials=profile_name),
            'aws_secret_access_key': self._get_aws_secret_access_key(
                credentials=profile_name)
        }

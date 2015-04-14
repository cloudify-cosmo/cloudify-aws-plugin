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
from StringIO import StringIO
from ConfigParser import ConfigParser

# Third-party Imports
from boto import config

# Cloudify Imports


class BotoConfig(object):
    """Functions that provide an interface into a boto or aws config.
    """

    def get_config(self, path=None, profile_name):
        """Gets a specifice configuration from a path to a aws or boto configuration
        and profile_name

        :param path: path to a aws or boto configuration file
        :param profile_name: a aws or boto configuration profile_name in a
            configuration file
        :returns formatted string containing profile_name aws_access_key_id
            aws_secret_access_key
        """

        credentials = self._load_credentials_from_path(path, profile_name)
        config = self.create_creds_string(credentials)
        return config.getvalue()

    def get_temp_file(self):
        temp_config = tempfile.mktemp()
        config = self.get_config()
        with open(temp_config, 'w') as temp_config_file:
            temp_config_file.write(config)
        return temp_config

    def create_creds_config(self,
                            aws_access_key_id, aws_secret_access_key,
                            profile_name='DEFAULT', region=None):
        creds = ConfigParser()
        if profile_name != 'DEFAULT':
            creds.add_section(profile_name)
        creds.set(profile_name, 'aws_access_key_id', aws_access_key_id)
        creds.set(profile_name, 'aws_secret_access_key', aws_secret_access_key)
        if region:
            creds.set(profile_name, 'region', region)
        return creds

    def create_creds_string(self, credentials):
        credentials_string = StringIO()
        credentials.write(credentials_string)
        return credentials_string

    def _load_credentials_from_path(self, path, profile_name):
        """Gets the Profile Name AWS Access Key and AWS Secret Access Key
        for a specified path to a configuraton file and profile_name.

        :param path: path to a aws or boto configuration file
        :param profile_name: a aws or boto configuration profile_name in a
            configuration file
        :returns dictionary containing profile_name aws_access_key_id
            aws_secret_access_key
        """

        if path:
            config.load_from_path(path)

        profile_name = \
            self._get_aws_credentials_name(credentials=profile_name)
        aws_access_key_id = \
            self._get_aws_access_key_id(credentials=profile_name)
        aws_secret_access_key = \
            self._get_aws_secret_access_key(credentials=profile_name)

        return self.create_creds_config(aws_access_key_id,
                                        aws_secret_access_key,
                                        profile_name=profile_name)

    def _get_aws_credentials_name(self, credentials):
        """Gets the Profile Name.

        :param credentials: profile_name in an aws or boto configuration file
        : returns the __name__ for specified credentials (profile)
        """

        return config.get_value(credentials, '__name__')

    def _get_aws_access_key_id(self, credentials):
        """Gets the AWS Access Key.

        :param credentials: profile_name in an aws or boto configuration file
        : returns the aws_access_key_id for specified credentials (profile)
        """

        return config.get(credentials, 'aws_access_key_id')

    def _get_aws_secret_access_key(self, credentials):
        """Gets the AWS Secret Access Key.

        :param credentials: profile_name in an aws or boto configuration file
        : returns the aws_secret_access_key for specified credentials (profile)
        """

        return config.get(credentials, 'aws_secret_access_key')

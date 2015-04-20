########
# Copyright (c) 2015 GigaSpaces Technologies Ltd. All rights reserved
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
from StringIO import StringIO
from ConfigParser import ConfigParser


class BotoConfig(object):
    """Functions that provide an interface into a boto or aws config.
    """

    def create_creds_config(self,
                            aws_access_key_id, aws_secret_access_key,
                            profile_name='DEFAULT',
                            ec2_region_name=None, ec2_region_endpoint=None):
        creds = ConfigParser()
        if profile_name != 'DEFAULT':
            creds.add_section(profile_name)
        creds.set(profile_name, 'aws_access_key_id', aws_access_key_id)
        creds.set(profile_name, 'aws_secret_access_key', aws_secret_access_key)
        if ec2_region_name and ec2_region_endpoint:
            creds.add_section('Boto')
            creds.set('Boto', 'ec2_region_name', ec2_region_name)
            creds.set('Boto', 'ec2_region_endpoint', ec2_region_endpoint)
        return creds

    def create_creds_string(self, credentials):
        credentials_string = StringIO()
        credentials.write(credentials_string)
        return credentials_string

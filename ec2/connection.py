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

# Third-party Imports
from boto.ec2 import get_region
from boto.ec2 import EC2Connection

# Cloudify Imports
from ec2 import utils
from ec2 import constants


class EC2ConnectionClient():
    """Provides functions for getting the EC2 Client
    """

    def __init__(self):
        self.connection = None

    def client(self):
        """Represents the EC2Connection Client
        """

        aws_config_property = self._get_aws_config_property()
        if not aws_config_property:
            return EC2Connection()
        elif aws_config_property.get('ec2_region_name'):
            region_object = \
                get_region(aws_config_property['ec2_region_name'])
            aws_config = aws_config_property.copy()
            aws_config['region'] = region_object
        else:
            aws_config = aws_config_property.copy()

        if 'ec2_region_name' in aws_config:
            del(aws_config['ec2_region_name'])

        return EC2Connection(**aws_config)

    def _get_aws_config_property(self):
        node_properties = \
            utils.get_instance_or_source_node_properties()
        return node_properties[constants.AWS_CONFIG_PROPERTY]

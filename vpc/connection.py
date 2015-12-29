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
from boto.vpc import VPCConnection

# Cloudify imports
from ec2.connection import EC2ConnectionClient
from ec2 import utils as ec2_utils
from ec2 import constants


class VPCConnectionClient(EC2ConnectionClient):
    """Provides functions for getting the VPC Client
    """

    def client(self, aws_config=None):
        """Represents the VPCConnection Client
        """

        aws_config_property = (self._get_aws_config_property(aws_config) or
                               self._get_aws_config_from_file())
        if not aws_config_property:
            return VPCConnection()
        elif aws_config_property.get('ec2_region_name'):
            region_object = \
                get_region(aws_config_property['ec2_region_name'])
            aws_config = aws_config_property.copy()
            if region_object and 'ec2_region_endpoint' in aws_config_property:
                region_object.endpoint = \
                    aws_config_property['ec2_region_endpoint']
            aws_config['region'] = region_object
        else:
            aws_config = aws_config_property.copy()

        if 'ec2_region_name' in aws_config:
            del(aws_config['ec2_region_name'])

        # for backward compatibility,
        # delete this key before passing config to Boto
        if 'ec2_region_endpoint' in aws_config:
            del(aws_config["ec2_region_endpoint"])

        return VPCConnection(**aws_config)

    def _get_aws_config_property(self, aws_config=None):
        if aws_config:
            return aws_config
        node_properties = \
            ec2_utils.get_instance_or_source_node_properties()
        return node_properties[constants.AWS_CONFIG_PROPERTY]

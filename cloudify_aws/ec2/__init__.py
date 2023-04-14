# Copyright (c) 2018 Cloudify Platform Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
    EC2
    ~~~
    AWS EC2 base interface
"""

# Cloudify AWS
from cloudify_aws.common import AWSResourceBase
from cloudify_aws.common.utils import check_region_name
from cloudify_common_sdk.utils import get_client_config
from cloudify_aws.common.connection import Boto3Connection

# pylint: disable=R0903


class EC2Base(AWSResourceBase):
    """
        AWS ELB base interface
    """
    def __init__(self,
                 ctx_node,
                 resource_id=None,
                 client=None,
                 logger=None):

        if not client:
            config_from_utils = get_client_config(
               ctx_node=ctx_node, alternate_key='aws_config')
            check_region_name(config_from_utils.get('region_name'))
        AWSResourceBase.__init__(
            self, client or Boto3Connection(ctx_node).client('ec2'),
            resource_id=resource_id, logger=logger)
        self.type_name = None
        self._properties = {}
        self._ids_key = None
        self._type_key = None
        self._id_key = None

    @property
    def properties(self):
        '''Gets the properties of an external resource'''
        if not self._properties:
            res = self.get_describe_result({self._ids_key: [self.resource_id]})
            if self._type_key in res:
                for n in res[self._type_key]:
                    if n[self._id_key] == self.resource_id:
                        self._properties = n
        return self._properties

    @property
    def status(self):
        '''Gets the status of an external resource'''
        return self.properties.get('State')

    def create(self, params):
        """Creates a resource"""
        raise NotImplementedError()

    def delete(self, params=None):
        """Deletes a resource"""
        raise NotImplementedError()

    def tag(self, params):
        """Creates a resource"""
        self.logger.info('Tagging %s.' % params)
        res = self.client.create_tags(**params)
        self.logger.debug('Response: %s' % res)
        return res

    def untag(self, params):
        """Creates a resource"""
        self.logger.info('Untagging %s.' % params)
        res = self.client.delete_tags(**params)
        self.logger.debug('Response: %s' % res)
        return res

    def get_available_zone(self, params):
        """method to get the first available zone given a region"""
        self.logger.info('checking available zones given {0}'.format(params))
        valid_zones = []
        aws_azs = self.client.describe_availability_zones(**params)
        for az in aws_azs['AvailabilityZones']:
            zone = az['ZoneName']
            zone_state = az['State']
            if zone_state == 'available':
                valid_zones.append(zone)
        self.logger.info('valid zones {0}'.format(valid_zones))
        if valid_zones and len(valid_zones) >= 1:
            return valid_zones[0]
        return None

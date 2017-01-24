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

# Built-in Imports
import os
import uuid

# import testtools

# Third Party Imports
from boto.vpc import VPCConnection
from boto.ec2 import get_region

# Cloudify Imports
from cloudify_aws import constants
from cosmo_tester.framework.testenv import TestCase


class TestVpcBase(TestCase):

    def get_blueprint_path(self, blueprint_name='vpc_test_blueprint.yaml'):

        path = os.path.join(
            os.path.dirname(
                os.path.dirname(__file__)
            ),
            'manager/resources',
            blueprint_name)
        return path

    def get_inputs(self, override_inputs=None):

        inputs = dict(
            aws_config=self._get_aws_config(),
            create_new_resource=False,
            vpc_two_create_new_resource=False,
            vpc_id='',
            subnet_id='',
            internet_gateway_id='',
            key_path='~/{0}.pem'.format(uuid.uuid4()),
            ami_id=self.env.ubuntu_trusty_image_id,
            instance_type=self.env.medium_instance_type,
            vpn_gateway_id='',
            customer_gateway_id='',
            acl_list_id='',
            dhcp_options_id='',
            route_table_id='',
            availability_zone=self.env.availability_zone,
            dhcp_options_domain_name=self.env.ec2_domain_name,
            dhcp_options_domain_name_servers='AmazonProvidedDNS'
        )
        if override_inputs:
            inputs.update(override_inputs)
        return inputs

    def _get_aws_config(self, set_boto_region=False):
        aws_config = {
            'aws_access_key_id': self.env.aws_access_key_id,
            'aws_secret_access_key': self.env.aws_secret_access_key
        }
        if set_boto_region:
            aws_config['region'] = get_region(self.env.ec2_region_name)
        else:
            aws_config['ec2_region_name'] = self.env.ec2_region_name

        return aws_config

    def vpc_client(self):
        credentials = self._get_aws_config(set_boto_region=True)
        return VPCConnection(**credentials)

    def get_current_list_of_used_resources(self, vpc_client):

        resources = {
            constants.VPC['CLOUDIFY_NODE_TYPE']:
                vpc_client.get_all_vpcs(),
            constants.SUBNET['CLOUDIFY_NODE_TYPE']:
                vpc_client.get_all_subnets(),
            constants.INTERNET_GATEWAY['CLOUDIFY_NODE_TYPE']:
                vpc_client.get_all_internet_gateways(),
            constants.VPN_GATEWAY['CLOUDIFY_NODE_TYPE']:
                vpc_client.get_all_vpn_gateways(),
            constants.NETWORK_ACL['CLOUDIFY_NODE_TYPE']:
                vpc_client.get_all_network_acls(),
            constants.DHCP_OPTIONS['CLOUDIFY_NODE_TYPE']:
                vpc_client.get_all_dhcp_options(),
            constants.CUSTOMER_GATEWAY['CLOUDIFY_NODE_TYPE']:
                vpc_client.get_all_customer_gateways(),
            constants.ROUTE_TABLE['CLOUDIFY_NODE_TYPE']:
                vpc_client.get_all_route_tables()
        }

        return resources

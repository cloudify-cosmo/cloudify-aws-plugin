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

EXTERNAL_RESOURCE_ID = 'aws_resource_id'

# instance module constants
INSTANCE_STATE_STARTED = 16
INSTANCE_STATE_TERMINATED = 48
INSTANCE_STATE_STOPPED = 80

INSTANCE_REQUIRED_PROPERTIES = ['image_id', 'instance_type']

INSTANCE_INTERNAL_ATTRIBUTES = \
    ['private_dns_name', 'public_dns_name', 'public_ip_address', 'ip']

RUN_INSTANCE_PARAMETERS = {
    'image_id': None, 'key_name': None, 'security_groups': None,
    'user_data': None, 'addressing_type': None,
    'instance_type': 'm1.small', 'placement': None, 'kernel_id': None,
    'ramdisk_id': None, 'monitoring_enabled': False, 'subnet_id': None,
    'block_device_map': None, 'disable_api_termination': False,
    'instance_initiated_shutdown_behavior': None,
    'private_ip_address': None, 'placement_group': None,
    'client_token': None, 'security_group_ids': None,
    'additional_info': None, 'instance_profile_name': None,
    'instance_profile_arn': None, 'tenancy': None, 'ebs_optimized': False,
    'network_interfaces': None, 'dry_run': False
}

INSTANCE_SECURITY_GROUP_RELATIONSHIP = 'instance_connected_to_security_group'
INSTANCE_KEYPAIR_RELATIONSHIP = 'instance_connected_to_keypair'

# securitygroup module constants
SECURITY_GROUP_REQUIRED_PROPERTIES = ['description', 'rules']

# keypair module constants
KEYPAIR_REQUIRED_PROPERTIES = ['private_key_path']

# config
AWS_DEFAULT_CONFIG_PATH = '~/aws_config.json'

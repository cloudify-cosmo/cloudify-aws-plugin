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
'''
    Common.Constants
    ~~~~~~~~~~~~~~~~
    AWS constants
'''

AWS_CONFIG_PROPERTY = 'client_config'
EXTERNAL_RESOURCE_ID = 'aws_resource_id'
EXTERNAL_RESOURCE_ARN = 'aws_resource_arn'
REL_CONTAINED_IN = 'cloudify.relationships.contained_in'
ARN_REGEX = '^arn\:aws\:'
REGION_REGEX = (
    '^[a-z]{2}\-([a-z]{4,10}|[a-z]{3}\-[a-z]{4,10})\-[1-3]{1}$'
)
AVAILABILITY_ZONE_REGEX = (
    '^[a-z]{2}\-([a-z]{4,10}|[a-z]{3}\-[a-z]{4,10})\-[1-3]{1}[a-e]{1}$'
)

SWIFT_NODE_PREFIX = 'cloudify.nodes.swift'
SWIFT_ERROR_TOKEN_CODE = 'SignatureDoesNotMatch'


MAX_AWS_NAME = 255

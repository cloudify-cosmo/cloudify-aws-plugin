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
EXTERNAL_RESOURCE_ID_MULTIPLE = 'aws_resource_ids'
EXTERNAL_RESOURCE_ARN = 'aws_resource_arn'
TAG_SPECIFICATIONS_KWARG = 'TagSpecifications'

REL_CONTAINED_IN = 'cloudify.relationships.contained_in'
ARN_REGEX = '^arn\:aws\:'
REGION_REGEX = (
    '^[a-z]{2}\-([a-z]{4,10}|[a-z]{3}\-[a-z]{4,10})\-[1-3]{1}$'
)
AVAILABILITY_ZONE_REGEX = (
    '^[a-z]{2}\-([a-z]{4,10}|[a-z]{3}\-[a-z]{4,10})\-[1-3]{1}[a-z]{1}$'
)

SWIFT_NODE_PREFIX = 'cloudify.nodes.swift'
SWIFT_ERROR_TOKEN_CODE = 'SignatureDoesNotMatch'


MAX_AWS_NAME = 255

LOCATIONS = {
    'ap-northeast-1': {
        'coordinates': '35.6828387, 139.7594549',
        'town': 'Tokyo'
    },
    'ap-northeast-2': {
        'coordinates': '37.5666791, 126.9782914',
        'town': 'Seoul'
    },
    'ap-northeast-3': {
        'coordinates': '34.6198813, 135.490357',
        'town': 'Osaka'
    },
    'ap-south-1': {
        'coordinates': '19.0759899, 72.8773928',
        'town': 'Mumbai'
    },
    'ap-southeast-1': {
        'coordinates': '1.357107, 103.8194992',
        'town': 'Singapore'
    },
    'ap-southeast-2': {
        'coordinates': '-33.8548157, 151.2164539',
        'town': 'Sydney'
    },
    'ca-central-1': {
        'coordinates': '45.4972159, -73.6103642',
        'town': 'Montreal'
    },
    'eu-central-1': {
        'coordinates': '50.1106444, 8.6820917',
        'town': 'Frankfurt'
    },
    'eu-north-1': {
        'coordinates': '59.3251172, 18.0710935',
        'town': 'Stockholm'
    },
    'eu-west-1': {
        'coordinates': '52.865196, -7.9794599',
        'town': 'Ireland'
    },
    'eu-west-2': {
        'coordinates': '51.5073219, -0.1276474',
        'town': 'London'
    },
    'eu-west-3': {
        'coordinates': '48.8566969, 2.3514616',
        'town': 'Paris'
    },
    'sa-east-1': {
        'coordinates': '-23.5506507, -46.6333824',
        'town': 'Sao Paulo'
    },
    'us-east-1': {
        'coordinates': '39.0438, -77.4874',
        'town': 'Ashburn, VA'
    },
    'us-east-2': {
        'coordinates': '40.1536742, -82.6851699',
        'town': 'Johnstown, OH'
    },
    'us-west-1': {
        'coordinates': '37.0065078, -121.5631723',
        'town': 'Gilroy, CA'
    },
    'us-west-2': {
        'coordinates': '45.839855, -119.7005834',
        'town': 'Boardman, OR'
    }
}

SUPPORT_DRIFT = [
    'cloudify.nodes.aws.ec2.Vpc',
    'cloudify.nodes.aws.ec2.Subnet',
    'cloudify.nodes.aws.ec2.Interface',
    'cloudify.nodes.aws.ec2.SecurityGroup',
    'cloudify.nodes.aws.ec2.Instances',
    'cloudify.nodes.aws.eks.Cluster',
    'cloudify.nodes.aws.eks.NodeGroup',
]

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

# Standard imports
import unittest

# Third party imports
from mock import patch, MagicMock

# Local imports
from cloudify_aws.common._compat import reload_module
from cloudify_aws.ec2.resources.vpc_peering import EC2VpcPeering
from cloudify_aws.ec2.resources import vpc_peering
from cloudify_aws.common import constants
from cloudify_aws.common.tests.test_base import (
    TestBase,
    mock_decorator
)


class TestEC2VpcPeering(TestBase):

    def setUp(self):
        super(TestEC2VpcPeering, self).setUp()
        self.vpc_peering = EC2VpcPeering(
            "ctx_node",
            resource_id='test_peering_connection_id',
            client=True,
            logger=None)
        mock1 = patch(
            'cloudify_aws.common.decorators.aws_resource', mock_decorator)

        mock1.start()
        reload_module(vpc_peering)

    def test_class_properties(self):
        effect = self.get_client_error_exception(
            name=vpc_peering.RESOURCE_TYPE)

        self.vpc_peering.client = \
            self.make_client_function('describe_vpc_peering_connections',
                                      side_effect=effect)
        self.assertEqual(self.vpc_peering.properties, {})

        response = \
            {
                vpc_peering.VPC_PEERING_CONNECTIONS: [
                    {
                        'AccepterVpcInfo': {
                            'CidrBlock': 'cidr_block_test',
                            'Ipv6CidrBlockSet': [
                                {
                                    'Ipv6CidrBlock': 'ip_6_cidr_block_test'
                                },
                            ],
                            'CidrBlockSet': [
                                {
                                    'CidrBlock': 'cidr_block_test'
                                },
                            ],
                            'OwnerId': 'owner_id_test',
                            'VpcId': 'vpc_id_test',
                            'Region': 'region_test'
                        },
                        'RequesterVpcInfo': {
                            'CidrBlock': 'cidr_block_test',
                            'Ipv6CidrBlockSet': [
                                {
                                    'Ipv6CidrBlock': 'ip_6_cidr_block_test'
                                },
                            ],
                            'CidrBlockSet': [
                                {
                                    'CidrBlock': 'cidr_block_test'
                                },
                            ],
                            'OwnerId': 'owner_id_test',
                            'VpcId': 'vpc_id_test',
                            'Region': 'region_test'
                        },
                        'Status': {
                            'Code': 'test_status_code',
                            'Message': 'test_status_message'
                        },
                        'VpcPeeringConnectionId': 'test_peering_connection_id'
                    },
                ]
            }

        self.vpc_peering._describe_vpc_peering_filter = {
            vpc_peering.VPC_PEERING_CONNECTION_IDS:
                ['vpc_id_test']
        }
        self.vpc_peering.client = self.make_client_function(
            'describe_vpc_peering_connections', return_value=response)

        self.assertEqual(
            self.vpc_peering.properties[
                vpc_peering.VPC_PEERING_CONNECTION_ID],
            'test_peering_connection_id'
        )

    def test_class_status(self):
        response = \
            {
                vpc_peering.VPC_PEERING_CONNECTIONS: [
                    {
                        'AccepterVpcInfo': {
                            'CidrBlock': 'cidr_block_test',
                            'Ipv6CidrBlockSet': [
                                {
                                    'Ipv6CidrBlock': 'ip_6_cidr_block_test'
                                },
                            ],
                            'CidrBlockSet': [
                                {
                                    'CidrBlock': 'cidr_block_test'
                                },
                            ],
                            'OwnerId': 'owner_id_test',
                            'VpcId': 'vpc_id_test',
                            'Region': 'region_test'
                        },
                        'RequesterVpcInfo': {
                            'CidrBlock': 'cidr_block_test',
                            'Ipv6CidrBlockSet': [
                                {
                                    'Ipv6CidrBlock': 'ip_6_cidr_block_test'
                                },
                            ],
                            'CidrBlockSet': [
                                {
                                    'CidrBlock': 'cidr_block_test'
                                },
                            ],
                            'OwnerId': 'owner_id_test',
                            'VpcId': 'vpc_id_test',
                            'Region': 'region_test'
                        },
                        'Status': {
                            'Code': 'test_status_code',
                            'Message': 'test_status_message'
                        },
                        'VpcPeeringConnectionId': 'test_peering_connection_id'
                    },
                ]
            }

        self.vpc_peering._describe_vpc_peering_filter = {
            vpc_peering.VPC_PEERING_CONNECTION_IDS:
                ['vpc_id_test']
        }
        self.vpc_peering.client = self.make_client_function(
            'describe_vpc_peering_connections', return_value=response)

        self.assertEqual(self.vpc_peering.status['Code'], 'test_status_code')

    def test_class_create(self):
        params = \
            {
                'DryRun': True,
                'PeerOwnerId': 'peer_owner_id_test',
                'PeerVpcId': 'test_peering_connection_id',
                'VpcId': 'vpc_id_test',
                'PeerRegion': 'peer_region_test'
            }

        response = \
            {
                vpc_peering.VPC_PEERING_CONNECTION: {
                    'AccepterVpcInfo': {
                        'CidrBlock': 'cidr_block_test',
                        'Ipv6CidrBlockSet': [
                            {
                                'Ipv6CidrBlock': 'ip_6_cidr_block_test'
                            },
                        ],
                        'CidrBlockSet': [
                            {
                                'CidrBlock': 'cidr_block_test'
                            },
                        ],
                        'OwnerId': 'owner_id_test',
                        'VpcId': 'vpc_id_test',
                        'Region': 'region_test'
                    },
                    'RequesterVpcInfo': {
                        'CidrBlock': 'cidr_block_test',
                        'Ipv6CidrBlockSet': [
                            {
                                'Ipv6CidrBlock': 'ip_6_cidr_block_test'
                            },
                        ],
                        'CidrBlockSet': [
                            {
                                'CidrBlock': 'cidr_block_test'
                            },
                        ],
                        'OwnerId': 'owner_id_test',
                        'VpcId': 'vpc_id_test',
                        'Region': 'region_test'
                    },
                    'Status': {
                        'Code': 'test_status_code',
                        'Message': 'test_status_message'
                    },
                    'VpcPeeringConnectionId': 'test_peering_connection_id'
                },
            }

        self.vpc_peering.client = self.make_client_function(
            'create_vpc_peering_connection', return_value=response)

        self.assertEqual(self.vpc_peering.create(params), response)

    def test_class_delete(self):
        params = \
            {
                'DryRun': True,
                'VpcPeeringConnectionId': 'test_peering_connection_id',
            }

        response = {'Return': True, }
        self.vpc_peering.client = self.make_client_function(
            'delete_vpc_peering_connection', return_value=response)
        self.assertEqual(self.vpc_peering.delete(params), response)

    def test_class_accept(self):
        params = \
            {
                'DryRun': True,
                'VpcPeeringConnectionId': 'test_peering_connection_id',
            }

        response = {'Return': True, }
        self.vpc_peering.client = self.make_client_function(
            'accept_vpc_peering_connection', return_value=response)
        self.assertEqual(self.vpc_peering.accept(params), response)

    def test_class_reject(self):
        params = \
            {
                'DryRun': True,
                'VpcPeeringConnectionId': 'test_peering_connection_id',
            }

        response = {'Return': True, }
        self.vpc_peering.client = self.make_client_function(
            'reject_vpc_peering_connection', return_value=response)
        self.assertEqual(self.vpc_peering.reject(params), response)

    def test_class_update(self):
        params = {
            vpc_peering.ACCEPTER_VPC_PEERING_CONNECTION: {
                'AllowDnsResolutionFromRemoteVpc': True,
                'AllowEgressFromLocalClassicLinkToRemoteVpc': False,
                'AllowEgressFromLocalVpcToRemoteClassicLink': False,
            },
            vpc_peering.REQUESTER_VPC_PEERING_CONNECTION: {
                'AllowDnsResolutionFromRemoteVpc': True,
                'AllowEgressFromLocalClassicLinkToRemoteVpc': False,
                'AllowEgressFromLocalVpcToRemoteClassicLink': False,
            },

            vpc_peering.VPC_PEERING_CONNECTION_ID:
                'test_peering_connection_id',

        }

        response = \
            {
                vpc_peering.ACCEPTER_VPC_PEERING_CONNECTION: {
                    'AllowDnsResolutionFromRemoteVpc': True,
                    'AllowEgressFromLocalClassicLinkToRemoteVpc': False,
                    'AllowEgressFromLocalVpcToRemoteClassicLink': False
                },
                vpc_peering.REQUESTER_VPC_PEERING_CONNECTION: {
                    'AllowDnsResolutionFromRemoteVpc': True,
                    'AllowEgressFromLocalClassicLinkToRemoteVpc': False,
                    'AllowEgressFromLocalVpcToRemoteClassicLink': False
                }
            }

        self.vpc_peering.client = self.make_client_function(
            'modify_vpc_peering_connection_options', return_value=response)
        self.assertEqual(self.vpc_peering.update(params), response)

    def test_prepare(self):
        ctx = self.get_mock_ctx("EC2VpcPeering")
        iface = MagicMock()
        vpc_peering.prepare(ctx, {'foo': 'bar'}, iface)
        self.assertEqual(
            ctx.instance.runtime_properties['resource_config'],
            {'foo': 'bar'})

    def test_create(self):
        iface = MagicMock()
        ctx = self.get_mock_ctx("EC2VpcPeering")
        config = \
            {
                'DryRun': True,
                'PeerVpcId': 'peer_vpc_id_test',
                'VpcId': 'vpc_id_test',
                'PeerRegion': 'peer_region_test'
            }

        response = \
            {
                vpc_peering.VPC_PEERING_CONNECTION: {
                    'AccepterVpcInfo': {
                        'CidrBlock': 'cidr_block_test',
                        'Ipv6CidrBlockSet': [
                            {
                                'Ipv6CidrBlock': 'ip_6_cidr_block_test'
                            },
                        ],
                        'CidrBlockSet': [
                            {
                                'CidrBlock': 'cidr_block_test'
                            },
                        ],
                        'OwnerId': 'owner_id_test',
                        'VpcId': 'vpc_id_test',
                        'Region': 'region_test'
                    },
                    'RequesterVpcInfo': {
                        'CidrBlock': 'cidr_block_test',
                        'Ipv6CidrBlockSet': [
                            {
                                'Ipv6CidrBlock': 'ip_6_cidr_block_test'
                            },
                        ],
                        'CidrBlockSet': [
                            {
                                'CidrBlock': 'cidr_block_test'
                            },
                        ],
                        'OwnerId': 'owner_id_test',
                        'VpcId': 'vpc_id_test',
                        'Region': 'region_test'
                    },
                    'Status': {
                        'Code': 'test_status_code',
                        'Message': 'test_status_message'
                    },
                    'VpcPeeringConnectionId': 'test_peering_connection_id'
                },
            }

        ctx.instance.runtime_properties['resource_config'] = config
        iface.create = self.mock_return(response)
        vpc_peering.create(ctx=ctx, iface=iface, resource_config=config)
        self.assertEqual(
            ctx.instance.runtime_properties[constants.EXTERNAL_RESOURCE_ID],
            'test_peering_connection_id'
        )

    def test_modify(self):
        iface = MagicMock()
        ctx = self.get_mock_ctx("EC2VpcPeering")
        config = {
            vpc_peering.ACCEPTER_VPC_PEERING_CONNECTION: {
                'AllowDnsResolutionFromRemoteVpc': True,
                'AllowEgressFromLocalClassicLinkToRemoteVpc': False,
                'AllowEgressFromLocalVpcToRemoteClassicLink': False,
            },
            vpc_peering.REQUESTER_VPC_PEERING_CONNECTION: {
                'AllowDnsResolutionFromRemoteVpc': True,
                'AllowEgressFromLocalClassicLinkToRemoteVpc': False,
                'AllowEgressFromLocalVpcToRemoteClassicLink': False,
            },
        }

        ctx.instance.runtime_properties[constants.EXTERNAL_RESOURCE_ID] =\
            'test_peering_connection_id'

        response = \
            {
                vpc_peering.ACCEPTER_VPC_PEERING_CONNECTION: {
                    'AllowDnsResolutionFromRemoteVpc': True,
                    'AllowEgressFromLocalClassicLinkToRemoteVpc': False,
                    'AllowEgressFromLocalVpcToRemoteClassicLink': False
                },
                vpc_peering.REQUESTER_VPC_PEERING_CONNECTION: {
                    'AllowDnsResolutionFromRemoteVpc': True,
                    'AllowEgressFromLocalClassicLinkToRemoteVpc': False,
                    'AllowEgressFromLocalVpcToRemoteClassicLink': False
                }
            }

        iface.update = self.mock_return(response)
        vpc_peering.modify(ctx, iface, config)
        self.assertTrue(iface.update.called)

    def test_delete(self):
        iface = MagicMock()
        ctx = self.get_mock_ctx("EC2VpcPeering")
        ctx.instance.runtime_properties[constants.EXTERNAL_RESOURCE_ID]\
            = 'test_peering_connection_id'
        vpc_peering.delete(ctx=ctx, iface=iface, resource_config={})
        self.assertTrue(iface.delete.called)

    def test_accept(self):
        iface = MagicMock()
        ctx = self.get_mock_ctx("EC2VpcPeering")
        config = \
            {
                'DryRun': True,
                'VpcPeeringConnectionId': 'test_peering_connection_id',
            }

        response = {'Return': True, }
        iface.accept = self.mock_return(response)
        vpc_peering.accept(ctx, iface, config)
        self.assertEqual(
            ctx.instance.runtime_properties[constants.EXTERNAL_RESOURCE_ID],
            'test_peering_connection_id'
        )

    def test_reject(self):
        iface = MagicMock()
        ctx = self.get_mock_ctx("EC2VpcPeering")
        config = \
            {
                'DryRun': True,
                'VpcPeeringConnectionId': 'test_peering_connection_id',
            }

        response = {'Return': True, }
        iface.reject = self.mock_return(response)
        vpc_peering.reject(ctx, iface, config)
        self.assertEqual(
            ctx.instance.runtime_properties[constants.EXTERNAL_RESOURCE_ID],
            'test_peering_connection_id'
        )


if __name__ == '__main__':
    unittest.main()

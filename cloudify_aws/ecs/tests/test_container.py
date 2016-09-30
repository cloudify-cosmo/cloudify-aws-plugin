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

# Stdlib imports

# Third party imports
import testtools
from mock import Mock

# Cloudify imports
from cloudify.exceptions import NonRecoverableError

# This package imports
from cloudify_aws.ecs import container
from cloudify_aws.ecs.tests import make_node_context


class TestContainer(testtools.TestCase):

    def setUp(self):
        super(TestContainer, self).setUp()

    def test_is_ip_address_ipv4(self):
        self.assertTrue(container._is_ip_address('127.0.0.1'))

    def test_is_ip_address_fail_ipv4_truncated(self):
        self.assertFalse(container._is_ip_address('127.1'))

    def test_is_ip_address_ipv6(self):
        self.assertTrue(container._is_ip_address('::1'))

    def test_is_ip_address_fail_arbitrary_string(self):
        self.assertFalse(container._is_ip_address('test'))

    def test_validate_not_enough_memory(self):
        memory = 3

        ctx = make_node_context(
            Mock(),
            node='ECSContainer',
            properties={'memory': memory},
        )

        self.assertRaises(
            NonRecoverableError,
            container.validate,
            ctx,
        )

    def test_validate_enough_memory(self):
        memory = 4

        ctx = make_node_context(
            Mock(),
            node='ECSContainer',
            properties={'memory': memory},
        )

        self.assertTrue(container.validate(ctx))

    def test_validate_too_many_tcp_mappings(self):
        tcp_port_mappings = {
            i: i
            # Use a range that doesn't contain reserved ports
            for i in range(6500, 6601)
        }

        ctx = make_node_context(
            Mock(),
            node='ECSContainer',
            properties={
                'memory': 4,
                'tcp_port_mappings': tcp_port_mappings,
            },
        )

        self.assertRaises(
            NonRecoverableError,
            container.validate,
            ctx,
        )

    def test_validate_too_many_udp_mappings(self):
        udp_port_mappings = {
            i: i
            # Use a range that doesn't contain reserved ports
            for i in range(6500, 6601)
        }

        ctx = make_node_context(
            Mock(),
            node='ECSContainer',
            properties={
                'memory': 4,
                'udp_port_mappings': udp_port_mappings,
            },
        )

        self.assertRaises(
            NonRecoverableError,
            container.validate,
            ctx,
        )

    def test_validate_too_many_tcp_and_udp_mappings(self):
        tcp_port_mappings = {
            i: i
            # Use a range that doesn't contain reserved ports
            for i in range(6500, 6550)
        }

        udp_port_mappings = {
            i: i
            # Use a range that doesn't contain reserved ports
            for i in range(6550, 6601)
        }

        ctx = make_node_context(
            Mock(),
            node='ECSContainer',
            properties={
                'memory': 4,
                'tcp_port_mappings': tcp_port_mappings,
                'udp_port_mappings': udp_port_mappings,
            },
        )

        self.assertRaises(
            NonRecoverableError,
            container.validate,
            ctx,
        )

    def test_validate_non_integer_tcp_mapping_key(self):
        tcp_port_mappings = {
            'test': 6500,
        }

        ctx = make_node_context(
            Mock(),
            node='ECSContainer',
            properties={
                'memory': 4,
                'tcp_port_mappings': tcp_port_mappings,
            },
        )

        self.assertRaises(
            NonRecoverableError,
            container.validate,
            ctx,
        )

    def test_validate_non_integer_tcp_mapping_value(self):
        tcp_port_mappings = {
            6500: 'test',
        }

        ctx = make_node_context(
            Mock(),
            node='ECSContainer',
            properties={
                'memory': 4,
                'tcp_port_mappings': tcp_port_mappings,
            },
        )

        self.assertRaises(
            NonRecoverableError,
            container.validate,
            ctx,
        )

    def test_validate_non_integer_udp_mapping_key(self):
        udp_port_mappings = {
            'test': 6500,
        }

        ctx = make_node_context(
            Mock(),
            node='ECSContainer',
            properties={
                'memory': 4,
                'udp_port_mappings': udp_port_mappings,
            },
        )

        self.assertRaises(
            NonRecoverableError,
            container.validate,
            ctx,
        )

    def test_validate_non_integer_udp_mapping_value(self):
        udp_port_mappings = {
            6500: 'test',
        }

        ctx = make_node_context(
            Mock(),
            node='ECSContainer',
            properties={
                'memory': 4,
                'udp_port_mappings': udp_port_mappings,
            },
        )

        self.assertRaises(
            NonRecoverableError,
            container.validate,
            ctx,
        )

    def test_validate_no_restricted_port_tcp_keys_allowed(self):
        for port in container.RESTRICTED_PORTS:
            tcp_port_mappings = {
                port: 6500,
            }

            ctx = make_node_context(
                Mock(),
                node='ECSContainer',
                properties={
                    'memory': 4,
                    'tcp_port_mappings': tcp_port_mappings,
                },
            )

            self.assertRaises(
                NonRecoverableError,
                container.validate,
                ctx,
            )

    def test_validate_no_restricted_port_udp_keys_allowed(self):
        for port in container.RESTRICTED_PORTS:
            udp_port_mappings = {
                port: 6500,
            }

            ctx = make_node_context(
                Mock(),
                node='ECSContainer',
                properties={
                    'memory': 4,
                    'udp_port_mappings': udp_port_mappings,
                },
            )

            self.assertRaises(
                NonRecoverableError,
                container.validate,
                ctx,
            )

    def test_validate_tcp_mapping_key_minimum_port(self):
        tcp_port_mappings = {
            1: 6500,
        }

        ctx = make_node_context(
            Mock(),
            node='ECSContainer',
            properties={
                'memory': 4,
                'tcp_port_mappings': tcp_port_mappings,
            },
        )

        self.assertTrue(container.validate(ctx))

    def test_validate_tcp_mapping_key_below_minimum_port(self):
        tcp_port_mappings = {
            0: 6500,
        }

        ctx = make_node_context(
            Mock(),
            node='ECSContainer',
            properties={
                'memory': 4,
                'tcp_port_mappings': tcp_port_mappings,
            },
        )

        self.assertRaises(
            NonRecoverableError,
            container.validate,
            ctx,
        )

    def test_validate_tcp_mapping_value_minimum_port(self):
        tcp_port_mappings = {
            6500: 1,
        }

        ctx = make_node_context(
            Mock(),
            node='ECSContainer',
            properties={
                'memory': 4,
                'tcp_port_mappings': tcp_port_mappings,
            },
        )

        self.assertTrue(container.validate(ctx))

    def test_validate_tcp_mapping_value_below_minimum_port(self):
        tcp_port_mappings = {
            6500: 0,
        }

        ctx = make_node_context(
            Mock(),
            node='ECSContainer',
            properties={
                'memory': 4,
                'tcp_port_mappings': tcp_port_mappings,
            },
        )

        self.assertRaises(
            NonRecoverableError,
            container.validate,
            ctx,
        )

    def test_validate_tcp_mapping_key_maximum_port(self):
        tcp_port_mappings = {
            65535: 6500,
        }

        ctx = make_node_context(
            Mock(),
            node='ECSContainer',
            properties={
                'memory': 4,
                'tcp_port_mappings': tcp_port_mappings,
            },
        )

        self.assertTrue(container.validate(ctx))

    def test_validate_tcp_mapping_key_above_maximum_port(self):
        tcp_port_mappings = {
            65536: 6500,
        }

        ctx = make_node_context(
            Mock(),
            node='ECSContainer',
            properties={
                'memory': 4,
                'tcp_port_mappings': tcp_port_mappings,
            },
        )

        self.assertRaises(
            NonRecoverableError,
            container.validate,
            ctx,
        )

    def test_validate_tcp_mapping_value_maximum_port(self):
        tcp_port_mappings = {
            6500: 65535,
        }

        ctx = make_node_context(
            Mock(),
            node='ECSContainer',
            properties={
                'memory': 4,
                'tcp_port_mappings': tcp_port_mappings,
            },
        )

        self.assertTrue(container.validate(ctx))

    def test_validate_tcp_mapping_value_above_maximum_port(self):
        tcp_port_mappings = {
            6500: 65536,
        }

        ctx = make_node_context(
            Mock(),
            node='ECSContainer',
            properties={
                'memory': 4,
                'tcp_port_mappings': tcp_port_mappings,
            },
        )

        self.assertRaises(
            NonRecoverableError,
            container.validate,
            ctx,
        )

    def test_validate_udp_mapping_key_minimum_port(self):
        udp_port_mappings = {
            1: 6500,
        }

        ctx = make_node_context(
            Mock(),
            node='ECSContainer',
            properties={
                'memory': 4,
                'udp_port_mappings': udp_port_mappings,
            },
        )

        self.assertTrue(container.validate(ctx))

    def test_validate_udp_mapping_key_below_minimum_port(self):
        udp_port_mappings = {
            0: 6500,
        }

        ctx = make_node_context(
            Mock(),
            node='ECSContainer',
            properties={
                'memory': 4,
                'udp_port_mappings': udp_port_mappings,
            },
        )

        self.assertRaises(
            NonRecoverableError,
            container.validate,
            ctx,
        )

    def test_validate_udp_mapping_value_minimum_port(self):
        udp_port_mappings = {
            6500: 1,
        }

        ctx = make_node_context(
            Mock(),
            node='ECSContainer',
            properties={
                'memory': 4,
                'udp_port_mappings': udp_port_mappings,
            },
        )

        self.assertTrue(container.validate(ctx))

    def test_validate_udp_mapping_value_below_minimum_port(self):
        udp_port_mappings = {
            6500: 0,
        }

        ctx = make_node_context(
            Mock(),
            node='ECSContainer',
            properties={
                'memory': 4,
                'udp_port_mappings': udp_port_mappings,
            },
        )

        self.assertRaises(
            NonRecoverableError,
            container.validate,
            ctx,
        )

    def test_validate_udp_mapping_key_maximum_port(self):
        udp_port_mappings = {
            65535: 6500,
        }

        ctx = make_node_context(
            Mock(),
            node='ECSContainer',
            properties={
                'memory': 4,
                'udp_port_mappings': udp_port_mappings,
            },
        )

        self.assertTrue(container.validate(ctx))

    def test_validate_udp_mapping_key_above_maximum_port(self):
        udp_port_mappings = {
            65536: 6500,
        }

        ctx = make_node_context(
            Mock(),
            node='ECSContainer',
            properties={
                'memory': 4,
                'udp_port_mappings': udp_port_mappings,
            },
        )

        self.assertRaises(
            NonRecoverableError,
            container.validate,
            ctx,
        )

    def test_validate_udp_mapping_value_maximum_port(self):
        udp_port_mappings = {
            6500: 65535,
        }

        ctx = make_node_context(
            Mock(),
            node='ECSContainer',
            properties={
                'memory': 4,
                'udp_port_mappings': udp_port_mappings,
            },
        )

        self.assertTrue(container.validate(ctx))

    def test_validate_udp_mapping_value_above_maximum_port(self):
        udp_port_mappings = {
            6500: 65536,
        }

        ctx = make_node_context(
            Mock(),
            node='ECSContainer',
            properties={
                'memory': 4,
                'udp_port_mappings': udp_port_mappings,
            },
        )

        self.assertRaises(
            NonRecoverableError,
            container.validate,
            ctx,
        )

    def test_validate_valid_link(self):
        links = [
            'test:yes',
        ]

        ctx = make_node_context(
            Mock(),
            node='ECSContainer',
            properties={
                'memory': 4,
                'links': links,
            },
        )

        self.assertTrue(container.validate(ctx))

    def test_validate_invalid_link_no_colon(self):
        links = [
            'testyes',
        ]

        ctx = make_node_context(
            Mock(),
            node='ECSContainer',
            properties={
                'memory': 4,
                'links': links,
            },
        )

        self.assertRaises(
            NonRecoverableError,
            container.validate,
            ctx,
        )

    def test_validate_invalid_link_multiple_colons(self):
        links = [
            'test:yes:no',
        ]

        ctx = make_node_context(
            Mock(),
            node='ECSContainer',
            properties={
                'memory': 4,
                'links': links,
            },
        )

        self.assertRaises(
            NonRecoverableError,
            container.validate,
            ctx,
        )

    def test_validate_valid_dns_servers(self):
        dns_servers = [
            '192.0.2.10',
            '192.0.2.138',
            '2001:db8::10',
            '2001:db8::1:10',
        ]

        ctx = make_node_context(
            Mock(),
            node='ECSContainer',
            properties={
                'memory': 4,
                'dns_servers': dns_servers,
            },
        )

        self.assertTrue(container.validate(ctx))

    def test_validate_invalid_dns_server(self):
        dns_servers = [
            '192.0.2.10',
            '192.0.2.138',
            '2001:db8::10',
            '2001:db8::1:10',
            'modern english',
        ]

        ctx = make_node_context(
            Mock(),
            node='ECSContainer',
            properties={
                'memory': 4,
                'dns_servers': dns_servers,
            },
        )

        self.assertRaises(
            NonRecoverableError,
            container.validate,
            ctx,
        )

    def test_validate_valid_extra_hosts_entries(self):
        extra_hosts_entries = {
            'myserver': '192.0.2.50',
            'myserver6': '2001:db8::56',
        }

        ctx = make_node_context(
            Mock(),
            node='ECSContainer',
            properties={
                'memory': 4,
                'extra_hosts_entries': extra_hosts_entries,
            },
        )

        self.assertTrue(container.validate(ctx))

    def test_validate_invalid_extra_hosts_entries(self):
        extra_hosts_entries = {
            'myserver': '192.0.2.50',
            'myserver6': '2001:db8::56',
            'myserverwrong': 'flock of seagulls',
        }

        ctx = make_node_context(
            Mock(),
            node='ECSContainer',
            properties={
                'memory': 4,
                'extra_hosts_entries': extra_hosts_entries,
            },
        )

        self.assertRaises(
            NonRecoverableError,
            container.validate,
            ctx,
        )

    def test_validate_non_list_mount_points_fails(self):
        mount_points = 'something'

        ctx = make_node_context(
            Mock(),
            node='ECSContainer',
            properties={
                'memory': 4,
                'mount_points': mount_points,
            },
        )

        self.assertRaises(
            NonRecoverableError,
            container.validate,
            ctx,
        )

    def test_validate_valid_mount_points(self):
        mount_points = [
            {
                'sourceVolume': 'yes',
                'containerPath': 'no',
                'readOnly': False,
            },
        ]

        ctx = make_node_context(
            Mock(),
            node='ECSContainer',
            properties={
                'memory': 4,
                'mount_points': mount_points,
            },
        )

        self.assertTrue(container.validate(ctx))

    def test_validate_mount_points_non_bool_readonly(self):
        mount_points = [
            {
                'sourceVolume': 'yes',
                'containerPath': 'no',
                'readOnly': 0,
            },
        ]

        ctx = make_node_context(
            Mock(),
            node='ECSContainer',
            properties={
                'memory': 4,
                'mount_points': mount_points,
            },
        )

        self.assertRaises(
            NonRecoverableError,
            container.validate,
            ctx,
        )

    def test_validate_mount_points_extra_attribute(self):
        mount_points = [
            {
                'sourceVolume': 'yes',
                'containerPath': 'no',
                'readOnly': False,
                'something': 'else',
            },
        ]

        ctx = make_node_context(
            Mock(),
            node='ECSContainer',
            properties={
                'memory': 4,
                'mount_points': mount_points,
            },
        )

        self.assertRaises(
            NonRecoverableError,
            container.validate,
            ctx,
        )

    def test_validate_mount_points_missing_attribute(self):
        mount_points = [
            {
                'sourceVolume': 'yes',
                'containerPath': 'no',
            },
        ]

        ctx = make_node_context(
            Mock(),
            node='ECSContainer',
            properties={
                'memory': 4,
                'mount_points': mount_points,
            },
        )

        self.assertRaises(
            NonRecoverableError,
            container.validate,
            ctx,
        )

    def test_validate_non_list_volumes_from_fails(self):
        volumes_from = 'something'

        ctx = make_node_context(
            Mock(),
            node='ECSContainer',
            properties={
                'memory': 4,
                'volumes_from': volumes_from,
            },
        )

        self.assertRaises(
            NonRecoverableError,
            container.validate,
            ctx,
        )

    def test_validate_valid_volumes_from(self):
        volumes_from = [
            {
                'sourceContainer': 'yes',
                'readOnly': False,
            },
        ]

        ctx = make_node_context(
            Mock(),
            node='ECSContainer',
            properties={
                'memory': 4,
                'volumes_from': volumes_from,
            },
        )

        self.assertTrue(container.validate(ctx))

    def test_validate_volumes_non_bool_readonly(self):
        volumes_from = [
            {
                'sourceContainer': 'yes',
                'readOnly': 1,
            },
        ]

        ctx = make_node_context(
            Mock(),
            node='ECSContainer',
            properties={
                'memory': 4,
                'volumes_from': volumes_from,
            },
        )

        self.assertRaises(
            NonRecoverableError,
            container.validate,
            ctx,
        )

    def test_validate_volumes_from_extra_attribute(self):
        volumes_from = [
            {
                'sourceContainer': 'yes',
                'readOnly': False,
                'other': 'invalid',
            },
        ]

        ctx = make_node_context(
            Mock(),
            node='ECSContainer',
            properties={
                'memory': 4,
                'volumes_from': volumes_from,
            },
        )

        self.assertRaises(
            NonRecoverableError,
            container.validate,
            ctx,
        )

    def test_validate_volumes_from_missing_attribute(self):
        volumes_from = [
            {
                'readOnly': False,
            },
        ]

        ctx = make_node_context(
            Mock(),
            node='ECSContainer',
            properties={
                'memory': 4,
                'volumes_from': volumes_from,
            },
        )

        self.assertRaises(
            NonRecoverableError,
            container.validate,
            ctx,
        )

    def test_validate_non_list_ulimits_fails(self):
        ulimits = 'something'

        ctx = make_node_context(
            Mock(),
            node='ECSContainer',
            properties={
                'memory': 4,
                'ulimits': ulimits,
            },
        )

        self.assertRaises(
            NonRecoverableError,
            container.validate,
            ctx,
        )

    def test_validate_valid_ulimits(self):
        ulimits = [
            {
                'name': 'cpu',
                'softLimit': 1,
                'hardLimit': 20,
            },
        ]

        ctx = make_node_context(
            Mock(),
            node='ECSContainer',
            properties={
                'memory': 4,
                'ulimits': ulimits,
            },
        )

        self.assertTrue(container.validate(ctx))

    def test_validate_ulimits_non_int_softlimit(self):
        ulimits = [
            {
                'name': 'cpu',
                'softLimit': True,
                'hardLimit': 20,
            },
        ]

        ctx = make_node_context(
            Mock(),
            node='ECSContainer',
            properties={
                'memory': 4,
                'ulimits': ulimits,
            },
        )

        self.assertRaises(
            NonRecoverableError,
            container.validate,
            ctx,
        )

    def test_validate_ulimits_non_int_hardlimit(self):
        ulimits = [
            {
                'name': 'cpu',
                'softLimit': 10,
                'hardLimit': "20",
            },
        ]

        ctx = make_node_context(
            Mock(),
            node='ECSContainer',
            properties={
                'memory': 4,
                'ulimits': ulimits,
            },
        )

        self.assertRaises(
            NonRecoverableError,
            container.validate,
            ctx,
        )

    def test_validate_ulimits_extra_attribute(self):
        ulimits = [
            {
                'name': 'cpu',
                'softLimit': 10,
                'hardLimit': 20,
                'more': 'attributes',
            },
        ]

        ctx = make_node_context(
            Mock(),
            node='ECSContainer',
            properties={
                'memory': 4,
                'ulimits': ulimits,
            },
        )

        self.assertRaises(
            NonRecoverableError,
            container.validate,
            ctx,
        )

    def test_validate_ulimits_missing_attribute(self):
        ulimits = [
            {
                'name': 'cpu',
                'softLimit': 10,
            },
        ]

        ctx = make_node_context(
            Mock(),
            node='ECSContainer',
            properties={
                'memory': 4,
                'ulimits': ulimits,
            },
        )

        self.assertRaises(
            NonRecoverableError,
            container.validate,
            ctx,
        )

    def test_validate_ulimits_invalid_limit_name(self):
        ulimits = [
            {
                'name': 'not_a_valid_ulimit',
                'softLimit': 10,
                'hardLimit': 20,
            },
        ]

        ctx = make_node_context(
            Mock(),
            node='ECSContainer',
            properties={
                'memory': 4,
                'ulimits': ulimits,
            },
        )

        self.assertRaises(
            NonRecoverableError,
            container.validate,
            ctx,
        )

    def test_validate_valid_log_driver(self):
        log_driver = 'syslog'

        ctx = make_node_context(
            Mock(),
            node='ECSContainer',
            properties={
                'memory': 4,
                'log_driver': log_driver,
            },
        )

        self.assertTrue(container.validate(ctx))

    def test_validate_invalid_log_driver(self):
        log_driver = 'not_a_valid_log_driver'

        ctx = make_node_context(
            Mock(),
            node='ECSContainer',
            properties={
                'memory': 4,
                'log_driver': log_driver,
            },
        )

        self.assertRaises(
            NonRecoverableError,
            container.validate,
            ctx,
        )

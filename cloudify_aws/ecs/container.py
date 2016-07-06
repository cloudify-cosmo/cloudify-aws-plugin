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
import socket

# Third party imports

# Cloudify imports
from cloudify.decorators import operation
from cloudify.exceptions import NonRecoverableError

# This package imports


# These ports are not allowed to be mapped on a container instance (host)
# per AWS documentation
RESTRICTED_PORTS = (22, 2375, 2376, 51678)

# Allowed ulimits are specified in AWS documentation
VALID_ULIMITS = [
    'core',
    'cpu',
    'data',
    'fsize',
    'locks',
    'memlock',
    'msgqueue',
    'nice',
    'nofile',
    'nproc',
    'rss',
    'rtprio',
    'rttime',
    'sigpending',
    'stack',
]

# Log drivers are listed in AWS documentation
VALID_LOG_DRIVERS = [
    'json-file',
    'syslog',
    'journald',
    'gelf',
    'fluentd',
    'awslogs',
]


def _is_ip_address(candidate):
    ip_address = False
    try:
        socket.inet_pton(socket.AF_INET, candidate)
        ip_address = True
    except socket.error:
        # Not IPv4
        pass
    try:
        socket.inet_pton(socket.AF_INET6, candidate)
        ip_address = True
    except socket.error:
        # Not IPv6
        pass
    return ip_address


# Note: Not currently using an AWSBaseNode derived class as this takes no
# direct action on the platform but is instead used to construct the
# container, etc, and is split out to make the blueprints nicer
@operation
def validate(ctx):
    # Check properties are valid
    if ctx.node.properties['memory'] < 4:
        raise NonRecoverableError(
            'ECSContainers must have at least 4MB of RAM assigned.'
        )

    tcp_port_mappings = ctx.node.properties['tcp_port_mappings']
    udp_port_mappings = ctx.node.properties['udp_port_mappings']
    # Check port mappings
    if len(tcp_port_mappings) + len(udp_port_mappings) > 100:
        raise NonRecoverableError(
            'At most 100 TCP and UDP port mappings may be specified.'
        )
    for port_mappings, proto in ((tcp_port_mappings, 'tcp'),
                                 (udp_port_mappings, 'udp')):
        for host, container in port_mappings.items():
            try:
                container = int(container)
                host = int(host)
            except ValueError:
                raise NonRecoverableError(
                    'A parameter specified in {proto}_port_mappings could '
                    'not be interpreted as an integer. Error occurred in: '
                    '{container}:{host}'.format(
                        proto=proto,
                        container=container,
                        host=host,
                    )
                )

            valid = False
            if (
                1 <= container <= 65535 and
                1 <= host <= 65535 and
                host not in RESTRICTED_PORTS
            ):
                valid = True

            if not valid:
                raise NonRecoverableError(
                    'A port mapping in {proto}_port_mappings did not '
                    'refer to a valid port. Valid ports are between '
                    '1 and 65535, and host ports may not be in the '
                    'restricted ports list ( '
                    '{restricted_ports} ). Error occurred in mapping : '
                    '{container}: {host}'.format(
                        proto=proto,
                        restricted_ports=','.join([
                            str(port) for port in RESTRICTED_PORTS
                        ]),
                        container=container,
                        host=host,
                    )
                )

    for link in ctx.node.properties['links']:
        if len(link.split(':')) != 2:
            raise NonRecoverableError(
                'links must be specified as a list of strings in the form '
                '<name>:<alias>. There should be no other : in the line. '
                '{link} was invalid.'.format(link=link)
            )

    for server in ctx.node.properties['dns_servers']:
        if not _is_ip_address(server):
            raise NonRecoverableError(
                'dns_servers must be a list of IP addresses. '
                '{server} does not appear to be an IP address.'.format(
                    server=server,
                )
            )

    for hostname, ip in ctx.node.properties['extra_hosts_entries'].items():
        if not _is_ip_address(ip):
            raise NonRecoverableError(
                'extra_hosts_entries must be a dictionary mapping host names '
                'to IPs. "{host}: {ip}" does not map to a valid IP '
                'address.'.format(
                    host=hostname,
                    ip=ip,
                )
            )

    for prop in ('mount_points', 'volumes_from', 'ulimits'):
        for entry in ctx.node.properties[prop]:
            if not isinstance(entry, dict):
                raise NonRecoverableError(
                    '{prop} must be a list of dictionaries'.format(
                        prop=prop,
                    )
                )
            problems = []
            keys = set(entry.keys())
            if prop == 'mount_points':
                expected_keys = [
                    'sourceVolume',
                    'containerPath',
                    'readOnly',
                ]
            elif prop == 'volumes_from':
                expected_keys = [
                    'sourceContainer',
                    'readOnly',
                ]
            elif prop == 'ulimits':
                expected_keys = [
                    'name',
                    'softLimit',
                    'hardLimit',
                ]
            expected_keys = set(expected_keys)
            missing_keys = expected_keys - keys
            extra_keys = keys - expected_keys
            for key in missing_keys:
                problems.append('missing {key} key'.format(key=key))
            for key in extra_keys:
                problems.append('found unknown key {key}'.format(key=key))
            if prop == 'ulimits':
                if 'name' in keys and entry['name'] not in VALID_ULIMITS:
                    problems.append(
                        'ulimit name must be one of {valid}'.format(
                            valid=','.join(VALID_ULIMITS)
                        )
                    )
                for limit in 'softLimit', 'hardLimit':
                    if limit in keys:
                        value = entry[limit]
                        if not (
                            isinstance(value, int) and
                            not isinstance(value, bool)
                        ):
                            problems.append(
                                '{limit} must be an integer'.format(
                                    limit=limit,
                                )
                            )
            if 'readOnly' in keys:
                if not isinstance(entry['readOnly'], bool):
                    problems.append(
                        'readOnly key must be true or false (boolean), but '
                        'was set to {value}'.format(value=entry['readOnly'])
                    )
            if problems:
                raise NonRecoverableError(
                    'Bad entry found in {section}: {problems}'.format(
                        section=prop,
                        problems=';'.join(problems),
                    )
                )

    if ctx.node.properties['log_driver'] != '':
        if ctx.node.properties['log_driver'] not in VALID_LOG_DRIVERS:
            raise NonRecoverableError(
                'log_driver must be one of {valid}'.format(
                    valid=VALID_LOG_DRIVERS,
                )
            )

    return True

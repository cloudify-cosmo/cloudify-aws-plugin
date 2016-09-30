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

# Cloudify imports
from cloudify import ctx
from cloudify.decorators import operation
from cloudify.exceptions import NonRecoverableError

# This package imports
from cloudify_aws import constants, utils
from cloudify_aws.base import AwsBaseNode
from cloudify_aws.connection import EC2ConnectionClient


@operation
def create(args=None, **_):
    return Task().created(args)


@operation
def delete(args=None, **_):
    return Task().deleted(args)


class Task(AwsBaseNode):
    def __init__(self, client=None):
        client = client or EC2ConnectionClient().client3('ecs')
        super(Task, self).__init__(
            constants.ECS_TASK['AWS_RESOURCE_TYPE'],
            constants.ECS_TASK['REQUIRED_PROPERTIES'],
            client=client,
            resource_id_key=constants.ECS_TASK['RESOURCE_ID_KEY'],
        )
        self.not_found_error = constants.ECS_TASK['NOT_FOUND_ERROR']
        if self.is_external_resource:
            ctx.instance.runtime_properties[constants.EXTERNAL_RESOURCE_ID] = (
                ctx.node.properties['name']
            )

    def get_resource(self):
        clusters = self.execute(
            self.client.list_clusters,
        ).get('clusterArns', [])

        tasks = []

        for cluster in clusters:
            tasks.extend(self.execute(
                self.client.list_tasks,
                {
                    'cluster': cluster,
                    'family': ctx.node.properties['name'],
                },
            ).get('taskArns', []))

        return tasks

    def get_appropriate_relationship_targets(
        self,
        relationships,
        target_relationship,
        target_node,
    ):
        results = []
        for relationship in relationships:
            if relationship.type == target_relationship:
                if relationship.target.node.type == target_node:
                    results.append(relationship.target.node)
                else:
                    raise NonRecoverableError(
                        '{rel} may only be made against nodes of type '
                        '{correct}, but was made against node type '
                        '{actual}'.format(
                            rel=target_relationship,
                            correct=target_node,
                            actual=relationship.target.node.type,
                        )
                    )
        return results

    def construct_volume_definitions(self):
        volumes = self.get_appropriate_relationship_targets(
            relationships=ctx.instance.relationships,
            target_relationship=constants.VOLUME_TASK_RELATIONSHIP,
            target_node='cloudify.aws.nodes.ECSVolume',
        )

        return [
            {'name': volume.properties['name']}
            for volume in volumes
        ]

    def construct_container_definitions(self):
        containers = self.get_appropriate_relationship_targets(
            relationships=ctx.instance.relationships,
            target_relationship=constants.CONTAINER_TASK_RELATIONSHIP,
            target_node='cloudify.aws.nodes.ECSContainer',
        )

        container_definitions = []

        for container in containers:
            props = container.properties

            definition = {
                'name': props['name'],
                'image': props['image'],
                'memory': props['memory'],
            }

            # We will trust the container node to have validated itself
            # We will, however, take pains not to include any parameters that
            # have not been set, and instead let AWS defaults rule in those
            # cases

            # Set up port mappings
            tcp_mappings = props['tcp_port_mappings']
            udp_mappings = props['udp_port_mappings']
            port_mappings = [
                {
                    'containerPort': int(container_port),
                    'hostPort': int(host_port),
                    'protocol': 'tcp',
                }
                for host_port, container_port in tcp_mappings.items()
            ]
            port_mappings.extend([
                {
                    'containerPort': int(container_port),
                    'hostPort': int(host_port),
                    'protocol': 'udp',
                }
                for host_port, container_port in udp_mappings.items()
            ])
            if len(port_mappings) > 0:
                definition['portMappings'] = port_mappings

            # Using -1 as 'not set'
            if props['cpu_units'] > -1:
                definition['cpu'] = props['cpu_units']

            definition['essential'] = props['essential']

            if props['entrypoint'] != []:
                definition['entryPoint'] = props['entrypoint']

            if props['command'] != []:
                definition['command'] = props['command']

            if props['workdir'] != '':
                definition['workingDirectory'] = props['workdir']

            if len(props['env_vars']) > 0:
                definition['environment'] = [
                    {
                        'name': name,
                        'value': value,
                    }
                    for name, value in props['env_vars'].items()
                ]

            if props['disable_networking'] is not None:
                definition['disableNetworking'] = props['disable_networking']

            if len(props['links']) > 0:
                definition['links'] = props['links']

            if props['hostname'] != '':
                definition['hostname'] = props['hostname']

            if len(props['dns_servers']) > 0:
                definition['dnsServers'] = props['dns_servers']

            if len(props['dns_search_domains']) > 0:
                definition['dnsSearchDomains'] = props['dns_search_domains']

            if len(props['extra_hosts_entries']) > 0:
                definition['extraHosts'] = [
                    {
                        'hostname': host,
                        'ipAddress': ip,
                    }
                    for host, ip in props['extra_hosts_entries'].items()
                ]

            definition['readonlyRootFilesystem'] = (
                props['read_only_root_filesystem']
            )

            if len(props['mount_points']) > 0:
                definition['mountPoints'] = props['mount_points']

            if len(props['volumes_from']) > 0:
                definition['volumesFrom'] = props['volumes_from']

            if props['log_driver'] != '':
                definition['logConfiguration'] = {
                    'logDriver': props['log_driver'],
                }
                if len(props['log_driver_options']) > 0:
                    definition['logConfiguration']['options'] = (
                        props['log_driver_options']
                    )

            definition['privileged'] = props['privileged']

            if props['user'] != '':
                definition['username'] = props['user']

            if len(props['security_options']) > 0:
                definition['dockerSecurityOptions'] = props['security_options']

            if len(props['ulimits']) > 0:
                definition['ulimits'] = props['ulimits']

            if len(props['docker_labels']) > 0:
                definition['dockerLabels'] = props['docker_labels']

            container_definitions.append(definition)

        return container_definitions

    def _generate_creation_args(self):
        containers = self.construct_container_definitions()

        ctx.instance.runtime_properties['container_names'] = [
            container['name'] for container in containers
        ]

        volumes = self.construct_volume_definitions()

        task_definition = {
            'family': ctx.node.properties['name'],
            'containerDefinitions': containers,
            'volumes': volumes,
        }
        return task_definition

    def create(self, args=None):
        create_args = utils.update_args(self._generate_creation_args(),
                                        args)

        result = self.execute(
            self.client.register_task_definition,
            create_args,
        )

        self.resource_id = result['taskDefinition']['taskDefinitionArn']
        return True

    def _generate_deletion_args(self):
        return dict(
            taskDefinition=self.resource_id,
        )

    def delete(self, args=None):
        delete_args = utils.update_args(self._generate_deletion_args(),
                                        args)

        self.execute(
            self.client.deregister_task_definition,
            delete_args,
        )
        return True

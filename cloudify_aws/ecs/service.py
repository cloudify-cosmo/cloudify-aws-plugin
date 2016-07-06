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
    return Service().created(args)


@operation
def delete(args=None, **_):
    return Service().deleted(args)


class Service(AwsBaseNode):
    def __init__(self, client=None):
        client = client or EC2ConnectionClient().client3('ecs')

        super(Service, self).__init__(
            constants.ECS_SERVICE['AWS_RESOURCE_TYPE'],
            constants.ECS_SERVICE['REQUIRED_PROPERTIES'],
            client=client,
            resource_id_key=constants.ECS_SERVICE['RESOURCE_ID_KEY'],
        )

        self.not_found_error = constants.ECS_SERVICE['NOT_FOUND_ERROR']

    def get_arn(self, relationships, from_relationship):
        return self.get_target_attribute(
            relationships=relationships,
            from_relationship=from_relationship,
            desired_attribute=constants.EXTERNAL_RESOURCE_ID,
        )

    def get_related_elb_name(self, relationships):
        return self.get_target_property(
            relationships=relationships,
            from_relationship=constants.SERVICE_LOAD_BALANCER_RELATIONSHIP,
            desired_property='elb_name',
        )

    def get_container_instance_count(self, relationships):
        return self.get_target_attribute(
            relationships=relationships,
            from_relationship=constants.SERVICE_CLUSTER_RELATIONSHIP,
            desired_attribute='instances',
        )

    def get_task_container_names(self, relationships):
        return self.get_target_attribute(
            relationships=relationships,
            from_relationship=constants.SERVICE_TASK_RELATIONSHIP,
            desired_attribute='container_names',
        )

    def _generate_creation_args(self):
        cluster_arn = self.get_cluster_arn(self.get_arn(
            ctx.instance.relationships,
            constants.SERVICE_CLUSTER_RELATIONSHIP,
        ))
        task_arn = self.get_arn(
            ctx.instance.relationships,
            constants.SERVICE_TASK_RELATIONSHIP,
        )

        if not cluster_arn or not task_arn:
            raise NonRecoverableError(
                'Could not create Service {service}. ECS Services must have '
                'relationships to both a cluster '
                '({cluster_rel}) '
                'and a task '
                '({task_rel}). '
                'Related cluster was {cluster}. '
                'Related task was {task}.'.format(
                    service=ctx.node.properties['name'],
                    cluster=cluster_arn,
                    task=task_arn,
                    cluster_rel=constants.SERVICE_CLUSTER_RELATIONSHIP,
                    task_rel=constants.SERVICE_TASK_RELATIONSHIP,
                )
            )

        service_definition = {
            'cluster': cluster_arn,
            'serviceName': ctx.node.properties['name'],
            'desiredCount': ctx.node.properties['desired_count'],
            'taskDefinition': task_arn,
        }

        related_elb = self.get_related_elb_name(ctx.instance.relationships)

        if related_elb is not None:
            containers = self.get_task_container_names(
                ctx.instance.relationships,
            )

            if len(containers) != 1:
                raise NonRecoverableError(
                    'Could not associate load balancer. '
                    'Associating a load balancer requires a task with exactly '
                    'one container.'
                )

            load_balancer = {
                'loadBalancerName': related_elb,
                'containerName': containers[0],
                'containerPort': (
                    ctx.node.properties['container_listening_port']
                ),
            }

            service_definition['loadBalancers'] = [load_balancer]

            service_definition['role'] = (
                ctx.node.properties['lb_management_role']
            )

        return service_definition

    def create(self, args=None, **_):
        # Don't try to do anything until the cluster has instances...
        container_instances = self.get_container_instance_count(
            ctx.instance.relationships,
        )
        if not container_instances:
            return ctx.operation.retry(
                'Waiting for cluster to have available instances.',
            )

        create_args = utils.update_args(self._generate_creation_args(),
                                        args)

        response = self.execute(
            self.client.create_service,
            create_args,
        )
        ctx.instance.runtime_properties[constants.EXTERNAL_RESOURCE_ID] = (
            response['service']['serviceArn']
        )

        return True

    def _get_delete_base_args(self):
        cluster_arn = self.get_cluster_arn(self.get_arn(
            ctx.instance.relationships,
            constants.SERVICE_CLUSTER_RELATIONSHIP,
        ))
        arn = ctx.instance.runtime_properties.get(
            constants.EXTERNAL_RESOURCE_ID,
            None
        )
        return cluster_arn, arn

    def _generate_deletion_update_args(self):
        cluster_arn, arn = self._get_delete_base_args()

        return dict(
            service=arn,
            cluster=cluster_arn,
            desiredCount=0,
        )

    def _generate_deletion_args(self):
        cluster_arn, arn = self._get_delete_base_args()

        return dict(
            service=arn,
            cluster=cluster_arn,
        )

    def delete(self, args=None, **_):
        update_args = utils.update_args(
            self._generate_deletion_update_args(),
            args,
        )
        self.execute(
            self.client.update_service,
            update_args,
        )

        delete_args = utils.update_args(
            self._generate_deletion_args(),
            args,
        )
        self.execute(
            self.client.delete_service,
            delete_args,
        )

        return True

    def get_resource(self):
        cluster_arn = self.get_arn(
            ctx.instance.relationships,
            constants.SERVICE_CLUSTER_RELATIONSHIP,
        )

        services = self.execute(
            self.client.list_services,
            {'cluster': cluster_arn},
        )
        arn = self.get_service_arn(
            ctx.instance.runtime_properties.get(
                constants.EXTERNAL_RESOURCE_ID,
                None
            ),
            cluster_arn,
        )

        services = services.get('serviceArns', [])
        if arn in services:
            return arn

        # If we get here, no key was found
        return None

    def get_cluster_arn(self, name):
        # This will get the ARN of a cluster whether given its name or its
        # ARN.
        clusters = self.execute(
            self.client.describe_clusters,
            {
                'clusters': [name],
            },
        ).get('clusters', [])

        if len(clusters) > 1:
            raise NonRecoverableError(
                'Cannot determine correct cluster for service from '
                '{cluster_names}.'.format(cluster_names=[
                    cluster.get('clusterName', 'unknown name')
                    for cluster in clusters
                ])
            )
        elif len(clusters) == 0:
            raise NonRecoverableError(
                'Cluster {cluster} not found.'.format(cluster=name)
            )
        else:
            cluster = clusters[0]
            arn = cluster['clusterArn']

            return arn

    def get_service_arn(self, name, cluster_arn):
        # This will get the ARN of a service within a cluster given
        # its name or ARN
        services = self.execute(
            self.client.describe_services,
            {
                'cluster': cluster_arn,
                'services': [name],
            },
        ).get('services', [])

        if len(services) > 1:
            raise NonRecoverableError(
                'Cannot find correct service in cluster '
                '{cluster}. Found {service_names}'.format(
                    cluster=cluster_arn,
                    service_names=[
                        service.get('serviceName', 'unknown name')
                        for service in services
                    ],
                )
            )
        elif len(services) == 0:
            raise NonRecoverableError(
                'Service {service} not found on cluster '
                '{cluster}. No services found.'.format(
                    service=name,
                    cluster=cluster_arn,
                )
            )
        else:
            service = services[0]
            arn = service['serviceArn']

            return arn

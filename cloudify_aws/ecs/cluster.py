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

# This package imports
from cloudify_aws import constants, utils
from cloudify_aws.base import AwsBaseNode, AwsBaseRelationship
from cloudify_aws.connection import EC2ConnectionClient


@operation
def create(args=None, **_):
    return Cluster().created(args)


@operation
def delete(args=None, **_):
    return Cluster().deleted(args)


@operation
def add_container_instance(args=None, **_):
    return ClusterInstance().associated(args)


@operation
def remove_container_instance(args=None, **_):
    return ClusterInstance().disassociated(args)


class Cluster(AwsBaseNode):
    def __init__(self, client=None):
        client = client or EC2ConnectionClient().client3('ecs')

        super(Cluster, self).__init__(
            constants.ECS_CLUSTER['AWS_RESOURCE_TYPE'],
            constants.ECS_CLUSTER['REQUIRED_PROPERTIES'],
            client=client,
            resource_id_key=constants.ECS_CLUSTER['RESOURCE_ID_KEY'],
        )

        self.not_found_error = constants.ECS_CLUSTER['NOT_FOUND_ERROR']

    def _generate_creation_args(self):
        return dict(
            clusterName=ctx.node.properties['name'],
        )

    def create(self, args=None, **_):
        create_args = utils.update_args(self._generate_creation_args(),
                                        args)

        response = self.execute(
            self.client.create_cluster,
            create_args,
        )
        ctx.instance.runtime_properties[constants.EXTERNAL_RESOURCE_ID] = (
            response['cluster']['clusterArn']
        )
        self.resource_id = response['cluster']['clusterArn']
        ctx.instance.runtime_properties['instances'] = []

        return True

    def _generate_deregister_container_args(self, container_arn):
        arn = ctx.instance.runtime_properties.get(
            constants.EXTERNAL_RESOURCE_ID,
            None,
        )

        return dict(
            cluster=arn,
            containerInstance=container_arn,
        )

    def _generate_deletion_args(self):
        arn = ctx.instance.runtime_properties.get(
            constants.EXTERNAL_RESOURCE_ID,
            None,
        )

        return dict(
            cluster=arn,
        )

    def delete(self, args=None, **_):
        arn = ctx.instance.runtime_properties.get(
            constants.EXTERNAL_RESOURCE_ID,
            None,
        )

        container_arns = self.execute(
            self.client.list_container_instances,
            {'cluster': arn},
        ).get('containerInstanceArns', [])

        for container_arn in container_arns:
            ctx.logger.warn(
                'Cluster still has attached container instances. '
                'Deregistering {arn}.'.format(arn=container_arn)
            )

            deregister_args = utils.update_args(
                self._generate_deregister_container_args(container_arn),
                args,
            )
            self.execute(
                self.client.deregister_container_instance,
                deregister_args,
            )

        delete_args = utils.update_args(self._generate_deletion_args(),
                                        args)

        self.execute(
            self.client.delete_cluster,
            delete_args,
        )

        return True

    def get_resource(self):
        arn = ctx.instance.runtime_properties.get(
            constants.EXTERNAL_RESOURCE_ID,
            None,
        )

        if arn is not None:
            cluster_name = arn
        else:
            cluster_name = ctx.node.properties['name']

        cluster_arns = self.execute(
            self.client.list_clusters,
        ).get('clusterArns', [])
        cluster_details = self.execute(
            self.client.describe_clusters,
            {'clusters': cluster_arns},
        )
        clusters = []
        for cluster in cluster_details['clusters']:
            clusters.append(cluster['clusterArn'])
            clusters.append(cluster['clusterName'])
        if cluster_name in clusters:
            return cluster_name

        # Cluster not found
        return None


class ClusterInstance(AwsBaseRelationship):
    def __init__(self, client=None):
        client = client or EC2ConnectionClient().client3('ecs')

        super(ClusterInstance, self).__init__(
            client=client,
        )
        self.args = dict(
            ec2_id=self.source_resource_id,
            cluster_arn=self.target_resource_id,
        )
        self.detachment_function = self.client.deregister_container_instance

    def associated(self, args=None):

        ctx.logger.info(
            'Attempting to associate {0} with {1}.'
            .format(self.source_resource_id,
                    self.target_resource_id))

        if self.use_source_external_resource_naively() \
                or self.associate(args):
            return self.post_associate()

        return ctx.operation.retry(
            message='Waiting for EC2 instance to register with cluster.'
        )

    def associate(self, args=None):
        instance_arn = self._get_container_instance_arn_from_ec2_id(
            **self.args
        )

        if instance_arn is None:
            # We're not registered with the cluster yet.
            # This is something the (correct) AMI will do by itself.
            return False

        # We store the ec2 ID so that we can look up and delete the associated
        # ARN when removing the container instance later if it fails to.
        # It has failed to more than once in initial testing.
        # We have to do the little retrieve,append,replace dance because
        # trying to just append on the object results in no instances in the
        # list.
        instances = ctx.target.instance.runtime_properties['instances']
        instances.append(self.source_resource_id)
        ctx.target.instance.runtime_properties['instances'] = instances

        # We don't actually need to do anything on the platform
        return True

    def _generate_disassociate_args(self, instance_arn):
        return dict(
            cluster=self.target_resource_id,
            containerInstance=instance_arn,
        )

    def disassociate(self, args=None):
        instance_arn = self._get_container_instance_arn_from_ec2_id(
            **self.args
        )

        disassociate_args = utils.update_args(
            self._generate_disassociate_args(instance_arn),
            args,
        )

        # If the instance_arn doesn't exist, we don't need to delete it- it
        # may have not yet been registered (as this takes some time)
        if instance_arn is not None:
            self.execute(
                self.detachment_function,
                disassociate_args,
            )

        # Ensure we've no longer got this in the list of container instances
        instances = ctx.target.instance.runtime_properties['instances']
        instances.remove(self.source_resource_id)
        ctx.target.instance.runtime_properties['instances'] = instances

        return True

    def _get_container_instance_arn_from_ec2_id(self, ec2_id, cluster_arn):
        container_instance_arns = self.execute(
            self.client.list_container_instances,
            {'cluster': cluster_arn},
        ).get('containerInstanceArns', [])

        if container_instance_arns == []:
            # Boto3 is aggravating and will traceback on an empty list
            # (sometimes- on this call anyway, but not on some others)
            container_instance_arns = ['this_stops_an_error_on_the_next_call']
        container_instances = self.execute(
            self.client.describe_container_instances,
            {
                'cluster': cluster_arn,
                'containerInstances': container_instance_arns,
            },
        ).get('containerInstances', [])
        container_instance_mapping = {
            item['ec2InstanceId']: item['containerInstanceArn']
            for item in container_instances
        }

        if ec2_id in container_instance_mapping.keys():
            return container_instance_mapping[ec2_id]
        else:
            return None

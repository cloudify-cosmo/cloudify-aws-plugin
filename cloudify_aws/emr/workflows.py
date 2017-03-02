# #######
# Copyright (c) 2017 GigaSpaces Technologies Ltd. All rights reserved
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
'''
    EMR.Workflows
    ~~~~~~~~~~~~~
    AWS EMR workflows
'''
# Cloudify imports
from cloudify.exceptions import OperationRetry, NonRecoverableError
from cloudify_aws.emr import utils
from cloudify_aws.emr.cluster import EMRCluster
# Cloudify AWS
from cloudify_aws import connection
from cloudify_aws.constants import (
    AWS_CONFIG_PROPERTY)


def scale_instance_group(ctx, cluster_node, instance_group_id, delta, **_):
    '''
        Scales the amount of instances in an instance group
        (specified by `instance_group_id`) by `delta`.

    :param str cluster_id: AWS ID of the EMR cluster to use
    :param str instance_group_id: AWS ID of the EMR instance group to scale
    :param int delta: Amount to scale by (positive integer for scaling up
        or negative integer for scaling down)
    '''
    # Naive type casting from string
    delta = int(delta)
    cluster_node = ctx.get_node(cluster_node)
    if not cluster_node.number_of_instances:
        raise NonRecoverableError(
            'Cluster node (%s) has no running instances!' % cluster_node.id)
    # Find a usable EMR cluster node instance
    cluster_node_instance = [x for x in cluster_node.instances]
    if len(cluster_node_instance) < 1:
        raise NonRecoverableError('No EMR Cluster node instances found')
    elif len(cluster_node_instance) > 1:
        ctx.logger.warn('Multiple EMR Cluster node instances found')
    cluster_node_instance = cluster_node_instance[0]
    # Get the EMR cluster ID
    cluster_id = utils.get_resource_id(
        cluster_node, cluster_node_instance, raise_on_missing=True)
    ctx.logger.debug('EMR Cluster: %s ("%s")' % (cluster_node.id, cluster_id))
    client = connection.EMRConnectionClient().client(
        cluster_node.properties[AWS_CONFIG_PROPERTY])
    # Get Cluster object
    cluster = EMRCluster(cluster_id, client=client, logger=ctx.logger)
    # Check if the cluster if running
    cluster_status = cluster.status
    if cluster_status.state in ['STARTING', 'BOOTSTRAPPING']:
        raise OperationRetry(
            message='Waiting for AWS EMR cluster to come online '
                    '(Status=%s)' % cluster_status.state,
            retry_after=30)
    elif cluster_status.state not in ['RUNNING', 'WAITING']:
        cluster.raise_bad_state(cluster.status)
    # Get a list of all cluster instance groups
    instance_group = cluster.get_instance_group(instance_group_id)
    ctx.logger.debug('Instance Group "%s" has %d instance(s) [%d running]' % (
        instance_group.id,
        int(instance_group.requestedinstancecount),
        int(instance_group.runninginstancecount)))
    # Scale the instance group
    new_instance_count = int(instance_group.requestedinstancecount) + delta
    if new_instance_count < 0:
        ctx.logger.warn(
            'User requested scaling by %d but that would set the '
            'new count to %d. Adjusting to zero.'
            % (delta, new_instance_count))
        new_instance_count = 0
    ctx.logger.info('Scaling InstanceGroup(%s) instance count to %d'
                    % (instance_group.id, new_instance_count))
    res = client.modify_instance_groups(
        [instance_group.id], [new_instance_count])
    ctx.logger.debug('ModifyInstanceGroups request-id=%s' % res.requestid)
    # Show the individual instances
    ctx.logger.debug('Dumping InstanceGroup(%s) instances'
                     % (instance_group.id))
    instances = client.list_instances(cluster_id, instance_group_id).instances
    for instance in instances:
        ctx.logger.debug(
            '\n- EC2 instance ID "%s" (EMR ID "%s")'
            '\n  Status:     %s'
            '\n  Public IP:  %s'
            '\n  Private IP: %s'
            % (instance.ec2instanceid,
               instance.id,
               instance.status.state,
               instance.publicipaddress if
               hasattr(instance, 'publicipaddress') else None,
               instance.privateipaddress if
               hasattr(instance, 'privateipaddress') else None))

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
    EMR.Cluster
    ~~~~~~~~~~~
    AWS EMR cluster interface
'''
# Cloudify imports
from cloudify.exceptions import OperationRetry, NonRecoverableError
# Cloudify AWS
from cloudify_aws.constants import (
    EXTERNAL_RESOURCE_ID,
    EMR_CLUSTER_GROUP_RELATIONSHIP,
    EMR_INSTANCE_GROUP_KEYS)
from cloudify_aws.emr import utils, EMRBase
from cloudify_aws.emr.boto_compat import build_applications_list
# Boto
from boto.emr.instance_group import InstanceGroup

STEP_TYPE_CUSTOM_JAR = 'cloudify.aws.nodes.emr.CustomJAR'
STEP_TYPE_STREAMING = 'cloudify.aws.nodes.emr.StreamingStep'


def create(ctx, **_):
    '''EMR cluster create workflow'''
    # If needed, create a new resource
    create_cluster_if_needed(ctx)
    # Get the resource ID (must exist at this point)
    resource_id = utils.get_resource_id(raise_on_missing=True)
    # Get the resource status
    resource = EMRCluster(resource_id, logger=ctx.logger)
    status = resource.status
    # Wait for the resource to be created
    if status.state in ['STARTING', 'BOOTSTRAPPING']:
        raise OperationRetry(
            message='Waiting for AWS EMR cluster to come online '
                    '(Status=%s)' % status.state,
            retry_after=30)
    elif status.state in ['RUNNING', 'WAITING']:
        return
    # Handle "error" states, normalize state change reason
    resource.raise_bad_state(status)


def delete(ctx, **_):
    '''EMR cluster delete workflow'''
    # Get the resource ID (must exist at this point)
    resource_id = utils.get_resource_id()
    if not resource_id:
        ctx.logger.warn('Missing resource ID. Skipping workflow...')
        return
    # Get the resource interface
    resource = EMRCluster(resource_id, logger=ctx.logger)
    # Delete the resource (if needed)
    if ctx.node.properties['use_external_resource']:
        return
    if ctx.operation.retry_number == 0:
        resource.delete()
    # Wait for the resource to delete
    status = resource.status
    if status.state in ['TERMINATING']:
        raise OperationRetry(
            message='Waiting for AWS EMR cluster to terminate '
                    '(Status=%s)' % status.state,
            retry_after=30)
    elif status.state in ['TERMINATED']:
        return
    # Handle "error" states, normalize state change reason
    resource.raise_bad_state(status)


def create_cluster_if_needed(ctx):
    '''
        Creates a new AWS EMR cluster if the context
        is that of a non-external type. This automatically
        updates the current contexts' resource ID.
    '''
    props = ctx.node.properties
    if props['use_external_resource'] or ctx.operation.retry_number > 0:
        return
    # Build API params
    api_params = dict(ReleaseLabel=props['release_label'])
    api_params.update(build_applications_list(
        ctx.node.properties.get('applications', list())))
    # Actually create the resource
    resource_id = EMRCluster(logger=ctx.logger).create(dict(
        name=props['name'],
        log_uri=props.get('log_uri'),
        ec2_keyname=props.get('ec2_keyname'),
        keep_alive=props['keep_alive'],
        action_on_failure=props['action_on_failure'],
        availability_zone=props.get('availability_zone'),
        instance_groups=list_connected_instance_groups(ctx.instance),
        job_flow_role=props.get('job_flow_role'),
        service_role=props.get('service_role'),
        api_params=api_params))
    ctx.instance.runtime_properties[EXTERNAL_RESOURCE_ID] = resource_id


def list_connected_instance_groups(
        ctx_instance, rel_type=EMR_CLUSTER_GROUP_RELATIONSHIP):
    '''
        Builds a list of InstanceGroup types based on
        a node instances' relationships. It searches (by default) for all
        relationship types connecting a cluster to an instance
        group and converts the target nodes' properties to
        a boto-consumable list.
    '''
    return [InstanceGroup(**{
        k: v for k, v in rel.target.node.properties.iteritems()
        if k in EMR_INSTANCE_GROUP_KEYS
    }) for rel in ctx_instance.relationships
            if rel_type in rel.type_hierarchy]


class EMRCluster(EMRBase):
    '''
        AWS EMR cluster interface
    '''
    def __init__(self, resource_id=None, client=None, logger=None):
        EMRBase.__init__(self, resource_id, client, logger)

    def create(self, config):
        '''
            Create a new AWS EMR cluster.

        .. note:
            See http://bit.ly/2l6SYv2 for config details.
        '''
        if not config.get('name'):
            raise NonRecoverableError('An AWS EMR cluster needs a name')
        if not config.get('instance_groups'):
            raise NonRecoverableError(
                'At least 1 AWS EMR Instance Group is needed')
        # Create the cluster
        jobflow = {k: v for k, v in config.iteritems() if v is not None}
        self.logger.debug('Creating cluster with parameters: %s' % jobflow)
        self.resource_id = self.client.run_jobflow(**jobflow)
        return self.resource_id

    def delete(self):
        '''Deletes an existing AWS EMR cluster'''
        self.client.terminate_jobflow(self.resource_id)

    @property
    def status(self):
        '''Queries the resource for its status and returns the result'''
        status = self.properties.status
        self.logger.debug('AWS EMR cluster "%s" status: %s'
                          % (self.resource_id, status.state))
        return status

    @property
    def properties(self):
        '''Gets a native resource description'''
        return self.client.describe_cluster(self.resource_id)

    def add_step(self, step):
        '''Adds a new job / step to the cluster'''
        res = self.client.add_jobflow_steps(self.resource_id, [step])
        if res and hasattr(res, 'stepids') and len(res.stepids) > 0:
            return res.stepids[0].value

    def get_step(self, step_id):
        '''Gets a step by ID'''
        return self.client.describe_step(self.resource_id, step_id)

    def add_instance_group(self, group):
        '''Adds a new instance group to the cluster'''
        res = self.client.add_instance_groups(self.resource_id, [group])
        if res and hasattr(res, 'instancegroupids') and \
           len(res.instancegroupids) > 0:
            return res.instancegroupids[0].value

    def get_instance_group(self, group_id):
        '''Gets an instance group by ID'''
        groups = self.client.list_instance_groups(
            self.resource_id).instancegroups
        for group in groups:
            if group.id == group_id:
                return group
        return None

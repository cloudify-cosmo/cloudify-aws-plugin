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
    EMR.Step
    ~~~~~~~~
    AWS EMR step interface
'''
# Cloudify imports
from cloudify.exceptions import OperationRetry, NonRecoverableError
# Cloudify AWS
from cloudify_aws.constants import (
    EXTERNAL_RESOURCE_ID,
    EMR_STEP_IN_CLUSTER_RELATIONSHIP)
from cloudify_aws.emr import utils, EMRBase
from cloudify_aws.emr.cluster import EMRCluster
# Boto
from boto.emr.step import StreamingStep

STEP_TYPE_CUSTOM_JAR = 'cloudify.aws.nodes.emr.CustomJAR'
STEP_TYPE_STREAMING = 'cloudify.aws.nodes.emr.StreamingStep'


def create(ctx, **_):
    '''EMR step create workflow'''
    # Get the parent cluster resource
    cluster = get_parent_cluster(ctx)
    if not cluster:
        raise NonRecoverableError(
            'Could not find a parent EMR cluster to run step on')
    # Create the resource if needed
    create_step_if_needed(ctx, cluster)
    # Get the resource ID (must exist at this point)
    resource_id = utils.get_resource_id(raise_on_missing=True)
    # Get the resource status
    resource = EMRStep(cluster, resource_id, logger=ctx.logger)
    status = resource.status
    # Wait for the resource to be created
    if status.state in ['PENDING', 'CANCEL_PENDING', 'RUNNING']:
        raise OperationRetry(
            message='Waiting for AWS EMR step to be created '
                    '(Status=%s)' % status.state,
            retry_after=30)
    elif status.state in ['COMPLETED']:
        return
    # Handle "error" states, normalize state change reason
    resource.raise_bad_state(status)


def create_step_if_needed(ctx, cluster):
    '''
        Creates a new AWS EMR step if the context
        is that of a non-external type. This automatically
        updates the current contexts' resource ID.
    '''
    props = ctx.node.properties
    if props['use_external_resource'] or ctx.operation.retry_number > 0:
        return
    # Determine the type of step
    if STEP_TYPE_STREAMING in ctx.node.type_hierarchy:
        step_build = build_streaming_step(props)
    else:
        raise NonRecoverableError(
            'Could not determine the type of EMR step')
    # Actually create the resource
    ctx.instance.runtime_properties[EXTERNAL_RESOURCE_ID] = \
        EMRStep(cluster, logger=ctx.logger).create(step_build)


def build_streaming_step(props):
    '''
        Creates a new Streaming Step build ready to
        be consumed by Cluster.add_step()
    '''
    return StreamingStep(**{k: v for k, v in dict(
        name=props['name'],
        jar=props.get('jar'),
        action_on_failure=props['action_on_failure'],
        input=props['input'],
        output=props['output'],
        mapper=props['mapper'],
        reducer=props.get('reducer'),
        combiner=props.get('combiner'),
        step_args=props.get('step_args')
        ).iteritems() if v is not None})


def get_parent_cluster(ctx):
    '''
        Finds a parent cluster node type for the current
        context node.
    '''
    for rel in ctx.instance.relationships:
        if EMR_STEP_IN_CLUSTER_RELATIONSHIP in rel.type_hierarchy:
            return EMRCluster(
                utils.get_resource_id(
                    rel.target.node,
                    rel.target.instance,
                    raise_on_missing=True),
                logger=ctx.logger)
    return None


class EMRStep(EMRBase):
    '''
        AWS EMR cluster step interface
    '''
    def __init__(self, cluster, resource_id=None, client=None, logger=None):
        EMRBase.__init__(self, resource_id, client, logger)
        self.cluster = cluster

    def create(self, boto_step):
        '''Creates a Step on a cluster'''
        self.logger.debug('Creating step with parameters: %s' % boto_step)
        self.resource_id = self.cluster.add_step(boto_step)
        return self.resource_id

    def delete(self):
        '''Deletes a Step from a cluster (not currently allowed by AWS)'''
        raise NotImplementedError()

    @property
    def status(self):
        '''Queries the resource for its status and returns the result'''
        status = self.properties.status
        self.logger.debug('AWS EMR step "%s" status: %s'
                          % (self.resource_id, status.state))
        return status

    @property
    def properties(self):
        '''Gets a native resource description'''
        return self.cluster.get_step(self.resource_id)

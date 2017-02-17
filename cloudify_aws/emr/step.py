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
from cloudify.decorators import operation
from cloudify_aws import constants
from cloudify_aws.emr import EMRBase
from cloudify_aws.emr.cluster import EMRCluster
# Boto
from boto.emr.step import StreamingStep

STEP_TYPE_CUSTOM_JAR = 'cloudify.aws.nodes.emr.CustomJAR'
STEP_TYPE_STREAMING = 'cloudify.aws.nodes.emr.StreamingStep'


@operation
def create(ctx, **_):
    '''EMR cluster create workflow'''
    return EMRStep(ctx).create()


class EMRStep(EMRBase):
    '''
        AWS EMR cluster step interface
    '''
    def __init__(self, ctx, client=None, logger=None):
        EMRBase.__init__(self, ctx, client=client, logger=logger)

    def create(self):
        '''Creates a Step on a cluster'''
        props = self.ctx.node.properties
        cluster = None
        # Find th eassociated cluster
        for rel in self.ctx.instance.relationships:
            if constants.EMR_STEP_IN_CLUSTER_RELATIONSHIP in rel.type_hierarchy:
                cluster = EMRCluster(rel.target, logger=self.logger)
        if not cluster:
            raise NonRecoverableError(
                'Could not find a suitable EMR cluster to run step on')
        if not self.is_external and self.ctx.operation.retry_number == 0:
            # Determine the type of step
            if STEP_TYPE_STREAMING in self.ctx.node.type_hierarchy:
                self.logger.info('Streaming Step type discovered')
                step_build = StreamingStep(**{k: v for k, v in dict(
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
            if not step_build:
                raise NonRecoverableError(
                    'Could not determine the type of EMR step')
            # If there's a step found, add it to the cluster
            self.update_resource_id(cluster.add_step(step_build))
        # Get the step's ID
        step_id = self.resource_id
        self.logger.info('Using AWS EMR step ID "%s"' % step_id)
        step = cluster.get_step(step_id)
        self.logger.debug('AWS EMR step "%s" status: %s'
                          % (step_id, step.status.state))
        # Check if the cluster if running
        # Handle "pending" states
        if step.status.state in ['PENDING', 'CANCEL_PENDING', 'RUNNING']:
            raise OperationRetry(
                message='Waiting for AWS EMR step to come online '
                        '(Status=%s)' % step.status.state,
                retry_after=15)
        elif step.status.state in ['COMPLETED']:
            return
        # Handle "error" states, normalize state change reason
        self.raise_bad_state(step.status)

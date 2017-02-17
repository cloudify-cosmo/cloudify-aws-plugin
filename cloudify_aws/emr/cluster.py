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
from cloudify.exceptions import OperationRetry
from cloudify.decorators import operation
# Cloudify AWS
from cloudify_aws import constants
from cloudify_aws.emr import EMRBase
from cloudify_aws.emr.boto_compat import Application
# Boto
from boto.emr.instance_group import InstanceGroup

STEP_TYPE_CUSTOM_JAR = 'cloudify.aws.nodes.emr.CustomJAR'
STEP_TYPE_STREAMING = 'cloudify.aws.nodes.emr.StreamingStep'


@operation
def create(ctx, **_):
    '''EMR cluster create workflow'''
    return EMRCluster(ctx).create()


class EMRCluster(EMRBase):
    '''
        AWS EMR cluster interface
    '''
    def __init__(self, ctx, client=None, logger=None):
        EMRBase.__init__(self, ctx, client=client, logger=logger)

    def create(self):
        '''Create'''
        if not self.is_external and self.ctx.operation.retry_number == 0:
            props = self.ctx.node.properties
            instance_groups = self.list_connected_instance_groups()
            # Start building api_params
            api_params = dict(ReleaseLabel=props['release_label'])
            # Handle application installation steps
            self.build_applications_list(api_params, props)
            # Create the cluster
            jobflow = {k: v for k, v in dict(
                name=props['name'],
                log_uri=props.get('log_uri'),
                ec2_keyname=props.get('ec2_keyname'),
                keep_alive=props['keep_alive'],
                action_on_failure=props['action_on_failure'],
                availability_zone=props.get('availability_zone'),
                instance_groups=instance_groups,
                job_flow_role=props.get('job_flow_role'),
                service_role=props.get('service_role'),
                api_params=api_params
            ).iteritems() if v is not None}
            self.logger.debug('Creating cluster with parameters: %s' % jobflow)
            self.update_resource_id(self.client.run_jobflow(**jobflow))
        # Get the cluster's ID
        cluster_id = self.resource_id
        # Get the current state of the cluster
        self.logger.info('Checking AWS EMR cluster "%s" status' % cluster_id)
        cluster = self.client.describe_cluster(cluster_id)
        # Keep the runtime properties updated
        self.ctx.instance.runtime_properties['emr_cluster'] = dict(
            name=cluster.name,
            status=cluster.status.state,
            tags=cluster.tags)
        self.logger.debug('AWS EMR cluster "%s" status: %s'
                          % (cluster_id, cluster.status.state))
        # Check if the cluster if running
        # Handle "pending" states
        if cluster.status.state in ['STARTING', 'BOOTSTRAPPING']:
            raise OperationRetry(
                message='Waiting for AWS EMR cluster to come online '
                        '(Status=%s)' % cluster.status.state,
                retry_after=30)
        elif cluster.status.state in ['RUNNING', 'WAITING']:
            return
        # Handle "error" states, normalize state change reason
        self.raise_bad_state(cluster.status)

    def add_step(self, step):
        '''Adds a new job / step to the cluster'''
        res = self.client.add_jobflow_steps(self.resource_id, [step])
        if res and hasattr(res, 'stepids') and len(res.stepids) > 0:
            return res.stepids[0].value

    def get_step(self, step_id):
        '''Gets a step by ID'''
        return self.client.describe_step(self.resource_id, step_id)

    @staticmethod
    def build_applications_list(api_params, props):
        '''Find user-specified applications to queue'''
        label = 'Applications.member.%d'
        apps = [Application(x) for x in props.get('applications', list())]
        # Update the api_params dict
        for idx, app in enumerate(apps):
            api_params.update(app.build(label % (idx + 1)))

    def list_connected_instance_groups(self):
        '''Finds all connected EMR instance groups'''
        groups = list()
        for rel in self.ctx.instance.relationships:
            if constants.EMR_CLUSTER_GROUP_RELATIONSHIP in rel.type_hierarchy:
                groups.append(InstanceGroup(**{
                    k: v for k, v in rel.target.node.properties.iteritems()
                    if k in constants.EMR_INSTANCE_GROUP_KEYS}))
        return groups

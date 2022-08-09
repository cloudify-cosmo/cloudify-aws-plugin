# Copyright (c) 2018 Cloudify Platform Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
    EC2.SpotInstances
    ~~~~~~~~~~~~~~
    AWS EC2 Spot Instances interface
"""

# Cloudify
from cloudify_aws.ec2.resources.instances import (
    TERMINATED,
    INSTANCE_ID,
    INSTANCE_IDS,
    EC2Instances,
    handle_userdata,
    assign_nics_param,
    assign_subnet_param,
    assign_groups_param)
from cloudify_aws.common import decorators, utils
from cloudify.exceptions import (
    OperationRetry,
    NonRecoverableError)

GOOD = ['open', 'active']
DELETED = ['cancelled',
           'closed',
           'completed']
REQUESTS = 'SpotInstanceRequests'
LAUNCH_SPEC = 'LaunchSpecification'
RESOURCE_TYPE = 'EC2 Spot Instances'
REQUEST_ID = 'SpotInstanceRequestId'
REQUEST_IDS = 'SpotInstanceRequestIds'


class EC2SpotInstances(EC2Instances):
    """
        EC2 Spot Instances interface
    """
    def __init__(self, ctx_node, resource_id=None, client=None, logger=None):
        EC2Instances.__init__(self, ctx_node, resource_id, client, logger)
        self.ctx_node = ctx_node
        self.type_name = RESOURCE_TYPE
        self._describe_call = 'describe_spot_instance_requests'
        self._type_key = REQUESTS
        self._id_key = REQUEST_ID
        self._ids_key = REQUEST_IDS

    def prepare_request_id_param(self, params=None):
        params = params or {}
        return {REQUEST_IDS: params.get(REQUEST_ID, [self.resource_id])}

    @property
    def properties(self):
        """Gets the properties of an external resource"""
        if not self._properties:
            resources = self.describe()
            if REQUESTS in resources:
                for request in resources[REQUESTS]:
                    if request[REQUEST_ID] == self.resource_id:
                        self._properties = request
        return self._properties

    def describe(self, params=None):
        params = params or self.prepare_request_id_param(params)
        try:
            return self.make_client_call(
                'describe_spot_instance_requests', params)
        except NonRecoverableError:
            pass
        return {}

    @property
    def status(self):
        """Gets the status of an external resource"""
        props = self.properties
        if not props:
            return None
        return props['State']

    def create(self, params):
        '''
            Create a new AWS EC2 Spot Instance Request.
        '''
        return self.make_client_call(
            'request_spot_instances', params)

    def delete(self, params=None):
        return self.make_client_call(
            'cancel_spot_instance_requests', params)

    def get_instance_ids(self):
        instance_ids = []
        for rq in self.describe()[REQUESTS]:
            if rq[REQUEST_ID] == self.resource_id and INSTANCE_ID in rq:
                instance_ids.append(rq[INSTANCE_ID])
        return instance_ids

    def delete_instances(self):
        '''
            Delete AWS EC2 Instances.
        '''
        ifaces = []
        for instance_id in self.get_instance_ids():
            self.logger.debug('Spot instance discovered: {i}. '
                              'Deleting...'.format(i=instance_id))
            iface = EC2Instances(
                self.ctx_node,
                instance_id,
                self.client,
                self.logger
            )
            iface.delete(iface.prepare_instance_ids_request())
            ifaces.append(iface)
        statuses = [i.status for i in ifaces]
        if any(s not in [TERMINATED] for s in statuses):
            raise OperationRetry(
                'Waiting for spot instances to be terminated. '
                'Instances: {i}'.format(i=[statuses]))


@decorators.aws_resource(EC2SpotInstances,
                         resource_type=RESOURCE_TYPE,
                         waits_for_status=False)
def prepare(ctx, iface, resource_config, **_):
    '''Prepares an AWS EC2 Spot Instance Request'''
    # Save the parameters
    ctx.instance.runtime_properties['resource_config'] = resource_config


@decorators.aws_resource(EC2SpotInstances,
                         RESOURCE_TYPE,
                         waits_for_status=False)
@decorators.tag_resources
def create(ctx, iface, resource_config, **_):
    '''Creates an AWS EC2 Spot Instance Request'''
    assign_launch_spec_param(resource_config)
    ctx.logger.debug(
        'Requesting spot instances with these parameters: {p}'.format(
            p=resource_config))
    create_response = iface.create(resource_config)
    ctx.instance.runtime_properties['create_response'] = \
        utils.JsonCleanuper(create_response[REQUESTS]).to_dict()
    instance_id = create_response[REQUESTS][0][REQUEST_ID]
    iface.update_resource_id(instance_id)
    utils.update_resource_id(ctx.instance, instance_id)


@decorators.aws_resource(EC2SpotInstances,
                         RESOURCE_TYPE)
@decorators.tag_resources
@decorators.wait_for_status(status_good=GOOD)
def configure(ctx, iface, resource_config, **_):
    '''Waits for an AWS EC2 Spot Instance Request to be ready'''
    if INSTANCE_IDS not in ctx.instance.runtime_properties:
        ctx.instance.runtime_properties[INSTANCE_IDS] = []
    ctx.instance.runtime_properties[INSTANCE_IDS] = iface.get_instance_ids()


@decorators.aws_resource(EC2SpotInstances,
                         RESOURCE_TYPE,
                         waits_for_status=False)
@decorators.tag_resources
def stop(ctx, iface, resource_config, **_):
    '''Deletes an AWS EC2 Spot Instance Request'''
    ctx.logger.info('Deleting instances created by spot instance request...')
    iface.delete_instances()


@decorators.aws_resource(EC2SpotInstances,
                         RESOURCE_TYPE,
                         waits_for_status=False)
@decorators.untag_resources
def delete(ctx, iface, resource_config, dry_run=False, **_):
    '''Deletes an AWS EC2 Spot Instance Request'''
    resource_config['DryRun'] = dry_run
    if not dry_run:
        ctx.logger.info('Deleting spot instance request...')
    iface.delete(iface.prepare_request_id_param(resource_config))


def assign_launch_spec_param(params):
    launch_spec = params.get(LAUNCH_SPEC, {})
    handle_userdata(launch_spec, encode=True)
    assign_subnet_param(launch_spec)
    assign_groups_param(launch_spec)
    assign_nics_param(launch_spec)
    params[LAUNCH_SPEC] = launch_spec

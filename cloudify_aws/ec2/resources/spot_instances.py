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
from cloudify_aws.ec2 import EC2Base
from cloudify_aws.ec2.resources.instances import (
    assign_nics_param,
    assign_subnet_param,
    assign_groups_param)
from cloudify_aws.common import decorators, utils
from cloudify.exceptions import NonRecoverableError

GOOD = ['open', 'active']
DELETED = ['cancelled',
           'closed',
           'completed']
REQUESTS = 'SpotInstanceRequests'
LAUNCH_SPEC = 'LaunchSpecification'
RESOURCE_TYPE = 'EC2 Spot Instances'
REQUEST_ID = 'SpotInstanceRequestId'
REQUEST_IDS = 'SpotInstanceRequestIds'


class EC2SpotInstances(EC2Base):
    """
        EC2 Spot Instances interface
    """
    def __init__(self, ctx_node, resource_id=None, client=None, logger=None):
        EC2Base.__init__(self, ctx_node, resource_id, client, logger)
        self.type_name = RESOURCE_TYPE

    def prepare_request_id_param(self, params=None):
        params = params or {}
        return {REQUEST_IDS: params.get(REQUEST_ID, [self.resource_id])}

    @property
    def request_id_param(self):
        return self.prepare_request_id_param()

    @property
    def properties(self):
        """Gets the properties of an external resource"""
        resources = {}
        try:
            resources = self.make_client_call(
                'describe_spot_instance_requests', self.request_id_param)
        except NonRecoverableError:
            pass
        return None if not resources else resources[REQUESTS][0]

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


@decorators.aws_resource(EC2SpotInstances, resource_type=RESOURCE_TYPE)
def prepare(ctx, iface, resource_config, **_):
    '''Prepares an AWS EC2 Spot Instance Request'''
    # Save the parameters
    ctx.instance.runtime_properties['resource_config'] = resource_config


@decorators.aws_resource(EC2SpotInstances, RESOURCE_TYPE)
@decorators.tag_resources
def create(ctx, iface, resource_config, **_):
    '''Creates an AWS EC2 Spot Instance Request'''
    params = utils.clean_params(
        dict() if not resource_config else resource_config.copy())
    assign_launch_spec_param(params)
    ctx.logger.debug(
        'Requesting spot instances with these parameters: {p}'.format(
            p=params))
    create_response = iface.create(params)
    ctx.instance.runtime_properties['create_response'] = \
        utils.JsonCleanuper(create_response[REQUESTS]).to_dict()


@decorators.aws_resource(EC2SpotInstances, RESOURCE_TYPE)
@decorators.tag_resources
@decorators.wait_for_status(status_good=GOOD)
def configure(ctx, iface, resource_config, **_):
    '''Waits for an AWS EC2 Spot Instance Request to be ready'''
    pass


@decorators.aws_resource(EC2SpotInstances, RESOURCE_TYPE)
@decorators.tag_resources
@decorators.wait_for_status(status_good=DELETED)
def delete(ctx, iface, resource_config, **_):
    '''Deletes an AWS EC2 Spot Instance Request'''
    params = utils.clean_params(
        dict() if not resource_config else resource_config.copy())
    iface.delete(iface.prepare_request_id_param(params))


def assign_launch_spec_param(params):
    launch_spec = params.get(LAUNCH_SPEC, {})
    assign_subnet_param(launch_spec)
    assign_groups_param(launch_spec)
    assign_nics_param(launch_spec)
    params[LAUNCH_SPEC] = launch_spec

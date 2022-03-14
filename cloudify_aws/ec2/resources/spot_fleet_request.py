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
'''
    EC2.VPC
    ~~~~~~~~~~~~~~
    AWS EC2 VPC interface
'''
# Third Party imports
from botocore.exceptions import ClientError
import time

from cloudify.exceptions import OperationRetry, NonRecoverableError

# Local imports
from cloudify_aws.ec2 import EC2Base
from cloudify_aws.common import decorators, utils
from cloudify_aws.ec2.resources.instances import INSTANCE_ID
from cloudify_aws.common.constants import (
    EXTERNAL_RESOURCE_ID_MULTIPLE as MULTI_ID)

RESOURCE_TYPE = 'EC2 Spot Fleet Request'
SpotFleetRequest = 'SpotFleetRequest'
SpotFleetRequests = 'SpotFleetRequests'
SpotFleetRequestId = 'SpotFleetRequestId'
SpotFleetRequestIds = 'SpotFleetRequestIds'
SpotFleetRequestConfig = 'SpotFleetRequestConfig'
SpotFleetRequestConfigs = 'SpotFleetRequestConfigs'


class EC2SpotFleetRequest(EC2Base):
    '''
        EC2 Spot Fleet Request interface
    '''
    def __init__(self, ctx_node, resource_id=None, client=None, logger=None):
        EC2Base.__init__(self, ctx_node, resource_id, client, logger)
        self.type_name = RESOURCE_TYPE
        self._properties = {}

    def get(self, spot_fleet_request_ids=None):
        self.logger.debug(
            'Getting list of {t}, max results page size is 123. '
            'If a larger page size is required, please '
            'open a ticket with Cloudify support.'.format(t=RESOURCE_TYPE))
        spot_fleet_request_ids = spot_fleet_request_ids or [self.resource_id]
        params = {SpotFleetRequestIds: spot_fleet_request_ids}
        try:
            return self.make_client_call(
                'describe_spot_fleet_requests', params)
        except (NonRecoverableError):
            return

    @property
    def properties(self):
        '''Gets the properties of an external resource'''
        if not self._properties:
            resources = self.get()
            if resources and 'SpotFleetRequestConfigs' in resources:
                self._properties = resources[SpotFleetRequestConfigs][0]
        return self._properties

    @property
    def status(self):
        '''Gets the status of an external resource'''
        props = self.properties
        if SpotFleetRequestConfig in props:
            return props[SpotFleetRequestConfig].get('SpotFleetRequestState')

    @property
    def check_status(self):
        if self.status in ['active']:
            return 'OK'
        return 'NOT OK'

    @property
    def active_instances(self):
        instances = self.list_spot_fleet_instances(
            {'SpotFleetRequestId': self.resource_id})
        active_instances = instances.get('ActiveInstances')
        if active_instances:
            return instances['ActiveInstances']

    def create(self, params):
        '''
            Create a new AWS EC2 Spot Fleet Request.
        '''
        return self.make_client_call('request_spot_fleet', params)

    def delete(self, params=None):
        '''
            Deletes an existing AWS EC2 Spot Fleet Request.
        '''
        return self.make_client_call('cancel_spot_fleet_requests', params)

    def list_spot_fleet_instances(self, params=None):
        '''
            Checks current instances of AWS EC2 Spot Fleet Request.
        '''
        params = params or {SpotFleetRequestIds: [self.resource_id]}
        return self.make_client_call('describe_spot_fleet_instances', params)


@decorators.aws_resource(EC2SpotFleetRequest,
                         resource_type=RESOURCE_TYPE,
                         waits_for_status=False)
def prepare(ctx, iface, resource_config, **_):
    '''Prepares an AWS EC2 Vpc'''
    # Save the parameters
    ctx.instance.runtime_properties['resource_config'] = resource_config


@decorators.aws_resource(EC2SpotFleetRequest, RESOURCE_TYPE)
#@decorators.wait_for_status(status_good=['active', 'fulfilled'],
#                            status_pending=['submitted', 'pending_fulfillment'])
@decorators.tag_resources
def create(ctx, iface, resource_config, **_):
    '''Creates an AWS EC2 Spot Fleet Request'''
    params = utils.clean_params(
        dict() if not resource_config else resource_config.copy())

    # Actually create the resource
    create_response = iface.create(params)
    ctx.logger.info("yaniv log response = {}".format(create_response))
    ctx.instance.runtime_properties['create_response'] = \
        utils.JsonCleanuper(create_response).to_dict()

    spot_fleed_request_id = create_response.get(SpotFleetRequestId, '')
    iface.update_resource_id(spot_fleed_request_id)
    utils.update_resource_id(ctx.instance, spot_fleed_request_id)
    time.sleep(15)
    ctx.instance.runtime_properties['describe'] = \
        iface.list_spot_fleet_instances(
            {'SpotFleetRequestId': iface.resource_id})


# def postcreate(ctx, iface, resource_config, **_):
#     '''Creates an AWS EC2 Spot Fleet Request'''
#     ctx.instance.runtime_properties['describe'] = \
#         iface.list_spot_fleet_instances(
#             {'SpotFleetRequestId': iface.resource_id})

@decorators.aws_resource(EC2SpotFleetRequest,
                         RESOURCE_TYPE,
                         ignore_properties=True,
                         waits_for_status=False)
def poststart(ctx, iface, resource_config, wait_for_target_capacity=True, **_):
    if not wait_for_target_capacity:
        return
    target_capacity = resource_config.get('TargetCapacity')
    spot_fleet_instances = iface.list_spot_fleet_instances()
    active = spot_fleet_instances.get('ActiveInstances')
    if not len(active) == target_capacity:
        raise OperationRetry(
            'Waiting for active instance number to match target capacity.')
    if MULTI_ID not in ctx.instance.runtime_properties:
        ctx.instance.runtime_properties[MULTI_ID] = []
    for instance in active:
        instance_id = instance.get(INSTANCE_ID, '')
        ctx.instance.runtime_properties[MULTI_ID].append(instance_id)


@decorators.aws_resource(EC2SpotFleetRequest,
                         RESOURCE_TYPE,
                         ignore_properties=True,
                         waits_for_status=False)
@decorators.untag_resources
def delete(iface, resource_config, terminate_instances=False, **_):
    '''Deletes an AWS EC2 Vpc'''
    params = dict()
    params.update({SpotFleetRequestIds: [iface.resource_id]})
    params.update({'TerminateInstances': terminate_instances})
    try:
        iface.delete(params)
    except ClientError:
        pass
    finally:
        if iface.active_instances:
            raise OperationRetry(
                'Waiting while all spot fleet instances are terminated.')

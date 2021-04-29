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
    Route53.HostedZone
    ~~~~~~~~~~~~~~~~~~
    AWS Route53 Hosted Zone interface
'''
# Standard Imports
from time import sleep

# Third party imports
from botocore.exceptions import ClientError

from cloudify_aws.common._compat import text_type

# Local imports
from cloudify_aws.common import decorators, utils
from cloudify_aws.common.connection import Boto3Connection
from cloudify_aws.route53 import Route53Base

RESOURCE_TYPE = 'Route53 Hosted Zone'


class Route53HostedZone(Route53Base):
    '''
        AWS Route53 Hosted Zone interface
    '''
    def __init__(self, ctx_node, resource_id=None, client=None, logger=None):
        Route53Base.__init__(self, ctx_node, resource_id, client, logger)
        self.type_name = RESOURCE_TYPE

    @property
    def properties(self):
        '''Gets the properties of an external resource'''
        try:
            return self.client.get_hosted_zone(Id=self.resource_id)
        except ClientError:
            return None

    @property
    def status(self):
        '''Gets the status of an external resource'''
        return 'available' if self.properties else None

    def create(self, params):
        '''
            Create a new AWS Route53 Hosted Zone.
        '''
        return self.make_client_call('create_hosted_zone', params)

    def delete(self, params=None):
        '''
            Deletes an existing AWS Route53 Hosted Zone.
        '''
        params = params or dict()
        params.update(dict(Id=self.resource_id))
        self.logger.debug('Deleting %s with parameters: %s'
                          % (self.type_name, params))
        return self.client.delete_hosted_zone(**params)

    def change_resource_record_sets(self, params):
        '''
            Changes an AWS Route53 Resource Record Set.
        '''
        self.logger.debug(
            'Changing Route53 Resource Record Set in %s with parameters: %s'
            % (self.type_name, params))
        res = self.client.change_resource_record_sets(**params)
        self.logger.debug('Response: %s' % res)
        return res['ChangeInfo']

    def list_resource_record_sets(self, params):
        '''
            Gets a list of all AWS Route53 Resource Record Sets.
        '''
        self.logger.debug(
            'Listing Route53 Resource Record Sets in %s with parameters: %s'
            % (self.type_name, params))
        res = self.client.list_resource_record_sets(**params)
        self.logger.debug('Response: %s' % res)
        return res['ResourceRecordSets']


@decorators.aws_resource(Route53HostedZone, RESOURCE_TYPE)
def prepare(ctx, resource_config, iface, **_):
    '''Prepares an AWS Route53 Hosted Zone'''
    # Save the parameters
    ctx.instance.runtime_properties['resource_config'] = resource_config


@decorators.aws_resource(Route53HostedZone, RESOURCE_TYPE)
def create(ctx, iface, resource_config, **_):
    '''Creates an AWS Route53 Hosted Zone'''
    # Build API params
    params = \
        dict() if not resource_config else resource_config.copy()
    if iface.resource_id:
        params.update({'Name': iface.resource_id})
    if not params.get('CallerReference'):
        params.update(dict(CallerReference=text_type(ctx.instance.id)))
    # Actually create the resource
    create_response = iface.create(params)['HostedZone']['Id']
    iface.update_resource_id(create_response)
    utils.update_resource_id(ctx.instance, create_response)
    utils.update_resource_arn(ctx.instance, create_response)


@decorators.aws_resource(Route53HostedZone, RESOURCE_TYPE,
                         ignore_properties=True)
@decorators.wait_for_delete(status_pending=['available'])
def delete(ctx, iface, resource_config, resource_type,
           force_delete, **_):
    '''Deletes an AWS Route53 Hosted Zone'''
    if force_delete:
        ctx.logger.warn(
            'Attempting to purge all Resource Record Sets from the %s'
            % resource_type)
        # Iterate over all Record Sets
        for record in iface.list_resource_record_sets(dict(
                HostedZoneId=iface.resource_id,
                MaxItems='100')):
            # Skip default record types
            if record['Type'] in ['NS', 'SOA']:
                continue
            # Delete the Record Set
            iface.change_resource_record_sets(dict(
                HostedZoneId=iface.resource_id,
                ChangeBatch=dict(
                    Changes=[dict(
                        Action='DELETE',
                        ResourceRecordSet=record)])))
            # Sleep to avoid hitting AWS throttling / limits
            sleep(1)
    iface.delete(resource_config)


@decorators.aws_relationship(Route53HostedZone, RESOURCE_TYPE)
def prepare_assoc(ctx, iface, resource_config, **inputs):
    '''Prepares to associate an Route53 Hosted Zone to something else'''
    if utils.is_node_type(ctx.target.node,
                          'cloudify.aws.nodes.VPC'):
        vpc_id = utils.get_resource_id(
            node=ctx.target.node,
            instance=ctx.target.instance,
            raise_on_missing=True)
        # Update VPC configuration
        vpccfg = ctx.source.instance.runtime_properties[
            'resource_config'].get('VPC', dict())
        vpccfg['VPCId'] = vpc_id
        if not vpccfg.get('VPCRegion'):
            vpccfg['VPCRegion'] = detect_vpc_region(Boto3Connection(
                ctx.source.node).client('ec2'), vpc_id)
        ctx.source.instance.runtime_properties[
            'resource_config']['VPC'] = vpccfg


@decorators.aws_relationship(Route53HostedZone, RESOURCE_TYPE)
def detach_from(ctx, iface, resource_config, **_):
    '''Detaches an Route53 Hosted Zone from something else'''
    pass


def detect_vpc_region(client, vpc_id):
    '''Attempts to detect which AWS Region a VPC is associated with'''
    # Get an associated Subnet
    subnets = client.describe_subnets(**dict(
        Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}]))
    if not subnets or not subnets.get('Subnets'):
        return None
    subnet_zone_id = subnets['Subnets'][0]['AvailabilityZone']
    # Get an associated Availability Zone
    zones = client.describe_availability_zones(**dict(
        Filters=[{'Name': 'zone-name', 'Values': [subnet_zone_id]}]))
    if not zones or not zones.get('AvailabilityZones'):
        return None
    # Get an associated Region
    return zones['AvailabilityZones'][0]['RegionName']

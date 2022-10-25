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
    EC2.NATGateway
    ~~~~~~~~~~~~~~
    AWS EC2 NAT Gateway interface
"""
# Boto
from botocore.exceptions import ClientError

# Cloudify
from cloudify_aws.common import decorators, utils
from cloudify_aws.ec2 import EC2Base
from cloudify.exceptions import NonRecoverableError

RESOURCE_TYPE = 'EC2 NAT Gateway'
NATGATEWAY = 'NatGateway'
NATGATEWAYS = 'NatGateways'
NATGATEWAY_ID = 'NatGatewayId'
NATGATEWAY_IDS = 'NatGatewayIds'
SUBNET_ID = 'SubnetId'
ALLOCATION_ID = 'AllocationId'
ALLOCATION_ID_DEPRECATED = 'allocation_id'
SUBNET_TYPE = 'cloudify.nodes.aws.ec2.Subnet'
SUBNET_TYPE_DEPRECATED = 'cloudify.aws.nodes.Subnet'
ELASTICIP_TYPE = 'cloudify.nodes.aws.ec2.ElasticIP'
ELASTICIP_TYPE_DEPRECATED = 'cloudify.aws.nodes.ElasticIP'


class EC2NatGateway(EC2Base):
    """
        EC2 NAT Gateway interface
    """

    def __init__(self, ctx_node, resource_id=None, client=None, logger=None):
        EC2Base.__init__(self, ctx_node, resource_id, client, logger)
        self.type_name = RESOURCE_TYPE
        self._describe_call = 'describe_nat_gateways'
        self._type_key = NATGATEWAYS
        self._id_key = NATGATEWAY_ID
        self._ids_key = NATGATEWAY_IDS

    @property
    def status(self):
        """Gets the status of an external resource"""
        props = self.properties
        if not props:
            return None
        return props['State']

    @property
    def check_status(self):
        if self.status in ['available']:
            return 'OK'
        return 'NOT OK'

    def create(self, params):
        """
            Create a new AWS EC2 NAT Gateway.
        """
        return self.make_client_call('create_nat_gateway', params)

    def delete(self, params=None):
        """
            Deletes an existing AWS EC2 NAT Gateway.
        """
        self.logger.debug('Deleting %s with parameters: %s'
                          % (self.type_name, params))
        res = self.client.delete_nat_gateway(**params)
        self.logger.debug('Response: %s' % res)
        return res


@decorators.aws_resource(EC2NatGateway, resource_type=RESOURCE_TYPE)
def prepare(ctx, resource_config, **_):
    """Prepares an AWS EC2 NAT Gateway"""
    # Save the parameters
    ctx.instance.runtime_properties['resource_config'] = resource_config


@decorators.aws_resource(EC2NatGateway, RESOURCE_TYPE)
@decorators.wait_for_status(
    status_good=['available'],
    status_pending=['pending'],
    fail_on_missing=False)
@decorators.tag_resources
def create(ctx, iface, resource_config, **_):
    """Creates an AWS EC2 NAT Gateway"""

    subnet_id = resource_config.get(SUBNET_ID)
    if not subnet_id:
        subnet_id = \
            utils.find_resource_id_by_type(
                ctx.instance, SUBNET_TYPE) or \
            utils.find_resource_id_by_type(
                ctx.instance, SUBNET_TYPE_DEPRECATED)
        resource_config.update({SUBNET_ID: subnet_id})

    allocation_id = resource_config.get(ALLOCATION_ID)
    if not allocation_id:
        targ = \
            utils.find_rel_by_node_type(
                ctx.instance,
                ELASTICIP_TYPE) or \
            utils.find_rel_by_node_type(
                ctx.instance,
                ELASTICIP_TYPE_DEPRECATED)
        if targ:
            allocation_id = \
                targ.target.instance.runtime_properties.get(
                    ALLOCATION_ID_DEPRECATED)

    ctx.instance.runtime_properties['allocation_id'] = \
        allocation_id
    if 'ConnectivityType' in resource_config and \
            resource_config['ConnectivityType'] != 'private':
        resource_config[ALLOCATION_ID] = allocation_id

    # Actually create the resource
    try:
        create_response = iface.create(resource_config)['NatGateway']
    except ClientError as e:
        if 'MissingParameter' in str(e):
            raise NonRecoverableError(
                'AWS create_nat_gateway api has changed. '
                'it is now required for private gateways '
                'to specify in the blueprint:\n '
                '"resource_config:\n'
                '    kwargs:\n'
                '        ConnectivityType: private"')
        raise e
    ctx.instance.runtime_properties['create_response'] = \
        utils.JsonCleanuper(create_response).to_dict()
    utils.update_resource_id(
        ctx.instance, create_response.get(NATGATEWAY_ID))


@decorators.aws_resource(EC2NatGateway, RESOURCE_TYPE,
                         ignore_properties=True)
@decorators.wait_for_delete(
    status_deleted=['deleted'],
    status_pending=['deleting', 'pending', 'available'])
@decorators.untag_resources
def delete(iface, resource_config, dry_run=False, **_):
    """Deletes an AWS EC2 NAT Gateway"""
    resource_config['DryRun'] = dry_run
    nat_gateway_id = resource_config.get(NATGATEWAY_ID)

    if not nat_gateway_id:
        nat_gateway_id = iface.resource_id

    resource_config.update({NATGATEWAY_ID: nat_gateway_id})
    iface.delete(resource_config)


interface = EC2NatGateway

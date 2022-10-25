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
    EC2.Customer Gateway
    ~~~~~~~~~~~~~~
    AWS EC2 Customer Gateway interface
"""
# Boto
from botocore.exceptions import ClientError, ParamValidationError

# Cloudify
from cloudify_aws.common import decorators, utils
from cloudify_aws.ec2 import EC2Base

RESOURCE_TYPE = 'EC2 Customer Gateway'
CUSTOMERGATEWAYS = 'CustomerGateways'
CUSTOMERGATEWAY_ID = 'CustomerGatewayId'
CUSTOMERGATEWAY_IDS = 'CustomerGatewayIds'
PUBLIC_IP = 'PublicIp'
ELASTICIP_TYPE = 'cloudify.nodes.aws.ec2.ElasticIP'
ELASTICIP_TYPE_DEPRECATED = 'cloudify.aws.nodes.ElasticIP'


class EC2CustomerGateway(EC2Base):
    """
        EC2 Customer Gateway interface
    """
    def __init__(self, ctx_node, resource_id=None, client=None, logger=None):
        EC2Base.__init__(self, ctx_node, resource_id, client, logger)
        self.type_name = RESOURCE_TYPE

    @property
    def properties(self):
        """Gets the properties of an external resource"""
        if not self.resource_id:
            return
        params = {CUSTOMERGATEWAY_IDS: [self.resource_id]}
        try:
            resources = \
                self.client.describe_customer_gateways(**params)
        except (ClientError, ParamValidationError):
            pass
        else:
            return resources.get(CUSTOMERGATEWAYS)[0] if resources else None

    @property
    def status(self):
        """Gets the status of an external resource"""
        props = self.properties
        if not props:
            return None
        return props['State']

    def create(self, params):
        """
            Create a new AWS EC2 Customer Gateway.
        """
        return self.make_client_call('create_customer_gateway', params)

    def delete(self, params=None):
        """
            Deletes an existing AWS EC2 Customer Gateway.
        """
        self.logger.debug('Deleting %s with parameters: %s'
                          % (self.type_name, params))
        res = self.client.delete_customer_gateway(**params)
        self.logger.debug('Response: %s' % res)
        return res


@decorators.aws_resource(EC2CustomerGateway,
                         resource_type=RESOURCE_TYPE,
                         waits_for_status=False)
def prepare(ctx, resource_config, **_):
    """Prepares an AWS EC2 Customer Gateway"""
    # Save the parameters
    ctx.instance.runtime_properties['resource_config'] = resource_config


@decorators.aws_resource(EC2CustomerGateway, RESOURCE_TYPE)
@decorators.wait_for_status(status_good=['available'],
                            status_pending=['pending'])
@decorators.tag_resources
def create(ctx, iface, resource_config, **_):
    """Creates an AWS EC2 Customer Gateway"""

    public_ip = resource_config.get(PUBLIC_IP)
    if not public_ip:
        targ = \
            utils.find_rel_by_node_type(ctx.instance, ELASTICIP_TYPE)
        if targ:
            public_ip = \
                targ.target.instance.runtime_properties \
                    .get(ELASTICIP_TYPE_DEPRECATED)
        resource_config.update({PUBLIC_IP: public_ip})

    # Actually create the resource
    create_response = iface.create(resource_config)['CustomerGateway']
    ctx.instance.runtime_properties['create_response'] = \
        utils.JsonCleanuper(create_response).to_dict()
    utils.update_resource_id(ctx.instance,
                             create_response.get(CUSTOMERGATEWAY_ID))


@decorators.aws_resource(EC2CustomerGateway,
                         RESOURCE_TYPE,
                         ignore_properties=True)
@decorators.wait_for_delete(status_deleted=['deleted'],
                            status_pending=['available', 'deleting'])
@decorators.untag_resources
def delete(iface, resource_config, dry_run=False, **_):
    """Deletes an AWS EC2 Customer Gateway"""
    resource_config['DryRun'] = dry_run

    customer_gateway_id = resource_config.get(CUSTOMERGATEWAY_ID)

    if not customer_gateway_id:
        customer_gateway_id = iface.resource_id

    resource_config.update({CUSTOMERGATEWAY_ID: customer_gateway_id})
    iface.delete(resource_config)

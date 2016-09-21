########
# Copyright (c) 2015 GigaSpaces Technologies Ltd. All rights reserved
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

# Cloudify imports
from . import constants
from core.base import AwsBaseNode
from ec2.utils import set_external_resource_id
from cloudify import ctx
from cloudify.decorators import operation
from cloudify.exceptions import NonRecoverableError


@operation
def creation_validation(**_):
    return Subnet().creation_validation()


@operation
def create_subnet(**_):
    return Subnet().created()


@operation
def start_subnet(**_):
    return Subnet().started()


@operation
def delete_subnet(**_):
    return Subnet().deleted()


class Subnet(AwsBaseNode):

    def __init__(self):
        super(Subnet, self).__init__(
            constants.SUBNET['AWS_RESOURCE_TYPE'],
            constants.SUBNET['REQUIRED_PROPERTIES']
        )
        self.not_found_error = constants.SUBNET['NOT_FOUND_ERROR']
        self.get_all_handler = {
            'function': self.client.get_all_subnets,
            'argument': '{0}_ids'.format(constants.SUBNET['AWS_RESOURCE_TYPE'])
        }

    def create(self):
        if ctx.operation.retry_number == 0:
            create_args = self._generate_creation_args()
            subnet = self.execute(self.client.create_subnet,
                                  create_args, raise_on_falsy=True)
            self.resource_id = subnet.id
        else:
            subnet = self.get_resource()
        # If the operation is still pending, set the ID and retry
        ctx.logger.debug('Subnet response: {0}'.format(vars(subnet)))
        if subnet.state == 'pending':
            set_external_resource_id(self.resource_id, ctx.instance)
            return ctx.operation.retry(
                message='Waiting to verify that AWS resource {0} '
                'has been added to your account.'.format(self.resource_id))
        return True

    def _generate_creation_args(self):

        relationships = \
            self.get_related_targets_and_types(ctx.instance.relationships)

        vpc_ids = self.get_target_ids_of_relationship_type(
            constants.SUBNET_IN_VPC, relationships)

        if not len(vpc_ids) == 1:
            raise NonRecoverableError(
                'subnet can only be connected to one vpc')

        vpc = self.filter_for_single_resource(
            self.client.get_all_vpcs,
            {'vpc_ids': vpc_ids[0]},
            constants.VPC['NOT_FOUND_ERROR']
        )

        create_args = dict(
            vpc_id=vpc.id,
            cidr_block=ctx.node.properties['cidr_block']
        )

        if ctx.node.properties[constants.AVAILABILITY_ZONE]:
            create_args.update(
                {
                    constants.AVAILABILITY_ZONE:
                    ctx.node.properties[constants.AVAILABILITY_ZONE]
                }
            )

        return create_args

    def start(self):
        return True

    def delete(self):
        delete_args = dict(subnet_id=self.resource_id)
        return self.execute(self.client.delete_subnet,
                            delete_args, raise_on_falsy=True)

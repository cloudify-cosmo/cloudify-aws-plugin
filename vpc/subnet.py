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

from . import constants
from core.base import AwsBaseNode
from cloudify import ctx
from cloudify.decorators import operation
from cloudify.exceptions import NonRecoverableError

RESOURCE_TYPE = 'subnet'


@operation
def creation_validation(**_):
    return Subnet().creation_validation()


@operation
def create_subnet(args, **_):
    return Subnet(override_args=args).created()


@operation
def delete_subnet(**_):
    return Subnet().deleted()


class Subnet(AwsBaseNode):

    def __init__(self, override_args=None):
        super(Subnet, self).__init__(
            RESOURCE_TYPE, constants.SUBNET_REQUIRED_PROPERTIES
        )
        self.InvalidNotFoundError = 'InvalidSubnetID.NotFound'
        self.get_all_function = self.client.get_all_subnets
        self.create_args_override = override_args

    def create(self):
        create_args = self.generate_create_args()
        subnet = self.raise_on_none(self.client.create_subnet, create_args)
        self.resource_id = subnet.id
        return True

    def generate_create_args(self):

        relationships = \
            self.get_related_targets_and_types(ctx.instance.relationships)

        vpc_ids = self.get_target_ids_of_relationship_type(
            constants.SUBNET_VPC_RELATIONSHIP, relationships)

        if len(vpc_ids) > 1:
            raise NonRecoverableError(
                'subnet can only be connected to one vpc')

        vpc = self.verify_resource_in_account(vpc_ids[0],
                                              self.client.get_all_vpcs)

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

        if self.create_args_override:
            create_args.update(self.create_args_override)

        return create_args

    def delete(self):
        delete_args = self.generate_delete_args()
        return self.raise_on_none(self.client.delete_subnet, delete_args)

    def generate_delete_args(self):
        return dict(subnet_id=self.resource_id)

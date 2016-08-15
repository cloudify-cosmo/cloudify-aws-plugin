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
from cloudify_aws import constants, connection, utils
from cloudify_aws.base import AwsBaseNode
from cloudify import ctx
from cloudify.decorators import operation
from cloudify.exceptions import NonRecoverableError


@operation
def creation_validation(**_):
    return Subnet().creation_validation()


@operation
def create_subnet(args=None, **_):
    return Subnet().created(args)


@operation
def start_subnet(args=None, **_):
    return Subnet().started(args)


@operation
def delete_subnet(args=None, **_):
    return Subnet().deleted(args)


class Subnet(AwsBaseNode):

    def __init__(self):
        super(Subnet, self).__init__(
            constants.SUBNET['AWS_RESOURCE_TYPE'],
            constants.SUBNET['REQUIRED_PROPERTIES'],
            client=connection.VPCConnectionClient().client()
        )
        self.not_found_error = constants.SUBNET['NOT_FOUND_ERROR']
        self.get_all_handler = {
            'function': self.client.get_all_subnets,
            'argument': '{0}_ids'.format(constants.SUBNET['AWS_RESOURCE_TYPE'])
        }

    def create(self, args):
        create_args = utils.update_args(
            self._generate_creation_args(),
            args)
        subnet = self.execute(self.client.create_subnet,
                              create_args, raise_on_falsy=True)
        self.resource_id = subnet.id
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

    def start(self, args):
        return True

    def delete(self, args):
        delete_args = dict(subnet_id=self.resource_id)
        delete_args = utils.update_args(delete_args, args)
        return self.execute(self.client.delete_subnet,
                            delete_args, raise_on_falsy=True)

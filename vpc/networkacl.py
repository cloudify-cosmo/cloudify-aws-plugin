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
from ec2 import utils as ec2_utils
from . import constants
from core.base import AwsBaseNode, AwsBaseRelationship
from cloudify import ctx
from cloudify.decorators import operation
from cloudify.exceptions import NonRecoverableError


@operation
def creation_validation(**_):
    return NetworkAcl().creation_validation()


@operation
def create_network_acl(**_):
    return NetworkAcl().created()


@operation
def start_network_acl(**_):
    return NetworkAcl().started()


@operation
def delete_network_acl(**_):
    return NetworkAcl().deleted()


@operation
def associate_network_acl(**_):
    return NetworkAclSubnetAssociation().associated()


@operation
def disassociate_network_acl(**_):
    return NetworkAclSubnetAssociation().disassociated()


class NetworkAclSubnetAssociation(AwsBaseRelationship):

    def __init__(self):
        super(NetworkAclSubnetAssociation, self).__init__()
        self.association_id = \
            ctx.source.instance.runtime_properties\
            .get('association_id', None)\
            if ctx.source.instance.runtime_properties\
            .get('association_id', None)\
            else {}
        self.source_get_all_handler = {
            'function': self.client.get_all_network_acls,
            'argument':
            '{0}_ids'.format(constants.NETWORK_ACL['AWS_RESOURCE_TYPE'])
        }

    def associate(self):
        assoicate_args = dict(
            network_acl_id=self.source_resource_id,
            subnet_id=self.target_resource_id
        )
        self.association_id = \
            self.execute(self.client.associate_network_acl,
                         assoicate_args, raise_on_falsy=True)
        return True

    def disassociate(self):
        disassociate_args = dict(
            subnet_id=self.target_resource_id,
            vpc_id=ctx.source.instance.runtime_properties['vpc_id']
        )
        return self.execute(self.client.disassociate_network_acl,
                            disassociate_args, raise_on_falsy=True)

    def post_associate(self):
        ctx.source.instance.runtime_properties['association_id'] = \
            self.association_id

    def post_disassociate(self):
        ec2_utils.unassign_runtime_property_from_resource(
            'association_id', ctx.source.instance)


class NetworkAcl(AwsBaseNode):

    def __init__(self):
        super(NetworkAcl, self).__init__(
            constants.NETWORK_ACL['AWS_RESOURCE_TYPE'],
            constants.NETWORK_ACL['REQUIRED_PROPERTIES']
        )
        self.not_found_error = constants.NETWORK_ACL['NOT_FOUND_ERROR']
        self.get_all_handler = {
            'function': self.client.get_all_network_acls,
            'argument':
            '{0}_ids'.format(constants.NETWORK_ACL['AWS_RESOURCE_TYPE'])
        }

    def create(self):
        create_args = self.generate_create_args()
        network_acl = self.execute(self.client.create_network_acl,
                                   create_args, raise_on_falsy=True)
        self.resource_id = network_acl.id
        ctx.instance.runtime_properties['vpc_id'] = create_args['vpc_id']
        self.add_entries_to_network_acl()
        return True

    def generate_create_args(self):
        relationships = \
            self.get_related_targets_and_types(ctx.instance.relationships)
        vpc_ids = \
            self.get_target_ids_of_relationship_type(
                constants.NETWORK_ACL_IN_VPC_RELATIONSHIP, relationships)
        if not len(vpc_ids) == 1:
            raise NonRecoverableError(
                'network acl can only be connected to one vpc')
        vpc = \
            self.filter_for_single_resource(
                self.client.get_all_vpcs,
                {'vpc_ids': vpc_ids[0]},
                constants.VPC['NOT_FOUND_ERROR']
            )
        create_args = dict(vpc_id=vpc.id)
        return create_args

    def add_entries_to_network_acl(self):

        ctx.logger.info(
            'adding network acl entries to network acl {0}'
            .format(self.resource_id))

        for acl_network_entry in ctx.node.properties['acl_network_entries']:
            acl_network_entry['network_acl_id'] = self.resource_id
            self.create_network_acl_entry(acl_network_entry)

    def create_network_acl_entry(self, args):
        ctx.logger.info('create network acl entry {0}'.format(args))
        return self.execute(self.client.create_network_acl_entry,
                            args, raise_on_falsy=True)

    def start(self):
        return True

    def delete(self):
        delete_args = dict(network_acl_id=self.resource_id)
        return self.execute(self.client.delete_network_acl,
                            delete_args, raise_on_falsy=True)

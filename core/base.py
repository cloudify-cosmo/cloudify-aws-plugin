#########
# Copyright (c) 2015 GigaSpaces Technologies Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
#  * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  * See the License for the specific language governing permissions and
#  * limitations under the License.

from boto import exception
from ec2 import utils as ec2_utils
from ec2 import constants
from vpc import connection
from cloudify.exceptions import NonRecoverableError, RecoverableError
from cloudify import ctx


class AwsBase(object):

    def __init__(self,
                 client=None
                 ):
        self.client = client if client else connection.VPCConnectionClient().client()

    def communicate(self, fn, args=None):

        try:
            output = fn(**args) if args else fn()
        except exception.EC2ResponseError as e:
            raise NonRecoverableError('{0}'.format(str(e)))
        except exception.BotoServerError as e:
            raise NonRecoverableError('{0}'.format(str(e)))

        return output

    def raise_on_none(self, fn, args=None):

        output = self.communicate(fn, args) if args else self.communicate(fn)

        if not output:
            raise NonRecoverableError('Function returned False.')

        return output

    def verify_resource_in_account(self, resource_id, get_all_function):

        try:
            list_of_matching_resources = get_all_function([resource_id])
        except exception.EC2ResponseError as e:
            if 'NotFound' in e:
                return None
            raise NonRecoverableError('{0}'.format(str(e)))
        except exception.BotoServerError as e:
            raise NonRecoverableError('{0}'.format(str(e)))

        if list_of_matching_resources:
            for resource in list_of_matching_resources:
                if resource.id == resource_id:
                    return resource

        return None

    def retry_on_ec2_response_error(self, fn, args=None):

        try:
            output = fn(**args) if args else fn()
        except exception.EC2ResponseError as e:
            raise RecoverableError('{0}'.format(str(e)))
        return output

    def get_resource(self, resource_id, get_all_function):
        return self.verify_resource_in_account(resource_id, get_all_function)

    def get_related_targets_and_types(self, relationships):
        """

        :param relationships: should be ctx.instance.relationships
        or ctx.source/target.instance.relationships
        :return: targets_and_types a dict of structure
        relationship-type: relationship_target_id
        """

        targets_and_types = dict()

        if len(relationships) > 0:

            for relationship in relationships:
                targets_and_types.update(
                    {
                        relationship.type:
                            relationship.target.instance
                            .runtime_properties.get(
                                constants.EXTERNAL_RESOURCE_ID)
                    }
                )

        return targets_and_types

    def get_target_ids_of_relationship_type(self, relationship_type, relationships):

        target_ids = []

        for key, value in relationships.items():

            if relationship_type in key:
                target_ids.append(value)

        return target_ids

    def raise_cannot_use_external_resource(self, resource_id):
        raise NonRecoverableError(
            'Cannot use_external_resource because resource {0} '
            'is not in this account.'.format(resource_id))


class AwsBaseRelationship(AwsBase):

    def __init__(self, client=None):
        super(AwsBaseRelationship, self).__init__(client)
        self.source_resource_id = \
            ctx.source.instance.runtime_properties.get(
                constants.EXTERNAL_RESOURCE_ID, None) if \
            constants.EXTERNAL_RESOURCE_ID in \
            ctx.source.instance.runtime_properties.keys() else \
            ctx.source.node.properties['resource_id']
        self.target_resource_id = ctx.target.instance.runtime_properties.get(
                constants.EXTERNAL_RESOURCE_ID, None) if \
            constants.EXTERNAL_RESOURCE_ID in \
            ctx.target.instance.runtime_properties.keys() else \
            ctx.target.node.properties['resource_id']
        self.source_external_resource = ctx.source.node.properties['use_external_resource']
        self.target_external_resource = ctx.target.node.properties['use_external_resource']
        self.source_get_all_matching = None
        self.target_get_all_matching = None
        self.source_get_all_argument = None
        self.target_get_all_argument = None

    def associate(self):
        return False

    def associated(self):
        if self.associate_external_resource():
            return self.post_associate()
        elif self.associate():
            return self.post_associate()

        raise NonRecoverableError('Unable to associate {0} with {1}.'.format(self.source_resource_id, self.target_resource_id))

    def associate_external_resource(self):

        if not self.source_external_resource:
            return False

        resource = self.source_get_all_matching([self.source_resource_id])[0]

        if resource is None:
            self.raise_cannot_use_external_resource(self.source_resource_id)

        ctx.logger.info('not associating external resource {0}.'.format(resource.id))

        return True

    def disassociate(self):
        return False

    def disassociated(self):
        if self.disassociate_external_resource():
            return self.post_disassociate()
        elif self.disassociate():
            return self.post_disassociate()
        raise NonRecoverableError('Unable to disassociate {0} from {1}.'.format(self.source_resource_id, self.target_resource_id))

    def disassociate_external_resource(self):
        if not self.source_external_resource:
            return False
        resource = self.source_get_all_matching([self.source_resource_id])[0]
        ctx.logger.info('not disassociating external resource {0}.'.format(resource.id))
        return True

    def post_associate(self):
        return True

    def post_disassociate(self):
        return True

class AwsBaseNode(AwsBase):

    def __init__(self,
                 aws_resource_type,
                 required_properties,
                 aws_resource_types=None,
                 client=None
                 ):
        super(AwsBaseNode, self).__init__(client)

        self.aws_resource_type = aws_resource_type
        self.cloudify_node_instance_id = ctx.instance.id
        self.cloudify_node_type = ctx.node.type
        self.cloudify_type_hierarchy = ctx.node.type_hierarchy
        self.resource_id = \
            ctx.instance.runtime_properties.get(
                constants.EXTERNAL_RESOURCE_ID, None) if \
                constants.EXTERNAL_RESOURCE_ID in \
                ctx.instance.runtime_properties.keys() else \
                ctx.node.properties['resource_id']
        self.external_resource = ctx.node.properties['use_external_resource']
        self.required_properties = required_properties
        self.aws_resource_type_pl = ''.format(self.aws_resource_type + 's') if not aws_resource_type else aws_resource_type
        self.get_all_function = {}
        self.get_all_argument = '{0}_ids'.format(self.aws_resource_type)
        self.possible_relationship_type = []
        self.InvalidNotFoundError = {}

    def creation_validation(self):
        """ This validates all VPC Nodes before bootstrap.
        """

        resource = self.get_resource()

        for property_key in self.required_properties:
            ec2_utils.validate_node_property(property_key, ctx.node.properties)

        if self.external_resource and not resource:
            raise NonRecoverableError(
                'External resource, but the supplied {0} does not exist in the account.'.format(self.aws_resource_type))

        if not self.external_resource and resource:
            raise NonRecoverableError(
                'Not external resource, but the supplied {0} exists in the account.'.format(self.aws_resource_type))

    def create(self):
        return False

    def created(self):

        if self.create_external_resource():
            return self.post_create()
        elif self.create():
            return self.post_create()

        raise NonRecoverableError('Unable to create this resource.')

    def create_external_resource(self):

        if not self.external_resource:
            return False

        resources = self.get_all_matching([self.resource_id])

        if not resources:
            self.raise_cannot_use_external_resource(self.resource_id)

        ec2_utils.set_external_resource_id(self.resource_id, ctx.instance)

        return True

    def delete(self):
        return False

    def deleted(self):

        if not self.get_resource():
            raise NonRecoverableError('resource is not in the account: {0}.'.format(self.resource_id))

        if self.delete_external_resource():
            return self.post_delete()
        elif self.delete():
            return self.post_delete()

        raise NonRecoverableError('Unable to delete this resource.')

    def delete_external_resource(self):

        if not self.external_resource:
            return False

        ctx.logger.info('External resource. Not deleting resource {0}.'.format(self.resource_id))

        return True

    def get_all_matching(self, list_of_ids=None):

        args = {self.get_all_argument: list_of_ids}

        try:
            resources = self.get_all_function(**args)
        except exception.EC2ResponseError as e:
            if self.InvalidNotFoundError in str(e):
                resources = self.get_all_function()
                ec2_utils.log_available_resources(resources)
                return None
            raise NonRecoverableError('{0}'.format(str(e)))
        except exception.BotoServerError as e:
            raise NonRecoverableError('{0}'.format(str(e)))

        return resources

    def get_resource(self):

        list_of_matching_resources = self.get_all_matching([self.resource_id])

        if list_of_matching_resources:
            for resource in list_of_matching_resources:
                if resource.id == self.resource_id:
                    return resource

        return None

    def post_create(self):
        ec2_utils.set_external_resource_id(self.resource_id, ctx.instance)
        ctx.logger.info('Created {0} {1}.'.format(self.aws_resource_type, self.resource_id))
        return True

    def post_delete(self):
        ec2_utils.unassign_runtime_property_from_resource(constants.EXTERNAL_RESOURCE_ID, ctx.instance)
        ctx.logger.info('Deleted {0} {1}.'.format(self.aws_resource_type, self.resource_id))
        return True

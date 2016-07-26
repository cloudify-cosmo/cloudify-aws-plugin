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

# Third-party Imports
from boto import exception

# Cloudify imports
from cloudify_aws import utils, constants
from cloudify import ctx
from cloudify.exceptions import NonRecoverableError
from cloudify.decorators import operation
from cloudify_aws.base import AwsBaseNode, AwsBaseRelationship


@operation
def creation_validation(**_):
    return ElasticIP().creation_validation()


@operation
def create(args=None, **_):
    return ElasticIP().created(args)


@operation
def delete(args=None, **_):
    return ElasticIP().deleted(args)


@operation
def associate(args=None, **_):
    return ElasticIPInstanceConnection().associated(args)


@operation
def disassociate(args=None, **_):
    return ElasticIPInstanceConnection().disassociated(args)


class ElasticIPInstanceConnection(AwsBaseRelationship):

    def __init__(self, client=None):
        super(ElasticIPInstanceConnection, self).__init__(client=client)
        self.not_found_error = 'InvalidAssociationID.NotFound'
        self.resource_id = None
        self.source_get_all_handler = {
            'function': self.client.get_all_instances,
            'argument':
                '{0}_ids'.format(constants.INSTANCE['AWS_RESOURCE_TYPE'])
        }

    def associate(self, args=None, **_):
        """ Associates an Elastic IP created by Cloudify with an EC2 Instance
        that was also created by Cloudify.
        """

        instance_id = \
            utils.get_external_resource_id_or_raise(
                    'associate elasticip', ctx.source.instance)
        elasticip = \
            utils.get_external_resource_id_or_raise(
                    'associate elasticip', ctx.target.instance)

        kw = dict(instance_id=instance_id, public_ip=elasticip)

        if constants.ELASTICIP['ALLOCATION_ID'] in \
                ctx.target.instance.runtime_properties:
            kw.pop('public_ip')
            kw.update(
                    {constants.ELASTICIP['ALLOCATION_ID']:
                     ctx.target.instance.runtime_properties[
                             constants.ELASTICIP['ALLOCATION_ID']]})

        try:
            self.execute(self.client.associate_address, kw,
                         raise_on_falsy=True)
        except (exception.EC2ResponseError,
                exception.BotoServerError) as e:
            raise NonRecoverableError('{0}'.format(str(e)))

        return True

    def post_associate(self):

        super(ElasticIPInstanceConnection, self).post_associate()
        ctx.source.instance.runtime_properties['public_ip_address'] = \
            self.target_resource_id
        ctx.target.instance.runtime_properties['instance_id'] = \
            ctx.source.instance.runtime_properties[
                constants.EXTERNAL_RESOURCE_ID]
        vpc_id = ctx.source.instance.runtime_properties.get('vpc_id')
        if vpc_id:
            ctx.target.instance.runtime_properties['vpc_id'] = vpc_id

        return True

    def disassociate(self, args=None, **_):
        """ Disassocates an Elastic IP created by Cloudify from an EC2 Instance
        that was also created by Cloudify.
        """

        elasticip = \
            utils.get_external_resource_id_or_raise(
                    'disassociate elasticip', ctx.target.instance)

        elasticip_object = self._get_address_object_by_id(elasticip)

        if not elasticip_object:
            raise NonRecoverableError(
                    'no matching elastic ip in account: {0}'.format(elasticip))

        disassociate_args = dict(
                public_ip=elasticip_object.public_ip,
                association_id=elasticip_object.association_id
        )

        try:
            self.execute(self.client.disassociate_address,
                         disassociate_args, raise_on_falsy=True)
        except (exception.EC2ResponseError,
                exception.BotoServerError) as e:
            raise NonRecoverableError('{0}'.format(str(e)))

        return True

    def post_disassociate(self):
        super(ElasticIPInstanceConnection, self).post_disassociate()
        utils.unassign_runtime_property_from_resource(
                'public_ip_address', ctx.source.instance)
        utils.unassign_runtime_property_from_resource(
                'instance_id', ctx.target.instance)
        if ctx.source.instance.runtime_properties.get('vpc_id'):
            utils.unassign_runtime_property_from_resource(
                'vpc_id', ctx.target.instance)

        return True

    def _get_address_object_by_id(self, address_id):
        """Returns the elastip object for a given address elastip.

        :param address_id: The ID of a elastip.
        :returns The boto elastip object.
        """

        address = self._get_all_addresses(address=address_id)

        return address[0] if address else address

    def _get_all_addresses(self, address=None):
        """Returns a list of elastip objects for a given address elastip.

        :param address: The ID of a elastip.
        :returns A list of elasticip objects.
        :raises NonRecoverableError: If Boto errors.
        """

        try:
            addresses = self.client.get_all_addresses(address)
        except exception.EC2ResponseError as e:
            if constants.ELASTICIP['NOT_FOUND_ERROR'] in e:
                addresses = self.client.get_all_addresses()
                utils.log_available_resources(addresses)
            return None
        except exception.BotoServerError as e:
            raise NonRecoverableError('{0}'.format(str(e)))

        return addresses

    def get_source_resource(self):
        return self._get_address_object_by_id(self.target_resource_id)


class ElasticIP(AwsBaseNode):

    def __init__(self):
        super(ElasticIP, self).__init__(
                constants.ELASTICIP['AWS_RESOURCE_TYPE'],
                constants.ELASTICIP['REQUIRED_PROPERTIES']
        )
        self.allocation_id = None
        self.not_found_error = constants.ELASTICIP['NOT_FOUND_ERROR']
        self.get_all_handler = {
            'function': self.client.get_all_addresses,
            'argument': 'addresses'
        }

    def create(self, args=None, **_):
        """This allocates an Elastic IP in the connected account."""

        ctx.logger.debug('Attempting to allocate elasticip.')

        provider_variables = utils.get_provider_variables()

        kw = {}
        domain = ctx.node.properties.get(
                constants.ELASTICIP['ELASTIC_IP_DOMAIN_PROPERTY']) or \
            provider_variables.get(constants.ELASTICIP['VPC_DOMAIN'])
        if domain:
            kw[constants.ELASTICIP['ELASTIC_IP_DOMAIN_PROPERTY']] = \
                constants.ELASTICIP['VPC_DOMAIN']

        try:
            address_object = self.execute(self.client.allocate_address,
                                          kw, raise_on_falsy=True)
        except (exception.EC2ResponseError,
                exception.BotoServerError) as e:
            raise NonRecoverableError('{0}'.format(str(e)))

        if constants.ELASTICIP['VPC_DOMAIN'] in address_object.domain:
            ctx.instance.runtime_properties[constants.ELASTICIP[
                'ALLOCATION_ID']] = address_object.allocation_id
            self.allocation_id = address_object.allocation_id

        self.resource_id = address_object.public_ip

        return True

    def delete(self, args=None, **_):
        """This releases an Elastic IP created by Cloudify
        in the connected account.
        """

        elasticip = \
            utils.get_external_resource_id_or_raise(
                    'release elasticip', ctx.instance)

        address_object = self._get_address_object_by_id(elasticip)

        if not address_object:
            raise NonRecoverableError(
                    'Unable to release elasticip. Elasticip not in account.')

        try:
            deleted = address_object.delete()
        except (exception.EC2ResponseError,
                exception.BotoServerError) as e:
            raise NonRecoverableError('{0}'.format(str(e)))

        if not deleted:
            raise NonRecoverableError(
                    'Elastic IP {0} deletion failed for an unknown reason.'
                    .format(address_object.public_ip))

        address = self._get_address_object_by_id(address_object.public_ip)

        if not address:
            utils.unassign_runtime_property_from_resource(
                    constants.ELASTICIP['ALLOCATION_ID'], ctx.instance)
        else:
            return ctx.operation.retry(
                    message='Elastic IP not released. Retrying...')

        return True

    def _get_address_object_by_id(self, address_id):
        """Returns the elastip object for a given address elastip.

        :param address_id: The ID of a elastip.
        :returns The boto elastip object.
        """

        address = self._get_all_addresses(address=address_id)

        return address[0] if address else address

    def _get_all_addresses(self, address=None):
        """Returns a list of elastip objects for a given address elastip.

        :param address: The ID of a elastip.
        :returns A list of elasticip objects.
        :raises NonRecoverableError: If Boto errors.
        """

        try:
            addresses = self.client.get_all_addresses(address)
        except exception.EC2ResponseError as e:
            if constants.ELASTICIP['NOT_FOUND_ERROR'] in e:
                addresses = self.client.get_all_addresses()
                utils.log_available_resources(addresses)
            return None
        except exception.BotoServerError as e:
            raise NonRecoverableError('{0}'.format(str(e)))

        return addresses

    def get_resource(self):
        return self._get_address_object_by_id(
                ctx.node.properties['resource_id'])

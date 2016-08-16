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
from cloudify_aws.base import AwsBaseNode


@operation
def creation_validation(**_):
    return SecurityGroup().creation_validation()


@operation
def create(args=None, **_):
    return SecurityGroup().created(args)


@operation
def start(args=None, **_):
    return SecurityGroup().started(args)


@operation
def delete(args=None, **_):
    return SecurityGroup().deleted(args)


class SecurityGroup(AwsBaseNode):

    def __init__(self):
        super(SecurityGroup, self).__init__(
                constants.SECURITYGROUP['AWS_RESOURCE_TYPE'],
                constants.SECURITYGROUP['REQUIRED_PROPERTIES']
        )
        self.not_found_error = constants.SECURITYGROUP['NOT_FOUND_ERROR']
        self.get_all_handler = {
            'function': self.client.get_all_security_groups,
            'argument': '{0}_ids'
            .format(constants.SECURITYGROUP['AWS_RESOURCE_TYPE'])
        }

    def create(self, args=None, **_):

        """Creates an EC2 security group.
        """
        name = utils.get_resource_id()

        create_args = dict(
                name=name,
                description=ctx.node.properties['description'],
                vpc_id=self._get_connected_vpc()
        )

        create_args = utils.update_args(create_args, args)

        if ctx.operation.retry_number == 0 and constants.EXTERNAL_RESOURCE_ID \
                not in ctx.instance.runtime_properties:
            try:
                security_group = self.execute(
                        self.client.create_security_group, create_args,
                        raise_on_falsy=True)
            except (exception.EC2ResponseError,
                    exception.BotoServerError) as e:
                raise NonRecoverableError('{0}'.format(str(e)))
            utils.set_external_resource_id(
                    security_group.id, ctx.instance, external=False)

        self.resource_id = \
            ctx.instance.runtime_properties[constants.EXTERNAL_RESOURCE_ID]
        security_group = self.get_resource()

        if not security_group:
            return ctx.operation.retry(
                    message='Waiting to verify that security group {0} '
                            'has been added.'
                            .format(constants.EXTERNAL_RESOURCE_ID))

        self._create_group_rules(security_group)

        return True

    def start(self, args=None, **_):
        return True

    def delete(self, args=None, **_):

        delete_args = dict(group_id=self.resource_id)
        delete_args = utils.update_args(delete_args, args)
        return self.execute(self.client.delete_security_group,
                            delete_args, raise_on_falsy=True)

    def _get_connected_vpc(self):

        list_of_vpcs = \
            utils.get_target_external_resource_ids(
                    constants.SECURITY_GROUP_VPC_RELATIONSHIP, ctx.instance
            )
        manager_vpc = utils.get_provider_variables()\
            .get(constants.VPC['AWS_RESOURCE_TYPE'])

        if manager_vpc:
            list_of_vpcs.append(manager_vpc)

        if len(list_of_vpcs) > 1:
            raise NonRecoverableError(
                    'security group may only be attached to one vpc')

        return list_of_vpcs[0] if list_of_vpcs else None

    def _create_group_rules(self, group_object):
        """For each rule listed in the blueprint,
        this will add the rule to the group with the given id.
        :param group: The group object that you want to add rules to.
        :raises NonRecoverableError: src_group_id OR ip_protocol,
        from_port, to_port, and cidr_ip are not provided.
        """

        for rule in ctx.node.properties['rules']:

            if 'src_group_id' in rule:

                if 'cidr_ip' in rule:
                    raise NonRecoverableError(
                            'You need to pass either src_group_id OR cidr_ip.')

                if not group_object.vpc_id:
                    src_group_object = self.get_resource()
                else:
                    src_group_object = self._get_vpc_security_group_from_name(
                            rule['src_group_id'])

                if not src_group_object:
                    raise NonRecoverableError(
                            'Supplied src_group_id {0} doesn ot exist in '
                            'the given account.'.format(rule['src_group_id']))

                del rule['src_group_id']
                rule['src_group'] = src_group_object

            elif 'cidr_ip' not in rule:
                raise NonRecoverableError(
                        'You need to pass either src_group_id OR cidr_ip.')

            try:
                group_object.authorize(**rule)
            except (exception.EC2ResponseError,
                    exception.BotoServerError) as e:
                raise NonRecoverableError('{0}'.format(str(e)))
            except Exception as e:
                self._delete_security_group(group_object.id)
                raise

    def _get_vpc_security_group_from_name(self, name):
        groups = self.get_all_matching()
        for group in groups:
            if group.name == name:
                return group
        return None

    def _delete_security_group(self, group_id):
        """Tries to delete a Security group
        """

        group_to_delete = self.get_resource()

        if not group_to_delete:
            raise NonRecoverableError(
                    'Unable to delete security group {0}, because the group '
                    'does not exist in the account'.format(group_id))

        try:
            self.execute(self.client.delete_security_group,
                         dict(group_id=group_id), raise_on_falsy=True)
        except (exception.EC2ResponseError,
                exception.BotoServerError) as e:
            raise NonRecoverableError('{0}'.format(str(e)))

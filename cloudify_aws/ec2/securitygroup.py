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

# Built-in Imports

# Third-party Imports
from boto import exception
import ipaddress

# Cloudify imports
from cloudify import ctx
from cloudify.decorators import operation
from cloudify_aws.base import AwsBaseNode, AwsBaseRelationship
from cloudify_aws import utils, constants
from cloudify.exceptions import NonRecoverableError


@operation
def creation_validation(**_):
    return SecurityGroup().creation_validation()


@operation
def create(args=None, rules=[], **_):
    ctx.instance.runtime_properties['rules_from_args'] = rules
    return SecurityGroup().create_helper(args)


@operation
def start(args=None, **_):
    return SecurityGroup().start_helper(args)


@operation
def update_rules(rules=[], **_):
    return SecurityGroup().update_rules(rules)


@operation
def delete(args=None, **_):
    return SecurityGroup().delete_helper(args)


class SecurityGroup(AwsBaseNode):

    def __init__(self):
        super(SecurityGroup, self).__init__(
                constants.SECURITYGROUP['AWS_RESOURCE_TYPE'],
                constants.SECURITYGROUP['REQUIRED_PROPERTIES'],
                resource_states=constants.SECURITYGROUP['STATES']
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

        try:
            security_group = self.execute(
                    self.client.create_security_group, create_args,
                    raise_on_falsy=True)
        except (exception.EC2ResponseError,
                exception.BotoServerError) as e:
            raise NonRecoverableError('{0}'.format(str(e)))

        self.resource_id = security_group.id

        return True

    def post_create(self):
        utils.set_external_resource_id(self.resource_id, ctx.instance)
        rules = ctx.instance.runtime_properties['rules_from_args']
        security_group = self.get_resource()
        if not security_group:
            return False
        self._create_group_rules(security_group, rules)
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

    def update_rules(self, rules):
        ctx.logger.debug('New rules for update: {0}'.format(rules))

        security_group = self.get_resource()

        if not security_group:
            return False

        self._create_group_rules(security_group, rules)

    def _get_rules_from_relationship(self):

        rules = []
        relationship_type = constants.SECURITY_GROUP_RULE_RELATIONSHIP
        for rel in ctx.instance.relationships:
            if relationship_type in rel.type or \
                            relationship_type in rel.type_hierarchy:
                rules += rel.target.node.properties['rule']
        return rules

    def _create_group_rules(self, group_object, rules=[]):
        """For each rule listed in the blueprint,
        this will add the rule to the group with the given id.
        :param group_object: The group object that you want to add rules to.
        :param rules: A list of rules to authorize.
        :raises NonRecoverableError:
        Could not locate the security group ID#.
        """

        rules_to_authorize = rules + ctx.node.properties['rules']
        relatreule = self._get_rules_from_relationship()

        if relatreule:
            rules_to_authorize += relatreule

        for rule in self.rules_cleanup(group_object, rules_to_authorize):

            if 'src_group_id' in rule:

                if not group_object.vpc_id:
                    src_group_object = self.get_resource()
                else:
                    src_group_object = \
                        self._get_vpc_security_group_from_name(
                            rule['src_group_id'])

                if not src_group_object:
                    raise NonRecoverableError(
                            'Could not locate the security group ID#: {0}.'
                            .format(rule['src_group_id']))

                del rule['src_group_id']
                rule['src_group'] = src_group_object
            if rule.pop('egress', False):
                self.authorize_egress(group_object.id, rule)
            else:
                self.authorize(group_object, rule)

    def authorize(self, group_object, rule):

        try:
            group_object.authorize(**rule)
        except (exception.EC2ResponseError,
                exception.BotoServerError) as e:
            raise NonRecoverableError('{0}'.format(str(e)))

    def authorize_egress(self, group_id, rule):
        authorize_egress_args = {'group_id': group_id}
        authorize_egress_args.update(**rule)
        self.execute(
            self.client.authorize_security_group_egress, authorize_egress_args,
            raise_on_falsy=True)

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

    @staticmethod
    def format_rule(protocol,
                    from_port,
                    to_port,
                    grant,
                    egress=False):
        """
        Format a rule for comparison in rules cleanup.

        :param protocol: string. 'tcp', 'udp', or 'icmp'.
        :param from_port: int. 0-65535
        :param to_port: int. 0-65535
        :param grant: string. either a cidr_ip or a source security group ID.
        :return: dict containing a formatted rule.
        """

        rule_format = {
            'ip_protocol': protocol,
            'from_port': from_port,
            'to_port': to_port
        }
        if not grant:
            raise NonRecoverableError(
                '{0} is not a valid rule target cidr_ip or src_group_ip'
                .format(grant))

        try:
            ipaddress.ip_network(grant)
        except (ipaddress.AddressValueError, ValueError):
            try:
                ipaddress.ip_address(grant)
            except (ipaddress.AddressValueError, ValueError):
                rule_format.update({'src_group_id': grant})
            else:
                rule_format.update({'cidr_ip': grant})
        else:
            rule_format.update({'cidr_ip': grant})

        if egress:
            rule_format.update({'egress': egress})

        return rule_format

    def rules_cleanup(self, group, rules):
        """
        Make sure that no rule in rules already
        exists in group.rules, if so, remove it from new rules.

        :param group: a boto.ec2.securitygroup object.
        :param rules:
        :return: clean_rules (a list of cleaned, non-conflicting rules.)
        """

        clean_rules = []
        for rule in rules:
            if rule.get('cidr_ip') and rule.get('src_group_id'):
                raise NonRecoverableError(
                    'You cannot pass both cidr_ip and src_group_id.')
            clean_rules.append(
                self.format_rule(rule['ip_protocol'],
                                 rule['from_port'],
                                 rule['to_port'],
                                 rule.get('cidr_ip') or
                                 rule.get('src_group_id'),
                                 egress=rule.get('egress', False)))

        for ip_permission in group.rules:
            for grant in ip_permission.grants:
                existing_rule = self.format_rule(ip_permission.ip_protocol,
                                                 ip_permission.from_port,
                                                 ip_permission.to_port,
                                                 str(grant))
                if existing_rule in clean_rules:
                    clean_rules.remove(existing_rule)
        for ip_permission in group.rules_egress:
            for grant in ip_permission.grants:
                existing_rule = self.format_rule(ip_permission.ip_protocol,
                                                 ip_permission.from_port,
                                                 ip_permission.to_port,
                                                 str(grant),
                                                 egress=True)
                if existing_rule in clean_rules:
                    clean_rules.remove(existing_rule)

        return clean_rules


class SecurityGroupUsesRuleConnection(AwsBaseRelationship):

    def __init__(self, client=None):
        super(SecurityGroupUsesRuleConnection, self).__init__(client=client)
        self.source_get_all_handler = {
            'function': self.client.get_all_security_groups(),
            'argument':
                '{0}_ids'.format(constants.SECURITYGROUP['AWS_RESOURCE_TYPE'])
        }

    def associate(self, args=None, **_):

        ctx.logger.info(
                'adding rule to security group {0}'
                .format(self.source_resource_id))

        if 'rules' not in ctx.source.instance.runtime_properties:
            return self._add_new_rule()
        else:
            if ctx.target.node.properties['rule'] not in \
                    [ctx.source.instance.runtime_properties['rules']]:
                return self._add_new_rule()

        ctx.logger.info('Rule already exists in security group {0}.'
                        .format(self.source_resource_id))
        return False

    def _add_new_rule(self):

        for property in ctx.target.node.properties['rule']:
            if 'egress' in property:
                ctx.source.instance.runtime_properties.update(
                        {'egress':
                         ctx.target.node.properties['rule']})
            else:
                ctx.source.instance.runtime_properties.update(
                        {'ingress':
                         ctx.target.node.properties['rule']})

        return True

    def disassociate(self, args=None, **_):

        ctx.logger.info(
                'removing rule from security group {0}'
                .format(self.source_resource_id))

        for property in ctx.target.node.properties['rule']:
            if 'egress' in property:
                ctx.source.instance.runtime_properties\
                    .pop('egress', 'Rule doesnt exists in security group {0}.'
                         .format(self.source_resource_id))
            else:
                ctx.source.instance.runtime_properties\
                    .pop('ingress', 'Rule doesnt exists in security group {0}.'
                         .format(self.source_resource_id))

        return True

    def associate_helper(self, args=None):

        ctx.logger.info(
                'Attempting to associate rule to {0}.'
                .format(self.source_resource_id))
        if self.associate(args):
            return self.post_associate()

    def disassociate_helper(self, args=None):

        ctx.logger.info(
                'Attempting to disassociate rule from {0}.'
                .format(self.source_resource_id))
        if self.disassociate(args):
            return self.post_disassociate()

    def post_associate(self):
        ctx.logger.info(
                'Associated rule with {0}.'
                .format(self.source_resource_id))
        return True

    def post_disassociate(self):
        ctx.logger.info(
                'Disassociated rule from {0}.'
                .format(self.source_resource_id))
        return True

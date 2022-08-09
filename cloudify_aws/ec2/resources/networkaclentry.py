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
    EC2.NetworkAcl Entry
    ~~~~~~~~~~~~~~
    AWS EC2 NetworkAcl Entry interface
"""
# Boto
from botocore.exceptions import ClientError, ParamValidationError

# Cloudify
from cloudify_aws.common import decorators, utils
from cloudify_aws.ec2 import EC2Base
from cloudify_aws.common.constants import EXTERNAL_RESOURCE_ID

RESOURCE_TYPE = 'EC2 Network Acl Entry'
NETWORKACLS = 'NetworkAcls'
NETWORKACL_ID = 'NetworkAclId'
NETWORKACL_IDS = 'NetworkAclIds'
RULE_NUMBER = 'RuleNumber'
ENTRIES = 'Entries'
EGRESS = 'Egress'
NETWORKACL_TYPE = 'cloudify.nodes.aws.ec2.NetworkACL'
NETWORKACL_TYPE_DEPRECATED = 'cloudify.aws.nodes.ACL'


class EC2NetworkAclEntry(EC2Base):
    """
        EC2 NetworkAcl Entry interface
    """
    def __init__(self, ctx_node, resource_id=None, client=None, logger=None):
        EC2Base.__init__(self, ctx_node, resource_id, client, logger)
        self.type_name = RESOURCE_TYPE
        self._describe_call = 'describe_network_acls'
        self._type_key = NETWORKACLS
        self._id_key = NETWORKACL_ID
        self._ids_key = NETWORKACL_IDS

    def get_properties_by_filter(self, **filters):
        try:
            resources = self.client.describe_network_acls(**filters)
        except (ClientError, ParamValidationError):
            pass
        else:
            return resources.get(NETWORKACLS)[0] if resources else None

    def create(self, params):
        """
            Create a new AWS EC2 NetworkAcl Entry.
        """
        return self.make_client_call(
            'create_network_acl_entry', params)

    def replace(self, params):
        """
            Create a new AWS EC2 NetworkAcl Entry.
        """
        self.logger.debug('Replacing %s with parameters: %s'
                          % (self.type_name, params))
        res = self.client.replace_network_acl_entry(**params)
        self.logger.debug('Response: %s' % res)
        return res

    def delete(self, params=None):
        """
            Deletes an existing AWS EC2 NetworkAcl Entry.
        """
        self.logger.debug('Deleting %s with parameters: %s'
                          % (self.type_name, params))
        res = self.client.delete_network_acl_entry(**params)
        self.logger.debug('Response: %s' % res)
        return res


@decorators.aws_resource(EC2NetworkAclEntry, resource_type=RESOURCE_TYPE)
def prepare(ctx, resource_config, **_):
    """Prepares an AWS EC2 NetworkAcl Entry"""
    # Save the parameters
    ctx.instance.runtime_properties['resource_config'] = resource_config


@decorators.aws_resource(EC2NetworkAclEntry, RESOURCE_TYPE)
def create(ctx, iface, resource_config, **_):
    """Creates an AWS EC2 NetworkAcl Entry"""

    network_acl_id = resource_config.get(NETWORKACL_ID)
    rule_number = resource_config.get(RULE_NUMBER)
    egress = resource_config.get(EGRESS)

    if not network_acl_id:
        targ = \
            utils.find_rel_by_node_type(ctx.instance, NETWORKACL_TYPE) or \
            utils.find_rel_by_node_type(ctx.instance,
                                        NETWORKACL_TYPE_DEPRECATED)

        # Attempt to use the NETWORKACL ID from parameters.
        # Fallback to connected NETWORKACL.
        resource_config[NETWORKACL_ID] = \
            network_acl_id or \
            targ.target.instance.runtime_properties.get(EXTERNAL_RESOURCE_ID)

    ctx.instance.runtime_properties['network_acl_id'] = \
        resource_config[NETWORKACL_ID]
    ctx.instance.runtime_properties['rule_number'] = rule_number
    ctx.instance.runtime_properties['egress'] = egress

    filters = {NETWORKACL_IDS: [resource_config[NETWORKACL_ID]]}
    network_acl_entry = iface.get_properties_by_filter(**filters)
    entry = network_acl_entry.get(ENTRIES)[0]
    # for rule in entries:
    if rule_number == entry.get(RULE_NUMBER):
        return iface.replace(resource_config)
    # Actually create the resource
    create_response = iface.create(resource_config)
    ctx.instance.runtime_properties['create_response'] = \
        utils.JsonCleanuper(create_response).to_dict()


@decorators.aws_resource(EC2NetworkAclEntry, RESOURCE_TYPE,
                         ignore_properties=True)
def delete(ctx, iface, resource_config, **_):
    """Deletes an AWS EC2 NetworkAcl Entry"""
    network_acl_id = resource_config.get(NETWORKACL_ID)
    rule_number = resource_config.get(RULE_NUMBER) or \
        ctx.instance.runtime_properties['rule_number']
    egress = resource_config.get(EGRESS) or \
        ctx.instance.runtime_properties['egress']

    if not network_acl_id:
        resource_config[NETWORKACL_ID] = \
            network_acl_id or ctx.instance.runtime_properties['network_acl_id']

    resource_config.update({RULE_NUMBER: rule_number})
    resource_config.update({EGRESS: egress})
    iface.delete(resource_config)

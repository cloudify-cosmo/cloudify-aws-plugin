# #######
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
#    * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    * See the License for the specific language governing permissions and
#    * limitations under the License.
'''
    Common.Utils
    ~~~~~~~~~~~~
    AWS helper utilities
'''

# Local imports
import sys
from six.moves import urllib
import re
import uuid

# Third party imports
import requests
from requests import exceptions
from cloudify import ctx
from cloudify.exceptions import NonRecoverableError
from cloudify.utils import exception_to_error_cause
from cloudify_aws.common import constants


def generate_traceback_exception():
    _, exc_value, exc_traceback = sys.exc_info()
    response = exception_to_error_cause(exc_value, exc_traceback)
    return response


def get_traceback_exception():
    error_traceback = generate_traceback_exception()
    error_message = 'Error traceback {0} with message' \
                    ' {1}'.format(error_traceback['traceback'],
                                  error_traceback['message'])
    ctx.logger.error(error_message)
    return error_traceback


def get_resource_string(
        node=None, instance=None,
        property_key=None, attribute_key=None):
    '''
        Gets a string of a Cloudify node and/or instance, searching
        both properties and runtime properties (attributes).
    :param `cloudify.context.NodeContext` node:
        Cloudify node.
    :param `cloudify.context.NodeInstanceContext` instance:
        Cloudify node instance.
    '''
    node = node if node else ctx.node
    instance = instance if instance else ctx.instance
    props = node.properties if node else {}
    runtime_props = instance.runtime_properties if instance else {}
    # Search instance runtime properties first, then the node properties
    value = runtime_props.get(attribute_key, props.get(property_key))
    return str(value) if value else None


def get_resource_id(node=None,
                    instance=None,
                    resource_name=None,
                    use_instance_id=False,
                    raise_on_missing=False):
    '''
        Gets the (external) resource ID of a Cloudify node and/or instance.
        depending on the environment available.
    :param `cloudify.context.NodeContext` node:
        Cloudify node.
    :param `cloudify.context.NodeInstanceContext` instance:
        Cloudify node instance.
    :param boolean raise_on_missing: If True, causes this method to raise
        an exception if the resource ID is not found.
    :param string resource_name: [RESOURCE_]NAME as set in resource_config.
        For example "LaunchConfigurationName".
    :raises: :exc:`cloudify.exceptions.NonRecoverableError`
    '''
    resource_id = get_resource_string(
        node, instance, 'resource_id', constants.EXTERNAL_RESOURCE_ID)
    if not resource_id and raise_on_missing:
        raise NonRecoverableError(
            'Missing resource ID! Node=%s, Instance=%s' % (
                node.id if node else None,
                instance.id if instance else None))
    elif resource_name and not resource_id:
        return resource_name
    elif use_instance_id and not resource_id:
        return ctx.instance.id
    return resource_id


def get_resource_arn(node=None, instance=None,
                     raise_on_missing=False):
    '''
        Gets the (external) resource ARN of a Cloudify node and/or instance.
        depending on the environment available.
    :param `cloudify.context.NodeContext` node:
        Cloudify node.
    :param `cloudify.context.NodeInstanceContext` instance:
        Cloudify node instance.
    :param boolean raise_on_missing: If True, causes this method to raise
        an exception if the resource ID is not found.
    :raises: :exc:`cloudify.exceptions.NonRecoverableError`
    '''
    resource_id = get_resource_string(
        node, instance, 'resource_arn', constants.EXTERNAL_RESOURCE_ARN)
    if not resource_id and raise_on_missing:
        raise NonRecoverableError(
            'Missing resource ARN! Node=%s, Instance=%s' % (
                node.id if node else None,
                instance.id if instance else None))
    return resource_id


def get_aws_resource_name(name, regex=r'[^a-zA-Z0-9]+'):
    """
    Create AWS accepted name of resource. From AWS specification:
    "Specifically, the name must be 1-255 characters long and match the
    regular expression based on aws resources. Default expression
    :param name: name of resource to be given
    :param regex: regex to be applied for the resource name ``[^a-zA-Z0-9]+``
    :return: AWS accepted instance name
    """

    final_name = re.sub(regex, '', name)
    # assure the first character is alpha
    if not final_name[0].isalpha():
        final_name = '{0}{1}'.format('a', final_name)
    # trim to the length limit
    if len(final_name) > constants.MAX_AWS_NAME:
        remain_len = constants.MAX_AWS_NAME - len(final_name)
        final_name = final_name[:remain_len]
    # convert string to lowercase
    return final_name.lower()


# This method return the resource name and in case the resource name is not
# specified, then the default value will be ASCII characters of the instance_id
def get_resource_name(name):
    return name or get_aws_resource_name(ctx.instance.id)


# This method return the resource name of the EC2-VPC resource and in case
# the resource name is not specified, then the default value will be
# instance_id but with by applying ``[^a-zA-Z0-9- ._:/()#,*@[]+=;{}!$]+`` regex
def get_ec2_vpc_resource_name(name):
    regex = 'r[^a-zA-Z0-9- ._:/()#,*@[]+=;{}!$]+'
    return name or get_aws_resource_name(ctx.instance.id, regex=regex)


def update_resource_id(instance, val):
    '''Updates an instance's resource ID'''
    instance.runtime_properties[constants.EXTERNAL_RESOURCE_ID] = str(val)


def update_resource_arn(instance, val):
    '''Updates an instance's resource ARN'''
    instance.runtime_properties[constants.EXTERNAL_RESOURCE_ARN] = str(val)


def get_parent_resource_id(node_instance,
                           rel_type=constants.REL_CONTAINED_IN,
                           raise_on_missing=True):
    '''Finds a relationship to a parent and gets its resource ID'''
    rel = find_rel_by_type(node_instance, rel_type)
    if not rel:
        if raise_on_missing:
            raise NonRecoverableError('Error locating parent resource ID')
        return None
    return get_resource_id(instance=rel.target.instance,
                           raise_on_missing=raise_on_missing)


def get_ancestor_resource_id(node_instance,
                             node_type,
                             raise_on_missing=True):
    '''Finds an ancestor and gets its resource ID'''
    ancestor = get_ancestor_by_type(node_instance, node_type)
    if not ancestor:
        if raise_on_missing:
            raise NonRecoverableError('Error locating ancestor resource ID')
        return None
    return get_resource_id(instance=ancestor.instance,
                           raise_on_missing=raise_on_missing)


def filter_boto_params(args, filters, preserve_none=False):
    '''
        Takes in a dictionary, applies a "whitelist" of key names,
        and removes keys which have associated values of None.

    :param dict args: Original dictionary to filter
    :param list filters: Whitelist list of keys
    :param boolean preserve_none: If True, keeps key-value pairs even
        if the value is None.
    '''
    return {
        k: v for k, v in args.iteritems()
        if k in filters and (preserve_none is True or v is not None)
    }


def find_rels_by_type(node_instance, rel_type):
    '''
        Finds all specified relationships of the Cloudify
        instance.
    :param `cloudify.context.NodeInstanceContext` node_instance:
        Cloudify node instance.
    :param str rel_type: Cloudify relationship type to search
        node_instance.relationships for.
    :returns: List of Cloudify relationships
    '''
    return [x for x in node_instance.relationships
            if rel_type in x.type_hierarchy]


def find_rel_by_type(node_instance, rel_type):
    '''
        Finds a single relationship of the Cloudify instance.
    :param `cloudify.context.NodeInstanceContext` node_instance:
        Cloudify node instance.
    :param str rel_type: Cloudify relationship type to search
        node_instance.relationships for.
    :returns: A Cloudify relationship or None
    '''
    rels = find_rels_by_type(node_instance, rel_type)
    return rels[0] if len(rels) > 0 else None


def find_rels_by_node_type(node_instance, node_type):
    '''
        Finds all specified relationships of the Cloudify
        instance where the related node type is of a specified type.
    :param `cloudify.context.NodeInstanceContext` node_instance:
        Cloudify node instance.
    :param str node_type: Cloudify node type to search
        node_instance.relationships for.
    :returns: List of Cloudify relationships
    '''
    return [x for x in node_instance.relationships
            if node_type in x.target.node.type_hierarchy]


def find_rel_by_node_type(node_instance, node_type):
    '''
        Finds a single relationship of the Cloudify
        instance where the related node type is of a specified type.
    :param `cloudify.context.NodeInstanceContext` node_instance:
        Cloudify node instance.
    :param str rel_type: Cloudify relationship type to search
        node_instance.relationships for.
    :returns: A Cloudify relationship or None
    '''
    rels = find_rels_by_node_type(node_instance, node_type)
    return rels[0] if len(rels) > 0 else None


def find_rels_by_node_name(node_instance, node_name):
    '''
        Finds all specified relationships of the Cloudify
        instance where the related node type is of a specified type.
    :param `cloudify.context.NodeInstanceContext` node_instance:
        Cloudify node instance.
    :param str node_bane: Cloudify node name to search
        node_instance.relationships for.
    :returns: List of Cloudify relationships
    '''
    return [x for x in node_instance.relationships
            if node_name in x.target.node.id]


def is_node_type(node, node_type):
    '''
        Checks if a node is of a given node type.
    :returns: `True` or `False`
    '''
    return node_type in node.type_hierarchy


def get_ancestor_by_type(inst, node_type):
    '''
        Gets an ancestor context (recursive search)
    :param `cloudify.context.NodeInstanceContext` inst: Cloudify instance
    :param string node_type: Node type name
    :returns: Ancestor context or None
    '''
    # Find a parent of a specific type
    rel = find_rel_by_type(inst, 'cloudify.relationships.contained_in')
    if not rel:
        return None
    if node_type in rel.target.node.type_hierarchy:
        return rel.target
    return get_ancestor_by_type(rel.target.instance, node_type)


def add_resources_from_rels(node_instance, node_type, current_list):
    '''
        Updates a resource list with relationships same target types
    :param `cloudify.context.NodeInstanceContext` inst: Cloudify instance
    :param string node_type: Node type name
    :param current_list: List of IDs
    :return: updated list
    '''
    resources = \
        find_rels_by_node_type(
            node_instance,
            node_type)
    for resource in resources:
        resource_id = \
            resource.target.instance.runtime_properties[
                constants.EXTERNAL_RESOURCE_ID]
        if resource_id not in current_list:
            current_list.append(resource_id)
    return current_list


def find_resource_id_by_type(node_instance, node_type):
    '''
        Finds the resource_id of a single node,
        which is connected via a relationship.
    :param `cloudify.context.NodeInstanceContext` inst: Cloudify instance
    :param string node_type: Node type name
    :return: None or the resource id
    '''

    targ = \
        find_rel_by_node_type(
            node_instance,
            node_type)
    if targ and getattr(targ, 'target'):
        resource_id = \
            targ.target.instance.runtime_properties.get(
                constants.EXTERNAL_RESOURCE_ID)
        return resource_id
    return None


def find_resource_arn_by_type(node_instance, node_type):
    '''
        Finds the resource_arn of a single node,
        which is connected via a relationship.
    :param `cloudify.context.NodeInstanceContext` inst: Cloudify instance
    :param string node_type: Node type name
    :return: None or the resource arn
    '''

    targ = \
        find_rel_by_node_type(
            node_instance,
            node_type)
    if targ and getattr(targ, 'target'):
        resource_id = \
            targ.target.instance.runtime_properties.get(
                constants.EXTERNAL_RESOURCE_ARN)
        return resource_id
    return None


def validate_arn(arn_candidate, arn_regex=constants.ARN_REGEX):
    arn_matcher = re.compile(arn_regex)
    return arn_matcher.match(arn_candidate)


def get_uuid():
    return str(uuid.uuid4())


class JsonCleanuper(object):

    def __init__(self, ob):
        try:
            resource = ob.to_dict()
        except AttributeError:
            resource = ob

        if isinstance(resource, list):
            self._cleanuped_list(resource)
        elif isinstance(resource, dict):
            self._cleanuped_dict(resource)

        self.value = resource

    def _cleanuped_list(self, resource):
        for k, v in enumerate(resource):
            if not v:
                continue
            if isinstance(v, list):
                self._cleanuped_list(v)
            elif isinstance(v, dict):
                self._cleanuped_dict(v)
            elif (not isinstance(v, int) and  # integer and bool
                  not isinstance(v, str) and
                  not isinstance(v, unicode)):
                resource[k] = str(v)

    def _cleanuped_dict(self, resource):
        for k in resource:
            if not resource[k]:
                continue
            if isinstance(resource[k], list):
                self._cleanuped_list(resource[k])
            elif isinstance(resource[k], dict):
                self._cleanuped_dict(resource[k])
            elif (not isinstance(resource[k], int) and  # integer and bool
                  not isinstance(resource[k], str) and
                  not isinstance(resource[k], unicode)):
                resource[k] = str(resource[k])

    def to_dict(self):
        return self.value


def generate_swift_access_config(auth_url, username, password):

    payload = dict()
    payload['X-Auth-User'] = username
    payload['X-Auth-Key'] = password

    # Try to generate the token and endpoint url to be used later on
    try:
        resp = requests.get(auth_url, headers=payload)
        resp.raise_for_status()
    except exceptions.HTTPError as error:
        _, _, tb = sys.exc_info()
        raise NonRecoverableError(
            "Failed generating swift endpoint and token",
            causes=[exception_to_error_cause(error, tb)])

    # Get the url which represent "endpoint_url"
    endpoint_url = urllib.parse.urljoin(resp.headers.get('X-Storage-Url'), '/')

    # This represent "aws_secret_access_key" which should be used with boto3
    # client
    token = resp.headers['X-Auth-Token']
    return endpoint_url, token


def get_tags_list(node_prop, runtime_prop, input_prop):
    tags_list = []
    if isinstance(node_prop, list):
        tags_list = node_prop
    if isinstance(runtime_prop, list):
        tags_list = list(set(tags_list + runtime_prop))
    if isinstance(input_prop, list):
        tags_list = list(set(tags_list + input_prop))
    return tags_list

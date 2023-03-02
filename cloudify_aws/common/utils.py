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
'''
    Common.Utils
    ~~~~~~~~~~~~
    AWS helper utilities
'''

# Standard imports
import re
import sys
import uuid
from time import sleep
from copy import deepcopy

# Third party imports
import requests
from requests import exceptions
from botocore.exceptions import ClientError


from cloudify import ctx
from cloudify.workflows import ctx as wtx
from cloudify.manager import get_rest_client
from cloudify.utils import exception_to_error_cause
from cloudify.exceptions import OperationRetry, NonRecoverableError
from cloudify_rest_client.exceptions import (
    CloudifyClientError,
    DeploymentEnvironmentCreationPendingError,
    DeploymentEnvironmentCreationInProgressError)
from cloudify_common_sdk.clean_json import JsonCleanuper  # noqa

# Local imports
from cloudify_aws.common import constants, _compat
from cloudify_aws.common._compat import urljoin, text_type


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
    return text_type(value) if value else None


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
    instance.runtime_properties[constants.EXTERNAL_RESOURCE_ID] = \
        text_type(val)


def update_resource_arn(instance, val):
    '''Updates an instance's resource ARN'''
    instance.runtime_properties[constants.EXTERNAL_RESOURCE_ARN] = \
        text_type(val)


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
        k: v for k, v in args.items()
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


def find_ids_of_rels_by_node_type(node_instance, node_type):
    '''
        Finds the IDs of all specified relationships of the Cloudify
        instance where the related node type is of a specified type.
    :param `cloudify.context.NodeInstanceContext` node_instance:
        Cloudify node instance.
    :param str node_type: Cloudify node type to search
        node_instance.relationships for.
    :returns: List of IDs of resources from Cloudify relationships
    '''
    rels = find_rels_by_node_type(node_instance, node_type)
    return [rel.target.instance.runtime_properties.get(
        constants.EXTERNAL_RESOURCE_ID) for rel in rels]


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
    return text_type(uuid.uuid4())


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
    endpoint_url = urljoin(resp.headers.get('X-Storage-Url'), '/')

    # This represent "aws_secret_access_key" which should be used with boto3
    # client
    token = resp.headers['X-Auth-Token']
    return endpoint_url, token


def get_tags_list(node_prop, runtime_prop, input_prop):
    tags_list = []
    if isinstance(node_prop, list):
        tags_list = node_prop
    if isinstance(runtime_prop, list):
        tags_list.extend(runtime_prop)
    if isinstance(input_prop, list):
        tags_list.extend(input_prop)
    tags_list = dedup_tags(tags_list)
    cleanup_tags(tags_list)
    return tags_list


def check_region_name(region):
    region_matcher = re.compile(constants.REGION_REGEX)
    if not region_matcher.match(region):
        raise NonRecoverableError(
            'The region_name {region} provided in client_config does not '
            'match the expected region regular expression.'
            .format(region=repr(region)))


def check_availability_zone(zone):
    zone_matcher = re.compile(constants.AVAILABILITY_ZONE_REGEX)
    if not zone_matcher.match(zone):
        raise NonRecoverableError(
            'The AvailabilityZone {zone} provided in resource_config does '
            'not match the expected availability zone regular expression.'
            .format(zone=repr(zone)))


def clean_params(p):
    p = dict() if not p else p.copy()
    if not isinstance(p, dict) or not p:
        return {}
    for _k, _v in list(p.items()):
        if _v is None or _v == {} or _v == []:
            del p[_k]
        elif _k == 'AvailabilityZone':
            check_availability_zone(_v)
    return p


def cleanup_tags(tags):
    for tag in tags:
        tag['Value'] = text_type(tag['Value'])


def dedup_tags(tags):
    return [dict(y) for y in set(tuple(t.items()) for t in tags)]


def exit_on_substring(iface,
                      method,
                      request=None,
                      substrings=None,
                      raisable=OperationRetry):
    """
    This method is useful for deleting something that may have already been
    deleted. We really want to make sure that the resource no longer exists.

    :param iface: Resource interface derived from EC2Base.
    :param method: The method on the Resource interface object.
    :param request: The parameters to method.
    :param substrings: Substrings to look for in the exception.
    :param raisable: The exception to raise if substrings are not found.
    :return:
    """

    if isinstance(substrings, text_type):
        substrings = [substrings]

    callable = getattr(iface, method)
    try:
        if request:
            return callable(request)
        else:
            return callable()
    except (NonRecoverableError, ClientError) as e:
        if hasattr(e, 'message'):
            message = e.message
        else:
            message = _compat.text_type(e)
        if any(substring in message for substring in substrings):
            return {}
        raise raisable(message)


def raise_on_substring(iface,
                       method,
                       request=None,
                       substrings=None,
                       raisable=OperationRetry):
    """
    This method is useful for deleting something that might be needed by
    another node.
    We really want to make sure that the resource will be deleted once its
    no longer needed.

    :param iface: Resource interface derived from EC2Base.
    :param method: The method on the Resource interface object.
    :param request: The parameters to method.
    :param substrings: Substrings to look for in the exception.
    :param raisable: The exception to raise if substrings are found.
    :return:
    """
    if isinstance(substrings, text_type):
        substrings = [substrings]

    callable = getattr(iface, method)
    try:
        if request:
            return callable(request)
        else:
            return callable()
    except (NonRecoverableError, ClientError) as e:
        if hasattr(e, 'message'):
            message = e.message
        else:
            message = _compat.text_type(e)
        if any(substring in message for substring in substrings):
            raise raisable(message)
        return {}


def handle_response(iface,
                    method,
                    request=None,
                    exit_substrings=None,
                    raise_substrings=None,
                    raisable=OperationRetry):
    """
    This method is useful for deleting something that might be needed by
    another node or might be already free.
    We really want to make sure that the resource will be deleted once its
    no longer needed.

    :param iface: Resource interface derived from EC2Base.
    :param method: The method on the Resource interface object.
    :param request: The parameters to method.
    :param exit_substrings: Substrings to look for in the exception.
                            This substring will cause the method to exit
    :param raise_substrings: Substrings to look for in the exception.
                             This substring will cause the method to raise
                             an exception
    :param raisable: The exception to raise if substrings are found.
    :return:
    """
    exit_substrings = exit_substrings or []
    if isinstance(exit_substrings, text_type):
        exit_substrings = [exit_substrings]

    raise_substrings = raise_substrings or []
    if isinstance(raise_substrings, text_type):
        raise_substrings = [raise_substrings]

    callable = getattr(iface, method)
    try:
        if request:
            return callable(request)
        else:
            return callable()
    except (NonRecoverableError, ClientError) as e:
        if hasattr(e, 'message'):
            message = e.message
        else:
            message = _compat.text_type(e)
        if any(substring in message for substring in raise_substrings):
            raise raisable(message)
        elif any(substring in message for substring in exit_substrings):
            return
        else:
            raise e


def with_rest_client(func):
    """
    :param func: This is a class for the aws resource need to be
    invoked
    :return: a wrapper object encapsulating the invoked function
    """

    def wrapper_inner(*args, **kwargs):
        kwargs['rest_client'] = get_rest_client()
        return func(*args, **kwargs)
    return wrapper_inner


@with_rest_client
def create_deployments(group_id,
                       blueprint_id,
                       deployment_ids,
                       inputs,
                       labels,
                       rest_client):
    """Create a deployment group and create deployments in it.

    :param group_id:
    :param blueprint_id:
    :param deployment_ids:
    :param inputs:
    :param labels:
    :param rest_client:
    :return:
    """
    rest_client.deployment_groups.put(
        group_id=group_id,
        blueprint_id=blueprint_id,
        labels=labels)
    try:
        rest_client.deployment_groups.add_deployments(
            group_id,
            new_deployments=[
                {
                    'display_name': dep_id,
                    'inputs': inp
                } for dep_id, inp in zip(deployment_ids, inputs)]
        )
    except TypeError:
        for dep_id, inp in zip(deployment_ids, inputs):
            rest_client.deployments.create(
                blueprint_id,
                dep_id,
                inputs=inp)
        rest_client.deployment_groups.add_deployments(
            group_id,
            deployment_ids=deployment_ids)


@with_rest_client
def install_deployments(group_id, rest_client):
    attempts = 0
    while True:
        try:
            return rest_client.execution_groups.start(group_id, 'install')
        except (DeploymentEnvironmentCreationPendingError,
                DeploymentEnvironmentCreationInProgressError) as e:
            attempts += 1
            if attempts > 15:
                raise NonRecoverableError(
                    'Maximum attempts waiting '
                    'for deployment group {group}" {e}.'.format(
                        group=group_id, e=e))
            sleep(5)
            continue


def generate_deployment_ids(deployment_id, resources):
    # TODO: This is not the final design.
    return '{}-{}'.format(deployment_id, resources)


def desecretize_client_config(config):
    for key, value in config.items():
        config[key] = resolve_intrinsic_functions(value)
    return config


def resolve_intrinsic_functions(prop, dep_id=None):
    if isinstance(prop, dict):
        if 'get_secret' in prop:
            prop = prop.get('get_secret')
            if isinstance(prop, dict):
                prop = resolve_intrinsic_functions(prop, dep_id)
            return get_secret(prop)
        if 'get_input' in prop:
            prop = prop.get('get_input')
            if isinstance(prop, dict):
                prop = resolve_intrinsic_functions(prop, dep_id)
            return get_input(prop)
        if 'get_attribute' in prop:
            prop = prop.get('get_attribute')
            if isinstance(prop, dict):
                prop = resolve_intrinsic_functions(prop, dep_id)
            node_id = prop[0]
            runtime_property = prop[1]
            return get_attribute(node_id, runtime_property, dep_id)
    return prop


@with_rest_client
def get_secret(secret_name, rest_client):
    secret = rest_client.secrets.get(secret_name)
    return secret.value


@with_rest_client
def get_input(input_name, rest_client):
    deployment = rest_client.deployments.get(wtx.deployment.id)
    return deployment.inputs.get(input_name)


@with_rest_client
def get_attribute(node_id, runtime_property, deployment_id, rest_client):
    for node_instance in rest_client.node_instances.list(node_id=node_id):
        if node_instance.deployment_id != deployment_id:
            continue
        return node_instance.runtime_properties.get(runtime_property)


def get_regions(node, deployment_id):
    regions = []
    for region in node.properties['regions']:
        regions.append(resolve_intrinsic_functions(region, deployment_id))
    return regions


def add_new_labels(new_labels, deployment_id):
    labels = get_deployment_labels(deployment_id)
    for k, v in new_labels.items():
        labels[k] = v
    update_deployment_labels(deployment_id, labels)


def add_new_label(key, value, deployment_id):
    labels = get_deployment_labels(deployment_id)
    labels[key] = value
    update_deployment_labels(deployment_id, labels)


def get_deployment_labels(deployment_id):
    deployment = get_deployment(deployment_id)
    return convert_list_to_dict(deepcopy(deployment.labels))


@with_rest_client
def update_deployment_labels(deployment_id, labels, rest_client):
    labels = convert_dict_to_list(labels)
    rest_client.deployments.update_labels(
        deployment_id,
        labels=labels)


def convert_list_to_dict(labels):
    labels = deepcopy(labels)
    target_dict = {}
    for label in labels:
        target_dict[label['key']] = label['value']
    return target_dict


def convert_dict_to_list(labels):
    labels = deepcopy(labels)
    target_list = []
    for key, value in labels.items():
        target_list.append({key: value})
    return target_list


@with_rest_client
def get_deployment(deployment_id, rest_client):
    try:
        return rest_client.deployments.get(deployment_id=deployment_id)
    except CloudifyClientError:
        return


def format_location_name(location_name):
    return re.sub('\\-+', '-', re.sub('[^0-9a-zA-Z]', '-', str(location_name)))


def assign_site(deployment_id, location, location_name):
    site = get_site(location_name)
    if not site:
        create_site(location_name, location)
    elif not site.get('location'):
        update_site(location_name, location)
    update_deployment_site(deployment_id, location_name)


@with_rest_client
def create_site(site_name, location, rest_client):
    return rest_client.sites.create(site_name, location)


@with_rest_client
def update_site(site_name, location, rest_client):
    return rest_client.sites.update(site_name, location)


@with_rest_client
def get_site(site_name, rest_client):
    try:
        return rest_client.sites.get(site_name)
    except CloudifyClientError:
        return


@with_rest_client
def update_deployment_site(deployment_id, site_name, rest_client):
    deployment = get_deployment(deployment_id)
    if deployment.site_name == site_name:
        return deployment
    elif deployment.site_name:
        return rest_client.deployments.set_site(
            deployment_id, detach_site=True)
    return rest_client.deployments.set_site(
        deployment_id, site_name)


@with_rest_client
def get_node_instances_by_type_related_to_node_name(node_name,
                                                    node_type,
                                                    deployment_id,
                                                    rest_client):
    """Filter node instances by type.

    :param node_name: the node name that we wish to find relationships to.
    :param node_type: the node type that we wish to filter.
    :type node_type: str
    :param deployment_id: The deployment ID.
    :type deployment_id: str
    :param rest_client: A Cloudify REST client.
    :type rest_client: cloudify_rest_client.client.CloudifyClient
    :return: A list of dicts of
      cloudify_rest_client.node_instances.NodeInstance and
      cloudify_rest_client.nodes.Node
    :rtype: list
    """
    nodes = []
    for ni in rest_client.node_instances.list(
            deployment_id=deployment_id,
            _includes=['id',
                       'version',
                       'runtime_properties',
                       'node_id',
                       'relationships']):
        node = rest_client.nodes.get(
            node_id=ni.node_id, deployment_id=deployment_id)
        rels = [rel['target_name'] for rel in ni.relationships]
        if node_type in node.type_hierarchy and node_name in rels:
            nodes.append({'node_instance': ni, 'node': node})
    return nodes


def clean_empty_vals(params):
    if isinstance(params, dict):
        new_params = {}
        for key, val in params.items():
            if isinstance(val, dict) or isinstance(val, list):
                val = clean_empty_vals(val)
            if val:
                new_params[key] = val
        return new_params
    if isinstance(params, list):
        new_params = []
        for val in params:
            if isinstance(val, dict) or isinstance(val, list):
                val = clean_empty_vals(val)
            if val:
                new_params.append(val)
        return new_params


def assign_parameter(iface, param_name, runtime_props, prop):
    prop = prop or {}
    if prop:
        runtime_props[param_name] = JsonCleanuper(prop).to_dict()  # noqa
    elif isinstance(runtime_props, dict):
        prop = runtime_props.get(param_name)
    setattr(iface, param_name, prop)


def assign_initial_configuration(iface, runtime_props, prop=None):
    iface.initial_configuration = \
        runtime_props['initial_configuration'] = \
        runtime_props.get('initial_configuration', prop)


def assign_create_response(iface, runtime_props, prop=None):
    assign_parameter(iface, 'create_response', runtime_props, prop)


def assign_remote_configuration(iface, runtime_props, prop=None):
    prop = prop or iface.properties
    assign_parameter(iface, 'remote_configuration', runtime_props, prop)


def assign_expected_configuration(iface, runtime_props, prop=None):
    assign_parameter(iface, 'expected_configuration', runtime_props, prop)


def update_expected_configuration(iface, runtime_props):
    assign_expected_configuration(iface, runtime_props, iface.properties)


@with_rest_client
def post_start_related_nodes(node_instance_ids, deployment_id, rest_client):
    if node_instance_ids:
        return rest_client.executions.start(
            deployment_id,
            'execute_operation',
            parameters={
                'operation': 'cloudify.interfaces.lifecycle.poststart',
                'node_instance_ids': node_instance_ids
            },
            force=True,
        )


def assign_previous_configuration(iface, runtime_props, prop=None):
    prop = prop or iface.expected_configuration
    assign_parameter(iface, 'previous_configuration', runtime_props, prop)


def check_drift(resource_type, iface, logger):
    logger.info(
        'Checking drift state for {resource_type} {resource_id}.'.format(
            resource_type=resource_type, resource_id=iface.resource_id))
    ctx.instance.refresh(force=True)
    iface.expected_configuration = ctx.instance.runtime_properties.get(
        'expected_configuration')
    result = iface.compare_configuration()
    if result:
        message = 'The {resource_type} {resource_id} configuration has ' \
                  'drifts: {res}.'.format(
                      resource_type=resource_type,
                      resource_id=iface.resource_id,
                      res=result)
        logger.error('Expected configuration: {}'.format(
            iface.expected_configuration))
        logger.error('Remote configuration: {}'.format(
            iface.remote_configuration))
        raise RuntimeError(message)
    logger.info(
        'The {resource_type} {resource_id} '
        'configuration has not drifted.'.format(
            resource_type=resource_type, resource_id=iface.resource_id))
    return


class SkipWaitingOperation(Exception):
    pass


def delete_will_succeed(fn, params):
    try:
        iface = params.pop('iface')
        __ctx = params.pop('ctx')
        fn_params = deepcopy(params)
        params['ctx'] = __ctx
        params['iface'] = iface
        fn(**fn_params, ctx=__ctx, iface=iface, dry_run=True)
    except (ClientError, NonRecoverableError) as e:
        if 'would have succeeded' in str(e):
            return True
        return False

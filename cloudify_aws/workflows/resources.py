from cloudify import ctx as _ctx
from cloudify.decorators import operation
from cloudify.exceptions import NonRecoverableError

from ..common import utils
from ..eks.resources import cluster
from ..common.connection import Boto3Connection

TYPES_MATRIX = {
    'AWS::EKS::CLUSTER': (cluster.EKSCluster, 'eks', 'cluster', 'name')
}


@operation
def initialize(resource_config=None, regions=None, ctx=None, **_):
    """ Initialize an cloudify.nodes.resources.AmazonWebServices node.
    This checks for resource_types in resource config and regions in regions.

    :param resource_config: A dict with key resource_types,
      a list of AWS types like AWS::EKS::CLUSTER.
    :param regions: A list of regions, like [us-east-1, us-east-2].
    :param ctx: Cloudify CTX
    :param _:
    :return:
    """

    ctx = ctx or _ctx
    ctx.logger.info('Initializing AWS Account Info')
    ctx.logger.info('Checking for these regions: {r}.'.format(r=regions))
    resource_types = resource_config.get('resource_types', [])
    ctx.logger.info('Checking for these resource types: {t}.'.format(
        t=resource_types))

    ctx.instance.runtime_properties['resources'] = get_resources(
        ctx.node, regions, resource_types, ctx.logger)


@operation
def deinitialize(ctx, **_):
    """Delete the resources runtime property. """
    ctx = ctx or _ctx
    del ctx.instance.runtime_properties['resources']


def get_resources(node, regions, resource_types, logger):
    """Get a dict of resources in the following structure:

    :param node: ctx.node
    :param regions: list of AWS regions, i.e. us-east-1
    :param resource_types: List of resource types, i.e. AWS::EKS::CLUSTER.
    :param logger: ctx logger
    :return: a dictionary of resources in the structure:
        {
            'AWS::EKS::CLUSTER': {
                'us-east-1': {
                    'resource_id': resource
                }
            }
        }
    """

    logger.info('Checking for these regions: {r}.'.format(r=regions))
    logger.info('Checking for these resource types: {t}.'.format(
        t=resource_types))
    resources = {}
    regions = regions or get_regions(node)
    # The structure goes resources.region.resource_type.resource, so we start
    # with region.
    for region in regions:
        logger.info('Checking for this region: {r}.'.format(
            r=region))
        # then resource type.
        for resource_type in resource_types:
            logger.info(
                'Checking for this resource type: {t}.'.format(
                    t=resource_type))
            if region not in resources:
                resources[region] = {resource_type: {}}
            elif resource_type not in resources[region]:
                resources[region][resource_type] = {}
            # Get the class callable, the service name, and resource_id key.
            class_decl, service_name, type_key, resource_key = \
                TYPES_MATRIX.get(resource_type)
            # Note that the service_name needs to be updated in the Cloudify
            # AWS plugin resource module class for supporting new types.
            if not class_decl:
                # It means that we don't support whatever they provided.
                raise NonRecoverableError(
                    'Unsupported resource type: {t}.'.format(t=resource_type))
            iface = class_decl(
                **class_declaration_attributes(
                    node, service_name, region, logger))
            # Get the resource response from the API.
            # Clean it up for context serialization.
            result = utils.JsonCleanuper(iface.describe_all()).to_dict()
            # Add this stuff to the resources dict.
            for resource in result:
                logger.debug('Checking this resource: {}'.format(resource))
                resource_id = resource[type_key][resource_key]
                resources[region][resource_type][resource_id] = resource
    return resources


def class_declaration_attributes(node, service, region=None, logger=None):
    """Create the arguments for initializing the resource class.

    :param node: ctx node
    :param service: service name for boto3 client
    :param region: region name
    :param logger: ctx logger
    :return:
    """
    logger = logger or _ctx.logger
    if region:
        connection = Boto3Connection(node)
        connection.aws_config['region_name'] = region
        client = connection.client(service)
    else:
        client = None
    attributes = {
        'ctx_node': node,
        'resource_id': '',
        'client': client,
        'logger': logger
    }
    return attributes


def get_regions(node):
    connection = Boto3Connection(node)
    client = connection.client('ec2')
    response = client.describe_regions()
    return [r['RegionName'] for r in response['Regions']]


def get_availability_zones(node):
    connection = Boto3Connection(node)
    client = connection.client('ec2')
    response = client.describe_availability_zones()
    return [r['ZoneName'] for r in response['AvailabilityZones']]

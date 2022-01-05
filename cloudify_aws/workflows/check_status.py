from contextlib import contextmanager

from cloudify.decorators import operation

from ..common import utils


@operation
def check_status(ctx, *_, **__):
    with node_interface(ctx) as interface:
        message = 'Resource {_id} of type {_type} is {status}'.format(
            _id=interface.resource_id,
            _type=interface.type_name,
            status=interface.check_status)
        if interface.check_status.lower() == 'ok':
            ctx.logger.info(message)
            return interface.check_status.lower()
        raise ValueError(message)


@contextmanager
def node_interface(ctx):
    if 'cloudify.nodes.aws.eks.Cluster' in ctx.node.type_hierarchy:
        from ..eks.resources import cluster as module
    elif 'cloudify.nodes.aws.eks.NodeGroup' in ctx.node.type_hierarchy:
        from ..eks.resources import node_group as module
    elif 'cloudify.nodes.aws.ec2.Vpc' in ctx.node.type_hierarchy:
        from ..ec2.resources import vpc as module
    elif 'cloudify.nodes.aws.ec2.Subnet' in ctx.node.type_hierarchy:
        from ..ec2.resources import subnet as module
    elif 'cloudify.nodes.aws.ec2.SecurityGroup' in ctx.node.type_hierarchy:
        from ..ec2.resources import securitygroup as module
    elif 'cloudify.nodes.aws.ec2.NATGateway' in ctx.node.type_hierarchy:
        from ..ec2.resources import nat_gateway as module
    elif 'cloudify.nodes.aws.ec2.Interface' in ctx.node.type_hierarchy:
        from ..ec2.resources import eni as module
    elif 'cloudify.nodes.aws.ec2.Instances' in ctx.node.type_hierarchy:
        from ..ec2.resources import instances as module
    elif 'cloudify.nodes.aws.ec2.ElasticIP' in ctx.node.type_hierarchy:
        from ..ec2.resources import elasticip as module
    elif 'cloudify.nodes.aws.ec2.InternetGateway' in ctx.node.type_hierarchy:
        from ..ec2.resources import internet_gateway as module
    elif 'cloudify.nodes.aws.ec2.RouteTable' in ctx.node.type_hierarchy:
        from ..ec2.resources import routetable as module
    else:
        raise ValueError(
            'Check status is not supported on node type {_type}.'.format(
                _type=ctx.node.type_hierarchy[-1]))
    yield initialize_node_interface(ctx, module.interface)


def initialize_node_interface(ctx, class_definition):
    module_init_kwargs = {
        'ctx_node': ctx.node,
        'logger': ctx.logger,
        'resource_id': utils.get_resource_id(
            node=ctx.node, instance=ctx.instance),
    }
    return class_definition(**module_init_kwargs)

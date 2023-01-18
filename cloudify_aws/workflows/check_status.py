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
        if not interface.check_status.lower() == 'ok':
            raise RuntimeError(message)
        ctx.logger.info(message)


@contextmanager
def node_interface(ctx):
    if 'cloudify.nodes.aws.eks.Cluster' in ctx.node.type_hierarchy:
        from ..eks.resources import cluster as module
        yield initialize_node_interface(ctx, module.interface)
    elif 'cloudify.nodes.aws.eks.NodeGroup' in ctx.node.type_hierarchy:
        from ..eks.resources import node_group as module
        yield initialize_node_interface(ctx, module.interface)
    elif 'cloudify.nodes.aws.ec2.Vpc' in ctx.node.type_hierarchy:
        from ..ec2.resources import vpc as module
        yield initialize_node_interface(ctx, module.interface)
    elif 'cloudify.nodes.aws.ec2.Subnet' in ctx.node.type_hierarchy:
        from ..ec2.resources import subnet as module
        yield initialize_node_interface(ctx, module.interface)
    elif 'cloudify.nodes.aws.ec2.SecurityGroup' in ctx.node.type_hierarchy:
        from ..ec2.resources import securitygroup as module
        yield initialize_node_interface(ctx, module.interface)
    elif 'cloudify.nodes.aws.ec2.NATGateway' in ctx.node.type_hierarchy:
        from ..ec2.resources import nat_gateway as module
        yield initialize_node_interface(ctx, module.interface)
    elif 'cloudify.nodes.aws.ec2.Interface' in ctx.node.type_hierarchy:
        from ..ec2.resources import eni as module
        yield initialize_node_interface(ctx, module.interface)
    elif 'cloudify.nodes.aws.ec2.Instances' in ctx.node.type_hierarchy:
        from ..ec2.resources import instances as module
        yield initialize_node_interface(ctx, module.interface)
    elif 'cloudify.nodes.aws.ec2.ElasticIP' in ctx.node.type_hierarchy:
        from ..ec2.resources import elasticip as module
        yield initialize_node_interface(ctx, module.interface)
    elif 'cloudify.nodes.aws.ec2.InternetGateway' in ctx.node.type_hierarchy:
        from ..ec2.resources import internet_gateway as module
        yield initialize_node_interface(ctx, module.interface)
    elif 'cloudify.nodes.aws.ec2.RouteTable' in ctx.node.type_hierarchy:
        from ..ec2.resources import routetable as module
        yield initialize_node_interface(ctx, module.interface)
    else:
        ctx.logger.error(
            'Check status is not supported on node type {_type}.'.format(
                _type=ctx.node.type_hierarchy[-1]))
        yield


def initialize_node_interface(ctx, class_definition):
    module_init_kwargs = {
        'ctx_node': ctx.node,
        'logger': ctx.logger,
        'resource_id': utils.get_resource_id(
            node=ctx.node, instance=ctx.instance),
    }
    return class_definition(**module_init_kwargs)

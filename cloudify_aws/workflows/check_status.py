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
    else:
        raise ValueError(
            'Check status is not supported on node type {_type}.'.format(
                _type=ctx.node.type_hierarchy))
    yield initialize_node_interface(ctx, module.interface)


def initialize_node_interface(ctx, class_definition):
    module_init_kwargs = {
        'ctx_node': ctx.node,
        'logger': ctx.logger,
        'resource_id': utils.get_resource_id(
            node=ctx.node, instance=ctx.instance),
    }
    return class_definition(**module_init_kwargs)

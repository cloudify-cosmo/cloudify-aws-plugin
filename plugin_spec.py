from yaml import dump

from cloudify.state import current_ctx
from cloudify.mocks import MockCloudifyContext
from cloudify_aws.ec2.resources.instances import EC2Instances

SUPPORTED_TYPES = [EC2Instances]
mock_ctx = MockCloudifyContext()
current_ctx.set(mock_ctx)


def create_plugin_yaml():
    plugin_dict = {}
    for supported_resource_type in SUPPORTED_TYPES:
        plugin_dict.update(supported_resource_type(mock_ctx,).to_dict())
    return dump(plugin_dict, sort_keys=False)


if __name__ == '__main__':
    print(create_plugin_yaml())

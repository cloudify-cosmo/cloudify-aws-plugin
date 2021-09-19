
class NodeProperty(object):
    def __init__(self, name, type=None, description=None, default=None, required=None):
        self.name = name
        self.type = type
        self.description = description
        self.default = default
        self.required = required

    def to_dict(self):
        return {
            self.name: {
                'type': self.type,
                'description': self.description,
                'default': self.default,
                'required': self.required
            }
        }


class CloudifyPluginSpec(object):

    def __init__(self):
        self._cloudify_node_type_properties = None
        self.default_node_properties = [
            NodeProperty(
                'use_external_resource',
                bool,
                'Indicate whether the resource exists or if '
                'Cloudify should create the resource, true if '
                'you are bringing an existing resource, false '
                'if you want cloudify to create it.',
                False,
            ),
            NodeProperty(
                'resource_id',
                str,
                'The AWS resource ID of the external resource, '
                'if use_external_resource is true. Otherwise '
                'it is an empty string.',
                '',
            ),
        ]

    @property
    def client_config(self):
        raise NotImplemented('The client_config property should be '
                             'implemented by subclass.')

    @property
    def cloudify_node_properties(self):
        node_properties = dict(**self.client_config.to_dict())
        for default_prop in self.default_node_properties:
            node_properties.update(default_prop.to_dict())
        if self._cloudify_node_type_properties:
            node_properties.update(self._cloudify_node_type_properties)
        return node_properties


class CloudifyAWSPluginSpec(CloudifyPluginSpec):

    @property
    def client_config(self):
        return NodeProperty(
            'client_config',
            dict,
            'A dictionary of values to pass to authenticate with the AWS API.',
            {}
        )

import yaml
from inspect import getfullargspec


class NodeProperty(object):
    def __init__(self,
                 cloudify_node_property_name,
                 cloudify_node_property_type=None,
                 cloudify_node_property_description=None,
                 cloudify_node_property_default=None,
                 cloudify_node_property_required=False):
        """ Represents a node type property.

        :param cloudify_node_property_name: Name, for example,
            use_external_resource.
        :param cloudify_node_property_type: Type, for example,
            bool. Type should be provided as Python name. (Boot, not boolean.)
        :param cloudify_node_property_description: A string description.
        :param cloudify_node_property_default: The default value, for example,
            False, not false.
        :param cloudify_node_property_required: Bool value.
        """

        self.cloudify_node_property_name = cloudify_node_property_name
        self.cloudify_node_property_type = cloudify_node_property_type
        self.cloudify_node_property_description = \
            cloudify_node_property_description
        self.cloudify_node_property_default = cloudify_node_property_default
        self.cloudify_node_property_required = cloudify_node_property_required

    def to_dict(self):
        return {
            self.cloudify_node_property_name: {
                'type': self.cloudify_node_property_type,
                'description': self.cloudify_node_property_description,
                'default': self.cloudify_node_property_default,
                'required': self.cloudify_node_property_required
            }
        }


class NodeInterfaceInput(object):

    def __init__(self,
                 cloudify_input_name,
                 cloudify_input_type=None,
                 cloudify_input_description=None,
                 cloudify_input_default=None,
                 cloudify_input_required=False):
        """ A node interface input.

        :param cloudify_input_name:
        :param cloudify_input_type:
        :param cloudify_input_description:
        :param cloudify_input_default:
        :param cloudify_input_required:
        """

        self.cloudify_input_name = cloudify_input_name
        self.cloudify_input_type = cloudify_input_type
        self.cloudify_input_description = \
            cloudify_input_description
        self.cloudify_input_default = cloudify_input_default
        self.cloudify_input_required = cloudify_input_required

    def to_dict(self):
        return {
            self.cloudify_input_name: {
                'type': self.cloudify_input_type,
                'description': self.cloudify_input_description,
                'default': self.cloudify_input_default,
                'required': self.cloudify_input_required
            }
        }


class NodeTypeInterface(object):
    def __init__(self,
                 node_interface_operation_name,
                 node_interface_implementation,
                 node_interface_executor=None,
                 node_interface_inputs=None):

        self.node_interface_operation_name = node_interface_operation_name
        self.node_interface_implementation = node_interface_implementation
        self.node_interface_executor = \
            node_interface_executor or 'central_deployment_agent'
        self._node_interface_inputs = node_interface_inputs
        self._common_node_interface_inputs = []

    @property
    def node_interface_inputs(self):
        inputs = {}
        for _input in self._common_node_interface_inputs:
            inputs.update(_input.to_dict())
        inputs.update(**self._node_interface_inputs)
        return inputs

    def to_dict(self):

        return {
            self.node_interface_operation_name: {
                'implementation': self.node_interface_implementation,
                'executor': self.node_interface_executor,
                'inputs': self.node_interface_inputs
            }
        }


class CloudifyAWSNodeInterface(NodeTypeInterface):

    @property
    def _common_node_interface_inputs(self):
        return [
            NodeInterfaceInput(
                'aws_resource_id',
                str,
                'This overrides the resource_id property '
                '(useful for setting the resource ID of a '
                'node instance at runtime).',
            ),
            NodeInterfaceInput(
                'runtime_properties',
                dict,
                'This overrides any runtime property at '
                'runtime. This is a key-value pair / '
                'dictionary that will be passed, as-is, to '
                'the runtime properties of the running '
                'instance.',
            ),
            NodeInterfaceInput(
                'force_operation',
                bool,
                'Forces the current operation to be executed '
                'regardless if the "use_external_resource" '
                'property is set or not.',
            ),
            NodeInterfaceInput(
                'resource_config',
                dict,
                'Configuration key-value data to be passed '
                'as-is to the corresponding Boto3 method. Key '
                'names must match the case that Boto3 '
                'requires.',
            ),
        ]


class CloudifyRelationship(object):

    def __init__(self,
                 cloudify_relationship_name,
                 supported_target_node_types=None):
        self.cloudify_relationship_name = cloudify_relationship_name
        self.supported_target_node_types = supported_target_node_types

    def to_dict(self):
        return {
            self.cloudify_relationship_name: {
                'supported_target_types': self.supported_target_node_types
            }
        }


class CloudifyPluginSpec(object):

    def __init__(self,
                 cloudify_node_type_name=None,
                 cloudify_node_type_parent=None,
                 cloudify_node_type_relationships=None,
                 **kwargs):
        self.cloudify_node_type_name = cloudify_node_type_name
        self.cloudify_node_type_parent = cloudify_node_type_parent
        self._cloudify_node_type_properties = None
        self._cloudify_node_type_relationships = \
            cloudify_node_type_relationships
        self.default_cloudify_node_properties = [
            NodeProperty(
                'use_external_resource',
                bool,
                'Indicate whether the resource exists or if '
                'Cloudify should create the resource, true if '
                'you are bringing an existing resource, false '
                'if you want cloudify to create it.',
                cloudify_node_property_default=False
            ),
            NodeProperty(
                'resource_id',
                str,
                'The AWS resource ID of the external resource, '
                'if use_external_resource is true. Otherwise '
                'it is an empty string.',
                cloudify_node_property_default='',
            ),
        ]

    @property
    def default_relationships(self):
        return [
            CloudifyRelationship('cloudify.relationships.depends_on'),
            CloudifyRelationship('cloudify.relationships.connected_to'),
            CloudifyRelationship('cloudify.relationships.contained_in',
                                 ['cloudify.nodes.Compute'])
        ]

    @property
    def cloudify_node_type_relationships(self):
        relationships = {}
        for relationship in self.default_relationships:
            relationships.update(**relationship.to_dict())
        for relationship in self._cloudify_node_type_relationships:
            relationships.update(**relationship)
        return relationships

    @property
    def cloudify_node_properties(self):
        node_properties = dict(**self.client_config_node_property.to_dict())
        for default_prop in self.default_cloudify_node_properties:
            node_properties.update(default_prop.to_dict())
        if self._cloudify_node_type_properties:
            node_properties.update(self._cloudify_node_type_properties)
        return node_properties

    @property
    def client_config_node_property(self):
        raise NotImplemented(
            'The client_config property should be implemented by subclass.')

    @property
    def cloudify_interfaces_lifecycle_precreate(self):
        return

    @property
    def cloudify_interfaces_lifecycle_create(self):
        return

    @property
    def cloudify_interfaces_lifecycle_preconfigure(self):
        return

    @property
    def cloudify_interfaces_lifecycle_configure(self):
        return

    @property
    def cloudify_interfaces_lifecycle_postconfigure(self):
        return

    @property
    def cloudify_interfaces_lifecycle_start(self):
        return

    @property
    def cloudify_interfaces_lifecycle_poststart(self):
        return

    @property
    def cloudify_interfaces_lifecycle_establish(self):
        return

    @property
    def cloudify_interfaces_lifecycle_prestop(self):
        return

    @property
    def cloudify_interfaces_lifecycle_stop(self):
        return

    @property
    def cloudify_interfaces_lifecycle_unlink(self):
        return

    @property
    def cloudify_interfaces_lifecycle_delete(self):
        return

    @property
    def cloudify_interfaces_lifecycle_postdelete(self):
        return

    @property
    def install_workflow_node_interfaces(self):
        raise NotImplementedError(
            'Must be implemented by subclass. '
            'For example, if you have create and start operations, like this: '
            '{'
            '    \'create\': self.cloudify_interfaces_lifecycle_create',
            '    \'start\': self.cloudify_interfaces_lifecycle_start',
            '}'
        )

    @property
    def uninstall_workflow_node_interfaces(self):
        raise NotImplementedError(
            'Must be implemented by subclass. '
            'For example, if you have stop and delete operations, like this: '
            '{'
            '    \'create\': self.cloudify_interfaces_lifecycle_stop',
            '    \'start\': self.cloudify_interfaces_lifecycle_delete',
            '}'
        )

    @property
    def cloudify_node_type_interfaces(self):
        # This can be customized for each node type.
        interfaces = {}
        interfaces.update(**self.install_workflow_node_interfaces)
        interfaces.update(**self.uninstall_workflow_node_interfaces)
        return interfaces

    @staticmethod
    def get_arg_names_and_defaults(method):
        arg_names_and_defaults = []
        spec = getfullargspec(method)
        kwargs_split_index = len(spec.args) - len(spec.defaults)
        for index in range(0, len(spec.args)):
            if index < kwargs_split_index:
                arg_name_and_default = {
                    spec.args[index]: {
                        'default': None
                    }
                }
                arg_names_and_defaults.append(arg_name_and_default)
            else:
                arg_name_and_default = {
                    spec.args[index]: {
                        'default': spec.defaults[index - kwargs_split_index]
                    }
                }
                arg_names_and_defaults.append(arg_name_and_default)
        return arg_names_and_defaults

    def to_dict(self):
        return {
            self.cloudify_node_type_name: {
                'derived_from': self.cloudify_node_type_parent,
                'properties': self.cloudify_node_properties,
                'interfaces': self.cloudify_node_type_interfaces,
            }
        }

    def to_yaml(self):
        return yaml.dump(self.to_dict(), allow_unicode=True)


class CloudifyAWSPluginSpec(CloudifyPluginSpec):

    @property
    def client_config(self):
        return NodeProperty(
            'client_config',
            dict,
            'A dictionary of values to pass to authenticate with the AWS API.',
            {}
        )

    @property
    def cloudify_interfaces_lifecycle_create(self):
        return CloudifyAWSNodeInterface(
            'create',
            None
        )

    @property
    def install_workflow_node_interfaces(self):
        raise NotImplementedError(
            'Must be implemented by subclass. '
            'For example, if you have create and start operations, like this: '
            '{'
            '    \'create\': self.cloudify_interfaces_lifecycle_create',
            '    \'start\': self.cloudify_interfaces_lifecycle_start',
            '}'
        )

    @property
    def uninstall_workflow_node_interfaces(self):
        raise NotImplementedError(
            'Must be implemented by subclass. '
            'For example, if you have stop and delete operations, like this: '
            '{'
            '    \'create\': self.cloudify_interfaces_lifecycle_stop',
            '    \'start\': self.cloudify_interfaces_lifecycle_delete',
            '}'
        )

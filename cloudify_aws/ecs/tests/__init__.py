########
# Copyright (c) 2015 GigaSpaces Technologies Ltd. All rights reserved
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

# Stdlib imports
import os

# Third party imports
import yaml
from mock import Mock

# Cloudify imports

# This package imports


_plugin_yaml_dict = None


def make_node_context(ctx,
                      node,
                      properties=None,
                      runtime_properties=None,
                      plugin_name='aws',
                      plugin_file=None):
    properties = properties or {}
    runtime_properties = runtime_properties or {}

    if plugin_file is None:
        # Assuming plugin.yaml in root of repo
        # Assuming tests folder in: <repo root>/cloudify_aws/<component>/tests
        # This is the directory we're in
        path = os.path.split(__file__)[0]
        # Equivalent to ../../..
        path = os.path.split(os.path.split(os.path.split(path)[0])[0])[0]
        plugin_file = os.path.join(path, 'plugin.yaml')

    global _plugin_yaml_dict
    if _plugin_yaml_dict is None:
        with open(plugin_file) as plugin_handle:
            _plugin_yaml_dict = yaml.load(plugin_handle.read())

    node = 'cloudify.{plugin}.nodes.{node}'.format(
        plugin=plugin_name,
        node=node,
    )

    node_properties = _plugin_yaml_dict['node_types'][node]['properties']

    ctx.node.properties = {}
    for prop, details in node_properties.items():
        if prop in properties.keys():
            ctx.node.properties[prop] = properties.pop(prop)
        elif 'default' in details.keys():
            ctx.node.properties[prop] = details['default']
        elif details.get('required', False):
            raise KeyError(
                'Key {key} was missing from properties for mock ctx'.format(
                    key=prop,
                )
            )

    if len(properties) > 0:
        raise KeyError(
            'Some properties could not be processed when creating a mock '
            'node context. Remaining properties: {props}'.format(
                props=str(properties),
            )
        )

    ctx.instance.runtime_properties = runtime_properties

    return ctx


def configure_mock_connection(mock_conn):
    mock_client = Mock()

    mock_conn.return_value.client3.return_value = mock_client

    return mock_client

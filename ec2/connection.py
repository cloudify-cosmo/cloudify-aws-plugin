########
# Copyright (c) 2014 GigaSpaces Technologies Ltd. All rights reserved
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

# Third-party Imports
from boto.ec2 import get_region
from boto.ec2 import EC2Connection

# Cloudify Imports
from ec2 import constants
from cloudify import ctx
from cloudify.exceptions import NonRecoverableError


class EC2ConnectionClient():
    """Provides functions for getting the EC2 Client
    """

    def __init__(self):
        self.connection = None

    def client(self):
        """Represents the EC2Connection Client
        """

        node_properties = self._get_node_type()

        if not node_properties['aws_configure']:
            return EC2Connection()
        elif 'region' in node_properties['aws_configure']:
            region = get_region(node_properties['aws_configure']['region'])
            aws_configure = node_properties['aws_configure'].copy()
            aws_configure.update({'region': region})

        return EC2Connection(**aws_configure)

    def _get_node_type(self):

        if ctx.type == constants.RELATIONSHIP_INSTANCE:
            return ctx.source.node.properties
        elif ctx.type == constants.NODE_INSTANCE:
            return ctx.node.properties
        else:
            raise NonRecoverableError(
                'Context is neither {0} nor {1}. '
                'Cannot create EC2ConnectionClient.'
                .format(
                    constants.RELATIONSHIP_INSTANCE,
                    constants.NODE_INSTANCE))

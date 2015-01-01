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

# built-in package

# other packages
from boto.ec2 import EC2Connection
from boto.ec2 import connect_to_region
from boto.exception import EC2ResponseError

# ctx packages
from cloudify import ctx
from cloudify.exceptions import NonRecoverableError


class EC2Client():

    def __init__(self):
        self.connection = None

    def connect(self):

        ctx.logger.info('(Node: {0}): Connecting to AWS EC2.'.format(ctx.instance.id))

        try:
            self.connection = EC2Connection()
        except EC2ResponseError:
            ctx.logger.error("""(Node: {0}): Error.
                             Failed to connect to EC2: API returned: {1}."""
                             .format(ctx.instance.id, EC2ResponseError.body))
            raise NonRecoverableError('(Node: {0}): Error. Failed to connect to EC2: API returned: {1}.'
                                      .format(ctx.instance.id, EC2ResponseError.body))

        return self.connection

    def connect_to_region(self, region):

        ctx.logger.info('(Node: {0}): Connecting to AWS EC2 region: {1}.'.format(ctx.instance.id, region))

        try:
            self.connection = connect_to_region(region)
        except EC2ResponseError:
            ctx.logger.error("""(Node: {0}): Error.
                             Failed to connect to EC2 region {1}: API returned: {2}."""
                             .format(ctx.instance.id, region, EC2ResponseError.body))
            raise NonRecoverableError('(Node: {0}): Error. Failed to connect to EC2 region {1}: API returned: {2}.'
                                      .format(ctx.instance.id, region, EC2ResponseError.body))

        return self.connection

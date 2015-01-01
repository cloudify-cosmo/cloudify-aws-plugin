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
from cloudify.decorators import operation


class EC2Client():

    def __init__(self):
        self.connection = None

    @operation
    def connect(self, **kwargs):

        ctx.logger.info('(Connecting to AWS EC2.')

        try:
            self.connection = EC2Connection()
        except EC2ResponseError:
            ctx.logger.error("""Failed to connect to EC2: API returned: {0}."""
                             .format(EC2ResponseError))
            raise NonRecoverableError("""Error. Failed to connect to EC2:
                                         API returned: {0}."""
                                      .format(EC2ResponseError))

        return self.connection

    @operation
    def connect_to_region(self, region, **kwargs):

        ctx.logger.info('(Connecting to AWS EC2.')

        try:
            self.connection = connect_to_region(region)
        except EC2ResponseError:
            ctx.logger.error("""Failed to connect to EC2: API returned: {0}."""
                             .format(EC2ResponseError))
            raise NonRecoverableError("""Error. Failed to connect to EC2:
                                         API returned: {0}."""
                                      .format(EC2ResponseError))

        return self.connection

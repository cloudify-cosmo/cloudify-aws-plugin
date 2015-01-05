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

# Other Imports
from boto.ec2 import EC2Connection
from boto.exception import EC2ResponseError, BotoServerError

# Cloudify Imports
from cloudify.exceptions import NonRecoverableError


class EC2Client():

    def __init__(self):
        self.connection = None

    def connect(self):

        try:
            self.connection = EC2Connection()
        except (EC2ResponseError, BotoServerError) as e:
            raise NonRecoverableError('Error. Failed to connect to EC2:'
                                      'API returned: {0}.'
                                      .format(e))

        return self.connection

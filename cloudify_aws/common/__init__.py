# #######
# Copyright (c) 2018 Cloudify Platform Ltd. All rights reserved
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
'''
    Common
    ~~~~~~
    AWS common interfaces
'''
import sys
from logging import NullHandler

# Boto
from botocore.exceptions import ClientError, ParamValidationError

# Cloudify
from cloudify.exceptions import NonRecoverableError
from cloudify.logs import init_cloudify_logger
from cloudify.utils import exception_to_error_cause

FATAL_EXCEPTIONS = (ClientError, ParamValidationError)


class AWSResourceBase(object):
    '''
        AWS base interface
    '''
    def __init__(self, client, resource_id=None, logger=None):
        self.logger = logger or init_cloudify_logger(NullHandler(),
                                                     'AWSResourceBase')
        self.client = client
        self.resource_id = str(resource_id) if resource_id else None

    def update_resource_id(self, resource_id):
        '''Updates the resource_id value'''
        self.resource_id = resource_id

    @property
    def properties(self):
        '''Gets the properties of an external resource'''
        raise NotImplementedError()

    @property
    def status(self):
        '''Gets the status of an external resource'''
        raise NotImplementedError()

    def create(self, params):
        '''Creates a resource'''
        raise NotImplementedError()

    def make_client_call(self,
                         client_method_name,
                         client_method_args=None,
                         log_response=True,
                         fatal_handled_exceptions=FATAL_EXCEPTIONS):
        """

        :param client_method_name: A method on self.client.
        :param client_method_args: Optional Args.
        :param log_response: Whether to log API response.
        :param fatal_handled_exceptions: exceptions to fail on.
        :return: Either Exception class or successful response content.
        """

        type_name = getattr(self, 'type_name')

        self.logger.debug(
            'Calling {0} method {1} with parameters: {2}'.format(
                type_name, client_method_name, client_method_args))

        client_method = getattr(self.client, client_method_name)

        if not client_method:
            return
        try:
            if isinstance(client_method_args, dict):
                res = client_method(**client_method_args)
            elif isinstance(client_method_args, list):
                res = client_method(*client_method_args)
            else:
                res = client_method_args()
        except fatal_handled_exceptions as error:
            _, _, tb = sys.exc_info()
            raise NonRecoverableError(
                str(error.message),
                causes=[exception_to_error_cause(error, tb)])
        else:
            if log_response:
                self.logger.debug('Response: {0}'.format(res))
        return res

    def delete(self, params=None):
        '''Deletes a resource'''
        raise NotImplementedError()

    def verify_resource_exists(self):
        if not getattr(self, 'properties', {}):
            return False
        return True

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
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
'''
    Common
    ~~~~~~
    AWS common interfaces
'''
import sys
from logging import NullHandler, DEBUG

# Boto
from boto3 import set_stream_logger
from botocore.exceptions import ClientError, ParamValidationError

# Cloudify
from cloudify.exceptions import NonRecoverableError
from cloudify.logs import init_cloudify_logger
from cloudify.utils import exception_to_error_cause
from cloudify_aws.common._compat import text_type

from deepdiff import DeepDiff

from . import utils

FATAL_EXCEPTIONS = (ClientError, ParamValidationError)
NTP_NOTE = ". If you are positive that you are using the correct " \
           "credentials, " \
           "verify that your system clock is in sync with its NTP server."


class AWSResourceBase(object):
    '''
        AWS base interface
    '''

    def __init__(self, client, resource_id=None, logger=None):
        # Botocore logs for debugging.
        set_stream_logger('botocore.parsers', level=DEBUG)
        self.logger = logger or init_cloudify_logger(NullHandler(),
                                                     'AWSResourceBase')
        self._client = client
        self._resource_id = text_type(resource_id) if resource_id else None
        self._initial_configuration = None  # resource_config from node props
        self._create_response = None  # create_response
        self._remote_configuration = None  # Describe Result
        self._expected_configuration = None  # Current extrapolation
        self._previous_configuration = None  # Previous extrapolation
        self._describe_call = None

    @property
    def client(self):
        return self._client

    @client.setter
    def client(self, value):
        self._client = value

    def get_describe_result(self, params):
        try:
            return self.make_client_call(self._describe_call, params)
        except NonRecoverableError:
            return {}

    def compare_configuration(self):
        result = DeepDiff(self.expected_configuration,
                          self.remote_configuration)
        delta = utils.JsonCleanuper(result)
        return delta.to_dict()

    def import_configuration(self, resource_config, runtime_props):
        """ Read all of the various runtime properties where we store
        state data into the current object.

        :param resource_config: from node props
        :param runtime_props: from ctx
        :return:
        """
        self.initial_configuration = resource_config
        self.create_response = runtime_props.get('create_response')
        self.expected_configuration = runtime_props.get(
            'expected_configuration')

    @property
    def previous_configuration(self):
        """This is the configuration that used to be expected_configuration.
        For example, if a VPC was created:
            {'cidr': '10.10.0.0/24'}
        Then it's current configuration is the same.
        However if then we changed it to:
            {'cidr': '10.11.0.0/32'}
        Then it's current configuration is now that, and the previous one is:
            {'cidr': '10.10.0.0/24'}
        This is used for debug and no logic is here except after updates
        to move current_configuration to this.
        :return:
        """
        return self._previous_configuration or {}

    @previous_configuration.setter
    def previous_configuration(self, value):
        self._previous_configuration = value

    @property
    def expected_configuration(self):
        """This is the expected configuration.
        It should be the last modification made to the resource.
        """
        return utils.JsonCleanuper(
            self._expected_configuration).to_dict() or {}

    @expected_configuration.setter
    def expected_configuration(self, value):
        self._expected_configuration = utils.JsonCleanuper(value).to_dict()

    @property
    def remote_configuration(self):
        """This is the current remote configuration. It is only used in
        compare_configuration.

        :return:
        """
        if not self._remote_configuration:
            self._remote_configuration = utils.JsonCleanuper(
                self.properties).to_dict()
        return utils.JsonCleanuper(self._remote_configuration).to_dict() or {}

    @remote_configuration.setter
    def remote_configuration(self, value):
        self._remote_configuration = utils.JsonCleanuper(value).to_dict()

    @property
    def create_response(self):
        """This is the result from create. It should be assigned only once
        during create.

        :return:
        """
        return self._create_response or {}

    @create_response.setter
    def create_response(self, value):
        self._create_response = utils.JsonCleanuper(value).to_dict()

    @property
    def initial_configuration(self):
        """This is the original resource_config as it was resolved during
        the create operation. This is kind of a pair with create_response.
        """
        return self._initial_configuration or {}

    @initial_configuration.setter
    def initial_configuration(self, value):
        self._initial_configuration = utils.JsonCleanuper(value).to_dict()

    @property
    def resource_id(self):
        return self._resource_id

    @resource_id.setter
    def resource_id(self, value):
        self.update_resource_id(value)

    def update_resource_id(self, resource_id):
        '''Updates the resource_id value'''
        self._resource_id = resource_id

    def wait_for_status(self, *args, **kwargs):
        return False

    @property
    def properties(self):
        '''Gets the properties of an external resource'''
        raise NotImplementedError()

    @property
    def status(self):
        '''Gets the status of an external resource'''
        raise NotImplementedError()

    @property
    def resource_id(self):
        return self._resource_id

    @resource_id.setter
    def resource_id(self, value):
        self._resource_id = value

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
                res = client_method()
        except fatal_handled_exceptions as error:
            _, _, tb = sys.exc_info()
            if isinstance(error, ClientError) and hasattr(error, 'message'):
                message = error.message + NTP_NOTE
            else:
                message = 'API error encountered: {}'.format(error)
            raise NonRecoverableError(
                text_type(message),
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

    def populate_resource(self, ctx):
        """
        Provides means for resource classes to populate runtime properties
        with auxiliary information about the resource:

        For new resources (use_external_resource=False), this function is
        called right after the 'cloudify.interfaces.lifecycle.configure'
        operation, when the AWS resource ID is already known.

        For existing resources (use_external_resource=True), this function is
        called after the resource is validated to exist (as the AWS resource
        ID is already known at that point).

        :param ctx: Cloudify context
        :return: None
        """
        pass

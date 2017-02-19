# #######
# Copyright (c) 2017 GigaSpaces Technologies Ltd. All rights reserved
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
    EMR
    ~~~
    AWS EMR base interface
'''
from logging import NullHandler
# Cloudify
from cloudify.logs import init_cloudify_logger
from cloudify.exceptions import NonRecoverableError

# Cloudify AWS
from cloudify_aws import connection


class EMRBase(object):
    '''
        AWS EMR base interface
    '''
    def __init__(self, resource_id=None, client=None, logger=None):
        self.client = client or connection.EMRConnectionClient().client()
        self.logger = logger or init_cloudify_logger(NullHandler(), 'EMRBase')
        self.resource_id = resource_id

    @property
    def status(self):
        '''Gets the status of an external resource'''
        raise NotImplementedError()

    def delete(self):
        '''
            Deletes an EMR resource.

        .. note:
            AWS EMR objects generally perform operations
            asynchronously. This method triggers the start
            of such an operation and does not wait until
            the resource has been deleted.
        '''
        raise NotImplementedError()

    @staticmethod
    def raise_bad_state(status):
        '''Reports error data when a bad state is encountered'''
        statereason = dict(code=None, message=None)
        if hasattr(status.statechangereason, 'code'):
            statereason['code'] = status.statechangereason.code
        if hasattr(status.statechangereason, 'message'):
            statereason['message'] = status.statechangereason.message
        raise NonRecoverableError(
            'AWS EMR step encountered a fatal error. '
            'State: %s, Reason: (%s) %s' % (
                status.state,
                statereason['code'], statereason['message']))

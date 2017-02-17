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
# Cloudify
from cloudify.exceptions import NonRecoverableError
# Cloudify AWS
from cloudify_aws import constants, connection


class EMRBase(object):
    '''
        AWS EMR base interface
    '''
    def __init__(self, ctx, client=None, logger=None):
        self.client = client or connection.EMRConnectionClient().client()
        self.ctx = ctx
        self.logger = logger or self.ctx.logger

    @property
    def is_external(self):
        '''Checks if the instance is external'''
        return self.ctx.node.properties['use_external_resource']

    @property
    def resource_id(self):
        '''Get current AWS resource ID'''
        return self.ctx.node.properties.get('resource_id') or \
            self.ctx.instance.runtime_properties.get(
                constants.EXTERNAL_RESOURCE_ID)

    def update_resource_id(self, resource_id):
        '''Updates runtime property resource_id'''
        self.ctx.instance.runtime_properties[
            constants.EXTERNAL_RESOURCE_ID] = resource_id

    def update_runtime_properties(self, props):
        '''Updates runtime properties from a dict'''
        for key, val in props.iteritems():
            self.ctx.instance.runtime_properties[key] = val

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

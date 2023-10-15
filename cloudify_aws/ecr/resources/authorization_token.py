# Copyright (c) 2023 Cloudify Platform LTD. All rights reserved
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

"""
    ECRAuthorizationToken
    ~~~~~~~~~~~~~~
    AWS ECR Authorization Token Interface
"""

from __future__ import unicode_literals
from datetime import datetime, timedelta

# Cloudify
from cloudify_aws.ecr import ECRBase
from cloudify_aws.common import decorators


RESOURCE_TYPE = 'ECR Authorization Token'


class ECRAuthorizationToken(ECRBase):
    """
        ECRAuthorization Token interface
    """
    def __init__(self, ctx_node, resource_id=None, logger=None):
        ECRBase.__init__(self, ctx_node, resource_id, logger)
        self.type_name = RESOURCE_TYPE
        self.describe_service_filter = {}
        self._properties = {}

    @property
    def properties(self):
        """Gets the properties of an external resource"""
        return self._properties

    @properties.setter
    def properties(self, value):
        self._properties = value

    @property
    def status(self):
        """Gets the status of an external resource"""
        auth_data = self.properties.get('authorizationData', {})
        for token_data in auth_data:
            if self.token_needs_refresh(token_data['expiresAt']):
                return False
        return True

    def _get_authorization_token(self, **kwargs):
        return self.make_client_call(
            'get_authorization_token',
            client_method_args=kwargs,
            log_response=False,
        )

    def get_authorization_token(self, **kwargs):
        final_auth_data_list = []
        result = self._get_authorization_token(**kwargs)
        authorization_data = result['authorizationData']
        for token_data in authorization_data:
            token_data['expiresAt'] = token_data['expiresAt'].isoformat()
            final_auth_data_list.append(token_data)
        result['authorizationData'] = final_auth_data_list
        return result

    def create(self, params):
        self.properties = self.get_authorization_token(**params)
        return self.properties

    @staticmethod
    def token_needs_refresh(expires_at_time, timediff=None):
        timediff = timediff or timedelta(hours=1)
        expires_at_time = datetime.strptime(
            expires_at_time[:19], "%Y-%m-%dT%H:%M:%S")
        current_time = datetime.now()
        if current_time + timediff <= expires_at_time:
            return False
        return True


@decorators.aws_resource(ECRAuthorizationToken, RESOURCE_TYPE)
def prepare(ctx, resource_config, **_):
    """Prepares an AWS ECR Properties"""
    # Save the parameters
    resource_config = correct_config(resource_config)
    ctx.instance.runtime_properties['resource_config'] = resource_config


@decorators.aws_resource(ECRAuthorizationToken, RESOURCE_TYPE)
def create(ctx, resource_config, iface, **_):
    """Generate a Token"""
    resource_config = correct_config(resource_config)
    # Check and see if we already created a token with this node instance.
    create_response = ctx.instance.runtime_properties.get('create_response')
    if create_response:
        iface.properties = create_response
        # Check if existing token is still valid, if so, do nothing.
        if iface.status:
            return
    resource_config['registryIds'] = [
        f'{registry_id}' for registry_id in resource_config['registryIds']
    ]
    ctx.instance.runtime_properties['create_response'] = iface.create(
        resource_config)


def correct_config(resource_config):
    registry_ids = resource_config.pop('registryIds', [])
    if 'registryIds' not in resource_config:
        resource_config['registryIds'] = []
    for item in registry_ids:
        resource_config['registryIds'].append(str(item))
    return resource_config

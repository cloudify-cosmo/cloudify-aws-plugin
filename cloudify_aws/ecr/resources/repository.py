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

# Cloudify
from cloudify_aws.ecr import ECRBase
from cloudify_aws.common import utils, decorators
from cloudify.exceptions import (
    OperationRetry,
    NonRecoverableError
)


RESOURCE_TYPE = 'ECR Repository'
DELETE_KEYS = ['registryId', 'repositoryName', 'force']


class ECRRepository(ECRBase):
    """
        ECRRepository interface
    """
    def __init__(self, ctx_node, resource_id=None, logger=None):
        ECRBase.__init__(
            self,
            ctx_node,
            resource_id=resource_id,
            logger=logger
        )
        self.type_name = RESOURCE_TYPE
        resource_config = ctx_node.properties.get('resource_config')
        self.describe_service_filter = {
            'registryId': str(resource_config.get('registryId', '')),
            'repositoryNames': [resource_config.get('repositoryName')]
        }
        self._properties = None

    @property
    def properties(self):
        """Gets the properties of an external resource"""
        if not self._properties:
            try:
                self._properties = self.make_client_call(
                    'describe_repositories',
                    client_method_args=self.describe_service_filter
                )
            except NonRecoverableError as e:
                if 'RepositoryNotFoundException' in str(e):
                    self._properties = {}
                else:
                    raise e
        self.logger.debug(
            'ECR Repository properties: {}'.format(self._properties))
        return self._properties

    @properties.setter
    def properties(self, value):
        self._properties = value

    @property
    def status(self):
        return len(self.properties.get('repositories', []))

    def create(self, params):
        return self.make_client_call(
            'create_repository',
            client_method_args=params
        )

    def delete(self, params):
        return self.make_client_call(
            'delete_repository',
            client_method_args=params
        )


@decorators.aws_resource(ECRRepository, RESOURCE_TYPE)
def prepare(ctx, resource_config, **_):
    """Prepare AWS ECR Properties"""
    # Save the parameters
    ctx.instance.runtime_properties['resource_config'] = resource_config


@decorators.aws_resource(ECRRepository, RESOURCE_TYPE)
def create(ctx, resource_config, iface, **_):
    """Create a new repo"""
    # Check and see if we already created a token with this node instance.
    registry_id = resource_config.get('registryId', '')
    if registry_id:
        resource_config['registryId'] = str(registry_id)
    if not resource_config.get('repositoryName'):
        raise NonRecoverableError(
            'A repositoryName was not provided.')
    if not iface.status:
        create_response = iface.create(resource_config)
        ctx.instance.runtime_properties['create_response'] = \
            utils.JsonCleanuper(create_response).to_dict()
        raise OperationRetry(
            'Waiting for repo {} to be successfully created.'.format(
                resource_config['repositoryName']))


@decorators.aws_resource(ECRRepository, RESOURCE_TYPE)
def delete(ctx, resource_config, iface, **_):
    """Delete a repo"""
    if not resource_config.get('repositoryName'):
        create = ctx.instance.runtime_properties['create_response']
        repo = create.get('respository', {})
        repo_name = repo.get('repositoryName')
        if not repo_name:
            raise NonRecoverableError(
                'A repositoryName was not provided.')
        else:
            resource_config['repositoryName'] = repo_name
    if iface.status:

        registry_id = resource_config.get('registryId', '')
        if registry_id:
            resource_config['registryId'] = str(registry_id)
        for key in list(resource_config.keys()):
            if key not in DELETE_KEYS:
                del resource_config[key]

        iface.delete(resource_config)
        raise OperationRetry(
            'Waiting for repo {} to be successfully deleted.'.format(
                resource_config['repositoryName']))

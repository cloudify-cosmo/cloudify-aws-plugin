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
    RDS.OptionGroup
    ~~~~~~~~~~~~~~~
    AWS RDS parameter group interface
'''
# Cloudify
from cloudify_aws.common import decorators, utils
from cloudify_aws.rds import RDSBase
# Boto
from botocore.exceptions import ClientError, ParamValidationError

RESOURCE_TYPE = 'RDS Parameter Group'


class ParameterGroup(RDSBase):
    '''
        AWS RDS Parameter Group interface
    '''
    def __init__(self, ctx_node, resource_id=None, client=None, logger=None):
        RDSBase.__init__(self, ctx_node, resource_id, client, logger)
        self.type_name = RESOURCE_TYPE

    @property
    def properties(self):
        '''Gets the properties of an external resource'''
        if not self.resource_id:
            return
        resources = None
        try:
            resources = self.client.describe_db_parameter_groups(
                DBParameterGroupName=self.resource_id)
        except (ParamValidationError, ClientError):
            pass
        if not resources or not resources.get('DBParameterGroups', list()):
            return None
        return resources['DBParameterGroups'][0]

    @property
    def status(self):
        '''Gets the status of an external resource'''
        if self.properties:
            return 'available'
        return None

    def update_parameter(self, param):
        '''Adds a parameter to an AWS RDS parameter group'''
        return self.update(dict(Parameters=[param]))

    def update(self, params):
        '''Updates an existing AWS RDS parameter group'''
        params['DBParameterGroupName'] = self.resource_id
        self.logger.debug('Modifying parameter group: %s' % params)
        res = self.client.modify_db_parameter_group(**params)
        self.logger.debug('Response: %s' % res)
        return res['DBParameterGroupName']

    def create(self, params):
        '''
            Create a new AWS RDS parameter group.
        '''
        return self.make_client_call('create_db_parameter_group', params)

    def delete(self, params=None):
        '''
            Deletes an existing AWS RDS parameter group.
        '''
        params = params or dict()
        params.update(dict(DBParameterGroupName=self.resource_id))
        self.logger.debug('Deleting %s with parameters: %s'
                          % (self.type_name, params))
        self.client.delete_db_parameter_group(**params)


@decorators.aws_resource(ParameterGroup, RESOURCE_TYPE,
                         waits_for_status=False)
def create(ctx, iface, resource_config, **_):
    '''Creates an AWS RDS Parameter Group'''
    if iface.resource_id:
        resource_config.update({'DBParameterGroupName': iface.resource_id})
    create_response = iface.create(resource_config)
    resource_id = create_response['DBParameterGroup']['DBParameterGroupName']
    iface.update_resource_id(resource_id)
    utils.update_resource_id(ctx.instance, resource_id)
    utils.update_resource_arn(
        ctx.instance,
        create_response['DBParameterGroup']['DBParameterGroupArn'])


@decorators.aws_resource(ParameterGroup, RESOURCE_TYPE,
                         ignore_properties=True,
                         waits_for_status=False)
def configure(iface, resource_config, **_):
    '''Configures an AWS RDS Parameter Group'''
    if not resource_config:
        return
    # Actually create the resource
    iface.update(resource_config)


@decorators.aws_resource(ParameterGroup, RESOURCE_TYPE,
                         ignore_properties=True)
@decorators.wait_for_delete(status_pending=['available'])
def delete(iface, resource_config, **_):
    '''Deletes an AWS Parameter Group'''
    iface.delete(resource_config)


@decorators.aws_relationship(ParameterGroup, RESOURCE_TYPE)
def attach_to(ctx, iface, resource_config, **_):
    '''Attaches an RDS ParameterGroup to something else'''
    rtprops = ctx.target.instance.runtime_properties
    params = resource_config or rtprops.get('resource_config') or dict()
    if utils.is_node_type(ctx.target.node,
                          'cloudify.nodes.aws.rds.Parameter'):
        params['ParameterName'] = utils.get_resource_id(
            node=ctx.target.node,
            instance=ctx.target.instance,
            raise_on_missing=True)
        iface.update_parameter(params)


@decorators.aws_relationship(ParameterGroup, RESOURCE_TYPE)
def detach_from(ctx, iface, resource_config, **_):
    '''Detaches an RDS ParameterGroup from something else'''
    pass

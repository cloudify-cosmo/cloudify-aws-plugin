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
    RDS.Instance
    ~~~~~~~~~~~~
    AWS RDS instance interface
'''
# Standard Imports
from datetime import datetime

# Third party imports
from botocore.exceptions import ClientError

# Local imports
from cloudify_aws.common._compat import text_type
from cloudify.exceptions import NonRecoverableError
from cloudify_aws.common import decorators, utils
from cloudify_aws.rds import RDSBase

RESOURCE_TYPE = 'RDS DB Instance'


class DBInstance(RDSBase):
    '''
        AWS RDS DB Instance interface
    '''
    def __init__(self, ctx_node, resource_id=None, client=None, logger=None):
        RDSBase.__init__(self, ctx_node, resource_id, client, logger)
        self.type_name = RESOURCE_TYPE

    @property
    def properties(self):
        '''Gets the properties of an external resource'''
        resources = None
        try:
            resources = self.client.describe_db_instances(
                DBInstanceIdentifier=self.resource_id)
        except ClientError:
            pass
        if not resources or not resources.get('DBInstances', list()):
            return None
        return resources['DBInstances'][0]

    @property
    def status(self):
        '''Gets the status of an external resource'''
        props = self.properties
        if not props:
            return None
        return props['DBInstanceStatus']

    def create(self, params):
        '''
            Create a new AWS RDS DB instance.
        .. note:
            See http://bit.ly/2p4c3Bx for config details.
        '''
        return self.make_client_call('create_db_instance', params)

    def delete(self, params=None):
        '''
            Deletes an existing AWS RDS DB instance.
        .. note:
            See http://bit.ly/2pkNk91 for config details.
        '''
        params = params or dict(SkipFinalSnapshot=True)
        params.update(dict(
            DBInstanceIdentifier=self.resource_id))
        self.logger.debug('Deleting %s with parameters: %s'
                          % (self.type_name, params))
        self.client.delete_db_instance(**params)


@decorators.aws_resource(resource_type=RESOURCE_TYPE)
def prepare(ctx, resource_config, **_):
    '''Prepares an AWS RDS Instance'''
    # Save the parameters
    ctx.instance.runtime_properties['resource_config'] = resource_config


@decorators.aws_resource(DBInstance, RESOURCE_TYPE)
@decorators.wait_for_status(
    status_good=['available'],
    status_pending=['creating', 'modifying', 'backing-up'])
def create(ctx, iface, resource_config, **_):
    '''Creates an AWS RDS Instance'''
    # Build API params
    params = \
        dict() if not resource_config else resource_config.copy()
    params.update(dict(DBInstanceIdentifier=iface.resource_id))
    # Actually create the resource
    res = iface.create(params)
    db_instance = res['DBInstance']
    for key, value in db_instance.items():
        if key == 'DBInstanceIdentifier':
            iface.update_resource_id(value)
            utils.update_resource_id(ctx.instance, value)
            continue
        elif key == 'DBInstanceArn':
            utils.update_resource_arn(ctx.instance, value)
            continue
        elif isinstance(value, datetime):
            value = text_type(value)
        ctx.instance.runtime_properties[key] = value


@decorators.aws_resource(DBInstance, RESOURCE_TYPE,
                         ignore_properties=True)
def start(ctx, iface, resource_config, **_):
    '''Updates an AWS RDS Instance Runtime Properties'''

    db_instance = iface.properties
    for key, value in db_instance.items():
        if key == 'DBInstanceIdentifier':
            iface.update_resource_id(value)
            utils.update_resource_id(ctx.instance, value)
            continue
        elif key == 'DBInstanceArn':
            utils.update_resource_arn(ctx.instance, value)
            continue
        elif isinstance(value, datetime):
            value = text_type(value)
        ctx.instance.runtime_properties[key] = value


@decorators.aws_resource(DBInstance, RESOURCE_TYPE,
                         ignore_properties=True)
@decorators.wait_for_delete(status_pending=['deleting'])
def delete(iface, resource_config, **_):
    '''Deletes an AWS RDS Instance'''
    iface.delete(resource_config)


@decorators.aws_relationship(DBInstance, RESOURCE_TYPE)
def prepare_assoc(ctx, iface, resource_config, **inputs):
    '''Prepares to associate an RDS Instance to something else'''
    if utils.is_node_type(ctx.target.node,
                          'cloudify.nodes.aws.rds.SubnetGroup'):
        ctx.source.instance.runtime_properties[
            'resource_config']['DBSubnetGroupName'] = utils.get_resource_id(
                node=ctx.target.node,
                instance=ctx.target.instance,
                raise_on_missing=True)
    elif utils.is_node_type(ctx.target.node,
                            'cloudify.nodes.aws.rds.OptionGroup'):
        ctx.source.instance.runtime_properties[
            'resource_config']['OptionGroupName'] = utils.get_resource_id(
                node=ctx.target.node,
                instance=ctx.target.instance,
                raise_on_missing=True)
    elif utils.is_node_type(ctx.target.node,
                            'cloudify.nodes.aws.rds.ParameterGroup'):
        ctx.source.instance.runtime_properties[
            'resource_config']['DBParameterGroupName'] = utils.get_resource_id(
                node=ctx.target.node,
                instance=ctx.target.instance,
                raise_on_missing=True)
    elif utils.is_node_type(ctx.target.node,
                            'cloudify.aws.nodes.SecurityGroup'):
        security_groups = ctx.source.instance.runtime_properties[
            'resource_config'].get('VpcSecurityGroupIds', list())
        security_groups.append(
            utils.get_resource_id(
                node=ctx.target.node,
                instance=ctx.target.instance,
                raise_on_missing=True))
        ctx.source.instance.runtime_properties[
            'resource_config']['VpcSecurityGroupIds'] = security_groups
    elif utils.is_node_type(ctx.target.node,
                            'cloudify.nodes.aws.iam.Role'):
        if not inputs.get('iam_role_type_key') or \
                not inputs.get('iam_role_id_key'):
            raise NonRecoverableError(
                'Missing required relationship inputs "iam_role_type_key" '
                'and/or "iam_role_id_key".')
        ctx.source.instance.runtime_properties[
            'resource_config'][inputs['iam_role_type_key']] = \
            utils.get_resource_string(
                node=ctx.target.node,
                instance=ctx.target.instance,
                attribute_key=inputs['iam_role_id_key'])


@decorators.aws_relationship(DBInstance, RESOURCE_TYPE)
def detach_from(ctx, iface, resource_config, **_):
    '''Detaches an RDS Instance from something else'''
    pass

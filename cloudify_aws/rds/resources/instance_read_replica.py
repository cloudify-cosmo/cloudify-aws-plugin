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
    RDS.InstanceReadReplica
    ~~~~~~~~~~~~~~~~~~~~~~~
    AWS RDS instance read replica interface
'''
# Cloudify
from cloudify.exceptions import NonRecoverableError
from cloudify_aws.common import decorators, utils
from cloudify_aws.rds import RDSBase
# Boto
from botocore.exceptions import ClientError

RESOURCE_TYPE = 'RDS DB Instance Read Replica'


class DBInstanceReadReplica(RDSBase):
    '''
        AWS RDS DB Instance Read Replica interface
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
            Create a new AWS RDS DB Instance Read Replica.
        '''
        return self.make_client_call('create_db_instance_read_replica', params)

    def delete(self, params=None):
        '''
            Deletes an existing AWS RDS DB Instance Read Replica.
        '''
        params = params or dict(SkipFinalSnapshot=True)
        params.update(dict(
            DBInstanceIdentifier=self.resource_id))
        self.logger.debug('Deleting %s with parameters: %s'
                          % (self.type_name, params))
        self.client.delete_db_instance(**params)


@decorators.aws_resource(resource_type=RESOURCE_TYPE)
def prepare(ctx, resource_config, **_):
    '''Prepares an AWS RDS Instance Read Replica'''
    # Save the parameters
    ctx.instance.runtime_properties['resource_config'] = resource_config


@decorators.aws_resource(DBInstanceReadReplica, RESOURCE_TYPE)
@decorators.wait_for_status(
    status_good=['available'],
    status_pending=['creating', 'modifying', 'backing-up'])
def create(ctx, iface, resource_config, **_):
    '''Creates an AWS RDS Instance Read Replica'''
    # Build API params
    params = \
        dict() if not resource_config else resource_config.copy()
    if iface.resource_id:
        params.update({'DBInstanceIdentifier': iface.resource_id})
    # Actually create the resource
    create_response = iface.create(params)
    resource_id = create_response['DBInstance']['DBInstanceIdentifier']
    iface.update_resource_id(resource_id)
    utils.update_resource_id(ctx.instance, resource_id)
    utils.update_resource_arn(
        ctx.instance, create_response['DBInstance']['DBInstanceArn'])


@decorators.aws_resource(DBInstanceReadReplica, RESOURCE_TYPE,
                         ignore_properties=True)
@decorators.wait_for_delete(status_pending=['deleting'])
def delete(iface, resource_config, **_):
    '''Deletes an AWS RDS Instance Read Replica'''
    iface.delete(resource_config)


@decorators.aws_relationship(DBInstanceReadReplica, RESOURCE_TYPE)
def prepare_assoc(ctx, iface, resource_config, **inputs):
    '''Prepares to associate an RDS Instance Read Replica to something else'''
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
                            'cloudify.nodes.aws.rds.Instance'):
        ctx.source.instance.runtime_properties[
            'resource_config']['SourceDBInstanceIdentifier'] = \
            utils.get_resource_id(
                node=ctx.target.node,
                instance=ctx.target.instance,
                raise_on_missing=True)
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


@decorators.aws_relationship(DBInstanceReadReplica, RESOURCE_TYPE)
def detach_from(ctx, iface, resource_config, **_):
    '''Detaches an RDS Instance Read Replica from something else'''
    pass

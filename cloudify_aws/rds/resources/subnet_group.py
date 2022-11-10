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
    RDS.SubnetGroup
    ~~~~~~~~~~~~~~~
    AWS RDS subnet group interface
'''
# Cloudify
from cloudify_aws.common import decorators, utils
from cloudify_aws.rds import RDSBase
from cloudify.exceptions import NonRecoverableError

# Boto
from botocore.exceptions import ClientError, ParamValidationError

RESOURCE_TYPE = 'RDS Subnet Group'


class SubnetGroup(RDSBase):
    '''
        AWS RDS Subnet Group interface
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
            resources = self.client.describe_db_subnet_groups(
                DBSubnetGroupName=self.resource_id)
        except (ParamValidationError, ClientError):
            pass
        if not resources or not resources.get('DBSubnetGroups', list()):
            return None
        return resources['DBSubnetGroups'][0]

    @property
    def status(self):
        '''Gets the status of an external resource'''
        props = self.properties
        if not props:
            return None
        return props['SubnetGroupStatus']

    def create(self, params):
        '''
            Create a new AWS RDS subnet group.
        .. note:
            See http://bit.ly/2ownCxX for config details.
        '''
        return self.make_client_call('create_db_subnet_group', params)

    def delete(self, params=None):
        '''
            Deletes an existing AWS RDS subnet group.
        .. note:
            See http://bit.ly/2pC0sWj for config details.
        '''
        params = params or dict()
        params.update(dict(DBSubnetGroupName=self.resource_id))
        self.logger.debug('Deleting %s with parameters: %s'
                          % (self.type_name, params))
        self.client.delete_db_subnet_group(**params)


@decorators.aws_resource(SubnetGroup, RESOURCE_TYPE)
def prepare(ctx, resource_config, **_):
    '''Prepares an AWS RDS Subnet Group'''
    # Save the parameters
    ctx.instance.runtime_properties['resource_config'] = resource_config


@decorators.aws_resource(SubnetGroup, RESOURCE_TYPE)
@decorators.wait_for_status(status_good=['Complete'])
def create(ctx, iface, resource_config, **_):
    '''Creates an AWS RDS Subnet Group'''

    rels = utils.find_rels_by_type(
        ctx.instance,
        'cloudify.relationships.connected_to')
    master_resource_config = {}
    for rel in rels:
        _prepare_assoc(ctx, rel.target)
        rel_resource_config = ctx.instance.runtime_properties.get(
            'resource_config', {})
        for k, v in rel_resource_config.items():
            master_resource_config[k] = v
    for k, v in resource_config.items():
        master_resource_config[k] = v

    node_subnet_ids = master_resource_config.get('SubnetIds', list())
    instance_subnet_ids = \
        ctx.instance.runtime_properties['resource_config'].get('SubnetIds',
                                                               list())
    if not node_subnet_ids:
        if not instance_subnet_ids:
            raise NonRecoverableError(
                'Missing required parameter in input: SubnetIds')

        master_resource_config['SubnetIds'] = instance_subnet_ids

    # if it is set then we need to combine them to what we already have as
    # runtime_properties
    else:
        for subnet_id in instance_subnet_ids:
            if subnet_id not in node_subnet_ids:
                node_subnet_ids.append(subnet_id)

        master_resource_config['SubnetIds'] = node_subnet_ids

    if iface.resource_id:
        master_resource_config.update({'DBSubnetGroupName': iface.resource_id})
    create_response = iface.create(master_resource_config)
    resource_id = create_response['DBSubnetGroup']['DBSubnetGroupName']
    utils.update_resource_id(ctx.instance, resource_id)
    utils.update_resource_arn(
        ctx.instance, create_response['DBSubnetGroup']['DBSubnetGroupArn'])
    ctx.instance.runtime_properties["create_response"] = create_response


@decorators.aws_resource(SubnetGroup, RESOURCE_TYPE,
                         ignore_properties=True)
@decorators.wait_for_delete()
def delete(iface, resource_config, **_):
    '''Deletes an AWS Subnet Group'''
    iface.delete(resource_config)


@decorators.aws_relationship(SubnetGroup, RESOURCE_TYPE)
def prepare_assoc(ctx, iface, resource_config, **_):
    assert iface is None or iface is not None  # qa
    assert resource_config is None or resource_config is not None  # qa
    _prepare_assoc(ctx.source, ctx.target)


def _prepare_assoc(ctx_source, ctx_target):
    '''Prepares to associate an RDS SubnetGroup to something else'''
    if utils.is_node_type(ctx_target.node, 'cloudify.nodes.aws.ec2.Subnet'):
        subnet_ids = ctx_source.instance.runtime_properties[
            'resource_config'].get('SubnetIds', list())
        subnet_ids.append(
            utils.get_resource_id(
                node=ctx_target.node,
                instance=ctx_target.instance,
                raise_on_missing=True))
        ctx_source.instance.runtime_properties[
            'resource_config']['SubnetIds'] = subnet_ids


@decorators.aws_relationship(SubnetGroup, RESOURCE_TYPE)
def detach_from(ctx, iface, resource_config, **_):
    '''Detaches an RDS SubnetGroup from something else'''
    pass

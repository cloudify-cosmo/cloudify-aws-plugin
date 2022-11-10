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
    Route53.RecordSet
    ~~~~~~~~~~~~~~~~~
    AWS Route53 Resource Record Set interface
'''
# Cloudify
from cloudify.exceptions import NonRecoverableError
from cloudify_aws.common import decorators, utils
from cloudify_aws.route53.resources.hosted_zone import Route53HostedZone

RESOURCE_TYPE = 'Route53 Resource Record Set'


@decorators.aws_resource(Route53HostedZone, RESOURCE_TYPE)
def prepare(ctx, iface, resource_config, **_):
    '''Prepares an AWS Route53 Resource Record Set'''
    # Save the parameters
    ctx.instance.runtime_properties['resource_config'] = dict(
        ChangeBatch=dict(Changes=[resource_config]))


@decorators.aws_resource(Route53HostedZone, RESOURCE_TYPE)
def create(ctx, iface, resource_config, **_):
    '''Creates an AWS Route53 Resource Record Set'''
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

    if 'ChangeBatch' not in master_resource_config:
        master_resource_config = {
            'ChangeBatch': {
                'Changes': [master_resource_config]
            }
        }
    rel = utils.find_rel_by_node_type(
        ctx.instance, 'cloudify.nodes.aws.route53.HostedZone')
    if rel:
        master_resource_config = associate(
            rel.target, ctx, master_resource_config)
    # There's other stuff in resource_config that is not currently used
    # by Boto.
    payload = dict(
        HostedZoneId=master_resource_config.get('HostedZoneId'),
        ChangeBatch=master_resource_config.get('ChangeBatch'),
    )
    iface.change_resource_record_sets(payload)


@decorators.aws_resource(Route53HostedZone, RESOURCE_TYPE)
def delete(ctx, iface, resource_config, resource_type, **_):
    '''Deletes an AWS Route53 Resource Record Set'''
    params = ctx.instance.runtime_properties['resource_config'] or dict()
    if not params.get('HostedZoneId') or \
       not params.get('ChangeBatch') or \
       not len(params['ChangeBatch'].get('Changes', list())) or \
       not params['ChangeBatch']['Changes'][0].get('ResourceRecordSet'):
        raise NonRecoverableError(
            'Missing required runtime properties to delete %s'
            % resource_type)
    change = params['ChangeBatch']['Changes'][0]
    if change.get('Action', '').upper() == 'DELETE':
        ctx.logger.warn('%s was initially set to by deleted. Skipping...'
                        % resource_type)
        return
    iface.change_resource_record_sets(dict(
        HostedZoneId=params['HostedZoneId'],
        ChangeBatch=dict(
            Changes=[dict(
                Action='DELETE',
                ResourceRecordSet=change['ResourceRecordSet'])])))


@decorators.aws_relationship(Route53HostedZone, RESOURCE_TYPE)
def prepare_assoc(ctx, iface, **_):
    '''Prepares to associate an Route53 Resource Record Set to something'''
    _prepare_assoc(ctx.source, ctx.target)


def _prepare_assoc(ctx_source, ctx_target):
    if utils.is_node_type(
            ctx_target.node, 'cloudify.nodes.aws.route53.HostedZone'):
        cfg = ctx_source.instance.runtime_properties['resource_config']
        cfg = associate(ctx_target, ctx_source, cfg)
        ctx_source.instance.runtime_properties['resource_config'] = cfg


@decorators.aws_relationship(resource_type=RESOURCE_TYPE)
def detach_from(ctx, **_):
    '''Detaches an Route53 Resource Record Set from something else'''
    pass


def associate(ctx_target, ctx_source, resource_config):
    zone_id = utils.get_resource_id(
        node=ctx_target.node,
        instance=ctx_target.instance,
        raise_on_missing=True)
    utils.update_resource_id(ctx_source.instance, zone_id)
    resource_config.update(
        dict(HostedZoneId=zone_id))
    return resource_config

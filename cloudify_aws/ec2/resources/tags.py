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
    EC2.Tags
    ~~~~~~~~~~~~~~
    AWS EC2 Tags interface
'''
# Cloudify
from cloudify_aws.common.constants import EXTERNAL_RESOURCE_ID
from cloudify_aws.common import decorators, utils
from cloudify_aws.ec2 import EC2Base

RESOURCE_TYPE = 'EC2 Tags'
TAGS = 'Tags'


class EC2Tags(EC2Base):
    '''
        EC2 Tags interface
    '''
    def __init__(self, ctx_node, resource_id=None, client=None, logger=None):
        EC2Base.__init__(self, ctx_node, resource_id, client, logger)
        self.type_name = RESOURCE_TYPE
        self._describe_call = 'describe_tags'
        self._type_key = TAGS

    @property
    def properties(self):
        '''Gets the properties of an external resource'''
        if not self.resource_id:
            return {}
        params = {'Filters': [{'resource-id': self.resource_id}]}
        if not self._properties:
            self._properties = self.get_describe_result(params).get(
                self._type_key, [{}])[0]

        return self._properties

    @property
    def status(self):
        '''Gets the status of an external resource'''
        return None


@decorators.aws_resource(EC2Tags,
                         resource_type=RESOURCE_TYPE,
                         waits_for_status=False)
def prepare(ctx, iface, resource_config, **_):
    '''Prepares an AWS EC2 Vpc'''
    # Save the parameters
    ctx.instance.runtime_properties['resource_config'] = resource_config


@decorators.aws_resource(EC2Tags, RESOURCE_TYPE, waits_for_status=False)
def create(ctx, iface, resource_config, **_):
    '''Creates an AWS EC2 Tags'''
    resources = resource_config.get('Resources')
    if not resources:
        targets = \
            utils.find_rels_by_type(
                ctx.instance,
                'cloudify.relationships.depends_on')
        resources = \
            [rel.target.instance.runtime_properties
             .get(EXTERNAL_RESOURCE_ID) for rel in targets]
        resource_config['Resources'] = resources

    # Actually create the resource
    create_response = iface.tag(resource_config)
    ctx.instance.runtime_properties['create_response'] = \
        utils.JsonCleanuper(create_response).to_dict()


@decorators.aws_resource(EC2Tags, RESOURCE_TYPE, waits_for_status=False)
def delete(ctx, iface, resource_config, **_):
    '''Deletes an AWS EC2 Tags'''
    resources = resource_config.get('Resources')
    if not resources:
        targets = \
            utils.find_rels_by_type(
                ctx.instance,
                'cloudify.relationships.depends_on')
        resources = \
            [rel.target.instance.runtime_properties
             .get(EXTERNAL_RESOURCE_ID) for rel in targets]
        resource_config['Resources'] = resources

    iface.untag(resource_config)

# #######
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
#    * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    * See the License for the specific language governing permissions and
#    * limitations under the License.
'''
    EC2.Tags
    ~~~~~~~~~~~~~~
    AWS EC2 Tags interface
'''
# Cloudify
from cloudify_aws.common.constants import EXTERNAL_RESOURCE_ID
from cloudify_aws.common import decorators, utils
from cloudify_aws.ec2 import EC2Base
# Boto
from botocore.exceptions import ClientError

RESOURCE_TYPE = 'EC2 Tags'


class EC2Tags(EC2Base):
    '''
        EC2 Tags interface
    '''
    def __init__(self, ctx_node, resource_id=None, client=None, logger=None):
        EC2Base.__init__(self, ctx_node, resource_id, client, logger)
        self.type_name = RESOURCE_TYPE

    @property
    def properties(self):
        '''Gets the properties of an external resource'''
        params = {'Filters': [{'resource-id': self.resource_id}]}
        try:
            resources = \
                self.client.client.describe_tags(**params)
        except ClientError:
            pass
        else:
            return None if not resources else resources.get('Tags', [None])[0]
        return None

    @property
    def status(self):
        '''Gets the status of an external resource'''
        return None


@decorators.aws_resource(EC2Tags, resource_type=RESOURCE_TYPE)
def prepare(ctx, iface, resource_config, **_):
    '''Prepares an AWS EC2 Vpc'''
    # Save the parameters
    ctx.instance.runtime_properties['resource_config'] = resource_config


@decorators.aws_resource(EC2Tags, RESOURCE_TYPE)
def create(ctx, iface, resource_config, **_):
    '''Creates an AWS EC2 Tags'''
    params = \
        dict() if not resource_config else resource_config.copy()

    resources = params.get('Resources')
    if not resources:
        targets = \
            utils.find_rels_by_type(
                ctx.instance,
                'cloudify.relationships.depends_on')
        resources = \
            [rel.target.instance.runtime_properties
             .get(EXTERNAL_RESOURCE_ID) for rel in targets]
        params['Resources'] = resources

    # Actually create the resource
    create_response = iface.tag(params)
    ctx.instance.runtime_properties['create_response'] = \
        utils.JsonCleanuper(create_response).to_dict()


@decorators.aws_resource(EC2Tags, RESOURCE_TYPE)
def delete(ctx, iface, resource_config, **_):
    '''Deletes an AWS EC2 Tags'''

    params = \
        dict() if not resource_config else resource_config.copy()

    resources = params.get('Resources')
    if not resources:
        targets = \
            utils.find_rels_by_type(
                ctx.instance,
                'cloudify.relationships.depends_on')
        resources = \
            [rel.target.instance.runtime_properties
             .get(EXTERNAL_RESOURCE_ID) for rel in targets]
        params['Resources'] = resources

    iface.untag(params)

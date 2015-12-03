########
# Copyright (c) 2015 GigaSpaces Technologies Ltd. All rights reserved
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

from ec2 import utils as ec2_utils
from ec2 import constants
from cloudify import ctx
from cloudify.exceptions import NonRecoverableError


def get_source_and_target_ids(source_instance,
                              target_instance):

    return source_instance.runtime_properties[
               constants.EXTERNAL_RESOURCE_ID],\
           target_instance.runtime_properties[
               constants.EXTERNAL_RESOURCE_ID]


def use_external_in_relationship(source_node_properties):
    if ec2_utils.use_external_resource(source_node_properties):
        ctx.logger.info(
            'Skipping attach operation because source node is external.')
        return True


def raise_cannot_use_external_resource(resource_id):
    raise NonRecoverableError(
        'Cannot use_external_resource because resource {0} '
        'is not in this account.'.format(resource_id))



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

from cosmo_tester.test_suites.test_blueprints import nodecellar_test

EXTERNAL_RESOURCE_ID = 'aws_resource_id'


class AWSNodeCellarTest(nodecellar_test.NodecellarAppTest):

    def test_aws_nodecellar(self):
        self._test_nodecellar_impl('aws-ec2-blueprint.yaml')

    def get_inputs(self):

        return {
            'image': self.env.ubuntu_trusty_image_id,
            'size': self.env.medium_instance_type,
            'agent_user': 'ubuntu'
        }

    @property
    def host_expected_runtime_properties(self):
        return ['ip']

    @property
    def entrypoint_node_name(self):
        return 'nodecellar_elasticip'

    @property
    def entrypoint_property_name(self):
        return EXTERNAL_RESOURCE_ID

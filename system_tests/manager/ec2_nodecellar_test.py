########
# Copyright (c) 2014 GigaSpaces Technologies Ltd. All rights reserved
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

import os
from cosmo_tester.test_suites.test_blueprints import nodecellar_test

EXTERNAL_RESOURCE_ID = 'aws_resource_id'
CLOUDIFY_EC2_NODECELLAR = '~/Environments/' \
    'cloudify-nodecellar-example'


class EC2NodeCellarTest(nodecellar_test.NodecellarAppTest):

    def test_ec2_nodecellar(self):
        self._test_nodecellar_impl('ec2-blueprint.yaml')

        self.modify_blueprint()

        before, after = self.upload_deploy_and_execute_install(
            inputs=self.get_inputs()
        )

        self.post_install_assertions(before, after)

        self.execute_uninstall()

        self.post_uninstall_assertions()

    def get_inputs(self):

        return {
            'image': self.env.ubuntu_agent_ami,
            'size': self.env.medium_instance_type,
            'agent_user': 'ubuntu'
        }

    def _test_nodecellar_impl(self, blueprint_file):
        self.repo_dir = os.path.expanduser(CLOUDIFY_EC2_NODECELLAR)
        self.blueprint_yaml = os.path.join(self.repo_dir, blueprint_file)

    @property
    def host_expected_runtime_properties(self):
        return ['ip']

    @property
    def entrypoint_node_name(self):
        return 'nodecellar_elasticip'

    @property
    def entrypoint_property_name(self):
        return EXTERNAL_RESOURCE_ID

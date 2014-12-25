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
import unittest

from cloudify.workflows import local


class TestPlugin(unittest.TestCase):

    def setUp(self):
        # build blueprint path
        blueprint_path = os.path.join(os.path.dirname(__file__),
                                      'blueprint', 'blueprint.yaml')

        # inject input from test
        inputs = {
            'test_input_a': 'a',
            'test_input_b': 'b'
        }

        # setup local workflow execution environment
        self.env = local.init_env(blueprint_path,
                                  name=self.test_run,
                                  inputs=inputs)

    def test_run(self):

        # execute install workflow
        self.env.execute('install', task_retries=0)

        # extract single node instance
        instance = self.env.storage.get_node_instances()[0]

        self.assertEqual(instance.runtime_properties['ami_image_id'],
                         'a')

        # assert deployment outputs are ok
        self.assertDictEqual(self.env.outputs(),
                             {'test_output': 'a' })

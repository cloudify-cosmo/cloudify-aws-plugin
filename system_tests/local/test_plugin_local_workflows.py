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

# Built-in Imports
import os

# Cloudify Imports
from ec2_test_utils import (
    EC2LocalTestUtils,
    EXTERNAL_RESOURCE_ID, INSTANCE_TO_IP, INSTANCE_TO_SG,
    SIMPLE_IP, SIMPLE_SG, SIMPLE_KP, SIMPLE_VM,
    PAIR_A_IP, PAIR_A_VM,
    PAIR_B_SG, PAIR_B_VM
)


class TestWorkflowClean(EC2LocalTestUtils):

    def test_simple_resources(self):

        test_name = 'test_simple_resources'

        inputs = self._get_inputs(test_name=test_name)
        self._set_up(inputs=inputs)

        # execute install workflow
        self.env.execute('install', task_retries=10)

        instance_storage = self._get_instances(self.env.storage)

        self.assertEquals(4, len(instance_storage))

        for node_instance in self._get_instances(self.env.storage):
            self.assertIn(EXTERNAL_RESOURCE_ID,
                          node_instance.runtime_properties)

        # Test assertions for simple nodes
        self.assertIsNotNone(
            self._get_instance_node_id(
                SIMPLE_IP, self.env.storage))

        self.assertIsNotNone(
            self._get_instance_node_id(
                SIMPLE_SG, self.env.storage))

        self.assertIsNotNone(
            self._get_instance_node_id(
                SIMPLE_KP, self.env.storage))

        self.assertIsNotNone(
            os.path.exists(
                inputs['key_path']))

        self.assertIsNotNone(
            self._get_instance_node_id(
                SIMPLE_VM, self.env.storage))

        self.env.execute('uninstall', task_retries=10)

    def test_simple_relationships(self):

        test_name = 'test_simple_relationships'

        inputs = self._get_inputs(test_name=test_name)

        self._set_up(
            inputs=inputs,
            filename='relationships.yaml')

        # execute install workflow
        self.env.execute('install', task_retries=10)

        instance_storage = self._get_instances(self.env.storage)

        self.assertEquals(4, len(instance_storage))

        # Test assertions for pair a nodes
        self.assertIsNotNone(
            self._get_instance_node_id(
                PAIR_A_IP, self.env.storage))

        self.assertIsNotNone(
            self._get_instance_node_id(
                PAIR_A_VM, self.env.storage))

        pair_a_vm_instance = \
            self._get_instance_node(PAIR_A_VM, self.env.storage)

        self.assertEquals(1, len(pair_a_vm_instance.relationships))

        relationship_types = \
            [relationship['type']
             for relationship in pair_a_vm_instance.relationships]

        self.assertIn(INSTANCE_TO_IP, relationship_types[0])

        # Test assertions for pair b nodes
        self.assertIsNotNone(
            self._get_instance_node_id(
                PAIR_B_SG, self.env.storage))

        self.assertIsNotNone(
            self._get_instance_node_id(
                PAIR_B_VM, self.env.storage))

        pair_b_vm_instance = \
            self._get_instance_node(PAIR_B_VM, self.env.storage)

        self.assertEquals(1, len(pair_b_vm_instance.relationships))

        relationship_types = \
            [relationship['type']
             for relationship in pair_b_vm_instance.relationships]

        self.assertIn(INSTANCE_TO_SG, relationship_types[0])

        self.env.execute('uninstall', task_retries=10)

    def test_external_resources(self):

        test_name = 'test_external_resources'

        client = self._get_ec2_client()

        ip = self._create_elastic_ip(client)
        kp = self._create_key_pair(client, test_name)
        sg = self._create_security_group(client, test_name, 'test desc')
        vm = self._create_instance(client)

        inputs = self._get_inputs(
            test_name=test_name,
            resource_id_ip=ip.public_ip,
            resource_id_kp=kp.name,
            resource_id_sg=sg.id,
            resource_id_vm=vm.id,
            external_ip=True,
            external_kp=True,
            external_sg=True,
            external_vm=True)

        self._set_up(inputs=inputs)

        self.env.execute('install', task_retries=10)

        instance_storage = self._get_instances(self.env.storage)

        self.assertEquals(4, len(instance_storage))

        for node_instance in self._get_instances(self.env.storage):
            self.assertIn(EXTERNAL_RESOURCE_ID,
                          node_instance.runtime_properties)

        cfy_ip = self._get_instance_node(SIMPLE_IP, self.env.storage)
        self.assertEquals(
            ip.public_ip,
            cfy_ip.runtime_properties[EXTERNAL_RESOURCE_ID])

        cfy_kp = self._get_instance_node(SIMPLE_KP, self.env.storage)
        self.assertEquals(
            kp.name,
            cfy_kp.runtime_properties[EXTERNAL_RESOURCE_ID])
        key_pair_file = os.path.expanduser(inputs['key_path'])

        cfy_sg = self._get_instance_node(SIMPLE_SG, self.env.storage)
        self.assertEquals(
            sg.id,
            cfy_sg.runtime_properties[EXTERNAL_RESOURCE_ID])

        cfy_vm = self._get_instance_node(SIMPLE_VM, self.env.storage)
        self.assertEquals(
            vm.id,
            cfy_vm.runtime_properties[EXTERNAL_RESOURCE_ID])

        self.assertIsNotNone(os.path.exists(key_pair_file))

        self.env.execute('uninstall', task_retries=10)

        ip.release()
        kp.delete()
        if os.path.exists(key_pair_file):
            os.remove(key_pair_file)
        sg.delete()
        vm.terminate()

    def test_external_relationships(self):

        test_name = 'test_external_relationships'

        inputs = self._get_inputs(
            test_name=test_name,
            resource_id_ip=ip.public_ip,
            resource_id_kp=kp.name,
            resource_id_sg=sg.id,
            resource_id_vm=vm.id,
            external_ip=False,
            external_kp=True,
            external_sg=False,
            external_vm=True)

        self._set_up(
            inputs=inputs,
            filename='relationships.yaml')

        # execute install workflow
        self.env.execute('install', task_retries=10)

        instance_storage = self._get_instances(self.env.storage)

        self.assertEquals(4, len(instance_storage))

        # Test assertions for pair a nodes
        self.assertIsNotNone(
            self._get_instance_node_id(
                PAIR_A_IP, self.env.storage))

        self.assertIsNotNone(
            self._get_instance_node_id(
                PAIR_A_VM, self.env.storage))

        pair_a_vm_instance = \
            self._get_instance_node(PAIR_A_VM, self.env.storage)

        self.assertEquals(1, len(pair_a_vm_instance.relationships))

        relationship_types = \
            [relationship['type']
             for relationship in pair_a_vm_instance.relationships]

        self.assertIn(INSTANCE_TO_IP, relationship_types[0])

        # Test assertions for pair b nodes
        self.assertIsNotNone(
            self._get_instance_node_id(
                PAIR_B_SG, self.env.storage))

        self.assertIsNotNone(
            self._get_instance_node_id(
                PAIR_B_VM, self.env.storage))

        pair_b_vm_instance = \
            self._get_instance_node(PAIR_B_VM, self.env.storage)

        self.assertEquals(1, len(pair_b_vm_instance.relationships))

        relationship_types = \
            [relationship['type']
             for relationship in pair_b_vm_instance.relationships]

        self.assertIn(INSTANCE_TO_SG, relationship_types[0])

        self.env.execute('uninstall', task_retries=10)

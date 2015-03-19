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
from ec2 import (
    utils,
    instance
)
from cloudify.exceptions import NonRecoverableError
from ec2_test_utils import (
    EC2LocalTestUtils, TEST_AMI,
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


class EC2UtilsUnitTests(EC2LocalTestUtils):

    def test_utils_get_resource_id(self):

        ctx = self.mock_cloudify_context(
            'test_utils_get_resource_id')

        ctx.node.properties['resource_id'] = \
            'test_utils_get_resource_id'

        resource_id = utils.get_resource_id(ctx=ctx)

        self.assertEquals(
            'test_utils_get_resource_id', resource_id)

    def test_utils_get_resource_id_from_key_path(self):

        ctx = self.mock_cloudify_context(
            'test_utils_get_resource_id_from_key_path')

        ctx.node.properties['private_key_path'] = \
            '~/.ssh/test_utils_get_resource_id_from_key_path.pem'

        del(ctx.node.properties['resource_id'])

        resource_id = utils.get_resource_id(ctx=ctx)

        self.assertEquals(
            'test_utils_get_resource_id_from_key_path', resource_id)

    def test_utils_validate_node_properties_missing_key(self):
        ctx = self.mock_cloudify_context(
            'test_utils_validate_node_properties_missing_key')

        ex = self.assertRaises(
            NonRecoverableError, utils.validate_node_property,
            'missing_key',
            ctx.node.properties)

        self.assertIn(
            'missing_key is a required input. Unable to create.',
            ex.message)

    def test_utils_log_available_resources(self):

        ctx = self.mock_cloudify_context(
            'test_utils_log_available_resources')

        client = self._get_ec2_client()

        key_pairs = client.get_all_key_pairs()

        utils.log_available_resources(key_pairs, ctx.logger)

    def test_utils_get_external_resource_id_or_raise_no_id(self):

        ctx = self.mock_cloudify_context(
            'test_utils_get_external_resource_id_or_raise_no_id')

        ctx.instance.runtime_properties['prop'] = None

        ex = self.assertRaises(
            NonRecoverableError,
            utils.get_external_resource_id_or_raise,
            'test_operation', ctx.instance, ctx.logger)

        self.assertIn(
            'Cannot test_operation because {0} is not assigned'
            .format(EXTERNAL_RESOURCE_ID),
            ex.message)

    def test_utils_get_external_resource_id_or_raise(self):

        ctx = self.mock_cloudify_context(
            'test_utils_get_external_resource_id_or_raise')

        ctx.instance.runtime_properties[EXTERNAL_RESOURCE_ID] = \
            'test_utils_get_external_resource_id_or_raise'

        output = utils.get_external_resource_id_or_raise(
            'test_operation', ctx.instance, ctx.logger)

        self.assertEquals(
            'test_utils_get_external_resource_id_or_raise', output)

    def test_utils_set_external_resource_id_cloudify(self):

        ctx = self.mock_cloudify_context(
            'test_utils_set_external_resource_id_cloudify')

        utils.set_external_resource_id(
            'id-value',
            ctx.instance,
            ctx.logger,
            external=False)

        self.assertEquals(
            'id-value',
            ctx.instance.runtime_properties[EXTERNAL_RESOURCE_ID])

    def test_utils_set_external_resource_id_external(self):

        ctx = self.mock_cloudify_context(
            'test_utils_set_external_resource_id_external')

        utils.set_external_resource_id(
            'id-value',
            ctx.instance,
            ctx.logger)

        self.assertEquals(
            'id-value',
            ctx.instance.runtime_properties[EXTERNAL_RESOURCE_ID])

    def test_utils_unassign_runtime_property_from_resource(self):

        ctx = self.mock_cloudify_context(
            'test_utils_unassign_runtime_property_from_resource')

        ctx.instance.runtime_properties[EXTERNAL_RESOURCE_ID] = \
            'test_utils_unassign_runtime_property_from_resource'

        utils.unassign_runtime_property_from_resource(
            EXTERNAL_RESOURCE_ID,
            ctx.instance,
            ctx.logger)

        self.assertNotIn(
            EXTERNAL_RESOURCE_ID,
            ctx.instance.runtime_properties)

    def test_utils_use_external_resource_not_external(self):

        ctx = self.mock_cloudify_context(
            'test_utils_use_external_resource_not_external')

        self.assertEquals(
            False,
            utils.use_external_resource(ctx.node.properties, ctx.logger))

    def test_utils_use_external_resource_external(self):

        ctx = self.mock_cloudify_context(
            'test_utils_use_external_resource_external')

        ctx.node.properties['use_external_resource'] = True
        ctx.node.properties['resource_id'] = \
            'test_utils_use_external_resource_external'

        self.assertEquals(
            True,
            utils.use_external_resource(ctx.node.properties, ctx.logger))


class EC2InstanceUnitTests(EC2LocalTestUtils):

    def test_instance_invalid_ami(self):

        image_id = 'ami-65b95565'

        ex = self.assertRaises(
            NonRecoverableError, instance._get_image, image_id)

        self.assertIn('InvalidAMIID.NotFound', ex.message)

    def test_instance_get_image_id(self):

        image_object = instance._get_image(TEST_AMI)
        self.assertEquals(image_object.id, TEST_AMI)

    def test_instance_external_invalid_instance(self):

        ctx = self.mock_cloudify_context(
            'test_instance_external_invalid_instance')

        ctx.node.properties['use_external_resource'] = True
        ctx.node.properties['resource_id'] = 'i-00z0zz0z'

        ex = self.assertRaises(
            NonRecoverableError, instance._create_external_instance, ctx=ctx)

        self.assertIn('is not in this account', ex.message)

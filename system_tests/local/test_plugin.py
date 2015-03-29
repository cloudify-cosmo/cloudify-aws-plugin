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
    securitygroup,
    keypair,
    elasticip,
    instance
)
from cloudify.state import current_ctx
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
        current_ctx.set(ctx=ctx)
        ctx.node.properties['resource_id'] = \
            'test_utils_get_resource_id'

        resource_id = utils.get_resource_id()

        self.assertEquals(
            'test_utils_get_resource_id', resource_id)

    def test_utils_get_resource_id_dynamic(self):

        ctx = self.mock_cloudify_context(
            'test_utils_get_resource_id')
        current_ctx.set(ctx=ctx)
        ctx.node.properties['resource_id'] = ''

        resource_id = utils.get_resource_id()

        self.assertEquals('None-test_utils_get_resource_id', resource_id)

    def test_utils_get_resource_id_from_key_path(self):

        ctx = self.mock_cloudify_context(
            'test_utils_get_resource_id_from_key_path')
        current_ctx.set(ctx=ctx)
        ctx.node.properties['private_key_path'] = \
            '~/.ssh/test_utils_get_resource_id_from_key_path.pem'

        resource_id = utils.get_resource_id()

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
        current_ctx.set(ctx=ctx)
        client = self._get_ec2_client()

        key_pairs = client.get_all_key_pairs()

        utils.log_available_resources(key_pairs)

    def test_utils_get_external_resource_id_or_raise_no_id(self):

        ctx = self.mock_cloudify_context(
            'test_utils_get_external_resource_id_or_raise_no_id')
        current_ctx.set(ctx=ctx)
        ctx.instance.runtime_properties['prop'] = None

        ex = self.assertRaises(
            NonRecoverableError,
            utils.get_external_resource_id_or_raise,
            'test_operation', ctx.instance)

        self.assertIn(
            'Cannot test_operation because {0} is not assigned'
            .format(EXTERNAL_RESOURCE_ID),
            ex.message)

    def test_utils_get_external_resource_id_or_raise(self):

        ctx = self.mock_cloudify_context(
            'test_utils_get_external_resource_id_or_raise')
        current_ctx.set(ctx=ctx)
        ctx.instance.runtime_properties[EXTERNAL_RESOURCE_ID] = \
            'test_utils_get_external_resource_id_or_raise'

        output = utils.get_external_resource_id_or_raise(
            'test_operation', ctx.instance)

        self.assertEquals(
            'test_utils_get_external_resource_id_or_raise', output)

    def test_utils_set_external_resource_id_cloudify(self):

        ctx = self.mock_cloudify_context(
            'test_utils_set_external_resource_id_cloudify')
        current_ctx.set(ctx=ctx)
        utils.set_external_resource_id(
            'id-value',
            ctx.instance,
            external=False)

        self.assertEquals(
            'id-value',
            ctx.instance.runtime_properties[EXTERNAL_RESOURCE_ID])

    def test_utils_set_external_resource_id_external(self):

        ctx = self.mock_cloudify_context(
            'test_utils_set_external_resource_id_external')
        current_ctx.set(ctx=ctx)
        utils.set_external_resource_id(
            'id-value',
            ctx.instance)

        self.assertEquals(
            'id-value',
            ctx.instance.runtime_properties[EXTERNAL_RESOURCE_ID])

    def test_utils_unassign_runtime_property_from_resource(self):

        ctx = self.mock_cloudify_context(
            'test_utils_unassign_runtime_property_from_resource')
        current_ctx.set(ctx=ctx)
        ctx.instance.runtime_properties[EXTERNAL_RESOURCE_ID] = \
            'test_utils_unassign_runtime_property_from_resource'

        utils.unassign_runtime_property_from_resource(
            EXTERNAL_RESOURCE_ID,
            ctx.instance)

        self.assertNotIn(
            EXTERNAL_RESOURCE_ID,
            ctx.instance.runtime_properties)

    def test_utils_use_external_resource_not_external(self):

        ctx = self.mock_cloudify_context(
            'test_utils_use_external_resource_not_external')
        current_ctx.set(ctx=ctx)
        self.assertEquals(
            False,
            utils.use_external_resource(ctx.node.properties))

    def test_utils_use_external_resource_external(self):

        ctx = self.mock_cloudify_context(
            'test_utils_use_external_resource_external')
        current_ctx.set(ctx=ctx)
        ctx.node.properties['use_external_resource'] = True
        ctx.node.properties['resource_id'] = \
            'test_utils_use_external_resource_external'

        self.assertEquals(
            True,
            utils.use_external_resource(ctx.node.properties))

    def test_get_target_external_resource_ids(self):

        ctx = self.mock_cloudify_context(
            'get_target_external_resource_ids')
        current_ctx.set(ctx=ctx)
        output = utils.get_target_external_resource_ids(
            'instance_connected_to_keypair',
            ctx.instance)

        self.assertEquals(0, len(output))

    def test_get_target_external_resource_ids_no_attr(self):

        ctx = self.mock_cloudify_context(
            'get_target_external_resource_ids')
        current_ctx.set(ctx=ctx)
        delattr(ctx.instance, 'relationships')

        output = utils.get_target_external_resource_ids(
            'instance_connected_to_keypair',
            ctx.instance)

        self.assertEquals(0, len(output))


class EC2SecurityGroupUnitTests(EC2LocalTestUtils):

    def test_get_all_security_groups(self):

        client = self._get_ec2_client()
        groups_from_test = client.get_all_security_groups()

        groups_from_plugin = securitygroup._get_all_security_groups()

        self.assertEqual(len(groups_from_test), len(groups_from_plugin))

    def test_get_all_security_groups_not_found(self):

        not_found_names = ['test_get_all_security_groups_not_found']

        groups_from_plugin = securitygroup._get_all_security_groups(
            list_of_group_names=not_found_names)

        self.assertIsNone(groups_from_plugin)

    def test_get_security_group_from_name(self):

        client = self._get_ec2_client()
        group = client.create_security_group(
            'test_get_security_group_from_name',
            'some description')
        group_from_plugin = securitygroup._get_security_group_from_id(
            group_id=group.id)
        self.assertEqual(group.name, group_from_plugin.name)
        group.delete()

    def test_get_security_group_from_id(self):

        client = self._get_ec2_client()
        group = client.create_security_group(
            'test_get_security_group_from_id',
            'some description')
        group_from_plugin = securitygroup._get_security_group_from_name(
            group_name=group.name)
        self.assertEqual(group.id, group_from_plugin.id)
        group.delete()

    def test_get_security_group_from_name_but_really_id(self):

        client = self._get_ec2_client()
        group = client.create_security_group(
            'test_get_security_group_from_name_but_really_id',
            'some description')
        group_from_plugin = securitygroup._get_security_group_from_name(
            group_name=group.id)
        self.assertEqual(group.name, group_from_plugin.name)
        group.delete()

    def test_get_security_group_from_id_but_really_name(self):

        client = self._get_ec2_client()
        group = client.create_security_group(
            'test_get_security_group_from_id_but_really_name',
            'some description')
        group_from_plugin = securitygroup._get_security_group_from_id(
            group_id=group.name)
        self.assertEqual(group.id, group_from_plugin.id)
        group.delete()

    def test_delete_external_securitygroup_external(self):

        ctx = self.mock_cloudify_context(
            'test_delete_external_securitygroup_external')
        current_ctx.set(ctx=ctx)
        ctx.node.properties['use_external_resource'] = True
        ctx.instance.runtime_properties[EXTERNAL_RESOURCE_ID] = \
            'sg-blahblah'

        output = securitygroup._delete_external_securitygroup()
        self.assertEqual(True, output)
        self.assertNotIn(
            EXTERNAL_RESOURCE_ID, ctx.instance.runtime_properties)

    def test_delete_external_securitygroup_not_external(self):

        ctx = self.mock_cloudify_context(
            'test_delete_external_securitygroup_not_external')
        current_ctx.set(ctx=ctx)
        ctx.node.properties['use_external_resource'] = False

        output = securitygroup._delete_external_securitygroup()
        self.assertEqual(False, output)

    def test_create_external_securitygroup_external(self):

        ctx = self.mock_cloudify_context(
            'test_create_external_securitygroup_external')
        current_ctx.set(ctx=ctx)
        client = self._get_ec2_client()
        group = client.create_security_group(
            'test_create_external_securitygroup_external',
            'some description')

        ctx.node.properties['use_external_resource'] = True
        ctx.node.properties['resource_id'] = group.id

        output = securitygroup._create_external_securitygroup(group.name)
        self.assertEqual(True, output)
        self.assertEqual(
            ctx.instance.runtime_properties[EXTERNAL_RESOURCE_ID],
            group.id)
        group.delete()

    def test_create_external_securitygroup_external_bad_id(self):

        ctx = self.mock_cloudify_context(
            'test_create_external_securitygroup_external_bad_id')
        current_ctx.set(ctx=ctx)
        ctx.node.properties['use_external_resource'] = True
        ctx.node.properties['resource_id'] = 'sg-73cd3f1e'

        ex = self.assertRaises(
            NonRecoverableError,
            securitygroup._create_external_securitygroup,
            'sg-73cd3f1e')
        self.assertIn('security group does not exist', ex.message)

    def test_create_external_securitygroup_not_external(self):

        ctx = self.mock_cloudify_context(
            'test_create_external_securitygroup_not_external')
        current_ctx.set(ctx=ctx)
        ctx.node.properties['use_external_resource'] = False

        output = securitygroup._delete_external_securitygroup()
        self.assertEqual(False, output)

    def test_authorize_by_id(self):

        client = self._get_ec2_client()
        group = client.create_security_group(
            'test_authorize_by_id',
            'some description')
        rules = [
            {
                'ip_protocol': 'tcp',
                'from_port': 22,
                'to_port': 22,
                'cidr_ip': '0.0.0.0/0'
            }
        ]
        securitygroup._authorize_by_id(
            client, group.id, rules
        )
        groups_from_test = \
            client.get_all_security_groups(groupnames=[group.name])
        self.assertEqual(group.id, groups_from_test[0].id)
        self.assertEqual(
            str(groups_from_test[0].rules[0]),
            'IPPermissions:tcp(22-22)'
        )
        group.delete()

    def test_authorize_by_id_bad_id(self):

        client = self._get_ec2_client()
        rules = [
            {
                'ip_protocol': 'tcp',
                'from_port': 22,
                'to_port': 22,
                'cidr_ip': '0.0.0.0/0'
            }
        ]

        ex = self.assertRaises(
            NonRecoverableError,
            securitygroup._authorize_by_id,
            client, 'sg-73cd3f1e', rules
        )
        self.assertIn('InvalidGroup.NotFound', ex.message)

    def test_delete_security_group_bad_group(self):

        client = self._get_ec2_client()

        ex = self.assertRaises(
            NonRecoverableError,
            securitygroup._delete_security_group,
            'sg-73cd3f1e', client
        )

        self.assertIn('InvalidGroup.NotFound', ex.message)


class EC2KeyPairUnitTests(EC2LocalTestUtils):

    def test_search_for_key_file_no_file(self):

        output = keypair._search_for_key_file(
            '~/.ssh/test_search_for_key_file.pem')

        self.assertEquals(
            False,
            output
        )

    def test_get_path_to_key_folder_no_private_key_path(self):

        ctx = self.mock_cloudify_context(
            'test_get_path_to_key_folder_no_private_key_path')
        current_ctx.set(ctx=ctx)
        ex = self.assertRaises(
            NonRecoverableError,
            keypair._get_path_to_key_file)

        self.assertIn(
            'private_key_path not set',
            ex.message
        )

    def test_get_path_to_key_folder(self):

        ctx = self.mock_cloudify_context(
            'test_get_path_to_key_folder')
        current_ctx.set(ctx=ctx)
        ctx.node.properties['private_key_path'] = \
            '~/.ssh/test_get_path_to_key_folder.pem'

        full_key_path = os.path.expanduser(
            ctx.node.properties['private_key_path']
        )

        key_directory, key_filename = os.path.split(full_key_path)

        output = keypair._get_path_to_key_folder()

        self.assertEqual(key_directory, output)

    def test_get_path_to_key_file_no_private_key_path(self):

        ctx = self.mock_cloudify_context(
            'test_get_path_to_key_folder_no_private_key_path')
        current_ctx.set(ctx=ctx)
        ex = self.assertRaises(
            NonRecoverableError,
            keypair._get_path_to_key_file)

        self.assertIn(
            'private_key_path not set',
            ex.message
        )

    def test_get_path_to_key_file(self):

        ctx = self.mock_cloudify_context(
            'test_get_path_to_key_folder')
        current_ctx.set(ctx=ctx)
        ctx.node.properties['private_key_path'] = \
            '~/.ssh/test_get_path_to_key_folder.pem'

        full_key_path = os.path.expanduser(
            ctx.node.properties['private_key_path']
        )

        output = keypair._get_path_to_key_file()

        self.assertEqual(full_key_path, output)

    def test_get_key_pair_by_id_no_kp(self):

        ex = self.assertRaises(
            NonRecoverableError,
            keypair._get_key_pair_by_id,
            'test_get_key_pair_by_id_no_kp')

        self.assertIn(
            'InvalidKeyPair.NotFound',
            ex.message)

    def test_get_key_pair_by_id(self):

        client = self._get_ec2_client()
        kp = client.create_key_pair(
            'test_get_key_pair_by_id')

        output = keypair._get_key_pair_by_id(kp.name)
        self.assertEqual(kp.name, output.name)
        kp.delete()


class EC2ElasticIPUnitTests(EC2LocalTestUtils):

    def test_get_all_addresses_bad_address(self):

        output = elasticip._get_all_addresses('127.0.0.1')

        self.assertIsNone(output)

    def test_get_address_object_by_id(self):

        client = self._get_ec2_client()
        address = client.allocate_address()
        address_object = \
            elasticip._get_address_object_by_id(address.public_ip)
        self.assertEqual(
            address.public_ip, address_object.public_ip)
        address_object.delete()

    def test_get_address_by_id(self):

        client = self._get_ec2_client()
        address_object = client.allocate_address()
        address = elasticip._get_address_by_id(address_object.public_ip)
        self.assertEqual(address, address_object.public_ip)
        address_object.delete()

    def test_disassociate_external_elasticip_or_instance(self):

        ctx = self.mock_relationship_context(
            'test_disassociate_external_elasticip_or_instance')
        current_ctx.set(ctx=ctx)
        ctx.source.node.properties['use_external_resource'] = False

        output = \
            elasticip._disassociate_external_elasticip_or_instance()

        self.assertEqual(False, output)

    def test_disassociate_external_elasticip_or_instance_external(self):

        ctx = self.mock_relationship_context(
            'test_disassociate_external_elasticip_or_instance_external')
        current_ctx.set(ctx=ctx)
        ctx.source.node.properties['use_external_resource'] = True
        ctx.target.node.properties['use_external_resource'] = True
        ctx.source.instance.runtime_properties['public_ip_address'] = \
            '127.0.0.1'

        output = \
            elasticip._disassociate_external_elasticip_or_instance()

        self.assertEqual(True, output)
        self.assertNotIn(
            'public_ip_address',
            ctx.source.instance.runtime_properties)

    def test_associate_external_elasticip_or_instance(self):

        ctx = self.mock_relationship_context(
            'test_associate_external_elasticip_or_instance')
        current_ctx.set(ctx=ctx)
        ctx.source.node.properties['use_external_resource'] = False

        output = \
            elasticip._associate_external_elasticip_or_instance(
                '127.0.0.1')

        self.assertEqual(False, output)

    def test_associate_external_elasticip_or_instance_external(self):

        ctx = self.mock_relationship_context(
            'test_associate_external_elasticip_or_instance_external')
        current_ctx.set(ctx=ctx)
        client = self._get_ec2_client()
        address_object = client.allocate_address()

        ctx.source.node.properties['use_external_resource'] = True
        ctx.target.node.properties['use_external_resource'] = True
        ctx.source.instance.runtime_properties['public_ip_address'] = \
            '127.0.0.1'

        output = \
            elasticip._associate_external_elasticip_or_instance(
                address_object.public_ip)

        self.assertEqual(True, output)

        self.assertIn(
            'public_ip_address',
            ctx.source.instance.runtime_properties)
        self.assertEqual(
            address_object.public_ip,
            ctx.source.instance.runtime_properties['public_ip_address'])
        address_object.delete()

    def test_release_external_elasticip(self):

        ctx = self.mock_cloudify_context(
            'test_release_external_elasticip')
        current_ctx.set(ctx=ctx)
        ctx.node.properties['use_external_resource'] = False

        output = \
            elasticip._release_external_elasticip()

        self.assertEqual(False, output)

    def test_release_external_elasticip_external(self):

        ctx = self.mock_cloudify_context(
            'test_release_external_elasticip')
        current_ctx.set(ctx=ctx)
        ctx.node.properties['use_external_resource'] = True
        ctx.instance.runtime_properties[EXTERNAL_RESOURCE_ID] = \
            '127.0.0.1'

        output = \
            elasticip._release_external_elasticip()

        self.assertEqual(True, output)
        self.assertNotIn(
            EXTERNAL_RESOURCE_ID,
            ctx.instance.runtime_properties)

    def test_allocate_external_elasticip(self):

        ctx = self.mock_cloudify_context(
            'test_allocate_external_elasticip')
        current_ctx.set(ctx=ctx)
        ctx.node.properties['use_external_resource'] = False

        output = \
            elasticip._allocate_external_elasticip()

        self.assertEqual(False, output)

    def test_allocate_external_elasticip_external(self):

        ctx = self.mock_cloudify_context(
            'test_allocate_external_elasticip_external')
        current_ctx.set(ctx=ctx)
        client = self._get_ec2_client()
        address_object = client.allocate_address()

        ctx.node.properties['use_external_resource'] = True
        ctx.node.properties['resource_id'] = address_object.public_ip

        output = \
            elasticip._allocate_external_elasticip()

        self.assertEqual(True, output)
        self.assertIn(
            EXTERNAL_RESOURCE_ID,
            ctx.instance.runtime_properties)
        self.assertEqual(
            address_object.public_ip,
            ctx.instance.runtime_properties[EXTERNAL_RESOURCE_ID])

        address_object.delete()

    def test_allocate_external_elasticip_external_bad_id(self):

        ctx = self.mock_cloudify_context(
            'test_allocate_external_elasticip_external')
        current_ctx.set(ctx=ctx)
        ctx.node.properties['use_external_resource'] = True
        ctx.node.properties['resource_id'] = '127.0.0.1'

        ex = self.assertRaises(
            NonRecoverableError,
            elasticip._allocate_external_elasticip)

        self.assertIn(
            'the given elasticip does not exist in the account',
            ex.message)


class EC2InstanceUnitTests(EC2LocalTestUtils):

    def test_instance_invalid_ami(self):

        image_id = 'ami-65b95565'

        ex = self.assertRaises(
            NonRecoverableError, instance._get_image, image_id)

        self.assertIn('InvalidAMIID.NotFound', ex.message)

    def test_instance_get_image_id(self):

        image_object = instance._get_image(TEST_AMI)
        self.assertEqual(image_object.id, TEST_AMI)

    def test_instance_external_invalid_instance(self):

        ctx = self.mock_cloudify_context(
            'test_instance_external_invalid_instance')
        current_ctx.set(ctx=ctx)
        ctx.node.properties['use_external_resource'] = True
        ctx.node.properties['resource_id'] = 'i-00z0zz0z'

        ex = self.assertRaises(
            NonRecoverableError, instance._create_external_instance)

        self.assertIn('is not in this account', ex.message)

    def test_get_instance_keypair(self):

        ctx = self.mock_cloudify_context(
            'test_get_instance_keypair')
        current_ctx.set(ctx=ctx)
        provider_variables = {
            'agents_keypair': '',
            'agents_security_group': ''
        }
        output = instance._get_instance_keypair(provider_variables)
        self.assertEqual(None, output)

    def test_get_instance_parameters(self):

        ctx = self.mock_cloudify_context(
            'test_get_instance_parameters')
        current_ctx.set(ctx=ctx)
        ctx.node.properties['image_id'] = 'abc'
        ctx.node.properties['instance_type'] = 'efg'
        ctx.node.properties['parameters']['image_id'] = 'abcd'
        ctx.node.properties['parameters']['key_name'] = 'xyz'
        parameters = instance._get_instance_parameters()
        self.assertIn('abcd', parameters['image_id'])
        self.assertIn('xyz', parameters['key_name'])
        self.assertIn('efg', parameters['instance_type'])

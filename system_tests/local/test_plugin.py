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

# Third Party
from boto.exception import EC2ResponseError

# Cloudify Imports
from ec2 import (
    securitygroup,
    keypair,
    elasticip,
    instance,
    constants
)
from cloudify.state import current_ctx
from cloudify.exceptions import NonRecoverableError
from ec2_test_utils import (
    EC2LocalTestUtils,
    EXTERNAL_RESOURCE_ID,
    SIMPLE_IP, SIMPLE_SG, SIMPLE_KP,
    SIMPLE_VOL, SIMPLE_VM,
    PAIR_A_IP, PAIR_A_VM,
    PAIR_B_SG, PAIR_B_VM,
    PAIR_C_VOL, PAIR_C_VM
)


class TestWorkflowClean(EC2LocalTestUtils):

    def test_simple_resources(self):
        client = self._get_ec2_client()

        test_name = 'test_simple_resources'

        inputs = self._get_inputs(test_name=test_name)
        self._set_up(inputs=inputs)

        # execute install workflow
        self.localenv.execute('install', task_retries=10)

        instance_storage = self._get_instances(self.localenv.storage)

        self.assertEquals(5, len(instance_storage))

        for node_instance in self._get_instances(self.localenv.storage):
            self.assertIn(EXTERNAL_RESOURCE_ID,
                          node_instance.runtime_properties)

        elastic_ip_node = \
            self._get_instance_node(
                SIMPLE_IP, self.localenv.storage)
        elastic_ip_address = \
            elastic_ip_node.runtime_properties[EXTERNAL_RESOURCE_ID]
        elastic_ip_object_list = \
            client.get_all_addresses(addresses=elastic_ip_address)
        self.assertEqual(1, len(elastic_ip_object_list))

        volume_node = \
            self._get_instance_node(
                SIMPLE_VOL, self.localenv.storage)
        volume_id = \
            volume_node.runtime_properties[EXTERNAL_RESOURCE_ID]
        volume_object_list = \
            client.get_all_volumes(volume_ids=[volume_id])
        self.assertEqual(1, len(volume_object_list))

        security_group_node = \
            self._get_instance_node(SIMPLE_SG, self.localenv.storage)
        security_group_id = \
            security_group_node.runtime_properties[EXTERNAL_RESOURCE_ID]
        security_group_object_list = \
            client.get_all_security_groups(group_ids=security_group_id)
        self.assertEqual(1, len(security_group_object_list))

        key_pair_node = \
            self._get_instance_node(SIMPLE_KP, self.localenv.storage)
        key_pair_name = \
            key_pair_node.runtime_properties[EXTERNAL_RESOURCE_ID]
        key_pair_object_list = \
            client.get_all_key_pairs(keynames=key_pair_name)
        self.assertEqual(1, len(key_pair_object_list))

        instance_node = \
            self._get_instance_node(SIMPLE_VM, self.localenv.storage)
        instance_id = \
            instance_node.runtime_properties[EXTERNAL_RESOURCE_ID]
        reservation_list = \
            client.get_all_reservations(instance_ids=instance_id)
        instance_list = reservation_list[0].instances
        self.assertEqual(1, len(instance_list))

        self.localenv.execute('execute_operation',
                              parameters={
                                  'operation':
                                  'cloudify.interfaces.aws.snapshot.create',
                                  'node_ids': SIMPLE_VOL
                              },
                              task_retries=10)

        instance_node = \
            self._get_instance_node(
                SIMPLE_VOL, self.localenv.storage)
        snapshot_id = \
            instance_node.runtime_properties[
                constants.VOLUME_SNAPSHOT_ATTRIBUTE]
        all_snapshots = client.get_all_snapshots(snapshot_id)
        self.assertIn(snapshot_id[0],
                      [snapshot.id for snapshot in all_snapshots])
        client.delete_snapshot(snapshot_id=snapshot_id[0])

        self.localenv.execute('uninstall', task_retries=10)

        with self.assertRaises(EC2ResponseError):
            client.get_all_addresses(addresses=elastic_ip_address)
        with self.assertRaises(EC2ResponseError):
            client.get_all_security_groups(group_ids=security_group_id)
        with self.assertRaises(EC2ResponseError):
            client.get_all_key_pairs(keynames=key_pair_name)
        with self.assertRaises(EC2ResponseError):
            client.get_all_volumes(volume_ids=[volume_id])

        client.get_all_reservations(instance_ids=instance_id)
        instance_state = reservation_list[0].instances[0].update()
        self.assertIn('terminated', instance_state)

    def test_simple_relationships(self):

        client = self._get_ec2_client()

        test_name = 'test_simple_relationships'

        inputs = self._get_inputs(test_name=test_name)

        self._set_up(
            inputs=inputs,
            filename='relationships-blueprint.yaml')

        # execute install workflow
        self.localenv.execute('install', task_retries=10)

        instance_storage = self._get_instances(self.localenv.storage)
        self.assertEquals(6, len(instance_storage))

        instance_node = \
            self._get_instance_node(PAIR_A_VM, self.localenv.storage)
        instance_id_a = \
            instance_node.runtime_properties[EXTERNAL_RESOURCE_ID]
        reservation_list = \
            client.get_all_reservations(instance_ids=instance_id_a)
        instance_list_ip = reservation_list[0].instances

        elastic_ip_node = \
            self._get_instance_node(
                PAIR_A_IP, self.localenv.storage)
        elastic_ip_address = \
            elastic_ip_node.runtime_properties[EXTERNAL_RESOURCE_ID]
        elastic_ip_object_list = \
            client.get_all_addresses(addresses=elastic_ip_address)

        self.assertEqual(
            str(elastic_ip_object_list[0].instance_id),
            str(instance_list_ip[0].id))

        instance_node = \
            self._get_instance_node(PAIR_B_VM, self.localenv.storage)
        instance_id_b = \
            instance_node.runtime_properties[EXTERNAL_RESOURCE_ID]
        reservation_list = \
            client.get_all_reservations(instance_ids=instance_id_b)
        instance_list = reservation_list[0].instances

        security_group_node = \
            self._get_instance_node(PAIR_B_SG, self.localenv.storage)
        security_group_id = \
            security_group_node.runtime_properties[EXTERNAL_RESOURCE_ID]
        security_group_object_list = \
            client.get_all_security_groups(group_ids=security_group_id)

        self.assertIn(
            str(security_group_object_list[0].instances()[0].id),
            str(instance_list[0].id))

        instance_node = \
            self._get_instance_node(PAIR_C_VM, self.localenv.storage)
        instance_id_c = \
            instance_node.runtime_properties[EXTERNAL_RESOURCE_ID]
        reservation_list = \
            client.get_all_reservations(instance_ids=instance_id_c)
        instance_list = reservation_list[0].instances

        volume_node = \
            self._get_instance_node(
                PAIR_C_VOL, self.localenv.storage)
        volume_id = \
            volume_node.runtime_properties[EXTERNAL_RESOURCE_ID]
        volume_object_list = \
            client.get_all_volumes(volume_ids=[volume_id])

        attachment = volume_object_list[0].attach_data

        self.assertIn(
            str(attachment.instance_id),
            str(instance_list[0].id))

        self.localenv.execute('uninstall', task_retries=10)

        with self.assertRaises(EC2ResponseError):
            client.get_all_addresses(addresses=elastic_ip_address)
        with self.assertRaises(EC2ResponseError):
            client.get_all_security_groups(group_ids=security_group_id)
        with self.assertRaises(EC2ResponseError):
            client.get_all_volumes(volume_ids=volume_id)

        try:
            output = client.get_all_volumes(volume_ids=[volume_id])
        except EC2ResponseError:
            self.assertTrue(True)
        else:
            print output
            if volume_id not in [vol.id for vol in output]:
                self.assertTrue(True)
            else:
                for vol in output:
                    if vol.id in volume_id:
                        self.assertNotIn(vol.status,
                                         ['available', 'in-use'])

        client.get_all_reservations(instance_ids=instance_id_a)
        instance_state = reservation_list[0].instances[0].update()
        self.assertIn('terminated', instance_state)
        client.get_all_reservations(instance_ids=instance_id_b)
        instance_state = reservation_list[0].instances[0].update()
        self.assertIn('terminated', instance_state)
        client.get_all_reservations(instance_ids=instance_id_c)
        instance_state = reservation_list[0].instances[0].update()
        self.assertIn('terminated', instance_state)


class EC2SecurityGroupUnitTests(EC2LocalTestUtils):

    def test_get_all_security_groups(self):

        ctx = self.mock_cloudify_context(
            'test_get_all_security_groups')
        current_ctx.set(ctx=ctx)

        client = self._get_ec2_client()
        groups_from_test = client.get_all_security_groups()

        groups_from_plugin = securitygroup._get_all_security_groups()

        self.assertEqual(len(groups_from_test), len(groups_from_plugin))

    def test_get_all_security_groups_not_found(self):

        ctx = self.mock_cloudify_context(
            'test_get_all_security_groups_not_found')
        current_ctx.set(ctx=ctx)

        not_found_names = ['test_get_all_security_groups_not_found']

        groups_from_plugin = securitygroup._get_all_security_groups(
            list_of_group_names=not_found_names)

        self.assertIsNone(groups_from_plugin)

    def test_get_security_group_from_name(self):

        ctx = self.mock_cloudify_context(
            'test_get_security_group_from_name')
        current_ctx.set(ctx=ctx)

        client = self._get_ec2_client()
        group = client.create_security_group(
            'test_get_security_group_from_name',
            'some description')
        self.addCleanup(group.delete)
        group_from_plugin = securitygroup._get_security_group_from_id(
            group_id=group.id)
        self.assertEqual(group.name, group_from_plugin.name)

    def test_get_security_group_from_id(self):

        ctx = self.mock_cloudify_context(
            'test_get_security_group_from_id')
        current_ctx.set(ctx=ctx)

        client = self._get_ec2_client()
        group = client.create_security_group(
            'test_get_security_group_from_id',
            'some description')
        self.addCleanup(group.delete)
        group_from_plugin = securitygroup._get_security_group_from_name(
            group_name=group.name)
        self.assertEqual(group.id, group_from_plugin.id)

    def test_get_security_group_from_name_but_really_id(self):

        ctx = self.mock_cloudify_context(
            'test_get_security_group_from_name_but_really_id')
        current_ctx.set(ctx=ctx)

        client = self._get_ec2_client()
        group = client.create_security_group(
            'test_get_security_group_from_name_but_really_id',
            'some description')
        self.addCleanup(group.delete)
        group_from_plugin = securitygroup._get_security_group_from_name(
            group_name=group.id)
        self.assertEqual(group.name, group_from_plugin.name)

    def test_get_security_group_from_id_but_really_name(self):

        ctx = self.mock_cloudify_context(
            'test_get_security_group_from_id_but_really_name')
        current_ctx.set(ctx=ctx)

        client = self._get_ec2_client()
        group = client.create_security_group(
            'test_get_security_group_from_id_but_really_name',
            'some description')
        self.addCleanup(group.delete)
        group_from_plugin = securitygroup._get_security_group_from_id(
            group_id=group.name)
        self.assertEqual(group.id, group_from_plugin.id)

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

    def test_create_external_securitygroup_external(self):

        ctx = self.mock_cloudify_context(
            'test_create_external_securitygroup_external')
        current_ctx.set(ctx=ctx)

        client = self._get_ec2_client()
        group = client.create_security_group(
            'test_create_external_securitygroup_external',
            'some description')
        self.addCleanup(group.delete)
        ctx.node.properties['use_external_resource'] = True
        ctx.node.properties['resource_id'] = group.id

        output = securitygroup._create_external_securitygroup(group.name)
        self.assertEqual(True, output)
        self.assertEqual(
            ctx.instance.runtime_properties[EXTERNAL_RESOURCE_ID],
            group.id)

    def test_create_external_securitygroup_external_bad_id(self):

        ctx = self.mock_cloudify_context(
            'test_create_external_securitygroup_external_bad_id')
        current_ctx.set(ctx=ctx)

        ctx.node.properties['use_external_resource'] = True
        ctx.node.properties['resource_id'] = 'sg-73cd3f1e'

        with self.assertRaisesRegexp(
                NonRecoverableError,
                'security group does not exist'):
            securitygroup._create_external_securitygroup(
                'sg-73cd3f1e')

    def test_create_group_rules_ruleset(self):

        ctx = self.mock_cloudify_context(
            'test_create_group_rules_ruleset')
        ctx.node.properties['rules'] = [
            {
                'ip_protocol': 'tcp',
                'from_port': 22,
                'to_port': 22,
                'cidr_ip': '0.0.0.0/0'
            }
        ]

        current_ctx.set(ctx=ctx)

        client = self._get_ec2_client()
        group = client.create_security_group(
            'test_create_group_rules',
            'some description')
        self.addCleanup(group.delete)
        securitygroup._create_group_rules(group)
        groups_from_test = \
            client.get_all_security_groups(groupnames=[group.name])
        self.assertEqual(group.id, groups_from_test[0].id)
        self.assertEqual(
            str(groups_from_test[0].rules[0]),
            'IPPermissions:tcp(22-22)'
        )

    def test_delete_security_group_bad_group(self):
        ctx = self.mock_cloudify_context(
            'test_delete_security_group_bad_group')
        current_ctx.set(ctx=ctx)

        with self.assertRaisesRegexp(
                NonRecoverableError,
                'does not exist in the account'):

            securitygroup._delete_security_group('sg-73cd3f1e')


class EC2KeyPairUnitTests(EC2LocalTestUtils):

    def test_get_key_pair_by_id(self):

        ctx = self.mock_cloudify_context(
            'test_get_key_pair_by_id')
        current_ctx.set(ctx=ctx)

        client = self._get_ec2_client()
        kp = client.create_key_pair(
            'test_get_key_pair_by_id')
        self.addCleanup(kp.delete)
        output = keypair._get_key_pair_by_id(kp.name)
        self.assertEqual(kp.name, output.name)


class EC2ElasticIPUnitTests(EC2LocalTestUtils):

    def test_get_address_object_by_id(self):

        ctx = self.mock_relationship_context(
            'test_get_address_object_by_id')
        current_ctx.set(ctx=ctx)

        client = self._get_ec2_client()
        address = client.allocate_address()
        address_object = \
            elasticip._get_address_object_by_id(address.public_ip)
        self.addCleanup(address_object.delete)
        self.assertEqual(
            address.public_ip, address_object.public_ip)

    def test_get_address_by_id(self):

        ctx = self.mock_relationship_context(
            'test_get_address_by_id')
        current_ctx.set(ctx=ctx)

        client = self._get_ec2_client()
        address_object = client.allocate_address()
        self.addCleanup(address_object.delete)
        address = elasticip._get_address_by_id(address_object.public_ip)
        self.assertEqual(address, address_object.public_ip)

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

    def test_associate_external_elasticip_or_instance_external(self):

        ctx = self.mock_relationship_context(
            'test_associate_external_elasticip_or_instance_external')
        current_ctx.set(ctx=ctx)
        client = self._get_ec2_client()
        address_object = client.allocate_address()
        self.addCleanup(address_object.delete)

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

    def test_allocate_external_elasticip_external(self):

        ctx = self.mock_cloudify_context(
            'test_allocate_external_elasticip_external')
        current_ctx.set(ctx=ctx)
        client = self._get_ec2_client()
        address_object = client.allocate_address()
        self.addCleanup(address_object.delete)
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

    def test_allocate_external_elasticip_external_bad_id(self):

        ctx = self.mock_cloudify_context(
            'test_allocate_external_elasticip_external')
        current_ctx.set(ctx=ctx)
        ctx.node.properties['use_external_resource'] = True
        ctx.node.properties['resource_id'] = '127.0.0.1'

        with self.assertRaisesRegexp(
                NonRecoverableError,
                'elasticip does not exist in the account'):
            elasticip._allocate_external_elasticip()


class EC2InstanceUnitTests(EC2LocalTestUtils):

    def test_instance_invalid_ami(self):
        ctx = self.mock_cloudify_context(
            'test_instance_invalid_ami')
        current_ctx.set(ctx=ctx)

        image_id = 'ami-65b95565'

        with self.assertRaisesRegexp(
                NonRecoverableError,
                'InvalidAMIID.NotFound'):
            instance._get_image(image_id)

    def test_instance_get_image_id(self):

        ctx = self.mock_cloudify_context(
            'test_instance_get_image_id')
        current_ctx.set(ctx=ctx)

        image_object = instance._get_image(
            self.env.ubuntu_trusty_image_id)
        self.assertEqual(image_object.id,
                         self.env.ubuntu_trusty_image_id)

    def test_instance_external_invalid_instance(self):

        ctx = self.mock_cloudify_context(
            'test_instance_external_invalid_instance')
        current_ctx.set(ctx=ctx)

        ctx.node.properties['use_external_resource'] = True
        ctx.node.properties['resource_id'] = 'i-00z0zz0z'

        with self.assertRaisesRegexp(
                NonRecoverableError,
                'not in this account'):
            instance._create_external_instance()

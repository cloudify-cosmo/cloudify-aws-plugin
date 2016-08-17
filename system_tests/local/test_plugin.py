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
from boto.exception import BotoServerError

# Cloudify Imports
from cloudify_aws import constants
from ec2_test_utils import (
    EC2LocalTestUtils,
    EXTERNAL_RESOURCE_ID,
    SIMPLE_IP, SIMPLE_SG, SIMPLE_KP,
    SIMPLE_VM, SIMPLE_LB,
    SIMPLE_VOL,
    PAIR_A_IP, PAIR_A_VM,
    PAIR_B_SG, PAIR_B_VM,
    PAIR_C_VOL, PAIR_C_VM,
    PAIR_C_LB
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

        self.assertEquals(6, len(instance_storage))

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

        elb_client = self._get_elb_client()

        elastic_load_balancer_node = \
            self._get_instance_node(
                SIMPLE_LB, self.localenv.storage)
        elastic_load_balancer_name = \
            elastic_load_balancer_node.runtime_properties[EXTERNAL_RESOURCE_ID]
        elastic_lb_object_list = \
            elb_client.get_all_load_balancers(
                load_balancer_names=[elastic_load_balancer_name])
        self.assertEqual(1, len(elastic_lb_object_list))

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
                constants.EBS['VOLUME_SNAPSHOT_ATTRIBUTE']]
        all_snapshots = client.get_all_snapshots(snapshot_id)
        self.assertIn(snapshot_id[0],
                      [snapshot.id for snapshot in all_snapshots])
        client.delete_snapshot(snapshot_id=snapshot_id[0])

        self.localenv.execute('uninstall', task_retries=10)

        with self.assertRaises(BotoServerError):
            elb_client.get_all_load_balancers(
                load_balancer_names=[elastic_load_balancer_name])
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
        elb_client = self._get_elb_client()

        test_name = 'test_simple_relationships'

        inputs = self._get_inputs(test_name=test_name)

        self._set_up(
            inputs=inputs,
            filename='relationships-blueprint.yaml')

        # execute install workflow
        self.localenv.execute('install', task_retries=10)

        instance_storage = self._get_instances(self.localenv.storage)
        self.assertEquals(7, len(instance_storage))

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

        elastic_load_balancer_node = \
            self._get_instance_node(
                PAIR_C_LB, self.localenv.storage)
        elastic_load_balancer_name = \
            elastic_load_balancer_node.runtime_properties[EXTERNAL_RESOURCE_ID]
        elastic_lb_object_list = \
            elb_client.get_all_load_balancers(
                load_balancer_names=[elastic_load_balancer_name])

        self.assertEqual(1, len(elastic_lb_object_list))

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
        with self.assertRaises(BotoServerError):
            elb_client.get_all_load_balancers(
                load_balancer_names=[elastic_load_balancer_name])
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

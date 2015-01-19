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
import testtools

# Third Party Imports
from moto import mock_ec2

# Cloudify Imports is imported and used in operations
from ec2 import connection
from ec2 import instance
from cloudify.mocks import MockCloudifyContext
from cloudify.exceptions import NonRecoverableError

TEST_AMI_IMAGE_ID = 'ami-e214778a'
TEST_INSTANCE_TYPE = 't1.micro'


class TestInstance(testtools.TestCase):

    def mock_ctx(self, test_name):
        """ Creates a mock context for the instance
            tests
        """

        test_node_id = test_name
        test_properties = {
            'image_id': TEST_AMI_IMAGE_ID,
            'instance_type': TEST_INSTANCE_TYPE,
            'attributes': {
                'security_groups': ['sg-73cd3f1e'],
                'instance_initiated_shutdown_behavior': 'stop'
            }
        }

        ctx = MockCloudifyContext(
            node_id=test_node_id,
            properties=test_properties
        )

        return ctx

    def test_create(self):
        """ this tests that the instance create function works
        """

        ctx = self.mock_ctx('test_instance_create')

        with mock_ec2():
            instance.run_instances(ctx=ctx)
            self.assertIn('instance_id',
                          ctx.instance.runtime_properties.keys())

    def test_stop(self):
        """
        this tests that the instance stop function works
        """

        ctx = self.mock_ctx('test_instance_stop')

        with mock_ec2():
            ec2_client = connection.EC2ConnectionClient().client()
            reservation = ec2_client.run_instances(
                TEST_AMI_IMAGE_ID, instance_type=TEST_INSTANCE_TYPE)
            id = reservation.instances[0].id
            ctx.instance.runtime_properties['instance_id'] = id
            instance.stop(ctx=ctx)
            reservations = ec2_client.get_all_reservations(id)
            instance_object = reservations[0].instances[0]
            state = instance_object.update()
            self.assertEqual(state, 'stopped')

    def test_start(self):
        """ this tests that the instance start function works
        """

        ctx = self.mock_ctx('test_instance_start')

        with mock_ec2():
            ec2_client = connection.EC2ConnectionClient().client()
            reservation = ec2_client.run_instances(
                TEST_AMI_IMAGE_ID, instance_type=TEST_INSTANCE_TYPE)
            id = reservation.instances[0].id
            ctx.instance.runtime_properties['instance_id'] = id
            ec2_client.stop_instances(id)
            instance.start(ctx=ctx)
            reservations = ec2_client.get_all_reservations(id)
            instance_object = reservations[0].instances[0]
            state = instance_object.update()
            self.assertEqual(state, 'running')

    def test_terminate(self):
        """ this tests that the instance.terminate function
            works
        """

        ctx = self.mock_ctx('test_instance_terminate')

        with mock_ec2():
            ec2_client = connection.EC2ConnectionClient().client()
            reservation = ec2_client.run_instances(
                TEST_AMI_IMAGE_ID, instance_type=TEST_INSTANCE_TYPE)
            id = reservation.instances[0].id
            ctx.instance.runtime_properties['instance_id'] = id
            instance.terminate(ctx=ctx)
            reservations = ec2_client.get_all_reservations(id)
            instance_object = reservations[0].instances[0]
            state = instance_object.update()
            self.assertEqual(state, 'terminated')

    def test_bad_id_start(self):
        """this tests that start fails when given an invalid
           instance_id and the proper error is raised
        """

        ctx = self.mock_ctx('test_bad_instance_id_start')

        with mock_ec2():
            ctx.instance.runtime_properties['instance_id'] = 'bad_id'
            ex = self.assertRaises(NonRecoverableError,
                                   instance.start, ctx=ctx)
            self.assertIn('InvalidInstanceID.NotFound', ex.message)

    def test_bad_id_stop(self):
        """ this tests that stop fails when given an invalid
            instance_id and the proper error is raised
        """

        ctx = self.mock_ctx('test_bad_instance_id_stop')

        with mock_ec2():
            ctx.instance.runtime_properties['instance_id'] = 'bad_id'
            ex = self.assertRaises(NonRecoverableError,
                                   instance.stop, ctx=ctx)
            self.assertIn('InvalidInstanceID.NotFound', ex.message)

    def test_bad_id_terminate(self):
        """ this tests that a terminate fails when given an
            invalid instance_id and the proper error is raised
        """

        ctx = self.mock_ctx('test_bad_instance_id_terminate')

        with mock_ec2():
            ctx.instance.runtime_properties['instance_id'] = 'bad_id'
            ex = self.assertRaises(NonRecoverableError,
                                   instance.terminate, ctx=ctx)
            self.assertIn('InvalidInstanceID.NotFound', ex.message)

    def test_bad_subnet_id_create(self):
        """ This tests that the NonRecoverableError is triggered
            when an non existing subnet_id is included in the create
            statement
        """

        ctx = self.mock_ctx('test_bad_subnet_id_create')

        with mock_ec2():
            ctx.node.properties['attributes']['subnet_id'] = 'test'
            ex = self.assertRaises(NonRecoverableError,
                                   instance.run_instances, ctx=ctx)
            self.assertIn('InvalidSubnetID.NotFound', ex.message)

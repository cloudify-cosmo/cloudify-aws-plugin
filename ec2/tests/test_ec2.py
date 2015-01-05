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
import unittest

# Boto Imports
from boto.ec2 import instance as ec2_instance_object
from boto.ec2 import EC2Connection
from moto import mock_ec2

# Cloudify Imports is imported and used in operations
from ec2 import connection
from ec2 import instance
from ec2 import utility
from cloudify.mocks import MockCloudifyContext
from cloudify.exceptions import NonRecoverableError

TEST_AMI_IMAGE_ID = 'ami-e214778a'
TEST_INSTANCE_TYPE = 't1.micro'
FQDN = '((?:[a-z][a-z\\.\\d\\-]+)\\.(?:[a-z][a-z\\-]+))(?![\\w\\.])'


class TestPlugin(unittest.TestCase):

    def mock_ctx(self, test_name):

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

    @mock_ec2
    def test_connect(self):

        c = connection.EC2Client().connect()
        self.assertTrue(type(c), EC2Connection)
        self.assertEqual(c.DefaultRegionEndpoint,
                         'ec2.us-east-1.amazonaws.com')

    def test_instance_create(self):

        ctx = self.mock_ctx('test_instance_create')

        with mock_ec2():

            instance.create(ctx=ctx)

    def test_instance_start(self):

        ctx = self.mock_ctx('test_instance_start')

        with mock_ec2():
            compute = connection.EC2Client().connect()
            reservation = compute.run_instances(
                TEST_AMI_IMAGE_ID, instance_type=TEST_INSTANCE_TYPE)
            id = reservation.instances[0].id
            ctx.instance.runtime_properties['instance_id'] = id
            EC2Connection().stop_instances(id)
            instance.start(ctx=ctx)

    def test_no_instance_start(self):

        ctx = self.mock_ctx('test_no_instance_start')
        ctx.instance.runtime_properties['instance_id'] = None

        with mock_ec2():
            self.assertRaises(IndexError, instance.start, ctx=ctx)

    def test_bad_instance_start(self):

        ctx = self.mock_ctx('test_bad_instance_start')
        ctx.instance.runtime_properties['instance_id'] = 'bad instance'

        with mock_ec2():
            self.assertRaises(NonRecoverableError, instance.start, ctx=ctx)

    def test_instance_stop(self):

        ctx = self.mock_ctx('test_instance_stop')

        with mock_ec2():
            compute = connection.EC2Client().connect()
            reservation = compute.run_instances(
                TEST_AMI_IMAGE_ID, instance_type=TEST_INSTANCE_TYPE)
            id = reservation.instances[0].id
            ctx.instance.runtime_properties['instance_id'] = id
            instance.stop(ctx=ctx)

    def test_no_instance_stop(self):

        ctx = self.mock_ctx('test_no_instance_stop')
        ctx.instance.runtime_properties['instance_id'] = None

        with mock_ec2():
            self.assertRaises(IndexError, instance.stop, ctx=ctx)

    def test_bad_instance_stop(self):

        ctx = self.mock_ctx('test_bad_instance_stop')
        ctx.instance.runtime_properties['instance_id'] = 'bad instance'

        with mock_ec2():
            self.assertRaises(NonRecoverableError, instance.stop, ctx=ctx)

    def test_instance_terminate(self):

        ctx = self.mock_ctx('test_instance_terminate')

        with mock_ec2():
            compute = connection.EC2Client().connect()
            reservation = compute.run_instances(
                TEST_AMI_IMAGE_ID, instance_type=TEST_INSTANCE_TYPE)
            id = reservation.instances[0].id
            ctx.instance.runtime_properties['instance_id'] = id
            instance.terminate(ctx=ctx)

    def test_no_instance_terminate(self):

        ctx = self.mock_ctx('test_no_instance_terminate')
        ctx.instance.runtime_properties['instance_id'] = None

        with mock_ec2():
            self.assertRaises(IndexError, instance.terminate, ctx=ctx)

    def test_bad_instance_terminate(self):

        ctx = self.mock_ctx('test_bad_instance_terminate')
        ctx.instance.runtime_properties['instance_id'] = 'bad instance'

        with mock_ec2():
            self.assertRaises(NonRecoverableError, instance.terminate, ctx=ctx)

    def test_validate_instance_id(self):

        ctx = self.mock_ctx('test_validate_instance_id')

        with mock_ec2():
            compute = connection.EC2Client().connect()
            reservation = compute.run_instances(
                TEST_AMI_IMAGE_ID, instance_type=TEST_INSTANCE_TYPE)
            id = reservation.instances[0].id
            self.assertTrue(utility.validate_instance_id(id, ctx=ctx))

    def test_get_instance_from_id(self):

        ctx = self.mock_ctx('test_get_instance_from_id')

        with mock_ec2():
            compute = connection.EC2Client().connect()
            reservation = compute.run_instances(
                TEST_AMI_IMAGE_ID, instance_type=TEST_INSTANCE_TYPE)
            id = reservation.instances[0].id
            instance_object = utility.get_instance_from_id(id, ctx=ctx)
            self.assertEqual(type(instance_object),
                             ec2_instance_object.Instance)

    def test_get_instance_state(self):
        ctx = self.mock_ctx('test_get_instance_state')
        with mock_ec2():
            compute = connection.EC2Client().connect()
            reservation = compute.run_instances(
                TEST_AMI_IMAGE_ID, instance_type=TEST_INSTANCE_TYPE)
            id = reservation.instances[0].id
            instance_object = utility.get_instance_from_id(id, ctx=ctx)
            instance_state = utility.get_instance_state(instance_object,
                                                        ctx=ctx)
            self.assertEqual(instance_state, 16)

    def test_get_private_dns_name(self):

        ctx = self.mock_ctx('test_get_private_dns_name')

        with mock_ec2():
            compute = connection.EC2Client().connect()
            reservation = compute.run_instances(
                TEST_AMI_IMAGE_ID, instance_type=TEST_INSTANCE_TYPE)
            id = reservation.instances[0].id
            instance_object = utility.get_instance_from_id(id, ctx=ctx)
            dns_name = utility.get_private_dns_name(instance_object)
            self.assertRegexpMatches(dns_name, FQDN)

    def test_get_public_dns_name(self):

        ctx = self.mock_ctx('test_get_public_dns_name')

        with mock_ec2():
            compute = connection.EC2Client().connect()
            reservation = compute.run_instances(
                TEST_AMI_IMAGE_ID, instance_type=TEST_INSTANCE_TYPE)
            id = reservation.instances[0].id
            instance_object = utility.get_instance_from_id(id, ctx=ctx)
            dns_name = utility.get_public_dns_name(instance_object)
            self.assertRegexpMatches(dns_name, FQDN)

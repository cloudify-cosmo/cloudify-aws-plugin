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

# Built-in Imports
import testtools

# Third Party Imports
from moto import mock_ec2

# Cloudify Imports is imported and used in operations
from ec2 import constants
from ec2 import connection
from ec2 import instance
from cloudify.state import current_ctx
from cloudify.mocks import MockCloudifyContext
from cloudify.exceptions import NonRecoverableError

TEST_AMI_IMAGE_ID = 'ami-e214778a'
TEST_INSTANCE_TYPE = 't1.micro'
FQDN = '((?:[a-z][a-z\\.\\d\\-]+)\\.(?:[a-z][a-z\\-]+))(?![\\w\\.])'


class TestInstance(testtools.TestCase):

    def mock_ctx(self, test_name):
        """ Creates a mock context for the instance
            tests
        """

        test_node_id = test_name
        test_properties = {
            constants.AWS_CONFIG_PROPERTY: {},
            'use_external_resource': False,
            'resource_id': '',
            'image_id': TEST_AMI_IMAGE_ID,
            'instance_type': TEST_INSTANCE_TYPE,
            'cloudify_agent': {},
            'agent_config': {},
            'parameters': {
                'security_group_ids': ['sg-73cd3f1e'],
                'instance_initiated_shutdown_behavior': 'stop'
            }
        }

        operation = {
            'retry_number': 0
        }

        ctx = MockCloudifyContext(
            node_id=test_node_id,
            properties=test_properties,
            operation=operation
        )
        ctx.node.type_hierarchy = ['cloudify.nodes.Compute']
        return ctx

    @mock_ec2
    def test_run_instances_clean(self):
        """ this tests that the instance create function
        adds the runtime_properties
        """

        ctx = self.mock_ctx('test_run_instances_clean')
        current_ctx.set(ctx=ctx)
        instance.run_instances(ctx=ctx)
        self.assertIn('aws_resource_id',
                      ctx.instance.runtime_properties.keys())

    @mock_ec2
    def test_with_userdata_clean(self):
        """ this tests that handle user data returns the expected output
        """

        ctx = self.mock_ctx('test_with_userdata_clean')
        ctx.agent.init_script = lambda: 'SCRIPT'
        ctx.node.properties['agent_config']['install_method'] = 'init_script'
        current_ctx.set(ctx=ctx)
        handle_userdata_output = \
            instance._handle_userdata(ctx.node.properties['parameters'])
        expected_userdata = 'SCRIPT'
        self.assertIn(expected_userdata,
                      handle_userdata_output.get('user_data'))

    @mock_ec2
    def test_with_existing_userdata_clean(self):
        """ this tests that handle user data returns the expected output when existing
        """

        ctx = self.mock_ctx('test_with_existing_userdata_clean')
        ctx.agent.init_script = lambda: 'EXISTING'
        current_ctx.set(ctx=ctx)
        handle_userdata_output = \
            instance._handle_userdata(ctx.node.properties['parameters'])
        expected_userdata = 'EXISTING'
        self.assertIn(
            expected_userdata, handle_userdata_output.get('user_data'))

    @mock_ec2
    def test_with_both_userdata_clean(self):
        """ this tests that handle user data returns the expected output when merging
        """

        ctx = self.mock_ctx('test_with_existing_userdata_clean')
        ctx.agent.init_script = lambda: '#! SCRIPT'
        ctx.node.properties['agent_config']['install_method'] = 'init_script'
        ctx.node.properties['parameters']['user_data'] = '#! EXISTING'
        current_ctx.set(ctx=ctx)
        handle_userdata_output = \
            instance._handle_userdata(ctx.node.properties['parameters'])
        self.assertTrue(handle_userdata_output['user_data'].startswith(
            'Content-Type: multi'))

    @mock_ec2
    def test_without_userdata_clean(self):
        """ this tests that handle user data returns the expected output
        when there is no init script specified in agent config
        """

        ctx = self.mock_ctx('test_run_instances_with_user_data_clean')
        current_ctx.set(ctx=ctx)
        handle_userdata_output = \
            instance._handle_userdata(ctx.node.properties['parameters'])
        self.assertNotIn('user_data', handle_userdata_output)

    @mock_ec2
    def test_stop_clean(self):
        """
        this tests that the instance stop function stops the
        isntance
        """

        ctx = self.mock_ctx('test_stop_clean')
        current_ctx.set(ctx=ctx)

        ec2_client = connection.EC2ConnectionClient().client()
        reservation = ec2_client.run_instances(
            TEST_AMI_IMAGE_ID, instance_type=TEST_INSTANCE_TYPE)
        instance_id = reservation.instances[0].id
        ctx.instance.runtime_properties['aws_resource_id'] = instance_id
        ctx.instance.runtime_properties['private_dns_name'] = '0.0.0.0'
        ctx.instance.runtime_properties['public_dns_name'] = '0.0.0.0'
        ctx.instance.runtime_properties['public_ip_address'] = '0.0.0.0'
        ctx.instance.runtime_properties['ip'] = '0.0.0.0'
        ctx.instance.runtime_properties['placement'] = 'us-east-1b'
        instance.stop(ctx=ctx)
        reservations = ec2_client.get_all_reservations(instance_id)
        instance_object = reservations[0].instances[0]
        state = instance_object.update()
        self.assertEqual(state, 'stopped')

    @mock_ec2
    def test_start_clean(self):
        """ this tests that the instance start function
        starts an instance.
        """

        ctx = self.mock_ctx('test_start_clean')
        current_ctx.set(ctx=ctx)

        ec2_client = connection.EC2ConnectionClient().client()
        reservation = ec2_client.run_instances(
            TEST_AMI_IMAGE_ID, instance_type=TEST_INSTANCE_TYPE)
        instance_id = reservation.instances[0].id
        ctx.instance.runtime_properties['aws_resource_id'] = instance_id
        ec2_client.stop_instances(instance_id)
        instance.start(ctx=ctx)
        reservations = ec2_client.get_all_reservations(instance_id)
        instance_object = reservations[0].instances[0]
        state = instance_object.update()
        self.assertEqual(state, 'running')

    @mock_ec2
    def test_terminate_clean(self):
        """ this tests that the instance.terminate function
            terminates the instance
        """

        ctx = self.mock_ctx('test_terminate_clean')
        current_ctx.set(ctx=ctx)

        ec2_client = connection.EC2ConnectionClient().client()
        reservation = ec2_client.run_instances(
            TEST_AMI_IMAGE_ID, instance_type=TEST_INSTANCE_TYPE)
        instance_id = reservation.instances[0].id
        ctx.instance.runtime_properties['aws_resource_id'] = instance_id
        instance.terminate(ctx=ctx)
        reservations = ec2_client.get_all_reservations(instance_id)
        instance_object = reservations[0].instances[0]
        state = instance_object.update()
        self.assertEqual(state, 'terminated')

    @mock_ec2
    def test_start_bad_id(self):
        """this tests that start fails when given an invalid
           instance_id and the proper error is raised
        """

        ctx = self.mock_ctx('test_start_bad_id')
        current_ctx.set(ctx=ctx)

        ctx.instance.runtime_properties['aws_resource_id'] = 'bad_id'
        ctx.instance.runtime_properties['reservation_id'] = 'r-54ce20b4'
        ex = self.assertRaises(NonRecoverableError,
                               instance.start, ctx=ctx)
        self.assertIn('no instance with id bad_id exists in this account',
                      ex.message)

    @mock_ec2
    def test_stop_bad_id(self):
        """ this tests that stop fails when given an invalid
            instance_id and the proper error is raised
        """

        ctx = self.mock_ctx('test_stop_bad_id')
        current_ctx.set(ctx=ctx)

        ctx.instance.runtime_properties['aws_resource_id'] = 'bad_id'
        ctx.instance.runtime_properties['private_dns_name'] = '0.0.0.0'
        ctx.instance.runtime_properties['public_dns_name'] = '0.0.0.0'
        ctx.instance.runtime_properties['public_ip_address'] = '0.0.0.0'
        ctx.instance.runtime_properties['ip'] = '0.0.0.0'
        ex = self.assertRaises(
            NonRecoverableError, instance.stop, ctx=ctx)
        self.assertIn('InvalidInstanceID', ex.message)

    @mock_ec2
    def test_terminate_bad_id(self):
        """ this tests that a terminate fails when given an
            invalid instance_id and the proper error is raised
        """

        ctx = self.mock_ctx('test_terminate_bad_id')
        current_ctx.set(ctx=ctx)

        ctx.instance.runtime_properties['aws_resource_id'] = 'bad_id'
        ctx.instance.runtime_properties['private_dns_name'] = '0.0.0.0'
        ctx.instance.runtime_properties['public_dns_name'] = '0.0.0.0'
        ctx.instance.runtime_properties['public_ip_address'] = '0.0.0.0'
        ctx.instance.runtime_properties['ip'] = '0.0.0.0'
        ex = self.assertRaises(NonRecoverableError,
                               instance.terminate, ctx=ctx)
        self.assertIn('InvalidInstanceID.NotFound', ex.message)

    @mock_ec2
    def test_run_instances_bad_subnet_id(self):
        """ This tests that the NonRecoverableError is triggered
            when an non existing subnet_id is included in the create
            statement
        """

        ctx = self.mock_ctx('test_run_instances_bad_subnet_id')
        ctx.node.properties['parameters']['subnet_id'] = 'test'
        current_ctx.set(ctx=ctx)

        ex = self.assertRaises(
            NonRecoverableError, instance.run_instances, ctx=ctx)
        self.assertIn('InvalidSubnetID.NotFound', ex.message)

    @mock_ec2
    def test_run_instances_external_resource(self):
        """ this tests that the instance create function adds
        the runtime_properties
        """
        ctx = self.mock_ctx('test_run_instances_external_resource')
        current_ctx.set(ctx=ctx)

        ec2_client = connection.EC2ConnectionClient().client()
        reservation = ec2_client.run_instances(
            TEST_AMI_IMAGE_ID, instance_type=TEST_INSTANCE_TYPE)
        instance_id = reservation.instances[0].id
        ctx.node.properties['use_external_resource'] = True
        ctx.node.properties['resource_id'] = instance_id
        instance.run_instances(ctx=ctx)
        self.assertIn('aws_resource_id',
                      ctx.instance.runtime_properties.keys())

    @mock_ec2
    def test_validation_external_resource(self):
        """ this tests that creation_validation raises an error
        when a use_external_resource is true but a bad instance_id
        is given.
        """
        ctx = self.mock_ctx('test_validation_external_resource')
        ctx.node.properties['use_external_resource'] = True
        ctx.node.properties['resource_id'] = 'bad_id'
        current_ctx.set(ctx=ctx)

        ex = self.assertRaises(
            NonRecoverableError, instance.creation_validation, ctx=ctx)
        self.assertIn(
            'External resource, but the supplied instance id',
            ex.message)

    @mock_ec2
    def test_validation_no_external_resource_is(self):
        """ this tests that creation_validation raises an error
        when a use_external_resource is false but a good instance_id
        is given.
        """
        ctx = self.mock_ctx('test_validation_no_external_resource_is')
        current_ctx.set(ctx=ctx)

        ec2_client = connection.EC2ConnectionClient().client()
        reservation = ec2_client.run_instances(
            TEST_AMI_IMAGE_ID, instance_type=TEST_INSTANCE_TYPE)
        instance_id = reservation.instances[0].id
        ctx.node.properties['use_external_resource'] = False
        ctx.node.properties['resource_id'] = instance_id
        ex = self.assertRaises(
            NonRecoverableError, instance.creation_validation, ctx=ctx)
        self.assertIn(
            'Not external resource, but the supplied',
            ex.message)

    @mock_ec2
    def test_no_instance_get_instance_from_id(self):
        """ this tests that a NonRecoverableError is thrown
        when a nonexisting instance_id is provided to the
        get_instance_from_id function
        """
        ctx = self.mock_ctx('test_no_instance_get_instance_from_id')
        current_ctx.set(ctx=ctx)

        instance_id = 'bad_id'
        ctx.instance.runtime_properties['aws_resource_id'] = instance_id
        output = instance._get_instance_from_id(instance_id)
        self.assertIsNone(output)

    @mock_ec2
    def test_get_private_dns_name(self):
        """ This checks that _get_instance_attribute
        sets the correct runtime property and it is an FQDN
        """

        ctx = self.mock_ctx('test_get_private_dns_name')
        current_ctx.set(ctx=ctx)

        ec2_client = connection.EC2ConnectionClient().client()
        reservation = ec2_client.run_instances(
            TEST_AMI_IMAGE_ID, instance_type=TEST_INSTANCE_TYPE)
        ctx.instance.runtime_properties['aws_resource_id'] = \
            reservation.instances[0].id
        property_name = 'private_dns_name'
        dns_name = instance._get_instance_attribute(
            property_name)
        self.assertRegexpMatches(dns_name, FQDN)

    @mock_ec2
    def test_get_all_instances_bad_id(self):
        """this checks that _get_all_instances returns None
        when there is no such instance.
        """

        ctx = self.mock_ctx('test_get_all_instances_bad_id')
        current_ctx.set(ctx=ctx)

        output = instance._get_all_instances(
            list_of_instance_ids='test_get_all_instances_bad_id')
        self.assertIsNone(output)

    @mock_ec2
    def test_get_instance_attribute_no_instance(self):
        """ This tests that _get_instance_attribute raises an
        error when use_external_resource is true and there
        is no such resource.
        """

        ctx = self.mock_ctx('test_get_private_dns_name')
        current_ctx.set(ctx=ctx)
        ctx.instance.runtime_properties['aws_resource_id'] = \
            'i-4339wSD9'
        ctx.node.properties['use_external_resource'] = True
        ex = self.assertRaises(
            NonRecoverableError,
            instance._get_instance_attribute,
            'state_code')
        self.assertIn(
            'External resource, but the supplied', ex.message)

    @mock_ec2
    def test_get_instance_parameters(self):
        """ This tests that the _get_instance_parameters
        function returns a dict with the correct structure.
        """

        ctx = self.mock_ctx(
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

    @mock_ec2
    def test_creation_validation_image_id(self):
        """This tests that creation validation gets to image_id
        it will return NonRecoverableError if the image_id
        doesn't exist.
        """

        ctx = self.mock_ctx('test_creation_validation_image_id')
        current_ctx.set(ctx=ctx)
        ctx.node.properties['image_id'] = 'abc'
        ctx.node.properties['instance_type'] = 'efg'
        with self.assertRaisesRegexp(
                NonRecoverableError,
                'Invalid id:'):
            instance.creation_validation(ctx=ctx)

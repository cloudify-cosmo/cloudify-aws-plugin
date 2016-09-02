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
import boto
import mock
from moto import mock_elb
from moto import mock_ec2

# Cloudify Imports is imported and used in operations
from cloudify.state import current_ctx
from cloudify_aws import constants
from cloudify.mocks import MockCloudifyContext
from cloudify_aws.ec2 import elasticloadbalancer
from cloudify.exceptions import NonRecoverableError


TEST_AMI_IMAGE_ID = 'ami-e214778a'
TEST_INSTANCE_TYPE = 't1.micro'


class TestLoadBalancer(testtools.TestCase):

    def setUp(self):
        super(TestLoadBalancer, self).setUp()

    def mock_elb_client_raise_NonRecoverableError(self):
        raise boto.exception.BotoClientError('fakeError')

    def mock_raise_BotoClientError(self, load_balancer_names):

        def Client():
            raise boto.exception.BotoClientError('fakeError')

        raise boto.exception.BotoClientError('fakeError')

    def _create_external_elb(self):
        return boto.connect_elb().create_load_balancer(
                name='myelb', zones='us-east-1a',
                listeners=[[80, 8080, 'http'], [443, 8443, 'tcp']])

    def _get_elbs(self):
        return boto.connect_elb().get_all_load_balancers(
                load_balancer_names=['myelb'])

    def _get_elb_instances(self):
        instance_list = boto.connect_elb().get_all_load_balancers(
                load_balancer_names=['myelb'])[0].instances
        l = []
        for i in instance_list:
            l.append(i.id)
        return l

    def _create_external_instance(self):
        return boto.connect_ec2().run_instances(
                image_id=TEST_AMI_IMAGE_ID, instance_type=TEST_INSTANCE_TYPE)

    def mock_instance_ctx(self, test_name, use_external_resource=False,
                          instance_id='i-nstance'):
        """ Creates a mock context for the instance
            tests
        """

        test_node_id = test_name
        test_properties = {
            constants.AWS_CONFIG_PROPERTY: {},
            'use_external_resource': use_external_resource,
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
        runtime_properties = {'aws_resource_id': instance_id}
        operation = {
            'retry_number': 0
        }

        ctx = MockCloudifyContext(
                node_id=test_node_id,
                properties=test_properties,
                operation=operation,
                runtime_properties=runtime_properties
        )
        ctx.node.type_hierarchy = ['cloudify.nodes.Compute']
        return ctx

    def mock_elb_ctx(self, test_name, use_external_resource=False,
                     elb_name='myelb', instance_list=[], resource_id='',
                     bad_health_checks=False):
        """ Creates a mock context for the elb
            tests
        """

        test_node_id = test_name
        test_properties = {
            constants.AWS_CONFIG_PROPERTY: {},
            'use_external_resource': use_external_resource,
            'resource_id': resource_id,
            'elb_name': elb_name,
            'listeners': [[80, 8080, 'http'], [443, 8443, 'tcp']],
            'zones': 'us-east-1a',
            'security_groups': ['sg-73cd3f1e'],
            'health_checks': [{'interval': '5',
                               'target': 'HTTP:8080/health',
                               'healthy_threshold': '3',
                               'timeout': '3',
                               'unhealthy_threshold': '5'}]
        }
        if bad_health_checks:
            test_properties['health_checks'] = [{'target': 'tp:321'}]
        runtime_properties = {'aws_resource_id': 'myelb',
                              'instance_list': instance_list}

        ctx = MockCloudifyContext(
                node_id=test_node_id,
                properties=test_properties,
                runtime_properties=runtime_properties
        )
        ctx.node.type_hierarchy = ['cloudify.nodes.LoadBalancer']

        return ctx

    def mock_relationship_context(self, testname, elb_context=None,
                                  instance_context=None,
                                  use_external_resource=False):
        """ Creates a mock relationship context for the elb
            tests
        """

        if not elb_context:
            elb_context = self.mock_elb_ctx(
                    'target_{0}'.format(testname),
                    use_external_resource=use_external_resource)

        if not instance_context:
            instance_context = self.mock_instance_ctx(
                    'source_{0}'.format(testname),
                    use_external_resource=use_external_resource)

        relationship_context = MockCloudifyContext(
                node_id=testname,
                source=instance_context,
                target=elb_context)

        return relationship_context

    def create_elb_for_checking(self):
        return elasticloadbalancer.Elb()

    def create_elbinstanceconnection_for_checking(self):
        return elasticloadbalancer.ElbInstanceConnection()

    @mock_elb
    def test_create_elb_with_health_check(self):
        ctx = self.mock_elb_ctx('test_create_elb')
        current_ctx.set(ctx=ctx)
        elasticloadbalancer.create(args=None, ctx=ctx)
        self.assertIsNotNone(ctx.instance.runtime_properties.get('elb_name'))
        self.assertIsNotNone(ctx.node.properties.get('health_checks'))

    @mock_elb
    def test_remove_elb(self):
        ctx = self.mock_elb_ctx('test_remove_elb')
        current_ctx.set(ctx=ctx)
        self._create_external_elb()
        elasticloadbalancer.delete(args=None, ctx=ctx)
        self.assertIsNone(ctx.instance.runtime_properties.get('elb_name'))

    @mock_ec2
    @mock_elb
    def test_add_instance_to_elb(self):
        self._create_external_elb()
        instance_id = self._create_external_instance().id
        instance_ctx = self.mock_instance_ctx(
                'source_test_add_instance_to_elb',
                instance_id=instance_id, use_external_resource=True)
        ctx = self.mock_relationship_context('test_add_instance_to_elb',
                                             use_external_resource=True,
                                             instance_context=instance_ctx)
        current_ctx.set(ctx=ctx)
        test_elbinstanceconnection = self \
            .create_elbinstanceconnection_for_checking()

        test_elbinstanceconnection.associate()
        self.assertEqual(1,
                         len(ctx.target.instance.runtime_properties.get(
                                 'instance_list')))
        self.assertIn(instance_id,
                      ctx.target.instance.runtime_properties.get(
                              'instance_list'))
        self.assertIn(instance_id, self._get_elb_instances())

    @mock_ec2
    @mock_elb
    def test_remove_instance_from_elb(self):
        self._create_external_elb()
        instance_id = self._create_external_instance().id
        instance_ctx = self.mock_instance_ctx(
                'source_test_remove_instance_from_elb',
                instance_id=instance_id, use_external_resource=True)
        elb_ctx = self.mock_elb_ctx(
                'source_test_remove_instance_from_elb',
                use_external_resource=True,
                instance_list=[instance_id])
        ctx = self.mock_relationship_context('test_remove_instance_from_elb',
                                             use_external_resource=True,
                                             instance_context=instance_ctx,
                                             elb_context=elb_ctx)
        current_ctx.set(ctx=ctx)
        elasticloadbalancer.ElbInstanceConnection().disassociate(ctx=ctx)
        self.assertEqual(0,
                         len(ctx.target.instance.runtime_properties.get(
                                 'instance_list')))

    @mock_ec2
    @mock_elb
    def test_delete_external_elb(self):
        elb_ctx = self.mock_elb_ctx(
                'test_delete_external_elb',
                use_external_resource=True,
                instance_list=[])
        current_ctx.set(elb_ctx)
        self.assertTrue(elasticloadbalancer.delete(args=None, ctx=elb_ctx))

    @mock_elb
    def test_validation_not_external(self):
        """ Tests that creation_validation raises an error
        the Elastic Load Balancer exists in the account and
        use_external_resource is false.
        """

        ctx = self.mock_elb_ctx('test_validation_not_external',
                                use_external_resource=False,
                                resource_id='myelb')
        self._create_external_elb()
        current_ctx.set(ctx=ctx)
        ex = self.assertRaises(NonRecoverableError,
                               elasticloadbalancer.creation_validation,
                               ctx=ctx)
        self.assertIn('Not external resource, but the supplied', ex.message)

    @mock_elb
    def test_client_error_create_elb(self):
        with mock.patch('cloudify_aws.connection.ELBConnectionClient',
                        new=self.mock_elb_client_raise_NonRecoverableError):
            ctx = self.mock_elb_ctx('test_client_error_get_elbs_by_names',
                                    use_external_resource=False,
                                    resource_id='myelb')
            current_ctx.set(ctx=ctx)
            self.assertRaises(boto.exception.BotoClientError,
                              elasticloadbalancer.create,
                              ctx=ctx)

    @mock_elb
    def test_client_error_add_health_check_to_elb(self, *_):
        with mock.patch('cloudify_aws.connection.ELBConnectionClient',
                        new=mock.Mock()):
            ctx = self.mock_elb_ctx('test_client_error_get_elbs_by_names',
                                    use_external_resource=False,
                                    resource_id='myelb')
            current_ctx.set(ctx=ctx)
            self.assertRaises(NonRecoverableError,
                              elasticloadbalancer.associate,
                              ctx=ctx)

    @mock_elb
    def test_create_elb_with_bad_health_check(self):
        ctx = self.mock_elb_ctx('test_create_elb', bad_health_checks=True)
        current_ctx.set(ctx=ctx)
        self.assertRaises(NonRecoverableError,
                          elasticloadbalancer.Elb().create,
                          ctx=ctx)

########
# Copyright (c) 2017 GigaSpaces Technologies Ltd. All rights reserved
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
from cloudify.state import current_ctx
from boto.ec2.ec2object import TaggedEC2Object

# Third Party Imports
import mock
from moto import mock_ec2
from cloudify_aws import constants
from cloudify_aws import utils
from cloudify_aws.base import AwsBaseNode
from cloudify.mocks import MockCloudifyContext
from cloudify.exceptions import NonRecoverableError

instance_arn_format = 'arn:aws:ec2:region:account-id:instance/instance-id'
subnet_arn_format = 'arn:aws:ec2:region:account-id:vpc/vpc-id'
bucket_arn_format = 'arn:aws:s3:::bucket_name'


class TestUtils(testtools.TestCase):

    def test_arn_split(self):
        self.assertEqual(len(utils.arn_split(instance_arn_format)), 7)
        self.assertEqual(len(utils.arn_split(subnet_arn_format)), 7)
        self.assertEqual(len(utils.arn_split(bucket_arn_format)), 6)

    def test_match_arn_to_arn_format(self):
        out = utils.match_arn_to_arn_format(instance_arn_format)
        self.assertEqual('instance-id', out.get('resource'))
        out = utils.match_arn_to_arn_format(subnet_arn_format)
        self.assertEqual('vpc-id', out.get('resource'))
        out = utils.match_arn_to_arn_format(bucket_arn_format)
        self.assertEqual('bucket_name', out.get('resource'))
        out = \
            utils.match_arn_to_arn_format(
                'jack:and:jill:went:up:the:hill:to:fetch:a:pale:of:water'
            )
        self.assertEqual({}, out)


class TestCloudifyAwsBase(testtools.TestCase):

    def get_mock_ctx(self, test_name, retry_number=0):
        """ Creates a mock context for the instance
            tests
        """
        test_node_id = test_name
        test_properties = {
            constants.AWS_CONFIG_PROPERTY: {},
            'use_external_resource': False,
            'resource_id': '{0}'.format(test_name)
        }

        operation = {
            'retry_number': retry_number
        }
        ctx = MockCloudifyContext(
                node_id=test_node_id,
                deployment_id=test_name,
                properties=test_properties,
                operation=operation,
                provider_context={'resources': {}}
        )
        ctx.node.type_hierarchy = ['cloudify.nodes.Root']
        return ctx

    @mock_ec2
    def test_base_operation_functions(self):
        ctx = self.get_mock_ctx('test_base_operation_functions')
        current_ctx.set(ctx=ctx)
        resource = AwsBaseNode('root', [], resource_states=[])
        # testing operations
        for operation in ('create', 'start', 'stop', 'delete'):
            function = getattr(resource, operation)
            output = function()
            self.assertEquals(False, output)

    @mock_ec2
    def test_base_operation_handler_functions(self):
        ctx = self.get_mock_ctx('test_base_operation_handler_functions')
        current_ctx.set(ctx=ctx)
        resource = AwsBaseNode('root', [], resource_states=[])

        with mock.patch('cloudify_aws.base.AwsBaseNode'
                        '.get_and_filter_resources_by_matcher') \
                as mock_get_and_filter_resources_by_matcher:
            mock_get_and_filter_resources_by_matcher.return_value = []

            for operation in ('create', 'start', 'stop', 'delete'):
                ctx.operation._operation_context['name'] = operation
                with mock.patch('cloudify_aws.base.AwsBaseNode.{0}'
                                .format(operation)):
                    function = getattr(resource, '{0}_helper'
                                       .format(operation))
                    output = function()
                    if operation in ('create_helper', 'start_helper',
                                     'modify_helper', 'stop_helper'):
                        self.assertIsNone(output)
                    elif operation == 'delete_helper':
                        self.assertEqual(output, True)

    @mock_ec2
    def test_base_operation_handler_functions_false(self):
        ctx = self.get_mock_ctx('test_base_operation_handler_functions_false')
        current_ctx.set(ctx=ctx)
        resource = AwsBaseNode('root', [], resource_states=[])

        with mock.patch('cloudify_aws.base.AwsBaseNode'
                        '.get_and_filter_resources_by_matcher') \
                as mock_get_and_filter_resources_by_matcher:
            mock_get_and_filter_resources_by_matcher.return_value = []

            for operation in ('create', 'start', 'stop', 'delete'):
                ctx.operation._operation_context['name'] = operation
                with mock.patch('cloudify_aws.base.AwsBaseNode.{0}'
                                .format(operation), return_value=False):
                    function = getattr(resource, '{0}_helper'
                                       .format(operation))
                    with self.assertRaisesRegexp(
                            NonRecoverableError,
                            'Neither external resource, nor Cloudify '
                            'resource'):
                        function()

            with mock.patch('cloudify_aws.base.AwsBaseNode.modify_attributes',
                            return_value=True):
                ctx.operation._operation_context['name'] = 'modify'
                function = getattr(resource, 'modify_helper')
                self.assertEqual(True, function({'key': 'value'}))

    @mock_ec2
    @mock.patch('boto.ec2.ec2object.TaggedEC2Object.add_tags')
    def test_tag_resource(self, *_):
        ctx = self.get_mock_ctx('test_tag_resource')
        current_ctx.set(ctx=ctx)
        resource = AwsBaseNode('root', [], resource_states=[])
        ctx.node.properties['name'] = 'root'
        test_resource = TaggedEC2Object()
        resource.tag_resource(test_resource)

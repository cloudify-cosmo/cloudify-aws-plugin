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
from ec2 import securitygroup
from cloudify.mocks import MockCloudifyContext


class TestSecurityGroup(testtools.TestCase):

    def security_group_mock(self, test_name, test_properties):
        """ Creates a mock context for security group tests
            with given properties
        """

        ctx = MockCloudifyContext(
            node_id=test_name,
            properties=test_properties
        )

        return ctx

    @testtools.skip
    def test_create(self):
        """ There are many places that this could fail,
            so I am first testing that everything works given
            really good input.
        """

        test_properties = {
            'resource_id': 'test_security_group',
            'description': 'This is a test.',
            'rules': [
                {
                    'ip_protocol': 'tcp',
                    'from_port': '22',
                    'to_port': '22',
                    'cidr_ip': '127.0.0.1/32'
                },
                {
                    'ip_protocol': 'tcp',
                    'from_port': '80',
                    'to_port': '80',
                    'cidr_ip': '127.0.0.1/32'
                }
            ]
        }

        ctx = self.security_group_mock('test_good_security_group_create',
                                       test_properties)

        with mock_ec2():
            securitygroup.create(ctx=ctx)

    @testtools.skip
    def test_delete(self):
        """ There are many places that this could fail,
            so I am first testing that everything works given
            really good input.
        """

        test_properties = {
            'resource_id': 'test',
            'description': 'this is test.',
        }

        ctx = self.security_group_mock('test_good_security_group_delete',
                                       test_properties)

        with mock_ec2():
            ec2_client = connection.EC2ConnectionClient().client()
            group = ec2_client.create_security_group('test',
                                                     'this is test')
            ctx.instance.runtime_properties['aws_resource_id'] = group.id
            securitygroup.delete(ctx=ctx)

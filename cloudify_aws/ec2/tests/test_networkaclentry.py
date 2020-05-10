# Copyright (c) 2018 Cloudify Platform Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Standard imports
import unittest

# Third party imports
from mock import patch, MagicMock

# Local imports
from cloudify_aws.common._compat import reload_module
from cloudify_aws.ec2.resources import networkaclentry
from cloudify_aws.common.tests.test_base import (
    TestBase,
    mock_decorator
)
from cloudify_aws.ec2.resources.networkaclentry import (
    EC2NetworkAclEntry,
    NETWORKACL_ID,
    RULE_NUMBER,
    NETWORKACLS,
    EGRESS,
    NETWORKACL_TYPE
)


class TestEC2NetworkAclEntry(TestBase):

    def setUp(self):
        self.networkaclentry = EC2NetworkAclEntry("ctx_node",
                                                  resource_id=True,
                                                  client=True, logger=None)
        mock1 = patch('cloudify_aws.common.decorators.aws_resource',
                      mock_decorator)
        mock1.start()
        reload_module(networkaclentry)

    def test_class_properties_by_filter(self):
        effect = self.get_client_error_exception(name='EC2 Network Acl Entry')
        self.networkaclentry.client = \
            self.make_client_function('describe_network_acls',
                                      side_effect=effect)
        config = {'NetworkAclIds': ['network acl']}
        res = self.networkaclentry.get_properties_by_filter(**config)
        self.assertIsNone(res)

        value = {}
        self.networkaclentry.client = \
            self.make_client_function('describe_network_acls',
                                      return_value=value)
        res = self.networkaclentry.get_properties_by_filter(**config)
        self.assertIsNone(res)

        value = {NETWORKACLS: [{NETWORKACL_ID: 'test_name'}]}
        self.networkaclentry.client = \
            self.make_client_function('describe_network_acls',
                                      return_value=value)
        res = self.networkaclentry.get_properties_by_filter(**config)
        self.assertEqual(res[NETWORKACL_ID], 'test_name')

    def test_class_create(self):
        value = True
        config = {NETWORKACL_ID: 'test'}
        self.networkaclentry.client = \
            self.make_client_function('create_network_acl_entry',
                                      return_value=value)
        res = self.networkaclentry.create(config)
        self.assertEqual(True, res)

    def test_class_replace(self):
        value = True
        config = {NETWORKACL_ID: 'test'}
        self.networkaclentry.client = \
            self.make_client_function('replace_network_acl_entry',
                                      return_value=value)
        res = self.networkaclentry.replace(config)
        self.assertEqual(True, res)

    def test_class_delete(self):
        params = {}
        self.networkaclentry.client = \
            self.make_client_function('delete_network_acl_entry')
        self.networkaclentry.delete(params)
        self.assertTrue(self.networkaclentry.client.delete_network_acl_entry
                        .called)

        params = {NETWORKACL_ID: 'networkaclentry'}
        self.networkaclentry.delete(params)
        self.assertEqual(params[NETWORKACL_ID], 'networkaclentry')

    def test_prepare(self):
        ctx = self.get_mock_ctx("NetworkAcl")
        config = {NETWORKACL_ID: 'network acl'}
        networkaclentry.prepare(ctx, config)
        self.assertEqual(ctx.instance.runtime_properties['resource_config'],
                         config)

    def test_create(self):
        ctx = self.get_mock_ctx("NetworkAcl")
        config = {NETWORKACL_ID: 'network acl',
                  RULE_NUMBER: 100, 'Protocol': '-1', 'RuleAction': 'allow',
                  EGRESS: False, 'CidrBlock': '0.0.0.0/0'}
        self.networkaclentry.resource_id = config[NETWORKACL_ID]
        iface = MagicMock()
        iface.create = self.mock_return(config)
        networkaclentry.create(ctx, iface, config)
        self.assertEqual(self.networkaclentry.resource_id,
                         'network acl')

    def test_create_exists(self):
        ctx = self.get_mock_ctx("NetworkAcl")
        config = {NETWORKACL_ID: 'network acl',
                  RULE_NUMBER: 100, 'Protocol': '-1', 'RuleAction': 'allow',
                  EGRESS: False, 'CidrBlock': '0.0.0.0/0'}
        self.networkaclentry.resource_id = config[NETWORKACL_ID]
        iface = MagicMock()
        iface.create = self.mock_return(config)
        prop = {NETWORKACL_ID: 'network acl',
                'Entries': [{RULE_NUMBER: 100, 'Protocol': '-1',
                             EGRESS: False}]}
        iface.get_properties_by_filter = self.mock_return(prop)
        networkaclentry.create(ctx, iface, config)
        self.assertEqual(self.networkaclentry.resource_id,
                         'network acl')

    def test_create_with_relationships(self):
        ctx = self.get_mock_ctx("NetworkAcl",
                                type_hierarchy=[NETWORKACL_TYPE])
        config = {}
        self.networkaclentry.resource_id = 'network acl'
        iface = MagicMock()
        iface.create = self.mock_return(config)
        with patch('cloudify_aws.common.utils.find_rel_by_node_type'):
            networkaclentry.create(ctx, iface, config)
            self.assertEqual(self.networkaclentry.resource_id,
                             'network acl')

    def test_delete(self):
        ctx = self.get_mock_ctx("NetworkAcl")
        iface = MagicMock()
        config = {NETWORKACL_ID: 'network acl', RULE_NUMBER: 100}
        ctx.instance.runtime_properties['egress'] = False
        networkaclentry.delete(ctx, iface, config)
        self.assertTrue(iface.delete.called)

    def test_delete_with_relationship(self):
        ctx = self.get_mock_ctx("NetworkAcl", type_hierarchy=[NETWORKACL_TYPE])
        iface = MagicMock()
        config = {RULE_NUMBER: 100}
        ctx.instance.runtime_properties['egress'] = False
        ctx.instance.runtime_properties['network_acl_id'] = 'network acl'
        with patch('cloudify_aws.common.utils.find_rel_by_node_type'):
            networkaclentry.delete(ctx, iface, config)
            self.assertTrue(iface.delete.called)


if __name__ == '__main__':
    unittest.main()

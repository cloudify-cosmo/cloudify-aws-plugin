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
from botocore.exceptions import UnknownServiceError

from cloudify.state import current_ctx
from cloudify.exceptions import NonRecoverableError

# Local imports
from cloudify_aws.common._compat import text_type
from cloudify_aws.rds.resources import instance
from cloudify_aws.common.tests.test_base import TestBase, CLIENT_CONFIG
from cloudify_aws.common.tests.test_base import DELETE_RESPONSE

# Constants
INSTANCE_TH = ['cloudify.nodes.Root',
               'cloudify.nodes.aws.rds.Instance']

NODE_PROPERTIES = {
    'use_external_resource': False,
    'resource_id': 'devdbinstance',
    'resource_config': {},
    'client_config': CLIENT_CONFIG
}

RUNTIME_PROPERTIES = {
    'resource_config': {
        'DBInstanceClass': 'db.t2.small',
        'Engine': 'mysql',
        'EngineVersion': '5.7.16',
        'AvailabilityZone': 'aq-testzone-1a',
        'StorageType': 'gp2',
        'AllocatedStorage': '10',
        'DBName': 'devdb',
        'MasterUsername': 'root',
        'MasterUserPassword': 'Password1234'
    }
}

RUNTIME_PROPERTIES_AFTER_CREATE = {
    'aws_resource_arn': 'DBInstanceArn',
    'aws_resource_id': 'devdbinstance',
    'resource_config': {
        'Engine': 'mysql',
        'AvailabilityZone': 'aq-testzone-1a',
        'MasterUsername': 'root',
        'MasterUserPassword': 'Password1234',
        'StorageType': 'gp2',
        'AllocatedStorage': '10',
        'EngineVersion': '5.7.16',
        'DBInstanceClass': 'db.t2.small',
        'DBName': 'devdb',
        'DBInstanceIdentifier': 'devdbinstance',
    }
}


class TestRDSInstance(TestBase):

    def setUp(self):
        super(TestRDSInstance, self).setUp()

        self.fake_boto, self.fake_client = self.fake_boto_client('rds')

        self.mock_patch = patch('boto3.client', self.fake_boto)
        self.mock_patch.start()

    def tearDown(self):
        self.mock_patch.stop()
        self.fake_boto = None
        self.fake_client = None

        super(TestRDSInstance, self).tearDown()

    def test_create_raises_UnknownServiceError(self):
        _test_name = 'test_create_UnknownServiceError'
        _test_node_properties = {
            'use_external_resource': False,
            'client_config': CLIENT_CONFIG
        }
        _test_runtime_properties = {
            'resource_config': {}
        }
        _ctx = self.get_mock_ctx(
            _test_name,
            test_properties=_test_node_properties,
            test_runtime_properties=_test_runtime_properties,
            type_hierarchy=INSTANCE_TH
        )
        current_ctx.set(_ctx)

        with self.assertRaises(UnknownServiceError) as error:
            instance.create(ctx=_ctx, resource_config=None, iface=None)

        self.assertEqual(
            text_type(error.exception),
            "Unknown service: 'rds'. Valid service names are: ['rds']"
        )

        self.fake_boto.assert_called_with('rds', aws_access_key_id='xxx',
                                          aws_secret_access_key='yyy',
                                          region_name='aq-testzone-1')

    def test_create(self):
        _test_name = 'test_create'
        _ctx = self.get_mock_ctx(
            _test_name,
            test_properties=NODE_PROPERTIES,
            test_runtime_properties=RUNTIME_PROPERTIES,
            type_hierarchy=INSTANCE_TH,
            ctx_operation_name='cloudify.interfaces.lifecycle.create',
        )
        current_ctx.set(_ctx)

        self.fake_client.create_db_instance = MagicMock(return_value={
            'DBInstance': {
                'DBInstanceIdentifier': 'devdbinstance',
                'DBInstanceArn': 'DBInstanceArn'
            }
        })

        self.fake_client.describe_db_instances = MagicMock(return_value={
            'DBInstances': [{
                'DBInstanceStatus': 'available'
            }]
        })

        instance.create(
            ctx=_ctx, resource_config=None, iface=None
        )

        self.fake_boto.assert_called_with(
            'rds', **CLIENT_CONFIG
        )
        self.fake_client.create_db_instance.assert_called_with(
            AllocatedStorage='10', AvailabilityZone='aq-testzone-1a',
            DBInstanceClass='db.t2.small',
            DBInstanceIdentifier='devdbinstance', DBName='devdb',
            Engine='mysql', EngineVersion='5.7.16',
            MasterUserPassword='Password1234', MasterUsername='root',
            StorageType='gp2'
        )
        self.fake_client.describe_db_instances.assert_called_with(
            DBInstanceIdentifier='devdbinstance'
        )
        # We are removing these
        self.assertEqual(
            _ctx.instance.runtime_properties['aws_resource_id'],
            RUNTIME_PROPERTIES_AFTER_CREATE['aws_resource_id']
        )
        self.assertEqual(
            _ctx.instance.runtime_properties['aws_resource_arn'],
            RUNTIME_PROPERTIES_AFTER_CREATE['aws_resource_arn']
        )

        self.assertEqual(
            _ctx.instance.runtime_properties['resource_config'],
            RUNTIME_PROPERTIES_AFTER_CREATE['resource_config']
        )

    def test_prepare(self):
        self._prepare_check(
            type_hierarchy=INSTANCE_TH,
            type_name='rds',
            type_class=instance
        )

    def test_delete(self):
        _test_name = 'test_delete'
        _ctx = self.get_mock_ctx(
            _test_name,
            test_properties=NODE_PROPERTIES,
            test_runtime_properties=RUNTIME_PROPERTIES_AFTER_CREATE,
            type_hierarchy=INSTANCE_TH,
            ctx_operation_name='cloudify.interfaces.lifecycle.delete'
        )
        current_ctx.set(_ctx)

        self.fake_client.delete_db_instance = self.mock_return(DELETE_RESPONSE)

        instance.delete(
            ctx=_ctx, resource_config=None, iface=None
        )

        self.fake_boto.assert_called_with(
            'rds', **CLIENT_CONFIG
        )
        self.fake_client.delete_db_instance.assert_called_with(
            DBInstanceIdentifier='devdbinstance', SkipFinalSnapshot=True
        )

        self.fake_client.describe_db_instances.assert_called_with(
            DBInstanceIdentifier='devdbinstance'
        )

        self.assertEqual(
            _ctx.instance.runtime_properties, {
                '__deleted': True,
            }
        )

    def _create_instance_relationships(self,
                                       node_id,
                                       type_hierarchy,
                                       op_name=None):
        _source_ctx = self.get_mock_ctx(
            'test_attach_source',
            test_properties={
                'client_config': CLIENT_CONFIG
            },
            test_runtime_properties={
                'resource_id': 'prepare_attach_source',
                'aws_resource_id': 'aws_resource_mock_id',
                '_set_changed': True,
                'resource_config': {}
            },
            type_hierarchy=INSTANCE_TH,
            ctx_operation_name=op_name
        )

        _target_ctx = self.get_mock_ctx(
            'test_attach_target',
            test_properties={},
            test_runtime_properties={
                'resource_id': 'prepare_attach_target',
                'aws_resource_id': 'aws_target_mock_id',
            },
            type_hierarchy=type_hierarchy,
            ctx_operation_name=op_name
        )

        _ctx = self.get_mock_relationship_ctx(
            node_id,
            test_properties={'client_config': CLIENT_CONFIG},
            test_runtime_properties={},
            test_source=_source_ctx,
            test_target=_target_ctx
        )

        return _source_ctx, _target_ctx, _ctx

    def test_prepare_assoc_SubnetGroup(self):
        _source_ctx, _target_ctx, _ctx = self._create_instance_relationships(
            'test_prepare_assoc',
            ['cloudify.nodes.Root', 'cloudify.nodes.aws.rds.SubnetGroup']
        )
        current_ctx.set(_ctx)

        instance.prepare_assoc(
            ctx=_ctx, resource_config=None, iface=None
        )
        self.assertEqual(
            _source_ctx.instance.runtime_properties, {
                '_set_changed': True,
                'aws_resource_id': 'aws_resource_mock_id',
                'resource_config': {
                    'DBSubnetGroupName': 'aws_target_mock_id'
                },
                'resource_id': 'prepare_attach_source'
            }
        )

    def test_prepare_assoc_OptionGroup(self):
        _source_ctx, _target_ctx, _ctx = self._create_instance_relationships(
            'test_prepare_assoc',
            ['cloudify.nodes.Root', 'cloudify.nodes.aws.rds.OptionGroup']
        )
        current_ctx.set(_ctx)

        instance.prepare_assoc(
            ctx=_ctx, resource_config=None, iface=None
        )
        self.assertEqual(
            _source_ctx.instance.runtime_properties, {
                '_set_changed': True,
                'aws_resource_id': 'aws_resource_mock_id',
                'resource_config': {
                    'OptionGroupName': 'aws_target_mock_id'
                },
                'resource_id': 'prepare_attach_source'
            }
        )

    def test_prepare_assoc_ParameterGroup(self):
        _source_ctx, _target_ctx, _ctx = self._create_instance_relationships(
            'test_prepare_assoc',
            ['cloudify.nodes.Root', 'cloudify.nodes.aws.rds.ParameterGroup']
        )
        current_ctx.set(_ctx)

        instance.prepare_assoc(
            ctx=_ctx, resource_config=None, iface=None
        )
        self.assertEqual(
            _source_ctx.instance.runtime_properties, {
                '_set_changed': True,
                'aws_resource_id': 'aws_resource_mock_id',
                'resource_config': {
                    'DBParameterGroupName': 'aws_target_mock_id'
                },
                'resource_id': 'prepare_attach_source'
            }
        )

    def test_prepare_assoc_SecurityGroup(self):
        _source_ctx, _target_ctx, _ctx = self._create_instance_relationships(
            'test_prepare_assoc',
            ['cloudify.nodes.Root', 'cloudify.nodes.aws.ec2.SecurityGroup'],
            op_name='cloudify.interfaces.relationship_lifecycle.establish'
        )
        current_ctx.set(_ctx)

        instance.prepare_assoc(
            ctx=_ctx, resource_config=None, iface=None
        )
        expected = {
            '_set_changed': True,
            'aws_resource_id': 'aws_resource_mock_id',
            'resource_config': {
                'VpcSecurityGroupIds': ['aws_target_mock_id']
            },
            'resource_id': 'prepare_attach_source'
        }
        self.assertEqual(
            expected,
            _source_ctx.instance.runtime_properties,
        )

    def test_prepare_assoc_Role_NonRecoverableError(self):
        _source_ctx, _target_ctx, _ctx = self._create_instance_relationships(
            'test_prepare_assoc',
            ['cloudify.nodes.Root', 'cloudify.nodes.aws.iam.Role']
        )
        current_ctx.set(_ctx)

        with self.assertRaises(NonRecoverableError) as error:
            instance.prepare_assoc(
                ctx=_ctx, resource_config=None, iface=None
            )
        self.assertEqual(
            text_type(error.exception),
            (
                'Missing required relationship inputs ' +
                '"iam_role_type_key" and/or "iam_role_id_key".'
            )
        )

    def test_prepare_assoc_Role(self):
        _source_ctx, _target_ctx, _ctx = self._create_instance_relationships(
            'test_prepare_assoc',
            ['cloudify.nodes.Root', 'cloudify.nodes.aws.iam.Role']
        )
        current_ctx.set(_ctx)

        _target_ctx.instance.runtime_properties[
            'iam_role_id_key'] = 'role_field'
        instance.prepare_assoc(
            ctx=_ctx, resource_config=None, iface=None,
            iam_role_type_key='iam_role_type_key',
            iam_role_id_key='iam_role_id_key'
        )
        self.assertEqual(
            _source_ctx.instance.runtime_properties, {
                '_set_changed': True,
                'aws_resource_id': 'aws_resource_mock_id',
                'resource_config': {
                    'iam_role_type_key': 'role_field'
                },
                'resource_id': 'prepare_attach_source'
            }
        )

    def test_detach_from_Role(self):
        _source_ctx, _target_ctx, _ctx = self._create_instance_relationships(
            'test_detach_from',
            ['cloudify.nodes.Root', 'cloudify.nodes.aws.iam.Role']
        )
        current_ctx.set(_ctx)

        instance.detach_from(
            ctx=_ctx, resource_config=None, iface=None
        )
        self.assertEqual(
            _source_ctx.instance.runtime_properties, {
                '_set_changed': True,
                'aws_resource_id': 'aws_resource_mock_id',
                'resource_config': {},
                'resource_id': 'prepare_attach_source'
            }
        )


if __name__ == '__main__':
    unittest.main()

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
from cloudify_aws.rds.resources import instance_read_replica
from cloudify_aws.common.tests.test_base import TestBase, CLIENT_CONFIG
from cloudify_aws.common.tests.test_base import DELETE_RESPONSE

# Constants
INSTANCE_READ_REPLICA_TH = ['cloudify.nodes.Root',
                            'cloudify.nodes.aws.rds.InstanceReadReplica']

NODE_PROPERTIES = {
    'use_external_resource': False,
    'resource_id': 'devdbinstance-replica',
    'resource_config': {
        'kwargs': {
            'DBInstanceClass': 'db.t2.small',
            'AvailabilityZone': 'aq-testzone-1a'
        }
    },
    'client_config': CLIENT_CONFIG
}

RUNTIME_PROPERTIES = {
    'resource_config': {
        'DBInstanceClass': 'db.t2.small',
        'AvailabilityZone': 'aq-testzone-1a'
    }
}

RUNTIME_PROPERTIES_AFTER_CREATE = {
    'aws_resource_arn': 'DBInstanceArn',
    'aws_resource_id': 'devdbinstance',
    'resource_config': {
        'DBInstanceClass': 'db.t2.small',
        'AvailabilityZone': 'aq-testzone-1a',
    }
}


class TestRDSInstanceReadReplica(TestBase):

    def setUp(self):
        super(TestRDSInstanceReadReplica, self).setUp()

        self.fake_boto, self.fake_client = self.fake_boto_client('rds')

        self.mock_patch = patch('boto3.client', self.fake_boto)
        self.mock_patch.start()

    def tearDown(self):
        self.mock_patch.stop()
        self.fake_boto = None
        self.fake_client = None

        super(TestRDSInstanceReadReplica, self).tearDown()

    def test_create_raises_UnknownServiceError(self):
        _test_name = 'test_create_UnknownServiceError'
        _test_runtime_properties = {
            'resource_config': {}
        }
        _ctx = self.get_mock_ctx(
            _test_name,
            test_properties=NODE_PROPERTIES,
            test_runtime_properties=_test_runtime_properties,
            type_hierarchy=INSTANCE_READ_REPLICA_TH,
            ctx_operation_name='cloudify.interfaces.lifecycle.create',
        )
        current_ctx.set(_ctx)

        with self.assertRaises(UnknownServiceError) as error:
            instance_read_replica.create(
                ctx=_ctx, resource_config=None, iface=None
            )

        self.assertEqual(
            text_type(error.exception),
            "Unknown service: 'rds'. Valid service names are: ['rds']"
        )

        self.fake_boto.assert_called_with('rds', **CLIENT_CONFIG)

    def test_create(self):
        _test_name = 'test_create'
        _ctx = self.get_mock_ctx(
            _test_name,
            test_properties=NODE_PROPERTIES,
            test_runtime_properties=RUNTIME_PROPERTIES,
            type_hierarchy=INSTANCE_READ_REPLICA_TH,
            ctx_operation_name='cloudify.interfaces.lifecycle.create',
        )
        current_ctx.set(_ctx)

        self.fake_client.create_db_instance_read_replica = MagicMock(
            return_value={
                'DBInstance': {
                    'DBInstanceIdentifier': 'devdbinstance',
                    'DBInstanceArn': 'DBInstanceArn'
                }
            }
        )

        self.fake_client.describe_db_instances = MagicMock(return_value={
            'DBInstances': [{
                'DBInstanceStatus': 'available'
            }]
        })

        instance_read_replica.create(
            ctx=_ctx, resource_config=None, iface=None
        )

        self.fake_boto.assert_called_with(
            'rds', **CLIENT_CONFIG
        )
        self.fake_client.create_db_instance_read_replica.assert_called_with(
            AvailabilityZone='aq-testzone-1a',
            DBInstanceClass='db.t2.small',
            DBInstanceIdentifier='devdbinstance-replica'
        )
        self.fake_client.describe_db_instances.assert_called_with(
            DBInstanceIdentifier='devdbinstance'
        )
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
            type_hierarchy=INSTANCE_READ_REPLICA_TH,
            type_name='rds',
            type_class=instance_read_replica
        )

    def test_delete(self):
        _test_name = 'test_delete'
        _ctx = self.get_mock_ctx(
            _test_name,
            test_properties=NODE_PROPERTIES,
            test_runtime_properties=RUNTIME_PROPERTIES_AFTER_CREATE,
            type_hierarchy=INSTANCE_READ_REPLICA_TH,
            ctx_operation_name='cloudify.interfaces.lifecycle.delete'
        )
        current_ctx.set(_ctx)

        self.fake_client.delete_db_instance = self.mock_return(DELETE_RESPONSE)

        instance_read_replica.delete(
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

    def test_prepare_assoc_SubnetGroup(self):
        _source_ctx, _target_ctx, _ctx = self._create_common_relationships(
            'test_prepare_assoc',
            source_type_hierarchy=INSTANCE_READ_REPLICA_TH,
            target_type_hierarchy=['cloudify.nodes.Root',
                                   'cloudify.nodes.aws.rds.SubnetGroup']
        )
        current_ctx.set(_ctx)
        inputs = dict(
            iam_role_id_key='foo',
            iam_role_type_key='bar'
        )
        instance_read_replica.prepare_assoc(
            ctx=_ctx, resource_config=None, iface=None, inputs=inputs
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
        _source_ctx, _target_ctx, _ctx = self._create_common_relationships(
            'test_prepare_assoc',
            source_type_hierarchy=INSTANCE_READ_REPLICA_TH,
            target_type_hierarchy=['cloudify.nodes.Root',
                                   'cloudify.nodes.aws.rds.OptionGroup']
        )
        current_ctx.set(_ctx)

        instance_read_replica.prepare_assoc(
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

    def test_prepare_assoc_Instance(self):
        _source_ctx, _target_ctx, _ctx = self._create_common_relationships(
            'test_prepare_assoc',
            source_type_hierarchy=INSTANCE_READ_REPLICA_TH,
            target_type_hierarchy=['cloudify.nodes.Root',
                                   'cloudify.nodes.aws.rds.Instance']
        )
        current_ctx.set(_ctx)

        instance_read_replica.prepare_assoc(
            ctx=_ctx, resource_config=None, iface=None
        )
        self.assertEqual(
            _source_ctx.instance.runtime_properties, {
                '_set_changed': True,
                'aws_resource_id': 'aws_resource_mock_id',
                'resource_config': {
                    'SourceDBInstanceIdentifier': 'aws_target_mock_id'
                },
                'resource_id': 'prepare_attach_source'
            }
        )

    def test_prepare_assoc_Role_NonRecoverableError(self):
        _source_ctx, _target_ctx, _ctx = self._create_common_relationships(
            'test_prepare_assoc',
            source_type_hierarchy=INSTANCE_READ_REPLICA_TH,
            target_type_hierarchy=['cloudify.nodes.Root',
                                   'cloudify.nodes.aws.iam.Role']
        )
        current_ctx.set(_ctx)

        with self.assertRaises(NonRecoverableError) as error:
            instance_read_replica.prepare_assoc(
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
        _source_ctx, _target_ctx, _ctx = self._create_common_relationships(
            'test_prepare_assoc',
            source_type_hierarchy=INSTANCE_READ_REPLICA_TH,
            target_type_hierarchy=['cloudify.nodes.Root',
                                   'cloudify.nodes.aws.iam.Role']
        )
        current_ctx.set(_ctx)

        _target_ctx.instance.runtime_properties[
            'iam_role_id_key'] = 'role_field'
        instance_read_replica.prepare_assoc(
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

    def test_detach_from_Instance(self):
        _source_ctx, _target_ctx, _ctx = self._create_common_relationships(
            'test_detach_from',
            source_type_hierarchy=INSTANCE_READ_REPLICA_TH,
            target_type_hierarchy=['cloudify.nodes.Root',
                                   'cloudify.nodes.aws.rds.Instance']
        )
        current_ctx.set(_ctx)

        instance_read_replica.detach_from(
            ctx=_ctx, resource_config=None, iface=None
        )
        self.assertEqual(
            _source_ctx.instance.runtime_properties, {
                'resource_id': 'prepare_attach_source',
                'aws_resource_id': 'aws_resource_mock_id',
                '_set_changed': True,
                'resource_config': {}
            }
        )


if __name__ == '__main__':
    unittest.main()

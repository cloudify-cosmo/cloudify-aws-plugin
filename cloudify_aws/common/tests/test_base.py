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

import copy
import unittest
from functools import wraps

from mock import MagicMock, patch

from botocore.exceptions import ClientError
from botocore.exceptions import UnknownServiceError

from cloudify.state import current_ctx
from cloudify.mocks import MockCloudifyContext
from cloudify.manager import DirtyTrackingDict
from cloudify.constants import RELATIONSHIP_INSTANCE

from cloudify_aws.common import AWSResourceBase
from cloudify_aws.common._compat import text_type


CLIENT_CONFIG = {
    'aws_access_key_id': 'xxx',
    'aws_secret_access_key': 'yyy',
    'region_name': 'aq-testzone-1'
}

DELETE_RESPONSE = {
    'ResponseMetadata': {
        'RetryAttempts': 0,
        'HTTPStatusCode': 200,
        'RequestId': 'xxxxxxxx',
        'HTTPHeaders': {
            'x-amzn-requestid': 'xxxxxxxx',
            'date': 'Fri, 28 Apr 2017 14:21:50 GMT',
            'content-length': '217',
            'content-type': 'text/xml'
        }
    }
}

DEFAULT_NODE_PROPERTIES = {
    'use_external_resource': False,
    'resource_config': {},
    'client_config': CLIENT_CONFIG
}

DEFAULT_RUNTIME_PROPERTIES = {
    'aws_resource_id': 'aws_resource',
    'resource_config': {},
}


def mock_decorator(*args, **kwargs):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            return f(*args, **kwargs)
        return decorated_function
    return decorator


class MockRelationshipContext(MockCloudifyContext):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._type = RELATIONSHIP_INSTANCE
        self._type_hierarchy = []

    @property
    def type(self):
        return 'relationship-instance'

    @property
    def type_hierarchy(self):
        return self._type_hierarchy

    @type_hierarchy.setter
    def type_hierarchy(self, value):
        self._type_hierarchy = value


class SpecialMockCloudifyContext(MockCloudifyContext):

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._plugin = MagicMock(properties={})

    @property
    def plugin(self):
        return self._plugin


class TestBase(unittest.TestCase):

    sleep_mock = None

    def setUp(self):
        super(TestBase, self).setUp()
        mock_sleep = MagicMock()
        self.sleep_mock = patch('time.sleep', mock_sleep)
        self.sleep_mock.start()
        self.maxDiff = None

    def tearDown(self):
        if self.sleep_mock:
            self.sleep_mock.stop()
            self.sleep_mock = None
        current_ctx.clear()
        super(TestBase, self).tearDown()

    def _to_DirtyTrackingDict(self, origin):
        if not origin:
            origin = {}
        dirty_dict = DirtyTrackingDict(origin)
        for k in origin:
            dirty_dict[k] = copy.deepcopy(origin[k])
        return dirty_dict

    def get_mock_ctx(self,
                     test_name,
                     test_properties=None,
                     test_runtime_properties=None,
                     test_relationships=None,
                     type_hierarchy=None,
                     type_node=None,
                     ctx_operation_name=None):

        type_node = type_node or 'cloudify.nodes.Root'

        operation_ctx = {
            'retry_number': 0,
            'name': 'cloudify.interfaces.lifecycle.configure'
        } if not ctx_operation_name else {
            'retry_number': 0, 'name': ctx_operation_name
        }
        test_properties = test_properties or {
            'client_config': {
                'region_name': 'us-foobar-1'
            }
        }
        if 'use_external_resource' not in test_properties:
            test_properties['use_external_resource'] = False
        if 'create_if_missing' not in test_properties:
            test_properties['create_if_missing'] = False
        if 'modify_external_resource' not in test_properties:
            test_properties['modify_external_resource'] = True

        test_runtime_properties = test_runtime_properties or {}

        ctx = SpecialMockCloudifyContext(
            node_id=test_name,
            node_name=test_name,
            deployment_id=test_name,
            properties=copy.deepcopy(test_properties),
            runtime_properties=self._to_DirtyTrackingDict(
                copy.deepcopy(test_runtime_properties)),
            relationships=test_relationships,
            operation=operation_ctx,
        )

        ctx.node._type = type_node
        ctx.node.type_hierarchy = type_hierarchy or ['cloudify.nodes.Root']
        ctx.instance.refresh = MagicMock()
        return ctx

    def get_mock_relationship_ctx(self,
                                  deployment_name,
                                  test_properties={},
                                  test_runtime_properties={},
                                  test_source=None,
                                  test_target=None):

        ctx = MockRelationshipContext(
            deployment_id=deployment_name,
            properties=copy.deepcopy(test_properties),
            source=test_source,
            target=test_target,
            runtime_properties=copy.deepcopy(test_runtime_properties))
        return ctx

    def _gen_client_error(self, name,
                          code='InvalidOptionGroupStateFault',
                          message='SomeThingIsGoingWrong'):
        return MagicMock(
            side_effect=ClientError(
                error_response={"Error": {
                    'Code': code,
                    'Message': message
                }},
                operation_name="client_error_" + name
            )
        )

    def _get_unknowservice(self, client_type):
        return MagicMock(
            side_effect=UnknownServiceError(
                service_name=client_type,
                known_service_names=['rds']
            )
        )

    def _fake_efs(self, fake_client, client_type):
        fake_client.describe_file_systems = self._gen_client_error(
            "describe_file_systems"
        )
        fake_client.describe_mount_targets = self._gen_client_error(
            "describe_mount_targets"
        )
        fake_client.describe_tags = self._gen_client_error(
            "describe_tags"
        )

        fake_client.create_file_system = self._get_unknowservice(client_type)
        fake_client.create_mount_target = self._get_unknowservice(client_type)
        fake_client.create_tags = self._get_unknowservice(client_type)

        fake_client.delete_mount_target = self._get_unknowservice(client_type)
        fake_client.delete_tags = self._get_unknowservice(client_type)
        fake_client.delete_file_system = self._get_unknowservice(client_type)

    def _fake_autoscaling(self, fake_client, client_type):
        fake_client.describe_auto_scaling_groups = self._gen_client_error(
            "describe_auto_scaling_groups"
        )
        fake_client.describe_launch_configurations = self._gen_client_error(
            "describe_launch_configurations"
        )
        fake_client.describe_lifecycle_hooks = self._gen_client_error(
            "describe_lifecycle_hooks"
        )
        fake_client.describe_policies = self._gen_client_error(
            "describe_policies"
        )

        fake_client.create_auto_scaling_group = self._get_unknowservice(
            client_type
        )
        fake_client.create_launch_configuration = self._get_unknowservice(
            client_type
        )
        fake_client.put_lifecycle_hook = self._get_unknowservice(client_type)
        fake_client.put_scaling_policy = self._get_unknowservice(client_type)

        fake_client.delete_auto_scaling_group = self._get_unknowservice(
            client_type
        )
        fake_client.update_auto_scaling_group = self._get_unknowservice(
            client_type
        )
        fake_client.delete_launch_configuration = self._get_unknowservice(
            client_type
        )
        fake_client.delete_lifecycle_hook = self._get_unknowservice(
            client_type
        )
        fake_client.delete_policy = self._get_unknowservice(client_type)
        fake_client.detach_instances = self._get_unknowservice(client_type)

    def _fake_cloudwatch(self, fake_client, client_type):
        fake_client.put_metric_alarm = self._get_unknowservice(client_type)
        fake_client.describe_alarms = self._gen_client_error(
            "describe_alarms"
        )
        fake_client.delete_alarms = self._get_unknowservice(client_type)

    def _fake_events(self, fake_client, client_type):
        fake_client.put_events = self._get_unknowservice(client_type)
        fake_client.put_rule = self._get_unknowservice(client_type)
        fake_client.put_targets = self._get_unknowservice(client_type)

        fake_client.describe_rule = self._gen_client_error(
            "describe_alarms"
        )

        fake_client.delete_rule = self._get_unknowservice(client_type)
        fake_client.remove_targets = self._get_unknowservice(client_type)

    def _fake_dynamodb(self, fake_client, client_type):
        fake_client.create_table = self._get_unknowservice(client_type)

        fake_client.describe_table = self._gen_client_error(
            "describe_table"
        )

        fake_client.delete_table = self._get_unknowservice(client_type)

    def _fake_iam(self, fake_client, client_type):
        fake_client.add_user_to_group = self._get_unknowservice(client_type)
        fake_client.attach_group_policy = self._get_unknowservice(client_type)
        fake_client.attach_role_policy = self._get_unknowservice(client_type)
        fake_client.attach_user_policy = self._get_unknowservice(client_type)
        fake_client.create_access_key = self._get_unknowservice(client_type)
        fake_client.create_group = self._get_unknowservice(client_type)
        fake_client.create_login_profile = self._get_unknowservice(client_type)
        fake_client.create_policy = self._get_unknowservice(client_type)
        fake_client.create_role = self._get_unknowservice(client_type)
        fake_client.create_user = self._get_unknowservice(client_type)
        fake_client.put_role_policy = self._get_unknowservice(client_type)

        fake_client.delete_access_key = self._get_unknowservice(client_type)
        fake_client.delete_group = self._get_unknowservice(client_type)
        fake_client.delete_login_profile = self._get_unknowservice(client_type)
        fake_client.delete_policy = self._get_unknowservice(client_type)
        fake_client.delete_role = self._get_unknowservice(client_type)
        fake_client.delete_user = self._get_unknowservice(client_type)
        fake_client.detach_group_policy = self._get_unknowservice(client_type)
        fake_client.detach_role_policy = self._get_unknowservice(client_type)
        fake_client.detach_user_policy = self._get_unknowservice(client_type)
        fake_client.delete_role_policy = self._get_unknowservice(client_type)

        fake_client.get_group = self._gen_client_error("get_group")
        fake_client.get_login_profile = self._gen_client_error(
            "get_login_profile"
        )
        fake_client.get_policy = self._gen_client_error("get_policy")
        fake_client.get_role = self._gen_client_error("get_role")
        fake_client.get_user = self._gen_client_error("get_user")

        fake_client.remove_user_from_group = self._get_unknowservice(
            client_type
        )
        fake_client.update_login_profile = self._get_unknowservice(client_type)

    def _fake_kms(self, fake_client, client_type):
        fake_client.create_alias = self._get_unknowservice(client_type)
        fake_client.create_grant = self._get_unknowservice(client_type)
        fake_client.create_key = self._get_unknowservice(client_type)

        fake_client.describe_key = self._gen_client_error(
            "describe_key"
        )

        fake_client.enable_key = self._get_unknowservice(client_type)
        fake_client.disable_key = self._get_unknowservice(client_type)

        fake_client.delete_alias = self._get_unknowservice(client_type)
        fake_client.revoke_grant = self._get_unknowservice(client_type)
        fake_client.schedule_key_deletion = self._get_unknowservice(
            client_type
        )

    def _fake_sqs(self, fake_client, client_type):
        fake_client.create_queue = self._get_unknowservice(
            client_type
        )

        fake_client.list_queues = self._gen_client_error(
            "list_queues"
        )

        fake_client.get_queue_attributes = self._gen_client_error(
            "list_queues"
        )

        fake_client.delete_queue = self._get_unknowservice(client_type)

    def _fake_s3(self, fake_client, client_type):
        fake_client.create_bucket = self._get_unknowservice(
            client_type
        )

        fake_client.delete_bucket = self._get_unknowservice(
            client_type
        )

    def _fake_elb(self, fake_client, client_type):
        fake_client.create_load_balancer = self._get_unknowservice(
            client_type
        )
        fake_client.delete_load_balancer = self._get_unknowservice(
            client_type
        )
        fake_client.describe_load_balancers = self._get_unknowservice(
            client_type
        )
        fake_client.modify_load_balancer_attributes = self._get_unknowservice(
            client_type
        )
        fake_client.register_instances_with_load_balancer = \
            self._get_unknowservice(client_type)
        fake_client.deregister_instances_from_load_balancer = \
            self._get_unknowservice(client_type)
        fake_client.create_load_balancer_policy = self._get_unknowservice(
            client_type
        )
        fake_client.create_lb_cookie_stickiness_policy = \
            self._get_unknowservice(client_type)
        fake_client.set_load_balancer_policies_of_listener = \
            self._get_unknowservice(client_type)
        fake_client.delete_load_balancer_policy = self._get_unknowservice(
            client_type
        )

    def _fake_elbv2(self, fake_client, client_type):
        fake_client.create_load_balancer = self._get_unknowservice(
            client_type
        )
        fake_client.delete_load_balancer = self._get_unknowservice(
            client_type
        )
        fake_client.describe_load_balancers = self._get_unknowservice(
            client_type
        )
        fake_client.modify_load_balancer_attributes = self._get_unknowservice(
            client_type
        )

    def _fake_rds(self, fake_client, client_type):

        fake_client.create_db_instance_read_replica = self._get_unknowservice(
            client_type
        )
        fake_client.create_db_instance = self._get_unknowservice(client_type)
        fake_client.create_db_parameter_group = self._get_unknowservice(
            client_type
        )
        fake_client.create_db_subnet_group = self._get_unknowservice(
            client_type
        )
        fake_client.create_option_group = self._get_unknowservice(client_type)

        fake_client.describe_db_parameter_groups = self._gen_client_error(
            "db_parameter_groups"
        )
        fake_client.describe_db_subnet_groups = self._gen_client_error(
            "db_subnet_groups"
        )
        fake_client.describe_option_groups = self._gen_client_error(
            "option_groups"
        )
        fake_client.describe_db_instances = self._gen_client_error(
            "db_instances"
        )

        fake_client.modify_db_parameter_group = self._get_unknowservice(
            client_type
        )
        fake_client.modify_option_group = self._get_unknowservice(
            client_type
        )

        fake_client.delete_db_instance = self._get_unknowservice(
            client_type
        )
        fake_client.delete_db_parameter_group = self._get_unknowservice(
            client_type
        )
        fake_client.delete_db_subnet_group = self._get_unknowservice(
            client_type
        )
        fake_client.delete_option_group = self._get_unknowservice(client_type)

    def _fake_codepipeline(self, fake_client, client_type):
        fake_client.create_pipeline = self._get_unknowservice(client_type)

        fake_client.get_pipeline_state = self._gen_client_error(
            "get_pipeline_state"
        )

        fake_client.delete_pipeline = self._get_unknowservice(client_type)

    def _fake_cloudformation(self, fake_client, client_type):

        fake_client.list_stack_resources = self._gen_client_error(
            "list_stack_resources"
        )
        fake_client.describe_stack_resource_drifts = self._gen_client_error(
            "describe_stack_resource_drifts"
        )

    def make_client_function(self, fun_name,
                             return_value=None,
                             side_effect=None,
                             client=None):

        if client:
            fake_client = client
        else:
            fake_client = MagicMock()
        fun = getattr(fake_client, fun_name)
        if side_effect:
            fun.side_effect = side_effect
        else:
            fun.return_value = return_value

        return fake_client

    def get_client_error_exception(self, name="Error"):
        return ClientError(error_response={"Error": {}},
                           operation_name=name)

    def get_unknown_service_exception(self, name="Error"):
        return UnknownServiceError(
            service_name=name,
            known_service_names=[name])

    def fake_boto_client(self, client_type):
        fake_client = MagicMock()

        if client_type == "rds":
            self._fake_rds(fake_client, client_type)
        elif client_type == "sqs":
            self._fake_sqs(fake_client, client_type)
        elif client_type == "kms":
            self._fake_kms(fake_client, client_type)
        elif client_type == "iam":
            self._fake_iam(fake_client, client_type)
        elif client_type == "dynamodb":
            self._fake_dynamodb(fake_client, client_type)
        elif client_type == "events":
            self._fake_events(fake_client, client_type)
        elif client_type == "cloudwatch":
            self._fake_cloudwatch(fake_client, client_type)
        elif client_type == "autoscaling":
            self._fake_autoscaling(fake_client, client_type)
        elif client_type == "efs":
            self._fake_efs(fake_client, client_type)
        elif client_type == "s3":
            self._fake_s3(fake_client, client_type)
        elif client_type == "elb":
            self._fake_elb(fake_client, client_type)
        elif client_type == "elbv2":
            self._fake_elbv2(fake_client, client_type)
        elif client_type == "codepipeline":
            self._fake_codepipeline(fake_client, client_type)
        elif client_type == "cloudformation":
            self._fake_cloudformation(fake_client, client_type)

        return MagicMock(return_value=fake_client), fake_client

    def mock_return(self, value):
        return MagicMock(return_value=value)

    def _prepare_create_raises_UnknownServiceError(
        self, type_hierarchy, type_name, type_class,
        type_node='cloudify.nodes.Root', operation_name=None,
    ):
        _ctx = self.get_mock_ctx(
            'test_create',
            test_properties=DEFAULT_NODE_PROPERTIES,
            test_runtime_properties=DEFAULT_RUNTIME_PROPERTIES,
            type_hierarchy=type_hierarchy,
            type_node=type_node,
            ctx_operation_name=operation_name,
        )

        current_ctx.set(_ctx)
        fake_boto, fake_client = self.fake_boto_client(type_name)

        with patch('boto3.client', fake_boto):
            with self.assertRaises(UnknownServiceError) as error:
                type_class.create(ctx=_ctx, resource_config=None, iface=None)

            self.assertEqual(
                text_type(error.exception),
                (
                    "Unknown service: '" +
                    type_name +
                    "'. Valid service names are: ['rds']"
                )
            )

            if type_name == 'iam':
                return fake_boto
            else:
                fake_boto.assert_called_with(type_name, **CLIENT_CONFIG)

    def _create_common_relationships(self,
                                     node_id,
                                     source_type_hierarchy,
                                     target_type_hierarchy,
                                     source_node_id=None,
                                     target_node_id=None,
                                     source_node_properties=None,
                                     target_node_properties=None,):
        _source_ctx = self.get_mock_ctx(
            source_node_id or 'test_attach_source',
            test_properties=source_node_properties or {
                'client_config': CLIENT_CONFIG
            },
            test_runtime_properties={
                'resource_id': 'prepare_attach_source',
                'aws_resource_id': 'aws_resource_mock_id',
                '_set_changed': True,
                'resource_config': {}
            },
            type_hierarchy=source_type_hierarchy
        )

        _target_ctx = self.get_mock_ctx(
            target_node_id or 'test_attach_target',
            test_properties=target_node_properties or {},
            test_runtime_properties={
                'resource_id': 'prepare_attach_target',
                'aws_resource_id': 'aws_target_mock_id',
                'aws_resource_arn': 'aws_resource_mock_arn'
            },
            type_hierarchy=target_type_hierarchy
        )

        _ctx = self.get_mock_relationship_ctx(
            node_id,
            test_properties={},
            test_runtime_properties={},
            test_source=_source_ctx,
            test_target=_target_ctx
        )

        return _source_ctx, _target_ctx, _ctx

    def _prepare_check(self, type_hierarchy, type_name, type_class):
        _ctx = self.get_mock_ctx(
            'test_prepare',
            test_properties=DEFAULT_NODE_PROPERTIES,
            test_runtime_properties=DEFAULT_RUNTIME_PROPERTIES,
            type_hierarchy=type_hierarchy,
            ctx_operation_name='cloudify.interfaces.lifecycle.create'
        )

        current_ctx.set(_ctx)
        fake_boto, fake_client = self.fake_boto_client(type_name)
        iface = MagicMock()
        with patch('boto3.client', fake_boto):
            type_class.prepare(ctx=_ctx, resource_config={}, iface=iface)

            self.assertEqual(
                _ctx.instance.runtime_properties, {
                    'aws_resource_id': 'aws_resource',
                    'resource_config': {}
                }
            )

    def _prepare_configure(self, type_hierarchy, type_name, type_class):
        _ctx = self.get_mock_ctx(
            'test_configure',
            test_properties=DEFAULT_NODE_PROPERTIES,
            test_runtime_properties=DEFAULT_RUNTIME_PROPERTIES,
            type_hierarchy=type_hierarchy
        )

        current_ctx.set(_ctx)
        fake_boto, fake_client = self.fake_boto_client(type_name)

        with patch('boto3.client', fake_boto):
            type_class.configure(ctx=_ctx, resource_config=None, iface=None)

            self.assertEqual(
                _ctx.instance.runtime_properties, {
                    'aws_resource_id': 'aws_resource',
                    'resource_config': {}
                }
            )


class TestServiceBase(TestBase):

    base = None

    def test_create(self):
        if not self.base:
            return
        with self.assertRaises(NotImplementedError):
            self.base.create(None)

    def test_delete(self):
        if not self.base:
            return
        with self.assertRaises(NotImplementedError):
            self.base.delete(None)

    def test_update_resource_id(self):
        if not self.base:
            return
        self.base.update_resource_id('abc')
        self.assertEqual(self.base.resource_id, 'abc')


class TestAWSResourceBase(TestServiceBase):

    def setUp(self):
        super(TestAWSResourceBase, self).setUp()
        self.base = AWSResourceBase("ctx_node", resource_id=True,
                                    logger=None)

from unittest import TestCase
from contextlib import contextmanager
from mock import patch, MagicMock

from cloudify.mocks import MockCloudifyContext

from .. import check_status


class AWSCheckStatus(TestCase):

    def test_initialize(self, *_):
        ctx = MockCloudifyContext(
            "test_initialize",
            properties={
                'client_config': 'foo',
            },
            runtime_properties={
                'aws_resource_id': 'foo',
            }
        )
        result = check_status.initialize_node_interface(ctx, MagicMock)
        self.assertEqual(result.logger, ctx.logger)
        self.assertEqual(result.resource_id, 'foo')
        self.assertEqual(result.ctx_node, ctx.node)

    def test_node_interface_value_error(self, *_):
        ctx = MockCloudifyContext(
            "test_node_interface_value_error",
            properties={
                'client_config': 'foo',
            },
            runtime_properties={
                'aws_resource_id': 'foo',
            }
        )
        ctx.node.type_hierarchy = ['cloudify.nodes.aws.NotSupported']
        with check_status.node_interface(ctx) as foo:
            self.assertIsNone(foo)

    @patch('cloudify_aws.eks.Boto3Connection')
    def test_node_interface(self, *_):
        ctx = MockCloudifyContext(
            "test_node_interface",
            properties={
                'client_config': 'foo',
            },
            runtime_properties={
                'aws_resource_id': 'foo',
            }
        )
        ctx.node.type_hierarchy = ['cloudify.nodes.aws.eks.Cluster']
        with check_status.node_interface(ctx) as interface:
            self.assertEqual(interface.resource_id, 'foo')
            self.assertEqual(interface.logger, ctx.logger)

    def test_check_status(self, *_):
        ctx = MockCloudifyContext(
            "test_check_status",
            properties={
                'client_config': 'foo',
            },
            runtime_properties={
                'aws_resource_id': 'foo',
            }
        )
        tn = 'cloudify.nodes.aws.eks.Cluster'
        ctx.node.type_hierarchy = [tn]

        @contextmanager
        def mock_y(*args, **kwargs):
            interface_mock = MagicMock(
                resource_id='foo', type_name=tn, check_status='ok')
            yield interface_mock

        @contextmanager
        def mock_y_bad(*args, **kwargs):
            interface_mock = MagicMock(
                resource_id='foo', type_name=tn, check_status='not ok')
            yield interface_mock

        with patch('cloudify_aws.workflows.check_status.node_interface',
                   mock_y):
            self.assertIsNone(check_status.check_status(ctx))

        with patch('cloudify_aws.workflows.check_status.node_interface',
                   mock_y_bad):
            with self.assertRaises(RuntimeError):
                check_status.check_status(ctx)

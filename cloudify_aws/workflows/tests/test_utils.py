from mock import patch, call
from unittest import TestCase

from ...common import utils


class AWSWorkflowUtilsTests(TestCase):

    def test_desecretize_client_config(self):
        expected = {'foo': 'bar'}
        result = utils.desecretize_client_config(expected)
        assert expected == result

    @patch('cloudify_aws.common.utils.get_rest_client')
    def test_with_rest_client(self, _):
        @utils.with_rest_client
        def mock_function(**kwargs):
            return kwargs
        self.assertIn('rest_client', mock_function())

    @patch('cloudify_aws.common.utils.get_rest_client')
    def test_resolve_intrinsic_functions(self, mock_client):
        expected = 'foo'
        result = utils.resolve_intrinsic_functions(expected)
        assert expected == result
        prop = {'get_secret': 'bar'}
        utils.resolve_intrinsic_functions(prop)
        assert call().secrets.get('bar') in mock_client.mock_calls

    @patch('cloudify_aws.common.utils.get_rest_client')
    def test_get_secret(self, mock_client):
        prop = 'bar'
        utils.get_secret(secret_name=prop)
        assert call().secrets.get('bar') in mock_client.mock_calls

    @patch('cloudify_aws.common.utils.get_rest_client')
    def test_create_deployment(self, mock_client):
        prop = {
            'group_id': 'bar',
            'blueprint_id': 'foo',
            'deployment_ids': ['foo'],
            'inputs': [{'baz': 'taco'}],
            'labels': [{'foo': 'bar'}],
        }
        utils.create_deployments(**prop)
        new_deployments = [{'display_name': 'foo', 'inputs': {'baz': 'taco'}}]
        labels = [{'foo': 'bar'}]
        assert call().deployment_groups.put(
            'bar',
            'foo',
            labels
        )
        assert call().deployment_groups.add_deployments(
            'bar',
            new_deployments=new_deployments,
        ) in mock_client.mock_calls

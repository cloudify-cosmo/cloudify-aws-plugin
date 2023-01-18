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
from cloudify.state import current_ctx
from cloudify_aws.common._compat import reload_module
from cloudify_aws.common.tests.test_base import (
    TestBase,
    mock_decorator
)
from cloudify_aws.eks.resources.cluster import EKSCluster
from cloudify_aws.eks.resources import cluster
from cloudify_aws.common import constants


class TestEKSCluster(TestBase):

    def setUp(self):
        super(TestEKSCluster, self).setUp()

        self.cluster = EKSCluster("ctx_node", resource_id=True,
                                  client=True, logger=None)
        self.mock_resource = patch(
            'cloudify_aws.common.decorators.aws_resource', mock_decorator
        )
        self.mock_resource.start()
        reload_module(cluster)

    def tearDown(self):
        self.mock_resource.stop()

        super(TestEKSCluster, self).tearDown()

    def test_class_properties(self):
        effect = self.get_client_error_exception(name=cluster.RESOURCE_TYPE)
        self.cluster.client = self.make_client_function('describe_cluster',
                                                        side_effect=effect)
        self.assertEqual(self.cluster.properties, {})

        response = \
            {
                cluster.CLUSTER:
                    {
                        'arn': 'test_cluster_arn',
                        'name': 'test_cluster_name',
                        'status': 'test_status',
                    },
            }

        self.cluster.describe_param = {
            cluster.CLUSTER_NAME: 'test_cluster_name'
        }
        self.cluster.resource_id = 'test_cluster_name'
        self.cluster.client = self.make_client_function('describe_cluster',
                                                        return_value=response)
        self.assertEqual(
            self.cluster.properties[cluster.CLUSTER_NAME],
            'test_cluster_name'
        )

    def test_class_status(self):
        response = {
            cluster.CLUSTER: {
                'arn': 'test_cluster_arn',
                'name': 'test_cluster_name',
                'status': 'test_status',
            },
        }
        self.cluster.resource_id = 'test_cluster_name'
        self.cluster.client = self.make_client_function(
            'describe_cluster', return_value=response)
        self.assertEqual(self.cluster.status, 'test_status')

    def test_class_status_empty(self):
        response = {cluster.CLUSTER: {}}
        self.cluster.client = self.make_client_function('describe_cluster',
                                                        return_value=response)

        self.assertIsNone(self.cluster.status)

    def test_class_create(self):
        params = {cluster.CLUSTER_NAME: 'test_cluster_name'}
        response = \
            {
                cluster.CLUSTER: {
                    'arn': 'test_cluster_arn',
                    'name': 'test_cluster_name',
                    'status': 'test_status',
                },
            }
        self.cluster.client = self.make_client_function(
            'create_cluster', return_value=response)
        self.cluster.create(params)
        self.assertEqual(
            self.cluster.create_response[cluster.CLUSTER],
            response.get(cluster.CLUSTER))

    def test_class_delete(self):
        params = {cluster.CLUSTER: 'test_cluster_name'}
        response = \
            {
                cluster.CLUSTER: {
                    'arn': 'test_cluster_arn',
                    'name': 'test_cluster_name',
                    'status': 'test_status',
                },
            }

        self.cluster.client = self.make_client_function(
            'delete_cluster', return_value=response)

        self.assertEqual(self.cluster.delete(params), response)

    def test_prepare(self):
        ctx = self.get_mock_ctx("Cluster")
        cluster.prepare(ctx, MagicMock(), {})
        self.assertEqual(
            ctx.instance.runtime_properties['resource_config'],
            {})

    def test_create(self):
        ctx = self.get_mock_ctx("Cluster")
        config = {cluster.CLUSTER_NAME: 'test_cluster_name'}
        ctx.node.properties['store_kube_config_in_runtime'] = False
        iface = MagicMock()
        response = \
            {
                cluster.CLUSTER: {
                    'arn': 'test_cluster_arn',
                    'name': 'test_cluster_name',
                    'status': 'test_status',
                },
            }

        iface.create = self.mock_return(response)
        cluster.create(ctx, iface, config)
        self.assertEqual(
            ctx.instance.runtime_properties[constants.EXTERNAL_RESOURCE_ID],
            'test_cluster_name'
        )

    def test_delete(self):
        ctx = self.get_mock_ctx("Cluster")
        iface = MagicMock()
        cluster.delete(ctx, iface, {})
        self.assertTrue(iface.delete.called)

    @patch('cloudify_aws.eks.resources.cluster'
           '._store_kubeconfig_in_runtime_properties')
    def test_refresh_kubeconfig_wrong_type_hierarchy(self,
                                                     store_kube_conf_mock):
        wrong_th = ['cloudify.nodes.Root']
        _ctx = self.get_mock_relationship_ctx(
            "ClusterRel",
            test_target=self.get_mock_ctx("Cluster",
                                          test_properties={},
                                          test_runtime_properties={},
                                          type_hierarchy=wrong_th))

        cluster.refresh_kubeconfig(_ctx)
        store_kube_conf_mock.assert_not_called()

    @patch('cloudify_aws.eks.resources.cluster.EKSCluster')
    @patch('cloudify_aws.eks.resources.cluster'
           '._store_kubeconfig_in_runtime_properties')
    def test_refresh_kubeconfig(self, store_kube_conf_mock, *_):
        pass
        _ctx = self.get_mock_relationship_ctx(
            "ClusterRel",
            test_target=self.get_mock_ctx(
                "Cluster",
                test_properties={'store_kube_config_in_runtime': True},
                test_runtime_properties={
                    constants.EXTERNAL_RESOURCE_ID: 'ext_id',
                    'instances': ['ext_id']},
                type_hierarchy=[
                    'cloudify.nodes.Root',
                    cluster.CLUSTER_TYPE]))

        cluster.refresh_kubeconfig(_ctx)
        store_kube_conf_mock.assert_called()

    def test_check_drift(self):
        original_value = {
            'name': 'test_name',
            'status': 'ACTIVE',
            'certificateAuthority': 'foo'
        }
        next_value = {
            'name': 'test_name',
            'status': 'ACTIVE',
            'certificateAuthority': 'bar'
        }

        ctx = self.get_mock_ctx("Cluster")
        ctx.instance.runtime_properties.update({
                'aws_resource_id': 'test_name',
                'expected_configuration': original_value,
                'previous_configuration': {},
                'create_response': {'cluster': original_value}
            })
        current_ctx.set(ctx)
        self.cluster.resource_id = 'test_name'
        self.cluster.client = self.make_client_function(
            'describe_cluster', return_value={'cluster': next_value})
        self.cluster.import_configuration(
            ctx.node.properties.get('resource_config', {}),
            ctx.instance.runtime_properties
        )
        expected = {
            'values_changed': {
                "root['certificateAuthority']": {
                    'new_value': 'bar', 'old_value': 'foo'
                }
            }
        }
        message = 'The EKS Cluster test_name configuration ' \
                  'has drifts: {}'.format(expected)
        with self.assertRaises(RuntimeError) as e:
            cluster.check_drift(ctx=ctx, iface=self.cluster)
            self.assertIn(message, str(e))


if __name__ == '__main__':
    unittest.main()

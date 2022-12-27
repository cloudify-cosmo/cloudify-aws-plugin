# Copyright (c) 2021 Cloudify Platform Ltd. All rights reserved
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

import os
import yaml
from mock import patch, MagicMock
from importlib import import_module

from cloudify.state import current_ctx
from cloudify.exceptions import (OperationRetry, NonRecoverableError)

from cloudify_aws.common.tests.test_base import TestBase

REL_LIFE = 'cloudify.interfaces.relationship_lifecycle'


def get_callable(operation_mapping):
    if not isinstance(operation_mapping, dict):
        raise Exception(
            'Operation {op} is not dict.'.format(op=operation_mapping))
    elif 'implementation' not in operation_mapping:
        return
    elif operation_mapping['implementation'] == '~':
        return
    elif not operation_mapping['implementation']:
        return
    modules = operation_mapping['implementation'].split('.')
    del modules[0]
    func = modules.pop(-1)
    import_path = '.'.join(modules)
    module = import_module(import_path)
    return module and getattr(module, func, None)


class testIfaceRequirement(TestBase):

    @staticmethod
    def get_plugin_yaml():
        plugin_yaml_path = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                '..', '..', '..', 'plugin.yaml'))
        plugin_yaml_file = open(plugin_yaml_path, 'r')
        return yaml.load(plugin_yaml_file, Loader=yaml.FullLoader)

    @staticmethod
    def get_node_type_operations(plugin_yaml):
        operations = []
        for _, node in plugin_yaml['node_types'].items():
            try:
                op_list = node['interfaces']['cloudify.interfaces.lifecycle']
            except KeyError:
                continue
            for _, op in op_list.items():
                module = get_callable(op)
                operations.append(module)
        return operations

    @staticmethod
    def get_relationships_operations(plugin_yaml):
        operations = []
        for _, rel in plugin_yaml['relationships'].items():
            op_list = rel.get('source_interfaces', {}).get(REL_LIFE, {})
            op_list.update(rel.get('target_interfaces', {}).get(REL_LIFE, {}))
            for _, op in op_list.items():
                module = get_callable(op)
                operations.append(module)
        return operations

    def get_op_ctx(self, operation):
        mock_group = MagicMock()
        mock_group.type_hierarchy = [
            'cloudify.relationships.depends_on',
            'cloudify.relationships.contained_in'
        ]
        mock_group.target.instance.runtime_properties = {
            'aws_resource_id': 'aws_id',
            'aws_resource_arn': 'foo',
            'ListenerArn': 'arn:aws:foo',
            'resource_config': {}
        }
        mock_group.target.node.type_hierarchy = [
            'cloudify.nodes.Root',
            'cloudify.nodes.aws.autoscaling.Group',
            'cloudify.nodes.aws.SNS.Topic',
            'cloudify.nodes.aws.elb.Classic.LoadBalancer',
            'cloudify.nodes.aws.elb.LoadBalancer',
            'cloudify.nodes.aws.elb.Listener',
            'cloudify.nodes.aws.ec2.Vpc',
            'cloudify.nodes.aws.s3.Bucket',
            'cloudify.nodes.aws.ec2.NetworkACL',
            'cloudify.nodes.aws.ec2.RouteTable',
            'cloudify.nodes.aws.efs.FileSystem',
            'cloudify.nodes.aws.ec2.Subnet',
            'cloudify.nodes.aws.kms.CustomerMasterKey',
            'cloudify.nodes.aws.ecs.Cluster'
        ]
        _ctx = self.get_mock_ctx(
            operation, test_relationships=[mock_group])
        _ctx.instance.runtime_properties['aws_resource_id'] = 'foo'
        _ctx.instance.runtime_properties['aws_resource_ids'] = ['foo']
        _ctx.instance.runtime_properties['aws_resource_arn'] = 'foo'
        _ctx.instance.runtime_properties['LoadBalancerName'] = 'foo'
        _ctx.instance.runtime_properties['PolicyName'] = 'foo'
        _ctx.instance.runtime_properties['rule_number'] = 'foo'
        _ctx.instance.runtime_properties['egress'] = 'foo'
        _ctx.instance.runtime_properties['network_acl_id'] = 'foo'
        _ctx.instance.runtime_properties['vpc_id'] = 'foo'
        _ctx.instance.runtime_properties['association_ids'] = \
            ['foo']
        _ctx.instance.runtime_properties['destination_cidr_block'] = \
            'foo'
        _ctx.instance.runtime_properties['AutoScalingGroupName'] = \
            'foo'
        _ctx.instance.runtime_properties['KeyId'] = 'foo'
        _ctx.instance.runtime_properties['instances'] = ['foo']
        _ctx.instance.runtime_properties['resources'] = {}
        _ctx.instance.runtime_properties['resource_config'] = {
            'UserPoolId': 'foo',
            'ProviderName': 'foo',
            'HostedZoneId': 'foo',
            'ChangeBatch': {
                'Changes': [{'ResourceRecordSet': 'foo'}]
            },
            'resourcesVpcConfig': {'subnetIds': []},
            'Endpoint': 'arn:aws:foo',
            'Key': 'foo',
            'GroupName': 'foo',
            'KeyName': 'foo',
            'DhcpConfigurations': ['foo'],
            'Type': 'foo',
            'DestinationCidrBlock': 'foo',
            'Targets': [{'Id': 'foo'}],
            'KeyId': 'foo',
        }
        _ctx.node.properties['client_config'] = \
            {'region_name': 'eu-west-1'}
        _ctx.node.properties['resource_config'] = {
            'UserPoolId': 'foo',
            'ProviderName': 'foo',
            'kwargs': {}
        }
        _ctx.node.properties['log_create_response'] = False
        _ctx.node.properties['create_secret'] = False
        _ctx.node.properties['store_kube_config_in_runtime'] = \
            False
        return _ctx

    def perform_operation(self, operation_callable, args, kwargs):
        try:
            operation_callable(*args, **kwargs)
        except NotImplementedError as e:
            if 'permission' in str(e):
                return
            raise
        except NonRecoverableError as e:
            if 'must provide a relationship' in str(e):
                return
            elif 'unexpected status' in str(e):
                return
            elif 'Found no AMIs matching provided filters' in str(e):
                return
            elif 'ctx.agent' in str(e):
                return
            raise
        except OperationRetry as e:
            if 'pending state' in str(e):
                return
            elif 'Updating Autoscaling Group' in str(e):
                return
            elif 'Waiting for Instance' in str(e):
                return
            elif 'Waiting for Instance' in str(e):
                return
            elif 'spot fleet instances' in str(e):
                return
            elif 'Sent the TransitGatewayVpcAttachment' in str(e):
                return
            elif 'Waiting for foo attachment' in str(e):
                return
            elif 'Waiting for Internet Gateway to be created' in str(e):
                return
            elif 'Waiting for VPC to be created' in str(e):
                return
            elif 'Waiting for route table to delete' in str(e):
                return
            raise
        except AttributeError as e:
            if "no attribute 'node'" not in str(e):
                raise
            kwargs['ctx'] = self.get_mock_relationship_ctx(
                operation_callable,
                test_source=self.get_op_ctx(operation_callable),
                test_target=self.get_op_ctx(operation_callable))
            self.perform_operation(operation_callable, args, kwargs)

    @patch('cloudify_aws.common.decorators.skip')
    @patch('cloudify_aws.common.utils.get_rest_client')
    @patch('cloudify_aws.common.connection.Boto3Connection')
    @patch('cloudify_aws.common.decorators._wait_for_status')
    @patch('cloudify_aws.common.decorators._wait_for_delete')
    @patch('cloudify_aws.common.AWSResourceBase.make_client_call')
    @patch('cloudify_aws.common.connection.Boto3Connection.client')
    @patch('cloudify_aws.common.connection.Boto3Connection.get_account_id')
    @patch('cloudify.context.CloudifyContext._verify_in_relationship_context')
    def test_iface_requirement(self, *_):
        plugin_yaml = self.get_plugin_yaml()
        operations = self.get_node_type_operations(plugin_yaml) + \
            self.get_relationships_operations(plugin_yaml)
        for operation in operations:
            if operation:
                _ctx = self.get_op_ctx(operation)
                current_ctx.set(ctx=_ctx)
                args = tuple()
                kwargs = dict(
                    ctx=_ctx,
                    resource_config={},
                    force_delete=False)
                self.perform_operation(operation, args, kwargs)

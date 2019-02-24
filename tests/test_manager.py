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

import os

from Crypto.PublicKey import RSA
from cloudify_cli.utils import get_local_path

from integration_tests.tests.test_cases import PluginsTest
from integration_tests.tests import utils as test_utils
from integration_tests.framework import utils

PLUGIN_NAME = 'cloudify-aws-plugin'

S3_BLUEPRINT_ID = 's3_blueprint'
DYNAMODB_BLUEPRINT_ID = 'dynamodb_blueprint'
SNS_BLUEPRINT_ID = 'sns_blueprint'
CFN_BLUEPRINT_ID = 'rds_cloudformation_blueprint'
AUTO_SCALING_BLUEPRINT_ID = 'autoscaling_blueprint'


class AWSPluginTestCase(PluginsTest):
    base_path = os.path.dirname(os.path.realpath(__file__))

    @property
    def plugin_root_directory(self):
        return os.path.abspath(os.path.join(self.base_path, '..'))

    @property
    def client_config(self):
        return {
            'aws_access_key_id': os.environ['AWS_ACCESS_KEY_ID'],
            'aws_secret_access_key': os.environ['AWS_SECRET_ACCESS_KEY'],
            'aws_region_name': os.environ['AWS_REGION'],
        }

    def cleanup_deployment(self, deployment_id):
        """force uninstall deployment

        :param deployment_id: the deployment to uninstall
        :returns: nothing
        :rtype: NoneType
        """
        # Un-deploy blueprint application
        self.undeploy_application(
            deployment_id,
            timeout_seconds=1200,
            parameters={'ignore_failure': True})

    def _wait_for_execution_by_wf_name(self, wf_name):
        install_plugin_ex = [ex for ex in self.client.executions.list(
            include_system_workflows=True) if ex.workflow_id == wf_name][0]
        self.wait_for_execution_to_end(install_plugin_ex, timeout_seconds=1200)

    def _create_deployment_secrets(self, secrets):

        for secret in secrets:
            secret_name, secret_value = secret.items()[0]
            self.client.secrets.create(
                secret_name,
                secret_value,
                update_if_exists=True)

    def _deploy_aws_example(self, blueprint_id, blueprint_path, inputs=None):
        if not inputs:
            inputs = self.client_config

        # Deploy blueprint application
        self.deploy_application(
            test_utils.get_resource(
                os.path.join(
                    self.plugin_root_directory,
                    blueprint_path)),
            timeout_seconds=1200,
            blueprint_id=blueprint_id,
            deployment_id=blueprint_id,
            inputs=inputs)

    def check_s3(self):

        # Before trigger S3 deployment, it is required to push the a clean the
        # deployment which should be called after tearDown on
        # test failure or success.
        self.addCleanup(self.cleanup_deployment, S3_BLUEPRINT_ID)

        # Blueprint Id
        blueprint_id = S3_BLUEPRINT_ID

        # Blueprint path
        blueprint_path = 'examples/s3-feature-demo/blueprint.yaml'

        # Trigger build for s3 example
        self._deploy_aws_example(blueprint_id, blueprint_path)

    def check_dynamodb(self):

        # Before trigger DynamoDB deployment, it is required to push the a clean the
        # deployment which should be called after tearDown on
        # test failure or success.
        self.addCleanup(self.cleanup_deployment, DYNAMODB_BLUEPRINT_ID)

        # Blueprint Id
        blueprint_id = DYNAMODB_BLUEPRINT_ID

        # Blueprint path
        blueprint_path = 'examples/dynamodb-feature-demo/blueprint.yaml'

        # Trigger build for dynamo example
        self._deploy_aws_example(blueprint_id, blueprint_path)

    def check_sns(self):

        # Before trigger sns deployment we need to handle cleanup  method
        self.addCleanup(self.cleanup_deployment, SNS_BLUEPRINT_ID)

        # Blueprint Id
        blueprint_id = SNS_BLUEPRINT_ID

        # Blueprint path
        blueprint_path = 'examples/sns-feature-demo/blueprint.yaml'

        # Trigger build for sns example
        self._deploy_aws_example(blueprint_id, blueprint_path)

    def check_cfn_stack(self):
        # Before trigger cfn we need to handle cleanup  method
        self.addCleanup(self.cleanup_deployment, CFN_BLUEPRINT_ID)

        # Prepare required inputs for deployment
        inputs = dict()

        # Populate inputs with required client config
        inputs.update(self.client_config)

        # Populate inputs with valid "availability zone"
        inputs['availability_zone'] = \
            '{0}c'.format(self.client_config['aws_region_name'])

        # Blueprint Id
        blueprint_id = CFN_BLUEPRINT_ID

        # Blueprint path
        blueprint_path =\
            'examples/cloudformation-feature-demo/blueprint.yaml'

        # Trigger build for cloudformation example
        self._deploy_aws_example(blueprint_id, blueprint_path, inputs)

    def check_autoscaling(self):

        # Before trigger cfn we need to handle cleanup method
        self.addCleanup(self.cleanup_deployment, AUTO_SCALING_BLUEPRINT_ID)

        # Blueprint Id
        blueprint_id = AUTO_SCALING_BLUEPRINT_ID

        # Blueprint path
        blueprint_path = 'examples/autoscaling-feature-demo/test.yaml'

        # Trigger build for autoscaling example
        self._deploy_aws_example(blueprint_id, blueprint_path)

    def test_blueprints(self):
        # Deploy plugin
        self.upload_mock_plugin(PLUGIN_NAME, self.plugin_root_directory)

        # Deploy S3 example
        self.check_s3()

        # Deploy SNS example
        self.check_sns()

        # Deploy Cloudformation example
        self.check_cfn_stack()

        # Deploy AutoScaling example
        self.check_autoscaling()

        # Deploy DynamoDB example.
        self.check_dynamodb()

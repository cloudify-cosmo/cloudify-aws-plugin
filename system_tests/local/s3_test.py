########
# Copyright (c) 2015 GigaSpaces Technologies Ltd. All rights reserved
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

from copy import copy
import os
import urlparse

import boto3
from cosmo_tester.framework.testenv import TestCase
from cloudify.workflows import local
from cloudify_cli import constants as cli_constants
import requests


class S3Test(TestCase):
    def setUp(self):
        super(S3Test, self).setUp()

        self.access_key = self.env.cloudify_config['aws_access_key_id']
        self.secret_key = self.env.cloudify_config['aws_secret_access_key']

        self.ext_inputs = {
            'aws_access_key_id': self.access_key,
            'aws_secret_access_key': self.secret_key,
            'bucket_name': 'sandy-test-system-test-bucket',
        }

        blueprints_path = os.path.split(os.path.abspath(__file__))[0]
        blueprints_path = os.path.split(blueprints_path)[0]
        self.blueprints_path = os.path.join(
            blueprints_path,
            'resources',
            's3'
        )

        self.aws_conn = boto3.Session(
            self.access_key,
            self.secret_key,
            region_name='us-east-1',
        )
        self.s3_conn = self.aws_conn.client('s3')

    def test_existing_bucket(self):
        blueprint = os.path.join(
            self.blueprints_path,
            'existing-blueprint.yaml'
        )

        if self.env.install_plugins:
            self.logger.info('installing required plugins')
            self.cfy.install_plugins_locally(
                blueprint_path=blueprint)

        self.logger.info('Trying to use existing s3 bucket')

        inputs = copy(self.ext_inputs)
        inputs['bucket_name'] = inputs['bucket_name'] + '.external'

        self.existing_bucket = inputs['bucket_name']
        self.s3_conn.create_bucket(
            Bucket=self.existing_bucket,
            ACL='public-read',
        )

        self.existing_env = local.init_env(
            blueprint,
            inputs=inputs,
            name=self._testMethodName,
            ignored_modules=cli_constants.IGNORED_LOCAL_WORKFLOW_MODULES)
        self.existing_env.execute(
            'install',
            task_retries=10,
            task_retry_interval=3,
        )

        self.addCleanup(self.cleanup_existing)

        base_url = self.existing_env.outputs()['endpoint']

        testfile = requests.get(urlparse.urljoin(base_url, 'testfile'))
        assert testfile.status_code == 200
        assert testfile.text == (
            'this is a test'
        ), 'Unexpected testfile. Saw {file}'.format(page=testfile.text)
        self.logger.info('Test file retrieved successfully.')

    def test_bucket(self):
        blueprint = os.path.join(
            self.blueprints_path,
            'basic-blueprint.yaml'
        )

        if self.env.install_plugins:
            self.logger.info('installing required plugins')
            self.cfy.install_plugins_locally(
                blueprint_path=blueprint)

        self.logger.info('Deploying s3 bucket')

        inputs = copy(self.ext_inputs)
        inputs['bucket_name'] = inputs['bucket_name'] + '-basic'

        self.bucket_env = local.init_env(
            blueprint,
            inputs=inputs,
            name=self._testMethodName,
            ignored_modules=cli_constants.IGNORED_LOCAL_WORKFLOW_MODULES)
        self.bucket_env.execute(
            'install',
            task_retries=10,
            task_retry_interval=3,
        )

        self.addCleanup(self.cleanup_bucket)

        base_url = self.bucket_env.outputs()['endpoint']

        testfile = requests.get(urlparse.urljoin(base_url, 'testfile'))
        assert testfile.status_code == 200
        assert testfile.text == (
            'this is a test'
        ), 'Unexpected testfile. Saw {file}'.format(page=testfile.text)
        self.logger.info('Test file retrieved successfully.')

    def test_website(self):
        blueprint = os.path.join(
            self.blueprints_path,
            'website-blueprint.yaml'
        )

        if self.env.install_plugins:
            self.logger.info('installing required plugins')
            self.cfy.install_plugins_locally(
                blueprint_path=blueprint)

        self.logger.info('Deploying s3 website')

        inputs = copy(self.ext_inputs)
        inputs['bucket_name'] = inputs['bucket_name'] + '-website'

        self.website_env = local.init_env(
            blueprint,
            inputs=inputs,
            name=self._testMethodName,
            ignored_modules=cli_constants.IGNORED_LOCAL_WORKFLOW_MODULES)
        self.website_env.execute(
            'install',
            task_retries=10,
            task_retry_interval=3,
        )

        self.addCleanup(self.cleanup_website)

        base_url = self.website_env.outputs()['endpoint']

        success = requests.get(base_url)
        assert success.status_code == 200
        assert success.text == (
            '<html><head><title>Test bucket</title></head>'
            '<body>This is a test bucket.</body></html>'
        ), 'Unexpected index page. Saw {page}'.format(page=success.text)
        self.logger.info('Website index retrieved successfully.')

        failure = requests.get(urlparse.urljoin(base_url, 'failure'))
        assert failure.status_code == 404
        assert failure.text == (
            '<html><head><title>No object here</title></head>'
            '<body>Object not found</body></html>\n'
        ), 'Unexpected error page. Saw {page}'.format(page=failure.text)

        self.logger.info('Website error page retrieved successfully.')

    def cleanup_existing(self):
        self.existing_env.execute(
            'uninstall',
            task_retries=10,
            task_retry_interval=3,
        )
        self.s3_conn.delete_bucket(Bucket=self.existing_bucket)

    def cleanup_bucket(self):
        self.bucket_env.execute(
            'uninstall',
            task_retries=10,
            task_retry_interval=3,
        )

    def cleanup_website(self):
        self.website_env.execute(
            'uninstall',
            task_retries=10,
            task_retry_interval=3,
        )

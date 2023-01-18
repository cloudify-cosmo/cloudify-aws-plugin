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
import copy
import datetime

# Third party imports
from mock import patch, MagicMock

from cloudify.state import current_ctx

# Local imports
from cloudify_aws.codepipeline.resources import pipeline
from cloudify_aws.common.tests.test_base import TestBase, CLIENT_CONFIG
from cloudify_aws.common.tests.test_base import DELETE_RESPONSE
from cloudify_aws.common.tests.test_base import DEFAULT_RUNTIME_PROPERTIES

# Constants
PIPELINE_NAME = 'Demopipeline'

PIPELINE_TH = ['cloudify.nodes.Root',
               'cloudify.nodes.aws.codepipeline.Pipeline']

NODE_PROPERTIES = {
    'resource_id': 'node_resource_id',
    'use_external_resource': False,
    'resource_config': {
        'kwargs': {'pipeline': {'name': PIPELINE_NAME, 'version': 1}}},
    'client_config': CLIENT_CONFIG
}

RUNTIME_PROPERTIES_AFTER_CREATE = {
    'aws_resource_id': PIPELINE_NAME,
    'resource_config': {},
}

TEST_DATE = datetime.datetime(2020, 1, 1)


class TestCodePipeline(TestBase):

    def setUp(self):
        super(TestCodePipeline, self).setUp()

        self.fake_boto, self.fake_client = self.fake_boto_client(
            'codepipeline')

        self.mock_patch = patch('boto3.client', self.fake_boto)
        self.mock_patch.start()

    def tearDown(self):
        self.mock_patch.stop()
        self.fake_boto = None
        self.fake_client = None

        super(TestCodePipeline, self).tearDown()

    def test_create(self):
        _ctx = self.get_mock_ctx(
            'test_create',
            test_properties=NODE_PROPERTIES,
            test_runtime_properties=DEFAULT_RUNTIME_PROPERTIES,
            type_hierarchy=PIPELINE_TH,
            ctx_operation_name='cloudify.interfaces.lifecycle.create',
        )

        current_ctx.set(_ctx)

        self.fake_client.create_pipeline = MagicMock(
            return_value={'pipeline': {'name': PIPELINE_NAME, 'version': 1}})

        self.fake_client.get_pipeline_state = MagicMock(return_value={
            'pipelineName': PIPELINE_NAME,
            'pipelineVersion': 1,
            'created': TEST_DATE
        })

        pipeline.create(
            ctx=_ctx, iface=None, params=None
        )

        self.fake_boto.assert_called_with('codepipeline', **CLIENT_CONFIG)

        self.fake_client.create_pipeline.assert_called_with(
            pipeline={"name": PIPELINE_NAME, "version": 1}
        )

        updated_runtime_prop = copy.deepcopy(RUNTIME_PROPERTIES_AFTER_CREATE)
        updated_runtime_prop['create_response'] = {
            'pipelineName': PIPELINE_NAME,
            'pipelineVersion': 1,
            'created': ''}

        # This is just because I'm not interested in the content
        # of remote_configuration right now.
        # If it doesn't exist, this test will fail, and that's good.
        _ctx.instance.runtime_properties.pop('remote_configuration')
        self.assertEqual(_ctx.instance.runtime_properties,
                         updated_runtime_prop)

    def test_delete(self):
        _ctx = self.get_mock_ctx(
            'test_delete',
            test_properties=NODE_PROPERTIES,
            test_runtime_properties=RUNTIME_PROPERTIES_AFTER_CREATE,
            type_hierarchy=PIPELINE_TH,
            ctx_operation_name='cloudify.interfaces.lifecycle.delete'
        )

        current_ctx.set(_ctx)

        self.fake_client.delete_pipeline = self.mock_return(DELETE_RESPONSE)

        pipeline.delete(ctx=_ctx, resource_config=None, iface=None)

        self.fake_boto.assert_called_with('codepipeline', **CLIENT_CONFIG)

        self.fake_client.delete_pipeline.assert_called_with(
            name=PIPELINE_NAME
        )

        self.assertEqual(
            _ctx.instance.runtime_properties,
            {
                '__deleted': True,
            }
        )

    def test_execute(self):
        _ctx = self.get_mock_ctx(
            'test_execute_pipeline',
            test_properties=NODE_PROPERTIES,
            test_runtime_properties=RUNTIME_PROPERTIES_AFTER_CREATE,
            type_hierarchy=PIPELINE_TH
        )

        current_ctx.set(_ctx)

        self.fake_client.start_pipeline_execution = MagicMock(
            return_value={'pipelineExecutionId': '12345'})

        pipeline.execute(ctx=_ctx, iface=None, name=PIPELINE_NAME,
                         clientRequestToken=None)

        self.fake_boto.assert_called_with('codepipeline', **CLIENT_CONFIG)

        self.fake_client.start_pipeline_execution.assert_called_with(
            name=PIPELINE_NAME
        )
        pipeline.execute(ctx=_ctx, iface=None, name=PIPELINE_NAME,
                         clientRequestToken='fake-token123')

        self.fake_client.start_pipeline_execution.assert_called_with(
            name=PIPELINE_NAME, clientRequestToken='fake-token123'
        )

        pipeline.execute(ctx=_ctx, iface=None)
        self.fake_client.start_pipeline_execution.assert_called_with(
            name=PIPELINE_NAME
        )

    def test_create_raises_UnknownServiceError(self):
        self._prepare_create_raises_UnknownServiceError(
            type_hierarchy=PIPELINE_TH,
            type_name='codepipeline',
            type_class=pipeline,
            operation_name='cloudify.interfaces.lifecycle.create',
        )

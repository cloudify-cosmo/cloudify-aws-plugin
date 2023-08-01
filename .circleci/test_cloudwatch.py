########
# Copyright (c) 2014-2019 Cloudify Platform Ltd. All rights reserved
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

from os import environ
from contextlib import contextmanager

import pytest

from ecosystem_tests.nerdl.api import (
    upload_blueprint,
    delete_blueprint,
    delete_deployment,
    get_node_instance,
    create_deployment,
    wait_for_workflow,
    cleanup_on_failure,
    list_node_instances)

TEST_ID = environ.get('__ECOSYSTEM_TEST_ID', 'hello-world-example')


@contextmanager
def test_cleaner_upper():
    try:
        yield
    except Exception:
        cleanup_on_failure(TEST_ID)
        raise


def test_cloudwatch(*_, **__):
    with test_cleaner_upper():
        vm_props = cloud_resources_node_instance_runtime_properties()
        instance_id = vm_props.get('aws_resource_id')
        deployment_id = TEST_ID + 'cloudwatch'
        try:
            # Upload Cloud Watch Blueprint
            upload_blueprint(
                'examples/cloudwatch-feature-demo/blueprint.yaml',
                deployment_id)
            # Create Cloud Watch Deployment with Instance ID input
            create_deployment(
                deployment_id,
                deployment_id,
                {
                    "aws_instance_id": str(instance_id),
                    "aws_region_name": "us-west-2"
                }
            )
            # Install Cloud Watch Deployment
            wait_for_workflow(deployment_id, 'install', 1800)
            # Uninstall Cloud Watch Deployment
            wait_for_workflow(deployment_id, 'uninstall', 1800)
            delete_deployment(deployment_id)
            delete_blueprint(deployment_id)
        except:
            cleanup_on_failure(deployment_id)


def cloud_resources_node_instance_runtime_properties():
    node_instance = node_instance_by_name('vm')
    if not node_instance:
        raise RuntimeError('No cloud_resources node instances found.')
    runtime_properties = node_instance_runtime_properties(
        node_instance['id'])
    if not runtime_properties:
        raise RuntimeError(
            'No cloud_resources runtime_properties found.')
    return runtime_properties


def node_instance_by_name(name):
    for node_instance in list_node_instances(TEST_ID):
        if node_instance['node_id'] == name:
            return node_instance
    raise Exception('No node instances found.')


def node_instance_runtime_properties(name):
    node_instance = get_node_instance(name)
    return node_instance['runtime_properties']

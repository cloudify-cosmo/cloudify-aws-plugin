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
import logging
from os import environ
from contextlib import contextmanager

import pytest

from boto3 import client
from ecosystem_tests.dorkl.constansts import logger
from ecosystem_tests.dorkl import cleanup_on_failure
from ecosystem_tests.dorkl.exceptions import EcosystemTestException
from ecosystem_tests.dorkl.cloudify_api import (
    cloudify_exec,
    blueprints_upload,
    deployments_create,
    executions_start)

TEST_ID = environ.get('__ECOSYSTEM_TEST_ID', 'virtual-machine')


@contextmanager
def test_cleaner_upper():
    try:
        yield
    except Exception:
        cleanup_on_failure(TEST_ID)
        raise


@pytest.mark.dependency(depends=['test_plan_protection'])
def test_cloudwatch(*_, **__):
    with test_cleaner_upper():
        vm_props = cloud_resources_node_instance_runtime_properties()
        instance_id = vm_props.get('aws_resource_id')
        deployment_id = TEST_ID + 'cloudwatch'
        try:
            # Upload Cloud Watch Blueprint
            blueprints_upload(
                'examples/cloudwatch-feature-demo/blueprint.yaml',
                deployment_id)
            # Create Cloud Watch Deployment with Instance ID input
            deployments_create(deployment_id,
                               {"aws_instance_id": str(instance_id),
                                "aws_region_name": "us-west-2"})
            # Install Cloud Watch Deployment
            executions_start('install', deployment_id)
            # Uninstall Cloud Watch Deployment
            executions_start('uninstall', deployment_id)
        except:
            cleanup_on_failure(deployment_id)


def cloud_resources_node_instance_runtime_properties():
    node_instance = node_instance_by_name('vm')
    logger.info('Node instance: {node_instance}'.format(
        node_instance=node_instance))
    if not node_instance:
        raise RuntimeError('No cloud_resources node instances found.')
    runtime_properties = node_instance_runtime_properties(
        node_instance['id'])
    logger.info('Runtime properties: {runtime_properties}'.format(
        runtime_properties=runtime_properties))
    if not runtime_properties:
        raise RuntimeError(
            'No cloud_resources runtime_properties found.')
    return runtime_properties


def node_instance_by_name(name):
    for node_instance in node_instances():
        if node_instance['node_id'] == name:
            return node_instance
    raise Exception('No node instances found.')


def node_instance_runtime_properties(name):
    node_instance = cloudify_exec(
        'cfy node-instance get {name}'.format(name=name))
    return node_instance['runtime_properties']


def nodes():
    return cloudify_exec('cfy nodes list')


def node_instances():
    return cloudify_exec('cfy node-instances list -d {}'.format(TEST_ID))

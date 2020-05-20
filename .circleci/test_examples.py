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


import os
import pytest

from ecosystem_tests.dorkl import (
    basic_blueprint_test,
    cleanup_on_failure, prepare_test
)

SECRETS_TO_CREATE = {
    'aws_access_key_id': False,
    'aws_secret_access_key': False,
}

prepare_test(secrets=SECRETS_TO_CREATE)

blueprint_list = ['examples/blueprint-examples/hello-world-example/aws.yaml',
                  'examples/blueprint-examples/'
                  'virtual-machine/aws-cloudformation.yaml',
                  'examples/blueprint-examples/'
                  'kubernetes/aws-eks/blueprint.yaml']


@pytest.fixture(scope='function', params=blueprint_list)
def blueprint_examples(request):
    test_name = os.path.dirname(request.param).split('/')[-1:][0]
    if os.environ['TEST_NAME'] not in test_name:
        return
    if 'eks' in test_name or 'cloudformation' in test_name:
        inputs = 'aws_region_name=us-east-1 -i resource_suffix={0}'.format(
            os.environ.get('CIRCLE_BUILD_NUM', 'tst'))
    else:
        inputs = 'aws_region_name=us-east-1'
    try:
        basic_blueprint_test(
            request.param,
            test_name,
            inputs=inputs,
            timeout=3000
        )
    except:
        cleanup_on_failure(test_name)
        raise


def test_blueprints(blueprint_examples):
    assert blueprint_examples is None

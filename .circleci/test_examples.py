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

'''Temporary until all the plugins in the bundle will 
released with py2py3 wagons'''
UT_VERSION = '1.23.5'
UT_WAGON = 'https://github.com/cloudify-incubator/cloudify-utilities-plugin/' \
           'releases/download/{v}/cloudify_utilities_plugin-{v}-centos' \
           '-Core-py27.py36-none-linux_x86_64.wgn'.format(v=UT_VERSION)
UT_PLUGIN = 'https://github.com/cloudify-incubator/cloudify-utilities-' \
            'plugin/releases/download/{v}/plugin.yaml'.format(v=UT_VERSION)
AN_VERSION = '2.9.2'
AN_WAGON = 'https://github.com/cloudify-cosmo/cloudify-ansible-plugin/' \
           'releases/download/{v}/cloudify_ansible_plugin-{v}-centos-' \
           'Core-py27.py36-none-linux_x86_64.wgn'.format(v=AN_VERSION)
AN_PLUGIN = 'https://github.com/cloudify-cosmo/cloudify-ansible-plugin' \
            '/releases/download/{v}/plugin.yaml'.format(v=AN_VERSION)
K8S_VERSION = '2.8.2'
K8S_WAGON = 'https://github.com/cloudify-cosmo/cloudify-kubernetes-plugin/' \
            'releases/download/{v}/cloudify_kubernetes_plugin-{v}-' \
            'centos-Core-py27.py36-none-linux_x86_64.wgn'.format(v=K8S_VERSION)
K8S_PLUGIN = 'https://github.com/cloudify-cosmo/cloudify-kubernetes-plugin/' \
             'releases/download/{v}/plugin.yaml'.format(v=K8S_VERSION)
PLUGINS_TO_UPLOAD = [(UT_WAGON, UT_PLUGIN), (AN_WAGON, AN_PLUGIN),
                     (K8S_WAGON, K8S_PLUGIN)]
SECRETS_TO_CREATE = {
    'aws_access_key_id': False,
    'aws_secret_access_key': False,
}

prepare_test(plugins=PLUGINS_TO_UPLOAD, secrets=SECRETS_TO_CREATE,
             execute_bundle_upload=False)

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

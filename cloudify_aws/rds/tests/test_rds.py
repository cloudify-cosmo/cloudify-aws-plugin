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
import mock

from cloudify.exceptions import NonRecoverableError

# Local imports
from cloudify_aws.rds import RDSBase
from cloudify_aws.common.tests.test_base import TestServiceBase
from cloudify_aws.common.constants import AWS_CONFIG_PROPERTY


class TestRDSInit(TestServiceBase):

    @mock.patch('cloudify_common_sdk.utils.get_ctx_instance')
    @mock.patch('cloudify_common_sdk.utils.get_ctx_plugin')
    def test_credentials(self, mock_plugin_ctx, *_):
        boto_client = mock.Mock()
        boto_mock = mock.Mock(return_value=boto_client)
        ctx_node = mock.Mock()
        ctx_node.properties = {
            AWS_CONFIG_PROPERTY: {
                'region_name': 'wr-ongvalu-e'
            }
        }
        mock_plugin_ctx.return_value = {
            'foo': 'bar'
        }
        with mock.patch(
            "cloudify_aws.rds.Boto3Connection", boto_mock
        ):
            with self.assertRaises(NonRecoverableError):
                RDSBase(ctx_node)

            ctx_node.properties[AWS_CONFIG_PROPERTY] = {
                'region_name': 'aq-testzone-1'
            }
            RDSBase(ctx_node)
            boto_mock.assert_called_with(ctx_node)
            boto_client.client.assert_called_with('rds')


if __name__ == '__main__':
    unittest.main()

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
from mock import patch, MagicMock

# Local imports
from cloudify_aws.iam import IAMBase
from cloudify_aws.common.tests.test_base import TestServiceBase

ctx_node = MagicMock(
    properties={},
    plugin=MagicMock(properties={})
)


class TestIAMBase(TestServiceBase):

    @patch('cloudify_common_sdk.utils.ctx_from_import')
    @patch('cloudify_aws.common.connection.Boto3Connection.get_account_id')
    def setUp(self, _, _ctx):
        _ctx = MagicMock(  # noqa
            node=ctx_node, plugin=MagicMock(properties={}))
        super(TestIAMBase, self).setUp()
        self.base = IAMBase(
            ctx_node, resource_id=True, client=True, logger=None)


if __name__ == '__main__':
    unittest.main()

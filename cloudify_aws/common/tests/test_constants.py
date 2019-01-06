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

import unittest

from cloudify_aws.common import constants


class TestConstants(unittest.TestCase):

    def test_default_constants(self):
        self.assertEqual(constants.AWS_CONFIG_PROPERTY, 'client_config')
        self.assertEqual(constants.EXTERNAL_RESOURCE_ID, 'aws_resource_id')
        self.assertEqual(constants.EXTERNAL_RESOURCE_ARN, 'aws_resource_arn')
        self.assertEqual(constants.REL_CONTAINED_IN,
                         'cloudify.relationships.contained_in')


if __name__ == '__main__':
    unittest.main()

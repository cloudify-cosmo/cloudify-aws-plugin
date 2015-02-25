########
# Copyright (c) 2014 GigaSpaces Technologies Ltd. All rights reserved
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

# Built-in Imports
import testtools

# Third Party Imports

# Cloudify Imports is imported and used in operations
from ec2 import configure


class TestConfigure(testtools.TestCase):

    def test_configure_file_contents(self):

        configure_file = configure.BotoConfig().get_temp_file()

        file_contents = self.get_file_as_string(configure_file)

        self.assertIn('aws_secret_access_key', file_contents)
        self.assertIn('aws_access_key_id', file_contents)
        self.assertIn('Credentials', file_contents)

    def get_file_as_string(self, file_path):
        with open(file_path, 'r') as configure_file:
            return configure_file.read()

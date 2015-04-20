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

# Built-in Imports
import testtools
from StringIO import StringIO
from ConfigParser import ConfigParser


class TestConfigure(testtools.TestCase):

    def mock_profile_string(self):
        creds = ConfigParser()
        creds.add_section('mock')
        creds.set(
            'mock',
            'aws_access_key_id',
            'AKIAZ0ZZZZ0ZZZOZZZ0Z')
        creds.set(
            'mock',
            'aws_secret_access_key',
            'zzZ/Z0Zzz00ZZzzZzZZZzzZ0ZZ/z+ZzZZZZZ+ZzZ')
        string = StringIO()
        creds.write(string)
        return string.getvalue()

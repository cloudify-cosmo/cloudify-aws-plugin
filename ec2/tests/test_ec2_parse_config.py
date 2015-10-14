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

# Builtin Imports
import os
import tempfile
from ConfigParser import ConfigParser

# Third Party Imports
import testtools
from nose.tools import nottest

# Cloudify Imports
from ec2 import connection
from ec2 import constants
from cloudify.exceptions import NonRecoverableError


@nottest
def test_config(**kwargs):
    """
    decorator-generator that can be used on test functions to set
    key-value pairs that may later be injected into functions using the
    "inject_test_config" decorator
    :param kwargs: key-value pairs to be stored on the function object
    :return: a decorator for a test function, which stores with the test's
     config on the test function's object under the "test_config" attribute
    """
    def _test_config_decorator(test_func):
        test_func.test_config = kwargs
        return test_func
    return _test_config_decorator


@nottest
def inject_test_config(f):
    """
    decorator for injecting "test_config" into a test obj method.
    also see the "test_config" decorator
    :param f: a test obj method to be injected with the "test_config" parameter
    :return: the method augmented with the "test_config" parameter
    """
    def _wrapper(test_obj, *args, **kwargs):
        test_func = getattr(test_obj, test_obj.id().split('.')[-1])
        if hasattr(test_func, 'test_config'):
            kwargs['test_config'] = test_func.test_config
        return f(test_obj, *args, **kwargs)
    return _wrapper


class TestParser(testtools.TestCase):

    @inject_test_config
    def setUp(self, test_config):

        os.environ[constants.AWS_CONFIG_PATH_ENV_VAR_NAME] = \
            self._generate_config_file(test_config["type"]) \
            if test_config["type"] != "no_file" \
            else "/unicorn-bigfoot/pony.cfg"

        super(TestParser, self).setUp()

    def tearDown(self):
        if constants.AWS_CONFIG_PATH_ENV_VAR_NAME in os.environ:
            del os.environ[constants.AWS_CONFIG_PATH_ENV_VAR_NAME]
        super(TestParser, self).tearDown()

    @test_config(type="invalid_section")
    def test_aws_config_file_invalid_section(self):
        client = connection.EC2ConnectionClient()
        self.assertRaisesRegexp(Exception,
                                'Unsupported Boto section',
                                client._get_aws_config_from_file)

    @test_config(type="invalid_option")
    def test_aws_config_file_invalid_option(self):
        client = connection.EC2ConnectionClient()
        self.assertRaisesRegexp(Exception,
                                'Unsupported Boto option',
                                client._get_aws_config_from_file)

    @test_config(type="valid")
    def test_aws_config_file_valid(self):
        client = connection.EC2ConnectionClient()
        config = client._get_aws_config_from_file()

        config_schema = constants.BOTO_CONFIG_SCHEMA
        for opt_group in config_schema.values():
            for opt in opt_group:
                self.assertIn(opt, config)

    @test_config(type="no_file")
    def test_aws_config_no_file(self):
        client = connection.EC2ConnectionClient()
        self.assertRaises(NonRecoverableError,
                          client._get_aws_config_from_file)

    def _generate_config_file(self, config_type):
        """Generate Boto cfg file and return its path
        """

        __, config_path = tempfile.mkstemp()
        config = ConfigParser()

        config_schema = constants.BOTO_CONFIG_SCHEMA
        for section in config_schema:
            config.add_section(section)
            for key in config_schema[section]:
                config.set(section, key, key)

        if config_type == "invalid_option":
            config.set("Boto", "invalid_option", "foo")
            config.set("Credentials", "invalid_option2", "foo")
        if config_type == "invalid_section":
            config.add_section("invalid_section1")
            config.add_section("invalid_section2")

        with open(config_path, 'w') as config_file:
            config.write(config_file)

        return config_path

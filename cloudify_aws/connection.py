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
import ConfigParser
import os

# Third-party Imports
from boto.ec2 import get_region
from boto.ec2 import EC2Connection
from boto.ec2.elb import ELBConnection
from boto.vpc import VPCConnection
from boto.regioninfo import RegionInfo
from boto.ec2.elb import connect_to_region as connect_to_elb_region

# Cloudify Imports
from . import utils, constants
from cloudify.exceptions import NonRecoverableError


class EC2ConnectionClient():
    """Provides functions for getting the EC2 Client
    """

    def __init__(self):
        self.connection = None

    def client(self):
        """Represents the EC2Connection Client
        """

        aws_config_property = (self._get_aws_config_property() or
                               self._get_aws_config_from_file())
        if not aws_config_property:
            return EC2Connection()
        elif aws_config_property.get('ec2_region_name'):
            region_object = \
                get_region(aws_config_property['ec2_region_name'])
            aws_config = aws_config_property.copy()
            if region_object and 'ec2_region_endpoint' in aws_config_property:
                region_object.endpoint = \
                    aws_config_property['ec2_region_endpoint']
            aws_config['region'] = region_object
        else:
            aws_config = aws_config_property.copy()

        aws_config = self.aws_config_cleanup(aws_config)

        return EC2Connection(**aws_config)

    def _get_aws_config_property(self):
        node_properties = \
            utils.get_instance_or_source_node_properties()
        return node_properties[constants.AWS_CONFIG_PROPERTY]

    def _get_aws_config_from_file(self):
        """Get aws config from a Boto cfg file
        """
        config_path = self._get_boto_config_file_path()
        return self._parse_config_file(config_path) if config_path else None

    def _get_boto_config_file_path(self):
        """Get aws config file path from environment
        """
        return os.environ.get(constants.AWS_CONFIG_PATH_ENV_VAR_NAME)

    def _parse_config_file(self, path):
        """Parse and validate Boto cfg file
        """
        path = str(path)
        if not os.path.isfile(path):
            raise NonRecoverableError('no aws config file at {0}'.format(path))

        parser = ConfigParser.ConfigParser()
        parser.read(path)

        if len(parser.sections()) == 0:
            raise NonRecoverableError("aws config file is empty")

        config_schema = constants.BOTO_CONFIG_SCHEMA
        config = {}

        # validate sections
        invalid_sections = \
            [s for s in parser.sections() if s not in config_schema]
        if invalid_sections:
            raise NonRecoverableError("Unsupported Boto section(s): {0}".
                                      format(', '.join(invalid_sections)))

        # validate options and populate config dict (option > value)
        invalid_options = []

        for section in parser.sections():
            allowed_opt_list = config_schema[section]
            for opt, value in parser.items(section):
                if opt in allowed_opt_list:
                    config[opt] = value
                else:
                    invalid_options.append((section, opt))

        if invalid_options:
            raise NonRecoverableError("Unsupported Boto option(s): {0}".
                                      format(invalid_options))

        return config

    def aws_config_cleanup(self, aws_config):

        # for backward compatibility,
        # delete this key before passing config to Boto
        if 'ec2_region_name' in aws_config:
            del(aws_config['ec2_region_name'])

        if 'ec2_region_endpoint' in aws_config:
            del(aws_config["ec2_region_endpoint"])

        if 'elb_region_name' in aws_config:
            del(aws_config["elb_region_name"])

        if 'elb_region_endpoint' in aws_config:
            del(aws_config["elb_region_endpoint"])

        return aws_config


class ELBConnectionClient(EC2ConnectionClient):

    def client(self):
        """Represents the ELBConnection Client
        """

        aws_config_property = (self._get_aws_config_property() or
                               self._get_aws_config_from_file())
        if not aws_config_property:
            return ELBConnection()

        aws_config = aws_config_property.copy()

        if aws_config_property.get('elb_region_name') and \
                aws_config_property.get('elb_region_endpoint'):
            region_object = \
                get_region(aws_config_property['elb_region_name'])
            region_object.endpoint = \
                aws_config_property['elb_region_endpoint']
            aws_config['region'] = region_object
        elif aws_config_property.get('elb_region_name') and \
                not aws_config_property.get('elb_region_endpoint'):
            aws_config['region'] = aws_config_property['elb_region_name']

        aws_config = self.aws_config_cleanup(aws_config)

        if 'region' in aws_config:
            if type(aws_config['region']) is RegionInfo:
                return ELBConnection(**aws_config)
            elif type(aws_config['region']) is str:
                elb_region = aws_config.pop('region')
                return connect_to_elb_region(
                        elb_region, **aws_config)

        raise NonRecoverableError(
                'Cannot connect to ELB endpoint. '
                'You must either provide elb_region_name or both '
                'elb_region_name and elb_region_endpoint.')


class VPCConnectionClient(EC2ConnectionClient):
    """Provides functions for getting the VPC Client
    """

    def client(self, aws_config=None):
        """Represents the VPCConnection Client
        """

        aws_config_property = (self._get_aws_config_property(aws_config) or
                               self._get_aws_config_from_file())
        if not aws_config_property:
            return VPCConnection()
        elif aws_config_property.get('ec2_region_name'):
            region_object = \
                get_region(aws_config_property['ec2_region_name'])
            aws_config = aws_config_property.copy()
            if region_object and 'ec2_region_endpoint' in aws_config_property:
                region_object.endpoint = \
                    aws_config_property['ec2_region_endpoint']
            aws_config['region'] = region_object
        else:
            aws_config = aws_config_property.copy()

        if 'ec2_region_name' in aws_config:
            del(aws_config['ec2_region_name'])

        # for backward compatibility,
        # delete this key before passing config to Boto
        if 'ec2_region_endpoint' in aws_config:
            del(aws_config["ec2_region_endpoint"])

        return VPCConnection(**aws_config)

    def _get_aws_config_property(self, aws_config=None):
        if aws_config:
            return aws_config
        node_properties = \
            utils.get_instance_or_source_node_properties()
        return node_properties[constants.AWS_CONFIG_PROPERTY]

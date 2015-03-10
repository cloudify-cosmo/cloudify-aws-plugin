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

import os
import copy
import random
from contextlib import contextmanager

from boto.ec2 import EC2Connection

from cosmo_tester.framework.handlers import (
    BaseHandler,
    BaseCloudifyInputsConfigReader)
from cosmo_tester.framework.util import get_actual_keypath


class EC2CleanupContext(BaseHandler.CleanupContext):
    pass


class CloudifyEC2InputsConfigReader(BaseCloudifyInputsConfigReader):

    def __init__(self, cloudify_config, manager_blueprint_path, **kwargs):
        super(CloudifyEC2InputsConfigReader, self).__init__(
            cloudify_config, manager_blueprint_path=manager_blueprint_path,
            **kwargs)

    @property
    def management_server_name(self):
        return self.config['manager_server_name']

    @property
    def agent_key_path(self):
        return self.config['agent_private_key_path']

    @property
    def management_user_name(self):
        return self.config['manager_server_user']

    @property
    def management_key_path(self):
        return self.config['manager_private_key_path']

    @property
    def agent_keypair_name(self):
        return self.config['agent_public_key_name']

    @property
    def management_keypair_name(self):
        return self.config['manager_public_key_name']

    @property
    def agents_security_group(self):
        return self.config['agents_security_group_name']

    @property
    def management_security_group(self):
        return self.config['manager_security_group_name']


class EC2Handler(BaseHandler):

    CleanupContext = EC2CleanupContext
    CloudifyConfigReader = CloudifyEC2InputsConfigReader

    def before_bootstrap(self):
        super(EC2Handler, self).before_bootstrap()
        with self.update_cloudify_config() as patch:
            suffix = '-%06x' % random.randrange(16 ** 6)
            server_name_prop_path = \
                'compute.management_server.instance.name' if \
                self.env.is_provider_bootstrap else 'manager_server_name'
            patch.append_value(server_name_prop_path, suffix)

    def after_bootstrap(self, provider_context):
        super(EC2Handler, self).after_bootstrap()
        resources = provider_context['resources']
        agent_keypair = resources['agents_keypair']
        management_keypair = resources['management_keypair']
        self.remove_agent_keypair = agent_keypair['external_resource'] is False
        self.remove_management_keypair = \
            management_keypair['external_resource'] is False

    def after_teardown(self):
        super(EC2Handler, self).after_teardown()
        if self.remove_agent_key:
            agent_key_path = get_actual_keypath(
                self.env, self.env.agent_key_path, raise_on_missing=False)
            if agent_key_path:
                os.remove(agent_key_path)

        if self.remove_management_key:
            management_key_path = get_actual_keypath(
                self.env, self.env.management_key_path, raise_on_missing=False)
            if management_key_path:
                os.remove(management_key_path)

    def ec2_client(self):
        credentials = self._client_credentials()
        return EC2Connection(
            aws_access_key_id=credentials['aws_access_key_id'],
            aws_secret_access_key_id=credentials['aws_secret_access_key_id'])

    def ec2_infra_state(self):
        ec2_client = self.ec2_client()

        return {
            'instances': dict(self._instances(ec2_client)),
            'key_pairs': dict(self._key_pairs(ec2_client)),
            'elasticips': dict(self._elasticips(ec2_client)),
            'security_groups': dict(self.security_groups(ec2_client))
        }

    def ec2_infra_state_delta(self, before, after):
        after = copy.deepcopy(after)
        return {
            prop: self._remove_keys(after[prop], before[prop].keys())
            for prop in before.keys()
        }

    def _remove_ec2_resources(self, resources_to_remove):
        ec2_client = self.ec2_client()

        instances = [instance for instance in reservation.instances
                     for reservation in ec2_client.get_all_reservations()]
        key_pairs = ec2_client.get_all_key_pairs()
        elasticips = ec2_client.get_all_addresses()
        security_groups = ec2_client.get_all_security_groups()

        failed = {
            'instances': {},
            'key_pairs': {},
            'elasticips': {},
            'security_groups': {}
        }

        for instance in instances:
            if instance.id in resources_to_remove['instances']:
                with self._handled_exception(instance.id, failed, 'servers'):
                    ec2_client.terminate_instances(instance.id)

        for kp in key_pairs:
            if kp.name in resources_to_remove['key_pairs']:
                with self._handled_exception(kp.id, failed, 'key_pairs'):
                    ec2_client.delete_key_pair(kp.name)

        for elasticip in elasticips:
            if elasticip.public_ip in resources_to_remove['elasticips']:
                with self._handled_exception(
                        elasticip.public_ip, failed, 'elasticips'):
                    elasticip.delete()

        for security_group in security_groups:
            if security_group.id in resources_to_remove['security_groups']:
                with self._handled_exception(
                        security_group.id, failed, 'security_groups'):
                    ec2_client.delete_security_group(security_group.id)

        return failed

    def _client_credentials(self):
        return {
            'aws_access_key_id': self.env.aws_access_key_id,
            'aws_secret_access_key_id': self.env.aws_secret_access_key_id
        }

    def _security_groups(self, ec2_client):
        return [(security_group.id, security_group.name)
                for security_group in ec2_client.get_all_security_groups()]

    def _instances(self, ec2_client):
        return [instance.id for instance in reservation.instances for
                reservation in ec2_client.get_all_reservations()]

    def _key_pairs(self, ec2_client):
        return [kp.id for kp in ec2_client.get_all_key_pairs()]

    def _elasticips(self, ec2_client):
        return [address.public_ip
                for address in ec2_client.get_all_addresses()]

    @contextmanager
    def _handled_exception(self, resource_id, failed, resource_group):
        try:
            yield
        except BaseException, ex:
            failed[resource_group][resource_id] = ex

handler = EC2Handler

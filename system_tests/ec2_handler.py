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

import copy
from contextlib import contextmanager

from boto.ec2 import get_region
from boto.ec2 import EC2Connection
from boto.vpc import VPCConnection

from cosmo_tester.framework.handlers import (
    BaseHandler,
    BaseCloudifyInputsConfigReader)


class EC2CleanupContext(BaseHandler.CleanupContext):
    def __init__(self, context_name, env):
        super(EC2CleanupContext, self).__init__(context_name, env)
        self.before_run = self.env.handler.ec2_infra_state()

    def cleanup(self):
        super(EC2CleanupContext, self).cleanup()
        resources_to_teardown = self.get_resources_to_teardown()
        if self.skip_cleanup:
            self.logger.warn('[{0}] SKIPPING cleanup: of the resources: {1}'
                             .format(self.context_name, resources_to_teardown))
            return
        self.logger.info('[{0}] Performing cleanup: will try removing these '
                         'resources: {1}'
                         .format(self.context_name, resources_to_teardown))

        leftovers = self.env.handler.remove_ec2_resources(
            resources_to_teardown)
        self.logger.info('[{0}] Leftover resources after cleanup: {1}'
                         .format(self.context_name, leftovers))

    def get_resources_to_teardown(self):
        current_state = self.env.handler.ec2_infra_state()
        return self.env.handler.ec2_infra_state_delta(
            before=self.before_run, after=current_state)

    @classmethod
    def clean_all(cls, env):
        resources_to_be_removed = env.handler.ec2_infra_state()
        cls.logger.info(
            "Current resources in account:"
            " {0}".format(resources_to_be_removed))
        if env.use_existing_manager_keypair:
            resources_to_be_removed['key_pairs'].pop(
                env.management_keypair_name, None)
        if env.use_existing_agent_keypair:
            resources_to_be_removed['key_pairs'].pop(env.agent_keypair_name,
                                                     None)
        cls.logger.info(
            "resources_to_be_removed: {0}".format(resources_to_be_removed))
        failed = env.handler.remove_ec2_resources(resources_to_be_removed)
        errorflag = not (
            (len(failed['instances']) == 0) and
            (len(failed['key_pairs']) == 0) and
            (len(failed['elasticips']) == 0) and
            # This is the default security group which cannot
            # be removed by a user.
            (len(failed['security_groups']) == 1))
        if errorflag:
            raise Exception(
                "Unable to clean up Environment, "
                "resources remaining: {0}".format(failed))


class CloudifyEC2InputsConfigReader(BaseCloudifyInputsConfigReader):
    @property
    def aws_access_key_id(self):
        return self.config['aws_access_key_id']

    @property
    def aws_secret_access_key(self):
        return self.config['aws_secret_access_key']

    @property
    def ec2_region_name(self):
        return self.config['ec2_region_name']

    @property
    def management_user_name(self):
        return self.config['manager_server_user']

    @property
    def management_server_name(self):
        return self.config['manager_server_name']

    @property
    def agent_key_path(self):
        return self.config['agent_key_pair_file_path']

    @property
    def management_key_path(self):
        return self.config['manager_key_pair_file_path']

    @property
    def agent_keypair_name(self):
        return self.config['agent_keypair_name']

    @property
    def management_keypair_name(self):
        return self.config['manager_keypair_name']

    @property
    def agents_security_group(self):
        return self.config['agent_security_group_name']

    @property
    def management_security_group(self):
        return self.config['manager_security_group_name']

    @property
    def use_existing_manager_keypair(self):
        return self.config['use_existing_manager_keypair']

    @property
    def use_existing_agent_keypair(self):
        return self.config['use_existing_agent_keypair']


class EC2Handler(BaseHandler):
    CleanupContext = EC2CleanupContext
    CloudifyConfigReader = CloudifyEC2InputsConfigReader

    def ec2_client(self):
        credentials = self._client_credentials()
        return EC2Connection(**credentials)

    def vpc_client(self):
        credentials = self._client_credentials()
        return VPCConnection(**credentials)

    def ec2_infra_state(self):

        ec2_client = self.ec2_client()
        vpc_client = self.vpc_client()

        return {
            'instances': dict(self._instances(ec2_client)),
            'key_pairs': dict(self._key_pairs(ec2_client)),
            'elasticips': dict(self._elasticips(ec2_client)),
            'security_groups': dict(self._security_groups(ec2_client)),
            'vpcs': dict(self._vpcs(vpc_client)),
            'subnets': dict(self._subnets(vpc_client)),
            'internet_gateways': dict(self._internet_gateways(vpc_client)),
            'vpn_gateways': dict(self._vpn_gateways(vpc_client)),
            'customer_gateways': dict(self._customer_gateways(vpc_client)),
            'network_acls': dict(self._network_acls(vpc_client)),
            'dhcp_options_sets': dict(self._dhcp_options_sets(vpc_client)),
            'route_tables': dict(self._route_tables(vpc_client))
        }

    def ec2_infra_state_delta(self, before, after):

        after = copy.deepcopy(after)

        return {
            prop: self._remove_keys(after[prop], before[prop].keys())
            for prop in before.keys()
        }

    def remove_ec2_resources(self, resources_to_remove):

        ec2_client = self.ec2_client()
        vpc_client = self.vpc_client()

        instances = self._instances(ec2_client)
        key_pairs = self._key_pairs(ec2_client)
        elasticips = self._elasticips(ec2_client)
        security_groups = self._security_groups(ec2_client)
        vpcs = self._vpcs(vpc_client)
        subnets = self._subnets(vpc_client)
        internet_gateways = self._internet_gateways(vpc_client)
        vpn_gateways = self._vpn_gateways(vpc_client)
        customer_gateways = self._customer_gateways(vpc_client)
        network_acls = self._network_acls(vpc_client)
        dhcp_options_sets = self._dhcp_options_sets(vpc_client)
        route_tables = self._route_tables(vpc_client)

        failed = {
            'instances': {},
            'key_pairs': {},
            'elasticips': {},
            'security_groups': {},
            'vpcs': {},
            'subnets': {},
            'internet_gateways': {},
            'vpn_gateways': {},
            'customer_gateways': {},
            'network_acls': {},
            'dhcp_options_sets': {},
            'route_tables': {}
        }

        for instance_id, _ in instances:
            if instance_id in resources_to_remove['instances']:
                with self._handled_exception(instance_id, failed, 'instances'):
                    ec2_client.terminate_instances(instance_id)

        for kp_name, _ in key_pairs:
            if kp_name in resources_to_remove['key_pairs']:
                with self._handled_exception(kp_name, failed, 'key_pairs'):
                    ec2_client.delete_key_pair(kp_name)

        for elasticip_id, elasticip in elasticips:
            if elasticip_id in resources_to_remove['elasticips']:
                with self._handled_exception(
                        elasticip_id, failed, 'elasticips'):
                    ec2_client.get_all_addresses(elasticip_id)[0].release()

        for security_group_id, _ in security_groups:
            if security_group_id in resources_to_remove['security_groups']:
                with self._handled_exception(
                        security_group_id, failed, 'security_groups'):
                    ec2_client.get_all_security_groups(
                        group_ids=[security_group_id])[0].delete()

        for vpc_id, _ in vpcs:
            if vpc_id in resources_to_remove['vpcs']:
                with self._handled_exception(vpc_id, failed, 'vpcs'):
                    vpc_client.delete_vpc(vpc_id)

        for subnet_id, _ in subnets:
            if subnet_id in resources_to_remove['subnets']:
                with self._handled_exception(subnet_id, failed, 'subnets'):
                    vpc_client.delete_subnet(subnet_id)

        for internet_gateway_id, _ in internet_gateways:
            if internet_gateway_id in resources_to_remove['internet_gateways']:
                with self._handled_exception(internet_gateway_id,
                                             failed,
                                             'internet_gateways'):
                    vpc_client.delete_internet_gateway(internet_gateway_id)

        for vpn_gateway_id, _ in vpn_gateways:
            if vpn_gateway_id in resources_to_remove['vpn_gateways']:
                with self._handled_exception(vpn_gateway_id,
                                             failed,
                                             'vpn_gateways'):
                    vpc_client.delete_vpn_gateway(vpn_gateway_id)

        for customer_gateway_id, _ in customer_gateways:
            if customer_gateway_id in resources_to_remove['customer_gateways']:
                with self._handled_exception(customer_gateway_id,
                                             failed,
                                             'customer_gateways'):
                    vpc_client.delete_customer_gateway(customer_gateway_id)

        for network_acl_id, _ in network_acls:
            if network_acl_id in resources_to_remove['network_acls']:
                with self._handled_exception(network_acl_id,
                                             failed,
                                             'network_acls'):
                    vpc_client.delete_network_acl(network_acl_id)

        for dhcp_options_set_id, _ in dhcp_options_sets:
            if dhcp_options_set_id in resources_to_remove['dhcp_options_sets']:
                with self._handled_exception(dhcp_options_set_id,
                                             failed,
                                             'dhcp_options_sets'):
                    vpc_client.delete_dhcp_options(dhcp_options_set_id)

        for route_table_id, _ in route_tables:
            if route_table_id in resources_to_remove['route_tables']:
                with self._handled_exception(route_table_id, failed,
                                             'route_tables'):
                    vpc_client.delete_route_table(route_table_id)

        return failed

    def _client_credentials(self):

        region = get_region(self.env.ec2_region_name)

        return {
            'aws_access_key_id': self.env.aws_access_key_id,
            'aws_secret_access_key': self.env.aws_secret_access_key,
            'region': region
        }

    def _security_groups(self, ec2_client):
        return [(security_group.id, security_group.id)
                for security_group in ec2_client.get_all_security_groups()]

    def _instances(self, ec2_client):
        return [(instance[0].id, instance[0].id)
                for instance in
                [res.instances for res in ec2_client.get_all_reservations()]]

    def _key_pairs(self, ec2_client):
        return [(kp.name, kp.name)
                for kp in ec2_client.get_all_key_pairs()]

    def _elasticips(self, ec2_client):
        return [(address.public_ip, address.public_ip)
                for address in ec2_client.get_all_addresses()]

    def _vpcs(self, vpc_client):
        return [(vpc.id, vpc.id)
                for vpc in vpc_client.get_all_vpcs()]

    def _subnets(self, vpc_client):
        return [(subnet.id, subnet.id)
                for subnet in vpc_client.get_all_subnets()]

    def _internet_gateways(self, vpc_client):
        return [(internet_gateway.id, internet_gateway.id)
                for internet_gateway in vpc_client.get_all_internet_gateways()]

    def _vpn_gateways(self, vpc_client):
        return [(vpn_gateway.id, vpn_gateway.id)
                for vpn_gateway in vpc_client.get_all_vpn_gateways()]

    def _customer_gateways(self, vpc_client):
        return [(customer_gateway.id, customer_gateway.id)
                for customer_gateway in vpc_client.get_all_customer_gateways()]

    def _network_acls(self, vpc_client):
        return [(network_acl.id, network_acl.id)
                for network_acl in vpc_client.get_all_network_acls()]

    def _dhcp_options_sets(self, vpc_client):
        return [(dhcp_options_set.id, dhcp_options_set.id)
                for dhcp_options_set in vpc_client.get_all_dhcp_options()]

    def _route_tables(self, vpc_client):
        return [(route_table.id, route_table.id)
                for route_table in vpc_client.get_all_route_tables()]

    def _remove_keys(self, dct, keys):
        for key in keys:
            if key in dct:
                del dct[key]
        return dct

    @contextmanager
    def _handled_exception(self, resource_id, failed, resource_group):
        try:
            yield
        except BaseException, ex:
            failed[resource_group][resource_id] = ex


handler = EC2Handler

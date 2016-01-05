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
from time import sleep
from contextlib import contextmanager

from boto.ec2 import get_region
from boto.ec2 import EC2Connection
from boto.vpc import VPCConnection
from boto.ec2.elb import connect_to_region as connect_to_elb_region
from boto.exception import EC2ResponseError

from cosmo_tester.framework.handlers import (
    BaseHandler,
    BaseCloudifyInputsConfigReader)


class EC2CleanupContext(BaseHandler.CleanupContext):
    def __init__(self, context_name, env):
        super(EC2CleanupContext, self).__init__(context_name, env)
        self.before_run = self.env.handler.ec2_infra_state()

    @classmethod
    def clean_resources(cls, env, resources):

        cls.logger.info('Performing cleanup: will try removing these '
                        'resources: {0}'
                        .format(resources))

        failed_to_remove = {}

        for segment in range(6):
            failed_to_remove = \
                env.handler.remove_ec2_resources(resources)
            if not failed_to_remove:
                break

        cls.logger.info('Leftover resources after cleanup: {0}'
                        .format(failed_to_remove))

        return failed_to_remove

    def cleanup(self):
        super(EC2CleanupContext, self).cleanup()
        resources_to_teardown = self.get_resources_to_teardown()
        if self.skip_cleanup:
            self.logger.warn('[{0}] SKIPPING cleanup: of the resources: {1}'
                             .format(self.context_name, resources_to_teardown))
            return

        self.clean_resources(self.env, resources_to_teardown)

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

        failed_to_remove = cls.clean_resources(env, resources_to_be_removed)

        errorflag = not (
            (len(failed_to_remove['instances']) == 0) and
            (len(failed_to_remove['key_pairs']) == 0) and
            (len(failed_to_remove['elasticips']) == 0) and
            (len(failed_to_remove['security_groups']) == 0) and
            (len(failed_to_remove['vpcs']) == 0))
        if errorflag:
            raise Exception(
                "Unable to clean up Environment, "
                "resources remaining: {0}".format(failed_to_remove))


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

    def elb_client(self):
        credentials = self._client_credentials()
        credentials.pop('region')
        elb_region = self.env.ec2_region_name
        return connect_to_elb_region(elb_region, **credentials)

    def ec2_infra_state(self):

        ec2_client = self.ec2_client()
        vpc_client = self.vpc_client()
        elb_client = self.elb_client()

        return {
            'instances': dict(self._instances(ec2_client)),
            'key_pairs': dict(self._key_pairs(ec2_client)),
            'elasticips': dict(self._elasticips(ec2_client)),
            'security_groups': dict(self._security_groups(ec2_client)),
            'volumes': dict(self._volumes(ec2_client)),
            'snapshots': dict(self._snapshots(ec2_client)),
            'load_balancers': dict(self._elbs(elb_client)),
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
        elb_client = self.elb_client()

        instances = self._instances(ec2_client)
        key_pairs = self._key_pairs(ec2_client)
        elasticips = self._elasticips(ec2_client)
        security_groups = self._security_groups(ec2_client)
        volumes = self._volumes(ec2_client)
        snapshots = self._snapshots(ec2_client)
        load_balancers = self._elbs(elb_client)
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
            'volumes': {},
            'snapshots': {},
            'load_balancers': {},
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
                    instances = ec2_client.get_only_instances(instance_id)
                    instance = instances[0]
                    instance.terminate()
                    # We need to make sure that the instance is terminated
                    # or VPC stuff is going to fail.
                    for segment in range(5):
                        if 'terminated' not in instance.update():
                            # Terminate is idempotent
                            instance.terminate()
                            sleep(10)

                    if 'terminated' not in instance.state:
                        raise RuntimeError(
                            'The test failed because '
                            'instance would not terminate.')

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

        for volume_id, _ in volumes:
            if volume_id in resources_to_remove['volumes']:
                with self._handled_exception(
                        volume_id, failed, 'volumes'):
                    volumes = []
                    try:
                        volumes = ec2_client.get_all_volumes(volume_id)
                    except EC2ResponseError:
                        continue
                    for volume in volumes:
                        if 'in-use' in volume.status:
                            volume.detach(force=True)
                        volume.delete()

        for snapshot_id, _ in snapshots:
            if snapshot_id in resources_to_remove['snapshots']:
                with self._handled_exception(
                        snapshot_id, failed, 'snapshots'):
                    ec2_client.get_all_snapshots(snapshot_id)[0].delete()

        for elb_name, _ in load_balancers:
            if elb_name in resources_to_remove['load_balancers']:
                with self._handled_exception(
                        elb_name, failed, 'load_balancers'):
                    elb_client.get_all_load_balancers(elb_name)[0].delete()

        for customer_gateway_id, _ in customer_gateways:
            if customer_gateway_id in resources_to_remove['customer_gateways']:
                with self._handled_exception(customer_gateway_id,
                                             failed,
                                             'customer_gateways'):
                    for vpnx in vpc_client.get_all_vpn_connections():
                        if customer_gateway_id in vpnx.customer_gateway_id:
                            vpnx.delete()
                    vpc_client.delete_customer_gateway(customer_gateway_id)

        for vpn_gateway_id, _ in vpn_gateways:
            if vpn_gateway_id in resources_to_remove['vpn_gateways']:
                with self._handled_exception(vpn_gateway_id,
                                             failed,
                                             'vpn_gateways'):
                    vgws = vpc_client.get_all_vpn_gateways(vpn_gateway_id)
                    for vgw in vgws:
                        for attachment in vgw.attachments:
                            try:
                                vpc_client.detach_vpn_gateway(
                                    vgw.id, attachment.vpc_id)
                            except EC2ResponseError:
                                pass
                    vpc_client.delete_vpn_gateway(vpn_gateway_id)

        for subnet_id, _ in subnets:
            if subnet_id in resources_to_remove['subnets']:
                with self._handled_exception(subnet_id, failed, 'subnets'):
                    vpc_client.delete_subnet(subnet_id)

        for internet_gateway_id, _ in internet_gateways:
            if internet_gateway_id in resources_to_remove['internet_gateways']:
                with self._handled_exception(internet_gateway_id,
                                             failed,
                                             'internet_gateways'):
                    igs = vpc_client.get_all_internet_gateways(
                        internet_gateway_id)
                    for ig in igs:
                        for attachment in ig.attachments:
                            try:
                                vpc_client.detach_internet_gateway(
                                    internet_gateway_id, attachment.vpc_id)
                            except EC2ResponseError:
                                pass
                    vpc_client.delete_internet_gateway(internet_gateway_id)

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
                    for route_table in vpc_client.get_all_route_tables(
                            route_table_id):
                        for association in route_table.associations:
                            vpc_client.disassociate_route_table(
                                association.id)
                        for route in route_table.routes:
                            try:
                                vpc_client.delete_route(
                                    route_table.id,
                                    route.destination_cidr_block)
                            except EC2ResponseError:
                                pass
                    vpc_client.delete_route_table(route_table_id)

        for network_acl_id, _ in network_acls:
            if network_acl_id in resources_to_remove['network_acls']:
                with self._handled_exception(network_acl_id,
                                             failed,
                                             'network_acls'):
                    for network_acl in vpc_client.get_all_network_acls(
                            network_acl_id):
                        for association in network_acl.associations:
                            vpc_client.disassociate_network_acl(
                                association.subnet_id)
                    vpc_client.delete_network_acl(network_acl_id)

        for vpc_id, _ in vpcs:
            if vpc_id in resources_to_remove['vpcs']:
                with self._handled_exception(vpc_id, failed, 'vpcs'):
                    for peer_cx in \
                            vpc_client.get_all_vpc_peering_connections():
                        if vpc_id in peer_cx.requester_vpc_info.vpc_id:
                            vpc_client.delete_vpc_peering_connection(
                                peer_cx.id)
                    vpc_client.delete_vpc(vpc_id)

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
                for security_group in ec2_client.get_all_security_groups()
                if 'default' not in security_group.name]

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

    def _volumes(self, ec2_client):
        return [(vol.id, vol.id)
                for vol in ec2_client.get_all_volumes()]

    def _snapshots(self, ec2_client):
        return [(ss.id, ss.id)
                for ss in ec2_client.get_all_snapshots(owner='self')]

    def _elbs(self, elb_client):
        return [(elb.name, elb.name)
                for elb in elb_client.get_all_load_balancers()]

    def _vpcs(self, vpc_client):
        return [(vpc.id, vpc.id)
                for vpc in vpc_client.get_all_vpcs()
                if not vpc.is_default]

    def _subnets(self, vpc_client):
        default_vpc = ''
        vpcs = vpc_client.get_all_vpcs()
        for vpc in vpcs:
            if vpc.is_default:
                default_vpc = vpc.id
        return [(subnet.id, subnet.id)
                for subnet in vpc_client.get_all_subnets()
                if subnet.vpc_id != default_vpc]

    def _internet_gateways(self, vpc_client):
        default_vpc_id = ''
        all_vpcs = vpc_client.get_all_vpcs()
        all_internet_gateways = vpc_client.get_all_internet_gateways()
        not_default_internet_gateways = []
        for vpc in all_vpcs:
            if vpc.is_default:
                default_vpc_id = vpc.id
        for ig in all_internet_gateways:
            for attachment in ig.attachments:
                if attachment.vpc_id != default_vpc_id:
                    not_default_internet_gateways.append((ig.id, ig.id))
        return not_default_internet_gateways

    def _vpn_gateways(self, vpc_client):
        return [(vpn_gateway.id, vpn_gateway.id)
                for vpn_gateway in vpc_client.get_all_vpn_gateways()]

    def _customer_gateways(self, vpc_client):
        return [(customer_gateway.id, customer_gateway.id)
                for customer_gateway in vpc_client.get_all_customer_gateways()]

    def _network_acls(self, vpc_client):
        default_vpc = ''
        vpcs = vpc_client.get_all_vpcs()
        for vpc in vpcs:
            if vpc.is_default:
                default_vpc = vpc.id
        return [(network_acl.id, network_acl.id)
                for network_acl in vpc_client.get_all_network_acls()
                if network_acl.vpc_id != default_vpc]

    def _dhcp_options_sets(self, vpc_client):
        default_dopt = ''
        vpcs = vpc_client.get_all_vpcs()
        for vpc in vpcs:
            if vpc.is_default:
                default_dopt = vpc.dhcp_options_id
        return [(dopt.id, dopt.id) for dopt
                in vpc_client.get_all_dhcp_options()
                if dopt.id != default_dopt]

    def _route_tables(self, vpc_client):
        default_vpc = ''
        vpcs = vpc_client.get_all_vpcs()
        for vpc in vpcs:
            if vpc.is_default:
                default_vpc = vpc.id
        return [(rtb.id, rtb.id) for rtb
                in vpc_client.get_all_route_tables()
                if rtb.vpc_id != default_vpc and not any(
                association.main for association in rtb.associations)]

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

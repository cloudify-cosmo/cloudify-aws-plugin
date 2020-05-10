# Standard imports
import os
import re
import sys
from time import sleep

# Third party imports
from ecosystem_tests import (
    EcosystemTestBase,
    utils,
    IP_ADDRESS_REGEX,
    PasswordFilter
)

from cloudify._compat import text_type

os.environ['ECOSYSTEM_SESSION_PASSWORD'] = 'admin'
sensitive_data = [os.environ['AWS_SECRET_ACCESS_KEY'],
                  os.environ['AWS_ACCESS_KEY_ID'],
                  os.environ['ECOSYSTEM_SESSION_PASSWORD']]

sys.stdout = PasswordFilter(sensitive_data, sys.stdout)
sys.stderr = PasswordFilter(sensitive_data, sys.stderr)
utils.upload_plugins_utility(
    os.environ['CIRCLE_BUILD_NUM'],
    'aws',
    []
)
secrets = {
    'ec2_region_endpoint': 'ec2.ap-northeast-1.amazonaws.com',
    'ec2_region_name': 'ap-northeast-1',
    'aws_region_name': 'ap-northeast-1',
    'availability_zone': 'ap-northeast-1b',
    'aws_availability_zone': 'ap-northeast-1b',
    'aws_secret_access_key': os.environ['AWS_SECRET_ACCESS_KEY'],
    'aws_access_key_id': os.environ['AWS_ACCESS_KEY_ID'],
    'agent_key_private': '',
    'agent_key_public': ''
}

for name, value in secrets.items():
    utils.execute_command(
        'cfy secrets create -u {0} -s {1}'.format(
            name, value
        )
    )

SSH_KEY_BP_ZIP = 'https://github.com/cloudify-examples/' \
                 'helpful-blueprint/archive/master.zip'


class TestAWS(EcosystemTestBase):

    @classmethod
    def setUpClass(cls):
        os.environ['ECOSYSTEM_SESSION_PASSWORD'] = 'admin'

    @classmethod
    def tearDownClass(cls):
        try:
            del os.environ['ECOSYSTEM_SESSION_MANAGER_IP']
            del os.environ['ECOSYSTEM_SESSION_LOADED']
            del os.environ['ECOSYSTEM_SESSION_PASSWORD']
            del os.environ['CLOUDIFY_STORAGE_DIR']
            del os.environ['ECOSYSTEM_SESSION_BLUEPRINT_DIR']
        except KeyError:
            pass

    def setUp(self):
        if self.password not in self.sensitive_data:
            self.sensitive_data.append(self.password)
        os.environ['ECOSYSTEM_SESSION_MANAGER_IP'] = 'localhost'
        os.environ['AWS_DEFAULT_REGION'] = self.inputs.get('ec2_region_name')

    @property
    def manager_ip(self):
        return 'localhost'

    @property
    def node_type_prefix(self):
        return 'cloudify.nodes.aws'

    @property
    def plugin_mapping(self):
        return 'aws'

    @property
    def blueprint_file_name(self):
        return 'aws.yaml'

    @property
    def external_id_key(self):
        return 'aws_resource_id'

    @property
    def server_ip_property(self):
        return 'ip'

    @property
    def sensitive_data(self):
        return [
            os.environ['AWS_SECRET_ACCESS_KEY'],
            os.environ['AWS_ACCESS_KEY_ID']
        ]

    def install_manager(self, _):
        pass

    @staticmethod
    def uninstall_manager(cfy_local):
        pass

    def remove_deployment(self, deployment_id, nodes_to_check):

        # UnDeploy the application
        utils.execute_command(
            'cfy executions start uninstall '
            '-p ignore_failure=true -d {0}'.format(
                deployment_id))

        deployment_nodes = \
            utils.get_deployment_resources_by_node_type_substring(
                deployment_id, self.node_type_prefix)

        self.check_resources_in_deployment_deleted(
            deployment_nodes, nodes_to_check
        )

    @staticmethod
    def install_blueprint(blueprint_path, blueprint_id):
        install_command =\
            'cfy install {0} -b {1}'.format(blueprint_path, blueprint_id)
        failed = utils.execute_command(install_command)
        if failed:
            raise Exception('Install {0} failed.'.format(blueprint_id))

    @property
    def inputs(self):
        # Setting m4.large for Tokyo.
        try:
            return {
                'password': os.environ['ECOSYSTEM_SESSION_PASSWORD'],
                'ec2_region_name': 'ap-northeast-1',
                'ec2_region_endpoint': 'ec2.ap-northeast-1.amazonaws.com',
                'availability_zone': 'ap-northeast-1b',
                'aws_secret_access_key': os.environ['AWS_SECRET_ACCESS_KEY'],
                'aws_access_key_id': os.environ['AWS_ACCESS_KEY_ID'],
                'instance_type': 'm4.large'
            }
        except KeyError:
            raise

    @property
    def plugins_to_upload(self):
        """plugin yamls to upload to manager"""
        return []

    def check_resource_method(self,
                              resource_id=None,
                              resource_type=None,
                              exists=True,
                              command=None):

        print 'Checking AWS resource args {0} {1} {2} {3}'.format(
            resource_id, resource_type, exists, command)

        if not isinstance(resource_id, text_type):
            print 'Warning resource_id is {0}'.format(resource_id)
            resource_id = str(resource_id)
        sleep(1)
        if command:
            pass
        elif 'cloudify.nodes.aws.ec2.Vpc' == \
                resource_type or resource_id.startswith('vpc-'):
            command = 'aws ec2 describe-vpcs --vpc-ids {0}'.format(resource_id)
        elif 'cloudify.nodes.aws.ec2.InternetGateway' == \
                resource_type or resource_id.startswith('igw-'):
            command = 'aws ec2 describe-internet-gateways ' \
                      '--internet-gateway-ids {0}'.format(resource_id)
        elif 'cloudify.nodes.aws.ec2.Subnet' == \
                resource_type or resource_id.startswith('subnet-'):
            command = 'aws ec2 describe-subnets --subnet-ids {0}'.format(
                resource_id)
        elif 'cloudify.nodes.aws.ec2.RouteTable' == \
                resource_type or resource_id.startswith('rtb-'):
            command = \
                'aws ec2 describe-route-tables --route-table-ids {0}'.format(
                    resource_id)
        elif 'cloudify.nodes.aws.ec2.NATGateway' == \
                resource_type or resource_id.startswith('nat-'):
            command = \
                'aws ec2 describe-nat-gateways --nat-gateway-ids {0}'.format(
                    resource_id)
        elif 'cloudify.nodes.aws.ec2.ElasticIP' == \
                resource_type or \
                re.compile(IP_ADDRESS_REGEX).match(resource_id):
            command = 'aws ec2 describe-addresses --public-ips {0}'.format(
                resource_id)
        elif 'cloudify.nodes.aws.ec2.SecurityGroup' == \
                resource_type or resource_id.startswith('sg-'):
            command = \
                'aws ec2 describe-security-groups --group-ids {0}'.format(
                    resource_id)
        elif 'cloudify.nodes.aws.ec2.Interface' == \
                resource_type or resource_id.startswith('eni-'):
            command = 'aws ec2 describe-network-interfaces ' \
                      '--network-interface-ids {0}'.format(
                          resource_id)
        elif 'cloudify.nodes.aws.ec2.EBSVolume' == \
                resource_type or resource_id.startswith('vol-'):
            command = 'aws ec2 describe-volumes --volume-ids {0}'.format(
                resource_id)
        elif 'cloudify.nodes.aws.ec2.Instances' == \
                resource_type or resource_id.startswith('i-'):
            command = 'aws ec2 describe-instances --instance-ids {0}'.format(
                resource_id)
        elif 'cloudify.nodes.aws.ec2.NATGateway' == \
                resource_type or resource_id.startswith('nat-'):
            command = \
                'aws ec2 describe-nat-gateways ' \
                '--nat-gateway-ids {0}'.format(resource_id)
        elif 'cloudify.nodes.aws.SQS.Queue' == resource_type:
            if not exists:
                return
            # Change queue url to name to get queue url.
            resource_id = resource_id.split('/')[-1]
            command = 'aws sqs get-queue-url --queue-name {0}'.format(
                resource_id)
        elif 'cloudify.nodes.aws.SNS.Topic' == resource_type:
            command = 'aws sns list-subscriptions-by-topic ' \
                      '--topic-arn {0}'.format(resource_id)
        elif 'cloudify.nodes.aws.s3.Bucket' == resource_type:
            command = 'aws s3 ls {0}'.format(resource_id)
        elif 'cloudify.nodes.aws.autoscaling.Group' == resource_type:
            command = 'aws autoscaling describe-auto-scaling-groups ' \
                      '--auto-scaling-group-names {0}'.format(resource_id)
        elif 'cloudify.nodes.aws.CloudFormation.Stack' == resource_type:
            sleep(1)
            command = 'aws cloudformation describe-stacks ' \
                      '--stack-name {0}'.format(resource_id)
        elif 'cloudify.nodes.aws.elb.Classic.LoadBalancer' == \
                resource_type:
            command = 'aws elb describe-load-balancers ' \
                      '--load-balancer-name my-load-balancer {0}'.format(
                          resource_id)
        elif resource_id.startswith('ami-'):
            return
        else:
            raise Exception('Unsupported type {0} for {1}.'.format(
                resource_type, resource_id))
        self.assertEqual(0 if exists else 255, utils.execute_command(command))

    def check_resources_in_deployment_created(self, nodes, node_names):
        for node in nodes:
            if node['id'] not in node_names:
                break
            external_id = node['instances'][0]['runtime_properties'].get(
                'aws_resource_id') if \
                'Classic.LoadBalancer' not in node['node_type'] else \
                node['instances'][0]['runtime_properties'].get(
                    'LoadBalancerName')
            if 'LifecycleHook' in node['node_type']:
                lifecycle_hook_command = \
                    'aws autoscaling describe-lifecycle-hooks ' \
                    '--auto-scaling-group-name test-autoscaling ' \
                    '--lifecycle-hook-names {0}'.format(external_id)
                self.check_resource_method(command=lifecycle_hook_command)
            else:
                self.check_resource_method(external_id, node['node_type'])

    def check_resources_in_deployment_deleted(self, nodes, node_names):
        for node in nodes:
            if node['id'] not in node_names:
                break
            external_id = node['instances'][0]['runtime_properties'].get(
                'aws_resource_id') if \
                'Classic.LoadBalancer' not in node['node_type'] else \
                node['instances'][0]['runtime_properties'].get(
                    'LoadBalancerName')
            if 'LifecycleHook' in node['node_type']:
                lifecycle_hook_command = \
                    'aws autoscaling describe-lifecycle-hooks' \
                    ' --auto-scaling-group-name test-autoscaling' \
                    ' --lifecycle-hook-names {0}'.format(external_id)
                self.check_resource_method(
                    command=lifecycle_hook_command, exists=False)
            else:
                self.check_resource_method(
                    external_id, node['node_type'], exists=False)

    def test_example_network(self):
        blueprint_path = \
            'examples/blueprint-examples/' \
            'aws-example-network/blueprint.yaml'
        blueprint_id = 'example-network-{0}'.format(
            self.application_prefix)
        aws_nodes = [
            'nat_gateway',
            'nat_gateway_ip',
            'private_subnet_routetable',
            'public_subnet_routetable',
            'private_subnet',
            'public_subnet',
            'internet_gateway',
            'vpc'
        ]

        # Prepare to call clean up method whenever test pass/fail
        self.addCleanup(self.remove_deployment,
                        blueprint_id,
                        aws_nodes)

        utils.check_deployment(
            blueprint_path,
            blueprint_id,
            self.node_type_prefix,
            aws_nodes,
            self.check_resources_in_deployment_created,
            self.check_resources_in_deployment_deleted
        )

    def test_autoscaling(self):
        blueprint_path = 'examples/autoscaling-feature-demo/test.yaml'
        blueprint_id = 'autoscaling-{0}'.format(self.application_prefix)
        autoscaling_nodes = ['autoscaling_group']

        # Prepare to call clean up method whenever test pass/fail
        self.addCleanup(self.remove_deployment,
                        blueprint_id,
                        autoscaling_nodes)

        utils.check_deployment(
            blueprint_path,
            blueprint_id,
            self.node_type_prefix,
            autoscaling_nodes,
            self.check_resources_in_deployment_created,
            self.check_resources_in_deployment_deleted
        )

    def test_s3(self):
        blueprint_path = 'examples/s3-feature-demo/blueprint.yaml'
        blueprint_id = 's3-{0}'.format(self.application_prefix)
        s3_nodes = ['bucket']

        # Prepare to call clean up method whenever test pass/fail
        self.addCleanup(self.remove_deployment, blueprint_id, s3_nodes)

        utils.check_deployment(
            blueprint_path,
            blueprint_id,
            self.node_type_prefix,
            s3_nodes,
            self.check_resources_in_deployment_created,
            self.check_resources_in_deployment_deleted
        )

    def test_sqs_sns(self):
        blueprint_path = 'examples/sns-feature-demo/blueprint.yaml'
        blueprint_id = 'sqs-{0}'.format(
            self.application_prefix)
        sns_nodes = ['queue', 'topic']

        # Prepare to call clean up method whenever test pass/fail
        self.addCleanup(self.remove_deployment, blueprint_id, sns_nodes)

        utils.check_deployment(
            blueprint_path,
            blueprint_id,
            self.node_type_prefix,
            sns_nodes,
            self.check_resources_in_deployment_created,
            self.check_resources_in_deployment_deleted
        )

    def test_cfn_stack(self):
        blueprint_path = 'examples/cloudformation-feature-demo/blueprint.yaml'
        blueprint_id = 'cfn-{0}'.format(self.application_prefix)
        cfn_nodes = ['wordpress_example', 'HelloBucket']

        # Prepare to call clean up method whenever test pass/fail
        self.addCleanup(self.remove_deployment, blueprint_id, cfn_nodes)

        utils.check_deployment(
            blueprint_path,
            blueprint_id,
            self.node_type_prefix,
            cfn_nodes,
            self.check_resources_in_deployment_created,
            self.check_resources_in_deployment_deleted
        )

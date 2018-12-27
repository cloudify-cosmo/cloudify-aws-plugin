# Built-in Imports
import os
import re
from time import sleep
import tempfile

# Cloudify Imports
from ecosystem_tests import EcosystemTestBase, utils, IP_ADDRESS_REGEX
from ecosystem_tests.utils import (
    execute_command,
    get_deployment_resources_by_node_type_substring
)

NC_AWS_NODES = [
    'security_group',
    'haproxy_nic',
    'nodejs_nic',
    'mongo_nic',
    'nodecellar_ip',
]

NC_MONITOTED_NODES = [
    'haproxy_frontend_host',
    'nodejs_host',
    'mongod_host'
]


class TestAWSSDK(EcosystemTestBase):

    def setUp(self):
        os.environ['AWS_DEFAULT_REGION'] = self.inputs.get('ec2_region_name')
        super(TestAWSSDK, self).setUp()

    def remove_deployment(self, deployment_id, nodes_to_check):

        # UnDeploy the application
        execute_command(
            'cfy executions start uninstall '
            '-p ignore_failure=true -d {0}'.format(
                deployment_id))

        deployment_nodes = \
            get_deployment_resources_by_node_type_substring(
                deployment_id, self.node_type_prefix)

        self.check_resources_in_deployment_deleted(
            deployment_nodes, nodes_to_check
        )

    @staticmethod
    def install_blueprint(blueprint_path, blueprint_id):
        install_command =\
            'cfy install {0} -b {1}'.format(blueprint_path, blueprint_id)
        failed = execute_command(install_command)
        if failed:
            raise Exception('Install {0} failed.'.format(blueprint_id))

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

        if not isinstance(resource_id, basestring):
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
            node_type = 'cloudify.nodes.aws.ec2.Instances' \
                if node['node_type'] == 'nodecellar.nodes.MonitoredServer' \
                else node['node_type']
            if node['id'] not in node_names:
                break
            external_id = node['instances'][0]['runtime_properties'].get(
                'aws_resource_id') if \
                'Classic.LoadBalancer' not in node_type else \
                node['instances'][0]['runtime_properties'].get(
                    'LoadBalancerName')
            if 'LifecycleHook' in node_type:
                lifecycle_hook_command = \
                    'aws autoscaling describe-lifecycle-hooks ' \
                    '--auto-scaling-group-name test-autoscaling ' \
                    '--lifecycle-hook-names {0}'.format(external_id)
                self.check_resource_method(command=lifecycle_hook_command)
            else:
                self.check_resource_method(external_id, node_type)

    def check_resources_in_deployment_deleted(self, nodes, node_names):
        for node in nodes:
            if node['id'] not in node_names:
                break
            node_type = 'cloudify.nodes.aws.ec2.Instances' \
                if node['node_type'] == 'nodecellar.nodes.MonitoredServer' \
                else node['node_type']
            external_id = node['instances'][0]['runtime_properties'].get(
                'aws_resource_id') if \
                'Classic.LoadBalancer' not in node_type else \
                node['instances'][0]['runtime_properties'].get(
                    'LoadBalancerName')
            if 'LifecycleHook' in node_type:
                lifecycle_hook_command = \
                    'aws autoscaling describe-lifecycle-hooks' \
                    ' --auto-scaling-group-name test-autoscaling' \
                    ' --lifecycle-hook-names {0}'.format(external_id)
                self.check_resource_method(
                    command=lifecycle_hook_command, exists=False)
            else:
                self.check_resource_method(
                    external_id, node_type, exists=False)

    @staticmethod
    def get_nc_deployment_nodes():
        return\
            utils.get_deployment_resources_by_node_type_substring('nc',
                                                                  'cloudify')

    def check_nodecellar(self):
        failed = utils.install_nodecellar(
            blueprint_file_name=self.blueprint_file_name)

        if failed:
            raise Exception('Nodecellar install failed.')
        del failed

        self.addCleanup(self.cleanup_deployment, 'nc')

        failed = utils.execute_scale('nc', scalable_entity_name='nodejs_group')
        if failed:
            raise Exception('Nodecellar scale failed.')
        del failed

        deployment_nodes = self.get_nc_deployment_nodes()

        self.check_resources_in_deployment_created(
            deployment_nodes, NC_AWS_NODES)
        self.check_resources_in_deployment_created(
            deployment_nodes, NC_MONITOTED_NODES)

    def check_external_nodecellar(self):
        blueprint_dir = tempfile.mkdtemp()
        blueprint_zip = os.path.join(blueprint_dir, 'blueprint.zip')
        blueprint_archive = 'nodecellar-auto-scale-auto-heal-blueprint-master'
        download_path = \
            os.path.join(blueprint_dir, blueprint_archive, 'aws.yaml')
        blueprint_path = utils.create_blueprint(
            utils.NODECELLAR, blueprint_zip, blueprint_dir, download_path)

        skip_transform = [
            'aws',
            'vpc',
            'public_subnet',
            'private_subnet',
            'ubuntu_trusty_ami'
        ]

        deployment_nodes = self.get_nc_deployment_nodes()
        new_blueprint_path = utils.create_external_resource_blueprint(
            blueprint_path,
            NC_AWS_NODES,
            deployment_nodes,
            resource_id_attr='aws_resource_id',
            nodes_to_keep_without_transform=skip_transform)

        # Install nc-external
        failed = utils.execute_command(
            'cfy install {0} -b nc-external'.format(new_blueprint_path))
        if failed:
            raise Exception('Nodecellar external install failed.')

        # Un-install nc-external
        failed = utils.execute_uninstall('nc-external')
        if failed:
            raise Exception('Nodecellar external uninstall failed.')

    def test_network_deployment(self):
        # Create a list of node templates to verify.
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
                        'aws-example-network',
                        aws_nodes)

        # Create Deployment (Blueprint already uploaded.)
        if utils.create_deployment('aws-example-network'):
            raise Exception('Deployment aws-example-network failed.')
        # Install Deployment.
        if utils.execute_install('aws-example-network'):
            raise Exception('Install aws-example-network failed.')
        # Get list of nodes in the deployment.
        deployment_nodes = \
            utils.get_deployment_resources_by_node_type_substring(
                'aws', self.node_type_prefix)
        # Check that the nodes really exist.
        self.check_resources_in_deployment_created(
            deployment_nodes, aws_nodes)

        self.check_nodecellar()

        self.check_external_nodecellar()

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

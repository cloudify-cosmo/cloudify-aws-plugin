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

# Standard imports
import unittest

# Third party imports
from mock import patch, MagicMock

from cloudify.state import current_ctx
from cloudify.exceptions import OperationRetry

# Local imports
from cloudify_aws.common._compat import reload_module
from cloudify_aws.ec2.resources import instances
from cloudify_aws.common.tests.test_base import (
    TestBase,
    CLIENT_CONFIG,
    mock_decorator
)
from cloudify_aws.ec2.resources.instances import (
    EC2Instances,
    INSTANCES,
    RESERVATIONS,
    INSTANCE_ID,
    GROUP_TYPE,
    NETWORK_INTERFACE_TYPE,
    SUBNET_TYPE,
    INSTANCE_IDS
)


class TestEC2Instances(TestBase):

    def setUp(self):
        self.instances = EC2Instances("ctx_node", resource_id='ec2 instance',
                                      client=True, logger=None)
        mock0 = patch('cloudify_aws.common.decorators.multiple_aws_resource',
                      mock_decorator)
        mock1 = patch('cloudify_aws.common.decorators.aws_resource',
                      mock_decorator)
        mock2 = patch('cloudify_aws.common.decorators.wait_for_status',
                      mock_decorator)
        mock0.start()
        mock1.start()
        mock2.start()
        reload_module(instances)

    def test_class_properties(self):
        effect = self.get_client_error_exception(name='EC2 Instances')
        self.instances.client = \
            self.make_client_function('describe_instances',
                                      side_effect=effect)
        res = self.instances.properties
        self.assertEqual(res, [])

        value = {}
        self.instances.client = \
            self.make_client_function('describe_instances',
                                      return_value=value)
        res = self.instances.properties
        self.assertEqual(res, [])

        value = {RESERVATIONS: [{INSTANCES: [{INSTANCE_ID: 'test_name'}]}]}
        self.instances.client = self.make_client_function(
            'describe_instances', return_value=value)
        res = self.instances.properties
        self.assertEqual(res[INSTANCE_ID], 'test_name')

    def test_class_status(self):
        value = {}
        self.instances.client = \
            self.make_client_function('describe_instances',
                                      return_value=value)
        res = self.instances.status
        self.assertIsNone(res)

        value = {RESERVATIONS: [{INSTANCES: [{
            INSTANCE_ID: 'test_name', 'State': {'Code': 16}}]}]}
        self.instances.client = \
            self.make_client_function('describe_instances',
                                      return_value=value)
        res = self.instances.status
        self.assertEqual(res, 16)

    def test_class_create(self):
        value = {RESERVATIONS: [{INSTANCES: [{INSTANCE_IDS: ['test_name']}]}]}
        self.instances.client = \
            self.make_client_function('run_instances',
                                      return_value=value)
        res = self.instances.create(value)
        self.assertEqual(res, value)

    def test_class_start(self):
        value = {INSTANCE_IDS: ['test_name']}
        self.instances.client = \
            self.make_client_function('start_instances',
                                      return_value=value)
        res = self.instances.start(value)
        self.assertEqual(res, value)

    def test_class_stop(self):
        value = {INSTANCE_IDS: ['test_name']}
        self.instances.client = \
            self.make_client_function('stop_instances',
                                      return_value=value)
        res = self.instances.stop(value)
        self.assertEqual(res, value)

    def test_class_delete(self):
        params = {INSTANCE_ID: 'test_name'}
        self.instances.client = \
            self.make_client_function('terminate_instances')
        self.instances.delete(params)
        self.assertTrue(self.instances.client.terminate_instances
                        .called)

        params = {INSTANCE_ID: 'test_name'}
        self.instances.delete(params)
        self.assertEqual(params[INSTANCE_ID], 'test_name')

    def test_prepare(self):
        ctx = self.get_mock_ctx(
            "EC2Instances",
            type_hierarchy=['cloudify.nodes.Root', 'cloudify.nodes.Compute'])
        params = {'ImageId': 'test image', 'InstanceType': 'test type'}
        instances.prepare(ctx, EC2Instances, params)
        self.assertEqual(ctx.instance.runtime_properties['resource_config'],
                         params)

    def test_create(self):
        ctx = self.get_mock_ctx(
            "EC2Instances",
            test_properties={'os_family': 'linux'},
            type_hierarchy=['cloudify.nodes.Root', 'cloudify.nodes.Compute'])
        current_ctx.set(ctx=ctx)
        params = {'ImageId': 'test image', 'InstanceType': 'test type'}
        self.instances.resource_id = 'test_name'
        iface = MagicMock()
        value = {INSTANCES: [{INSTANCE_ID: 'test_name'}]}
        iface.create = self.mock_return(value)
        instances.create(ctx=ctx, iface=iface, resource_config=params)
        self.assertEqual(self.instances.resource_id,
                         'test_name')

    def test_create_with_relationships(self):
        ctx = self.get_mock_ctx(
            "EC2Instances",
            test_properties={'os_family': 'linux'},
            type_hierarchy=['cloudify.nodes.Root', 'cloudify.nodes.Compute'])
        current_ctx.set(ctx=ctx)
        params = {'ImageId': 'test image', 'InstanceType': 'test type'}
        self.instances.resource_id = 'test_name'
        iface = MagicMock()
        with patch('cloudify_aws.common.utils.find_rel_by_node_type'):
            instances.create(ctx=ctx, iface=iface, resource_config=params)
            self.assertEqual(self.instances.resource_id,
                             'test_name')

    def test_delete(self):
        ctx = self.get_mock_ctx(
            "EC2Instances",
            test_properties={'os_family': 'linux'},
            test_runtime_properties={'aws_resource_ids': ['foo']},
            type_hierarchy=['cloudify.nodes.Root', 'cloudify.nodes.Compute'])
        current_ctx.set(ctx=ctx)
        iface = MagicMock()
        iface.status = 48
        instances.delete(ctx=ctx, iface=iface, resource_config={})
        self.assertTrue(iface.delete.called)
        for prop in ['ip',
                     'private_ip_address',
                     'public_ip_address',
                     'create_response']:
            self.assertTrue(prop not in ctx.instance.runtime_properties)

    def test_create_relatonships(self):
        _source_ctx, _target_ctx, _group_rel = \
            self._create_common_relationships(
                'test_node',
                source_type_hierarchy=['cloudify.nodes.Root',
                                       'cloudify.nodes.Compute'],
                target_type_hierarchy=['cloudify.nodes.Root',
                                       GROUP_TYPE])

        _source_ctx, _target_ctx, _subnet_type = \
            self._create_common_relationships(
                'test_node',
                source_type_hierarchy=['cloudify.nodes.Root',
                                       'cloudify.nodes.Compute'],
                target_type_hierarchy=['cloudify.nodes.Root',
                                       SUBNET_TYPE])

        _source_ctx, _target_ctx, _nic_type = \
            self._create_common_relationships(
                'test_node',
                source_type_hierarchy=['cloudify.nodes.Root',
                                       'cloudify.nodes.Compute'],
                target_type_hierarchy=['cloudify.nodes.Root',
                                       NETWORK_INTERFACE_TYPE])

        _ctx = self.get_mock_ctx(
            "EC2Instances",
            test_properties={'os_family': 'linux'},
            type_hierarchy=['cloudify.nodes.Root', 'cloudify.nodes.Compute'],
            test_relationships=[_group_rel, _subnet_type, _nic_type])
        current_ctx.set(_ctx)
        params = {'ImageId': 'test image', 'InstanceType': 'test type'}
        iface = MagicMock()
        self.instances.resource_id = 'test_name'
        with patch('cloudify_aws.common.utils.find_rels_by_node_type'):
            instances.create(ctx=_ctx, iface=iface, resource_config=params)
            self.assertEqual(self.instances.resource_id, 'test_name')

    def test_multiple_nics(self):

        _source_ctx1, _target_ctx1, _nic_type1 = \
            self._create_common_relationships(
                'test_node',
                source_type_hierarchy=['cloudify.nodes.Root',
                                       'cloudify.nodes.Compute',
                                       'cloudify.nodes.aws.ec2.Instances'],
                target_type_hierarchy=['cloudify.nodes.Root',
                                       NETWORK_INTERFACE_TYPE])
        _target_ctx1.instance.runtime_properties['aws_resource_id'] = 'eni-0'
        _target_ctx1.instance.runtime_properties['device_index'] = 0

        _source_ctx2, _target_ctx2, _nic_type2 = \
            self._create_common_relationships(
                'test_node',
                source_type_hierarchy=['cloudify.nodes.Root',
                                       'cloudify.nodes.Compute',
                                       'cloudify.nodes.aws.ec2.Instances'],
                target_type_hierarchy=['cloudify.nodes.Root',
                                       NETWORK_INTERFACE_TYPE])
        _target_ctx2.instance.runtime_properties['aws_resource_id'] = 'eni-1'
        _target_ctx2.instance.runtime_properties['device_index'] = 1

        _ctx = self.get_mock_ctx(
            "EC2Instances",
            test_properties={'os_family': 'linux'},
            type_hierarchy=['cloudify.nodes.Root',
                            'cloudify.nodes.Compute',
                            'cloudify.nodes.aws.ec2.Instances'],
            test_relationships=[_nic_type1, _nic_type2])

        current_ctx.set(_ctx)
        params = {
            'ImageId': 'test image',
            'InstanceType': 'test type',
            'NetworkInterfaces': [
                {
                    'NetworkInterfaceId': 'eni-2',
                    'DeviceIndex': 2
                }
            ]
        }
        iface = MagicMock()
        value = {INSTANCES: [{INSTANCE_ID: 'test_name'}]}
        iface.create = self.mock_return(value)
        instances.create(ctx=_ctx, iface=iface, resource_config=params)

    def test_start(self):
        ctx = self.get_mock_ctx(
            "EC2Instances",
            test_properties={'os_family': 'linux',
                             'client_config': CLIENT_CONFIG},
            test_runtime_properties={'aws_resource_ids': ['foo']},
            type_hierarchy=['cloudify.nodes.Root', 'cloudify.nodes.Compute'])
        current_ctx.set(ctx=ctx)
        iface = MagicMock()
        iface.status = 0
        self.instances.resource_id = 'test_name'
        try:
            instances.start(ctx=ctx, iface=iface, resource_config={})
        except OperationRetry:
            pass
        self.assertTrue(iface.start.called)

    def test_modify_instance_attribute(self):
        ctx = self.get_mock_ctx(
            "EC2Instances",
            test_properties={'os_family': 'linux'},
            type_hierarchy=['cloudify.nodes.Root', 'cloudify.nodes.Compute'])
        current_ctx.set(ctx=ctx)
        iface = MagicMock()
        iface.status = 0
        self.instances.resource_id = 'test_name'
        try:
            instances.modify_instance_attribute(
                ctx, iface, {INSTANCE_ID: self.instances.resource_id})
        except OperationRetry:
            pass
        self.assertTrue(iface.modify_instance_attribute.called)

    def test_stop(self):
        ctx = self.get_mock_ctx(
            "EC2Instances",
            test_properties={'os_family': 'linux',
                             'client_config': CLIENT_CONFIG},
            test_runtime_properties={'aws_resource_ids': ['foo']},
            type_hierarchy=['cloudify.nodes.Root', 'cloudify.nodes.Compute'])
        current_ctx.set(ctx=ctx)
        iface = MagicMock()
        instances.stop(ctx=ctx, iface=iface, resource_config={})
        self.assertTrue(iface.stop.called)

    def test_with_userdata(self):
        """ this tests that handle user data returns the expected output
        """
        _tp = \
            {
                'os_family': 'windows',
                'agent_config': {'install_method': 'init_script'}
            }

        ctx = self.get_mock_ctx(
            "EC2Instances",
            test_properties=_tp,
            type_hierarchy=['cloudify.nodes.Root', 'cloudify.nodes.Compute'])
        current_ctx.set(ctx=ctx)
        ctx.agent.init_script = lambda: 'SCRIPT'
        ctx.node.properties['agent_config']['install_method'] = 'init_script'
        current_ctx.set(ctx=ctx)
        params = \
            {
                'ImageId': 'test image',
                'InstanceType': 'test type',
                'UserData': ''
            }
        instances.handle_userdata(params)
        expected_userdata = 'SCRIPT'
        self.assertIn(expected_userdata, params['UserData'])

    def test_sort_devices(self):
        test_devices = [
            {
                'NetworkInterfaceId': '1',
                'DeviceIndex': 1
            },
            {
                'NetworkInterfaceId': '3',
                'DeviceIndex': 3,
            },
            {
                'NetworkInterfaceId': '0',
                'DeviceIndex': None
            },
            {
                'NetworkInterfaceId': '2',
                'DeviceIndex': 2
            }
        ]
        sorted_devices = [dev['NetworkInterfaceId'] for dev in
                          instances.sort_devices(test_devices)]
        self.assertEqual(['0', '1', '2', '3'], sorted_devices)

    def test_cloudify_node_type(self):
        expected_node_type_string = """plugins:
  aws:
    executor: central_deployment_agent
    package_name: cloudify-aws-plugin
data_types:
  BlockDeviceMappings:
    type: BlockDeviceMappingRequestList
    description: <p>The block device mapping, which defines the EBS volumes and instance
      store volumes to attach to the instance at launch. For more information, see
      <a href="https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/block-device-mapping-concepts.html">Block
      device mappings</a> in the <i>Amazon EC2 User Guide</i>.</p>
    required: false
  ImageId:
    type: ImageId
    description: <p>The ID of the AMI. An AMI ID is required to launch an instance
      and must be specified here or in a launch template.</p>
    required: false
  InstanceType:
    type: InstanceType
    description: '<p>The instance type. For more information, see <a href="https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/instance-types.html">Instance
      types</a> in the <i>Amazon EC2 User Guide</i>.</p> <p>Default: <code>m1.small</code>
      </p>'
    required: false
  Ipv6AddressCount:
    type: Integer
    description: <p>[EC2-VPC] The number of IPv6 addresses to associate with the primary
      network interface. Amazon EC2 chooses the IPv6 addresses from the range of your
      subnet. You cannot specify this option and the option to assign specific IPv6
      addresses in the same request. You can specify this option if you've specified
      a minimum number of instances to launch.</p> <p>You cannot specify this option
      and the network interfaces option in the same request.</p>
    required: false
  Ipv6Addresses:
    type: InstanceIpv6AddressList
    description: <p>[EC2-VPC] The IPv6 addresses from the range of the subnet to associate
      with the primary network interface. You cannot specify this option and the option
      to assign a number of IPv6 addresses in the same request. You cannot specify
      this option if you've specified a minimum number of instances to launch.</p>
      <p>You cannot specify this option and the network interfaces option in the same
      request.</p>
    required: false
  KernelId:
    type: KernelId
    description: <p>The ID of the kernel.</p> <important> <p>We recommend that you
      use PV-GRUB instead of kernels and RAM disks. For more information, see <a href="https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/UserProvidedkernels.html">PV-GRUB</a>
      in the <i>Amazon EC2 User Guide</i>.</p> </important>
    required: false
  KeyName:
    type: KeyPairName
    description: <p>The name of the key pair. You can create a key pair using <a href="https://docs.aws.amazon.com/AWSEC2/latest/APIReference/API_CreateKeyPair.html">CreateKeyPair</a>
      or <a href="https://docs.aws.amazon.com/AWSEC2/latest/APIReference/API_ImportKeyPair.html">ImportKeyPair</a>.</p>
      <important> <p>If you do not specify a key pair, you can't connect to the instance
      unless you choose an AMI that is configured to allow users another way to log
      in.</p> </important>
    required: false
  MaxCount:
    type: Integer
    description: '<p>The maximum number of instances to launch. If you specify more
      instances than Amazon EC2 can launch in the target Availability Zone, Amazon
      EC2 launches the largest possible number of instances above <code>MinCount</code>.</p>
      <p>Constraints: Between 1 and the maximum number you''re allowed for the specified
      instance type. For more information about the default limits, and how to request
      an increase, see <a href="http://aws.amazon.com/ec2/faqs/#How_many_instances_can_I_run_in_Amazon_EC2">How
      many instances can I run in Amazon EC2</a> in the Amazon EC2 FAQ.</p>'
    required: true
  MinCount:
    type: Integer
    description: '<p>The minimum number of instances to launch. If you specify a minimum
      that is more instances than Amazon EC2 can launch in the target Availability
      Zone, Amazon EC2 launches no instances.</p> <p>Constraints: Between 1 and the
      maximum number you''re allowed for the specified instance type. For more information
      about the default limits, and how to request an increase, see <a href="http://aws.amazon.com/ec2/faqs/#How_many_instances_can_I_run_in_Amazon_EC2">How
      many instances can I run in Amazon EC2</a> in the Amazon EC2 General FAQ.</p>'
    required: true
  Monitoring:
    type: RunInstancesMonitoringEnabled
    description: <p>Specifies whether detailed monitoring is enabled for the instance.</p>
    required: false
  Placement:
    type: Placement
    description: <p>The placement for the instance.</p>
    required: false
  RamdiskId:
    type: RamdiskId
    description: <p>The ID of the RAM disk to select. Some kernels require additional
      drivers at launch. Check the kernel requirements for information about whether
      you need to specify a RAM disk. To find kernel requirements, go to the Amazon
      Web Services Resource Center and search for the kernel ID.</p> <important> <p>We
      recommend that you use PV-GRUB instead of kernels and RAM disks. For more information,
      see <a href="https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/UserProvidedkernels.html">PV-GRUB</a>
      in the <i>Amazon EC2 User Guide</i>.</p> </important>
    required: false
  SecurityGroupIds:
    type: SecurityGroupIdStringList
    description: <p>The IDs of the security groups. You can create a security group
      using <a href="https://docs.aws.amazon.com/AWSEC2/latest/APIReference/API_CreateSecurityGroup.html">CreateSecurityGroup</a>.</p>
      <p>If you specify a network interface, you must specify any security groups
      as part of the network interface.</p>
    required: false
  SecurityGroups:
    type: SecurityGroupStringList
    description: '<p>[EC2-Classic, default VPC] The names of the security groups.
      For a nondefault VPC, you must use security group IDs instead.</p> <p>If you
      specify a network interface, you must specify any security groups as part of
      the network interface.</p> <p>Default: Amazon EC2 uses the default security
      group.</p>'
    required: false
  SubnetId:
    type: SubnetId
    description: <p>[EC2-VPC] The ID of the subnet to launch the instance into.</p>
      <p>If you specify a network interface, you must specify any subnets as part
      of the network interface.</p>
    required: false
  UserData:
    type: String
    description: <p>The user data to make available to the instance. For more information,
      see <a href="https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/user-data.html">Running
      commands on your Linux instance at launch</a> (Linux) and <a href="https://docs.aws.amazon.com/AWSEC2/latest/WindowsGuide/ec2-instance-metadata.html#instancedata-add-user-data">Adding
      User Data</a> (Windows). If you are using a command line tool, base64-encoding
      is performed for you, and you can load the text from a file. Otherwise, you
      must provide base64-encoded text. User data is limited to 16 KB.</p>
    required: false
  AdditionalInfo:
    type: String
    description: <p>Reserved.</p>
    required: false
  ClientToken:
    type: String
    description: '<p>Unique, case-sensitive identifier you provide to ensure the idempotency
      of the request. If you do not specify a client token, a randomly generated token
      is used for the request to ensure idempotency.</p> <p>For more information,
      see <a href="https://docs.aws.amazon.com/AWSEC2/latest/APIReference/Run_Instance_Idempotency.html">Ensuring
      Idempotency</a>.</p> <p>Constraints: Maximum 64 ASCII characters</p>'
    required: false
  DisableApiTermination:
    type: Boolean
    description: '<p>If you set this parameter to <code>true</code>, you can''t terminate
      the instance using the Amazon EC2 console, CLI, or API; otherwise, you can.
      To change this attribute after launch, use <a href="https://docs.aws.amazon.com/AWSEC2/latest/APIReference/API_ModifyInstanceAttribute.html">ModifyInstanceAttribute</a>.
      Alternatively, if you set <code>InstanceInitiatedShutdownBehavior</code> to
      <code>terminate</code>, you can terminate the instance by running the shutdown
      command from the instance.</p> <p>Default: <code>false</code> </p>'
    required: false
  DryRun:
    type: Boolean
    description: <p>Checks whether you have the required permissions for the action,
      without actually making the request, and provides an error response. If you
      have the required permissions, the error response is <code>DryRunOperation</code>.
      Otherwise, it is <code>UnauthorizedOperation</code>.</p>
    required: false
  EbsOptimized:
    type: Boolean
    description: '<p>Indicates whether the instance is optimized for Amazon EBS I/O.
      This optimization provides dedicated throughput to Amazon EBS and an optimized
      configuration stack to provide optimal Amazon EBS I/O performance. This optimization
      isn''t available with all instance types. Additional usage charges apply when
      using an EBS-optimized instance.</p> <p>Default: <code>false</code> </p>'
    required: false
  IamInstanceProfile:
    type: IamInstanceProfileSpecification
    description: <p>The name or Amazon Resource Name (ARN) of an IAM instance profile.</p>
    required: false
  InstanceInitiatedShutdownBehavior:
    type: ShutdownBehavior
    description: '<p>Indicates whether an instance stops or terminates when you initiate
      shutdown from the instance (using the operating system command for system shutdown).</p>
      <p>Default: <code>stop</code> </p>'
    required: false
  NetworkInterfaces:
    type: InstanceNetworkInterfaceSpecificationList
    description: <p>The network interfaces to associate with the instance. If you
      specify a network interface, you must specify any security groups and subnets
      as part of the network interface.</p>
    required: false
  PrivateIpAddress:
    type: String
    description: <p>[EC2-VPC] The primary IPv4 address. You must specify a value from
      the IPv4 address range of the subnet.</p> <p>Only one private IP address can
      be designated as primary. You can't specify this option if you've specified
      the option to designate a private IP address as the primary IP address in a
      network interface specification. You cannot specify this option if you're launching
      more than one instance in the request.</p> <p>You cannot specify this option
      and the network interfaces option in the same request.</p>
    required: false
  ElasticGpuSpecification:
    type: ElasticGpuSpecifications
    description: <p>An elastic GPU to associate with the instance. An Elastic GPU
      is a GPU resource that you can attach to your Windows instance to accelerate
      the graphics performance of your applications. For more information, see <a
      href="https://docs.aws.amazon.com/AWSEC2/latest/WindowsGuide/elastic-graphics.html">Amazon
      EC2 Elastic GPUs</a> in the <i>Amazon EC2 User Guide</i>.</p>
    required: false
  ElasticInferenceAccelerators:
    type: ElasticInferenceAccelerators
    description: <p>An elastic inference accelerator to associate with the instance.
      Elastic inference accelerators are a resource you can attach to your Amazon
      EC2 instances to accelerate your Deep Learning (DL) inference workloads.</p>
      <p>You cannot specify accelerators from different generations in the same request.</p>
    required: false
  TagSpecifications:
    type: TagSpecificationList
    description: <p>The tags to apply to the resources during launch. You can only
      tag instances and volumes on launch. The specified tags are applied to all instances
      or volumes that are created during launch. To tag a resource after it has been
      created, see <a href="https://docs.aws.amazon.com/AWSEC2/latest/APIReference/API_CreateTags.html">CreateTags</a>.</p>
    required: false
  LaunchTemplate:
    type: LaunchTemplateSpecification
    description: <p>The launch template to use to launch the instances. Any parameters
      that you specify in <a>RunInstances</a> override the same parameters in the
      launch template. You can specify either the name or ID of a launch template,
      but not both.</p>
    required: false
  InstanceMarketOptions:
    type: InstanceMarketOptionsRequest
    description: <p>The market (purchasing) option for the instances.</p> <p>For <a>RunInstances</a>,
      persistent Spot Instance requests are only supported when <b>InstanceInterruptionBehavior</b>
      is set to either <code>hibernate</code> or <code>stop</code>.</p>
    required: false
  CreditSpecification:
    type: CreditSpecificationRequest
    description: '<p>The credit option for CPU usage of the burstable performance
      instance. Valid values are <code>standard</code> and <code>unlimited</code>.
      To change this attribute after launch, use <a href="https://docs.aws.amazon.com/AWSEC2/latest/APIReference/API_ModifyInstanceCreditSpecification.html">
      ModifyInstanceCreditSpecification</a>. For more information, see <a href="https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/burstable-performance-instances.html">Burstable
      performance instances</a> in the <i>Amazon EC2 User Guide</i>.</p> <p>Default:
      <code>standard</code> (T2 instances) or <code>unlimited</code> (T3/T3a instances)</p>'
    required: false
  CpuOptions:
    type: CpuOptionsRequest
    description: <p>The CPU options for the instance. For more information, see <a
      href="https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/instance-optimize-cpu.html">Optimizing
      CPU options</a> in the <i>Amazon EC2 User Guide</i>.</p>
    required: false
  CapacityReservationSpecification:
    type: CapacityReservationSpecification
    description: <p>Information about the Capacity Reservation targeting option. If
      you do not specify this parameter, the instance's Capacity Reservation preference
      defaults to <code>open</code>, which enables it to run in any open Capacity
      Reservation that has matching attributes (instance type, platform, Availability
      Zone).</p>
    required: false
  HibernationOptions:
    type: HibernationOptionsRequest
    description: <p>Indicates whether an instance is enabled for hibernation. For
      more information, see <a href="https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/Hibernate.html">Hibernate
      your instance</a> in the <i>Amazon EC2 User Guide</i>.</p> <p>You can't enable
      hibernation and Amazon Web Services Nitro Enclaves on the same instance.</p>
    required: false
  LicenseSpecifications:
    type: LicenseSpecificationListRequest
    description: <p>The license configurations.</p>
    required: false
  MetadataOptions:
    type: InstanceMetadataOptionsRequest
    description: <p>The metadata options for the instance. For more information, see
      <a href="https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-instance-metadata.html">Instance
      metadata and user data</a>.</p>
    required: false
  EnclaveOptions:
    type: EnclaveOptionsRequest
    description: <p>Indicates whether the instance is enabled for Amazon Web Services
      Nitro Enclaves. For more information, see <a href="https://docs.aws.amazon.com/enclaves/latest/user/nitro-enclave.html">
      What is Amazon Web Services Nitro Enclaves?</a> in the <i>Amazon Web Services
      Nitro Enclaves User Guide</i>.</p> <p>You can't enable Amazon Web Services Nitro
      Enclaves and hibernation on the same instance.</p>
    required: false
  cloudify.datatypes.aws.ec2.RunInstancesRequest:
    properties:
      BlockDeviceMappings:
        type: BlockDeviceMappingRequestList
        description: <p>The block device mapping, which defines the EBS volumes and
          instance store volumes to attach to the instance at launch. For more information,
          see <a href="https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/block-device-mapping-concepts.html">Block
          device mappings</a> in the <i>Amazon EC2 User Guide</i>.</p>
        required: false
      ImageId:
        type: ImageId
        description: <p>The ID of the AMI. An AMI ID is required to launch an instance
          and must be specified here or in a launch template.</p>
        required: false
      InstanceType:
        type: InstanceType
        description: '<p>The instance type. For more information, see <a href="https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/instance-types.html">Instance
          types</a> in the <i>Amazon EC2 User Guide</i>.</p> <p>Default: <code>m1.small</code>
          </p>'
        required: false
      Ipv6AddressCount:
        type: Integer
        description: <p>[EC2-VPC] The number of IPv6 addresses to associate with the
          primary network interface. Amazon EC2 chooses the IPv6 addresses from the
          range of your subnet. You cannot specify this option and the option to assign
          specific IPv6 addresses in the same request. You can specify this option
          if you've specified a minimum number of instances to launch.</p> <p>You
          cannot specify this option and the network interfaces option in the same
          request.</p>
        required: false
      Ipv6Addresses:
        type: InstanceIpv6AddressList
        description: <p>[EC2-VPC] The IPv6 addresses from the range of the subnet
          to associate with the primary network interface. You cannot specify this
          option and the option to assign a number of IPv6 addresses in the same request.
          You cannot specify this option if you've specified a minimum number of instances
          to launch.</p> <p>You cannot specify this option and the network interfaces
          option in the same request.</p>
        required: false
      KernelId:
        type: KernelId
        description: <p>The ID of the kernel.</p> <important> <p>We recommend that
          you use PV-GRUB instead of kernels and RAM disks. For more information,
          see <a href="https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/UserProvidedkernels.html">PV-GRUB</a>
          in the <i>Amazon EC2 User Guide</i>.</p> </important>
        required: false
      KeyName:
        type: KeyPairName
        description: <p>The name of the key pair. You can create a key pair using
          <a href="https://docs.aws.amazon.com/AWSEC2/latest/APIReference/API_CreateKeyPair.html">CreateKeyPair</a>
          or <a href="https://docs.aws.amazon.com/AWSEC2/latest/APIReference/API_ImportKeyPair.html">ImportKeyPair</a>.</p>
          <important> <p>If you do not specify a key pair, you can't connect to the
          instance unless you choose an AMI that is configured to allow users another
          way to log in.</p> </important>
        required: false
      MaxCount:
        type: Integer
        description: '<p>The maximum number of instances to launch. If you specify
          more instances than Amazon EC2 can launch in the target Availability Zone,
          Amazon EC2 launches the largest possible number of instances above <code>MinCount</code>.</p>
          <p>Constraints: Between 1 and the maximum number you''re allowed for the
          specified instance type. For more information about the default limits,
          and how to request an increase, see <a href="http://aws.amazon.com/ec2/faqs/#How_many_instances_can_I_run_in_Amazon_EC2">How
          many instances can I run in Amazon EC2</a> in the Amazon EC2 FAQ.</p>'
        required: true
      MinCount:
        type: Integer
        description: '<p>The minimum number of instances to launch. If you specify
          a minimum that is more instances than Amazon EC2 can launch in the target
          Availability Zone, Amazon EC2 launches no instances.</p> <p>Constraints:
          Between 1 and the maximum number you''re allowed for the specified instance
          type. For more information about the default limits, and how to request
          an increase, see <a href="http://aws.amazon.com/ec2/faqs/#How_many_instances_can_I_run_in_Amazon_EC2">How
          many instances can I run in Amazon EC2</a> in the Amazon EC2 General FAQ.</p>'
        required: true
      Monitoring:
        type: RunInstancesMonitoringEnabled
        description: <p>Specifies whether detailed monitoring is enabled for the instance.</p>
        required: false
      Placement:
        type: Placement
        description: <p>The placement for the instance.</p>
        required: false
      RamdiskId:
        type: RamdiskId
        description: <p>The ID of the RAM disk to select. Some kernels require additional
          drivers at launch. Check the kernel requirements for information about whether
          you need to specify a RAM disk. To find kernel requirements, go to the Amazon
          Web Services Resource Center and search for the kernel ID.</p> <important>
          <p>We recommend that you use PV-GRUB instead of kernels and RAM disks. For
          more information, see <a href="https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/UserProvidedkernels.html">PV-GRUB</a>
          in the <i>Amazon EC2 User Guide</i>.</p> </important>
        required: false
      SecurityGroupIds:
        type: SecurityGroupIdStringList
        description: <p>The IDs of the security groups. You can create a security
          group using <a href="https://docs.aws.amazon.com/AWSEC2/latest/APIReference/API_CreateSecurityGroup.html">CreateSecurityGroup</a>.</p>
          <p>If you specify a network interface, you must specify any security groups
          as part of the network interface.</p>
        required: false
      SecurityGroups:
        type: SecurityGroupStringList
        description: '<p>[EC2-Classic, default VPC] The names of the security groups.
          For a nondefault VPC, you must use security group IDs instead.</p> <p>If
          you specify a network interface, you must specify any security groups as
          part of the network interface.</p> <p>Default: Amazon EC2 uses the default
          security group.</p>'
        required: false
      SubnetId:
        type: SubnetId
        description: <p>[EC2-VPC] The ID of the subnet to launch the instance into.</p>
          <p>If you specify a network interface, you must specify any subnets as part
          of the network interface.</p>
        required: false
      UserData:
        type: String
        description: <p>The user data to make available to the instance. For more
          information, see <a href="https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/user-data.html">Running
          commands on your Linux instance at launch</a> (Linux) and <a href="https://docs.aws.amazon.com/AWSEC2/latest/WindowsGuide/ec2-instance-metadata.html#instancedata-add-user-data">Adding
          User Data</a> (Windows). If you are using a command line tool, base64-encoding
          is performed for you, and you can load the text from a file. Otherwise,
          you must provide base64-encoded text. User data is limited to 16 KB.</p>
        required: false
      AdditionalInfo:
        type: String
        description: <p>Reserved.</p>
        required: false
      ClientToken:
        type: String
        description: '<p>Unique, case-sensitive identifier you provide to ensure the
          idempotency of the request. If you do not specify a client token, a randomly
          generated token is used for the request to ensure idempotency.</p> <p>For
          more information, see <a href="https://docs.aws.amazon.com/AWSEC2/latest/APIReference/Run_Instance_Idempotency.html">Ensuring
          Idempotency</a>.</p> <p>Constraints: Maximum 64 ASCII characters</p>'
        required: false
      DisableApiTermination:
        type: Boolean
        description: '<p>If you set this parameter to <code>true</code>, you can''t
          terminate the instance using the Amazon EC2 console, CLI, or API; otherwise,
          you can. To change this attribute after launch, use <a href="https://docs.aws.amazon.com/AWSEC2/latest/APIReference/API_ModifyInstanceAttribute.html">ModifyInstanceAttribute</a>.
          Alternatively, if you set <code>InstanceInitiatedShutdownBehavior</code>
          to <code>terminate</code>, you can terminate the instance by running the
          shutdown command from the instance.</p> <p>Default: <code>false</code> </p>'
        required: false
      DryRun:
        type: Boolean
        description: <p>Checks whether you have the required permissions for the action,
          without actually making the request, and provides an error response. If
          you have the required permissions, the error response is <code>DryRunOperation</code>.
          Otherwise, it is <code>UnauthorizedOperation</code>.</p>
        required: false
      EbsOptimized:
        type: Boolean
        description: '<p>Indicates whether the instance is optimized for Amazon EBS
          I/O. This optimization provides dedicated throughput to Amazon EBS and an
          optimized configuration stack to provide optimal Amazon EBS I/O performance.
          This optimization isn''t available with all instance types. Additional usage
          charges apply when using an EBS-optimized instance.</p> <p>Default: <code>false</code>
          </p>'
        required: false
      IamInstanceProfile:
        type: IamInstanceProfileSpecification
        description: <p>The name or Amazon Resource Name (ARN) of an IAM instance
          profile.</p>
        required: false
      InstanceInitiatedShutdownBehavior:
        type: ShutdownBehavior
        description: '<p>Indicates whether an instance stops or terminates when you
          initiate shutdown from the instance (using the operating system command
          for system shutdown).</p> <p>Default: <code>stop</code> </p>'
        required: false
      NetworkInterfaces:
        type: InstanceNetworkInterfaceSpecificationList
        description: <p>The network interfaces to associate with the instance. If
          you specify a network interface, you must specify any security groups and
          subnets as part of the network interface.</p>
        required: false
      PrivateIpAddress:
        type: String
        description: <p>[EC2-VPC] The primary IPv4 address. You must specify a value
          from the IPv4 address range of the subnet.</p> <p>Only one private IP address
          can be designated as primary. You can't specify this option if you've specified
          the option to designate a private IP address as the primary IP address in
          a network interface specification. You cannot specify this option if you're
          launching more than one instance in the request.</p> <p>You cannot specify
          this option and the network interfaces option in the same request.</p>
        required: false
      ElasticGpuSpecification:
        type: ElasticGpuSpecifications
        description: <p>An elastic GPU to associate with the instance. An Elastic
          GPU is a GPU resource that you can attach to your Windows instance to accelerate
          the graphics performance of your applications. For more information, see
          <a href="https://docs.aws.amazon.com/AWSEC2/latest/WindowsGuide/elastic-graphics.html">Amazon
          EC2 Elastic GPUs</a> in the <i>Amazon EC2 User Guide</i>.</p>
        required: false
      ElasticInferenceAccelerators:
        type: ElasticInferenceAccelerators
        description: <p>An elastic inference accelerator to associate with the instance.
          Elastic inference accelerators are a resource you can attach to your Amazon
          EC2 instances to accelerate your Deep Learning (DL) inference workloads.</p>
          <p>You cannot specify accelerators from different generations in the same
          request.</p>
        required: false
      TagSpecifications:
        type: TagSpecificationList
        description: <p>The tags to apply to the resources during launch. You can
          only tag instances and volumes on launch. The specified tags are applied
          to all instances or volumes that are created during launch. To tag a resource
          after it has been created, see <a href="https://docs.aws.amazon.com/AWSEC2/latest/APIReference/API_CreateTags.html">CreateTags</a>.</p>
        required: false
      LaunchTemplate:
        type: LaunchTemplateSpecification
        description: <p>The launch template to use to launch the instances. Any parameters
          that you specify in <a>RunInstances</a> override the same parameters in
          the launch template. You can specify either the name or ID of a launch template,
          but not both.</p>
        required: false
      InstanceMarketOptions:
        type: InstanceMarketOptionsRequest
        description: <p>The market (purchasing) option for the instances.</p> <p>For
          <a>RunInstances</a>, persistent Spot Instance requests are only supported
          when <b>InstanceInterruptionBehavior</b> is set to either <code>hibernate</code>
          or <code>stop</code>.</p>
        required: false
      CreditSpecification:
        type: CreditSpecificationRequest
        description: '<p>The credit option for CPU usage of the burstable performance
          instance. Valid values are <code>standard</code> and <code>unlimited</code>.
          To change this attribute after launch, use <a href="https://docs.aws.amazon.com/AWSEC2/latest/APIReference/API_ModifyInstanceCreditSpecification.html">
          ModifyInstanceCreditSpecification</a>. For more information, see <a href="https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/burstable-performance-instances.html">Burstable
          performance instances</a> in the <i>Amazon EC2 User Guide</i>.</p> <p>Default:
          <code>standard</code> (T2 instances) or <code>unlimited</code> (T3/T3a instances)</p>'
        required: false
      CpuOptions:
        type: CpuOptionsRequest
        description: <p>The CPU options for the instance. For more information, see
          <a href="https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/instance-optimize-cpu.html">Optimizing
          CPU options</a> in the <i>Amazon EC2 User Guide</i>.</p>
        required: false
      CapacityReservationSpecification:
        type: CapacityReservationSpecification
        description: <p>Information about the Capacity Reservation targeting option.
          If you do not specify this parameter, the instance's Capacity Reservation
          preference defaults to <code>open</code>, which enables it to run in any
          open Capacity Reservation that has matching attributes (instance type, platform,
          Availability Zone).</p>
        required: false
      HibernationOptions:
        type: HibernationOptionsRequest
        description: <p>Indicates whether an instance is enabled for hibernation.
          For more information, see <a href="https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/Hibernate.html">Hibernate
          your instance</a> in the <i>Amazon EC2 User Guide</i>.</p> <p>You can't
          enable hibernation and Amazon Web Services Nitro Enclaves on the same instance.</p>
        required: false
      LicenseSpecifications:
        type: LicenseSpecificationListRequest
        description: <p>The license configurations.</p>
        required: false
      MetadataOptions:
        type: InstanceMetadataOptionsRequest
        description: <p>The metadata options for the instance. For more information,
          see <a href="https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-instance-metadata.html">Instance
          metadata and user data</a>.</p>
        required: false
      EnclaveOptions:
        type: EnclaveOptionsRequest
        description: <p>Indicates whether the instance is enabled for Amazon Web Services
          Nitro Enclaves. For more information, see <a href="https://docs.aws.amazon.com/enclaves/latest/user/nitro-enclave.html">
          What is Amazon Web Services Nitro Enclaves?</a> in the <i>Amazon Web Services
          Nitro Enclaves User Guide</i>.</p> <p>You can't enable Amazon Web Services
          Nitro Enclaves and hibernation on the same instance.</p>
        required: false
node_types:
  cloudify.nodes.aws.ec2.Instances:
    derived_from: cloudify.nodes.Compute
    properties:
      client_config:
        type: dict
        description: A dictionary of values to pass to authenticate with the AWS API.
        default: {}
        required: false
      use_external_resource:
        type: boolean
        description: Indicate whether the resource exists or if Cloudify should create
          the resource, true if you are bringing an existing resource, false if you
          want cloudify to create it.
        default: false
        required: false
      resource_id:
        type: string
        description: The AWS resource ID of the external resource, if use_external_resource
          is true. Otherwise it is an empty string.
        default: ''
        required: false
      resource_config:
        type: cloudify.datatypes.aws.ec2.RunInstancesRequest
        description: A dictionary of keys.
        required: true
      cloudify_tagging:
        type: boolean
        description: Generate unique tag to identify ec2 instance.
        default: false
      use_ipv6_ip:
        type: boolean
        description: Tells us to use the IPv6 IP if one exists for agent installation.
          If use_public_ip is provided, this is overridden.
        default: false
      use_public_ip:
        type: boolean
        description: Tells the deployment to use the public IP (if available) of the
          resource for Cloudify Agent connections
        default: false
      use_password:
        type: boolean
        description: Whether to use a password for agent communication.
        default: false
    interfaces:
      create:
        implementation: null
        executor: central_deployment_agent
        inputs:
          aws_resource_id:
            type: string
            description: This overrides the resource_id property (useful for setting
              the resource ID of a node instance at runtime).
            default: null
            required: false
          runtime_properties:
            type: dict
            description: This overrides any runtime property at runtime. This is a
              key-value pair / dictionary that will be passed, as-is, to the runtime
              properties of the running instance.
            default: null
            required: false
          force_operation:
            type: boolean
            description: Forces the current operation to be executed regardless if
              the "use_external_resource" property is set or not.
            default: null
            required: false
          resource_config:
            type: dict
            description: Configuration key-value data to be passed as-is to the corresponding
              Boto3 method. Key names must match the case that Boto3 requires.
            default: null
            required: false
      configure:
        implementation: cloudify_aws.resources.ec2.instances.create
        executor: central_deployment_agent
        inputs:
          aws_resource_id:
            type: string
            description: This overrides the resource_id property (useful for setting
              the resource ID of a node instance at runtime).
            default: null
            required: false
          runtime_properties:
            type: dict
            description: This overrides any runtime property at runtime. This is a
              key-value pair / dictionary that will be passed, as-is, to the runtime
              properties of the running instance.
            default: null
            required: false
          force_operation:
            type: boolean
            description: Forces the current operation to be executed regardless if
              the "use_external_resource" property is set or not.
            default: null
            required: false
          resource_config:
            type: dict
            description: Configuration key-value data to be passed as-is to the corresponding
              Boto3 method. Key names must match the case that Boto3 requires.
            default: null
            required: false
      start:
        implementation: cloudify_aws.resources.ec2.instances.start
        executor: central_deployment_agent
        inputs:
          aws_resource_id:
            type: string
            description: This overrides the resource_id property (useful for setting
              the resource ID of a node instance at runtime).
            default: null
            required: false
          runtime_properties:
            type: dict
            description: This overrides any runtime property at runtime. This is a
              key-value pair / dictionary that will be passed, as-is, to the runtime
              properties of the running instance.
            default: null
            required: false
          force_operation:
            type: boolean
            description: Forces the current operation to be executed regardless if
              the "use_external_resource" property is set or not.
            default: null
            required: false
          resource_config:
            type: dict
            description: Configuration key-value data to be passed as-is to the corresponding
              Boto3 method. Key names must match the case that Boto3 requires.
            default: null
            required: false
      stop:
        implementation: cloudify_aws.resources.ec2.instances.stop
        executor: central_deployment_agent
        inputs:
          aws_resource_id:
            type: string
            description: This overrides the resource_id property (useful for setting
              the resource ID of a node instance at runtime).
            default: null
            required: false
          runtime_properties:
            type: dict
            description: This overrides any runtime property at runtime. This is a
              key-value pair / dictionary that will be passed, as-is, to the runtime
              properties of the running instance.
            default: null
            required: false
          force_operation:
            type: boolean
            description: Forces the current operation to be executed regardless if
              the "use_external_resource" property is set or not.
            default: null
            required: false
          resource_config:
            type: dict
            description: Configuration key-value data to be passed as-is to the corresponding
              Boto3 method. Key names must match the case that Boto3 requires.
            default: null
            required: false
      delete:
        implementation: cloudify_aws.resources.ec2.instances.delete
        executor: central_deployment_agent
        inputs:
          aws_resource_id:
            type: string
            description: This overrides the resource_id property (useful for setting
              the resource ID of a node instance at runtime).
            default: null
            required: false
          runtime_properties:
            type: dict
            description: This overrides any runtime property at runtime. This is a
              key-value pair / dictionary that will be passed, as-is, to the runtime
              properties of the running instance.
            default: null
            required: false
          force_operation:
            type: boolean
            description: Forces the current operation to be executed regardless if
              the "use_external_resource" property is set or not.
            default: null
            required: false
          resource_config:
            type: dict
            description: Configuration key-value data to be passed as-is to the corresponding
              Boto3 method. Key names must match the case that Boto3 requires.
            default: null
            required: false
      modify_instance_attribute:
        implementation: cloudify_aws.resources.ec2.instances.modify_instance_attribute
        executor: central_deployment_agent
        inputs:
          aws_resource_id:
            type: string
            description: This overrides the resource_id property (useful for setting
              the resource ID of a node instance at runtime).
            default: null
            required: false
          runtime_properties:
            type: dict
            description: This overrides any runtime property at runtime. This is a
              key-value pair / dictionary that will be passed, as-is, to the runtime
              properties of the running instance.
            default: null
            required: false
          force_operation:
            type: boolean
            description: Forces the current operation to be executed regardless if
              the "use_external_resource" property is set or not.
            default: null
            required: false
          resource_config:
            type: dict
            description: Configuration key-value data to be passed as-is to the corresponding
              Boto3 method. Key names must match the case that Boto3 requires.
            default: null
            required: false
"""  # noqa
        self.assertEqual(expected_node_type_string,
                         self.instances.to_yaml())

    def test_resource_config_data_type(self, *_):
        expected_data_type = {'cloudify.datatypes.aws.ec2.RunInstancesRequest': {'properties': {'BlockDeviceMappings': {'type': 'BlockDeviceMappingRequestList', 'description': '<p>The block device mapping, which defines the EBS volumes and instance store volumes to attach to the instance at launch. For more information, see <a href="https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/block-device-mapping-concepts.html">Block device mappings</a> in the <i>Amazon EC2 User Guide</i>.</p>', 'required': False}, 'ImageId': {'type': 'ImageId', 'description': '<p>The ID of the AMI. An AMI ID is required to launch an instance and must be specified here or in a launch template.</p>', 'required': False}, 'InstanceType': {'type': 'InstanceType', 'description': '<p>The instance type. For more information, see <a href="https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/instance-types.html">Instance types</a> in the <i>Amazon EC2 User Guide</i>.</p> <p>Default: <code>m1.small</code> </p>', 'required': False}, 'Ipv6AddressCount': {'type': 'Integer', 'description': "<p>[EC2-VPC] The number of IPv6 addresses to associate with the primary network interface. Amazon EC2 chooses the IPv6 addresses from the range of your subnet. You cannot specify this option and the option to assign specific IPv6 addresses in the same request. You can specify this option if you've specified a minimum number of instances to launch.</p> <p>You cannot specify this option and the network interfaces option in the same request.</p>", 'required': False}, 'Ipv6Addresses': {'type': 'InstanceIpv6AddressList', 'description': "<p>[EC2-VPC] The IPv6 addresses from the range of the subnet to associate with the primary network interface. You cannot specify this option and the option to assign a number of IPv6 addresses in the same request. You cannot specify this option if you've specified a minimum number of instances to launch.</p> <p>You cannot specify this option and the network interfaces option in the same request.</p>", 'required': False}, 'KernelId': {'type': 'KernelId', 'description': '<p>The ID of the kernel.</p> <important> <p>We recommend that you use PV-GRUB instead of kernels and RAM disks. For more information, see <a href="https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/UserProvidedkernels.html">PV-GRUB</a> in the <i>Amazon EC2 User Guide</i>.</p> </important>', 'required': False}, 'KeyName': {'type': 'KeyPairName', 'description': '<p>The name of the key pair. You can create a key pair using <a href="https://docs.aws.amazon.com/AWSEC2/latest/APIReference/API_CreateKeyPair.html">CreateKeyPair</a> or <a href="https://docs.aws.amazon.com/AWSEC2/latest/APIReference/API_ImportKeyPair.html">ImportKeyPair</a>.</p> <important> <p>If you do not specify a key pair, you can\'t connect to the instance unless you choose an AMI that is configured to allow users another way to log in.</p> </important>', 'required': False}, 'MaxCount': {'type': 'Integer', 'description': '<p>The maximum number of instances to launch. If you specify more instances than Amazon EC2 can launch in the target Availability Zone, Amazon EC2 launches the largest possible number of instances above <code>MinCount</code>.</p> <p>Constraints: Between 1 and the maximum number you\'re allowed for the specified instance type. For more information about the default limits, and how to request an increase, see <a href="http://aws.amazon.com/ec2/faqs/#How_many_instances_can_I_run_in_Amazon_EC2">How many instances can I run in Amazon EC2</a> in the Amazon EC2 FAQ.</p>', 'required': True}, 'MinCount': {'type': 'Integer', 'description': '<p>The minimum number of instances to launch. If you specify a minimum that is more instances than Amazon EC2 can launch in the target Availability Zone, Amazon EC2 launches no instances.</p> <p>Constraints: Between 1 and the maximum number you\'re allowed for the specified instance type. For more information about the default limits, and how to request an increase, see <a href="http://aws.amazon.com/ec2/faqs/#How_many_instances_can_I_run_in_Amazon_EC2">How many instances can I run in Amazon EC2</a> in the Amazon EC2 General FAQ.</p>', 'required': True}, 'Monitoring': {'type': 'RunInstancesMonitoringEnabled', 'description': '<p>Specifies whether detailed monitoring is enabled for the instance.</p>', 'required': False}, 'Placement': {'type': 'Placement', 'description': '<p>The placement for the instance.</p>', 'required': False}, 'RamdiskId': {'type': 'RamdiskId', 'description': '<p>The ID of the RAM disk to select. Some kernels require additional drivers at launch. Check the kernel requirements for information about whether you need to specify a RAM disk. To find kernel requirements, go to the Amazon Web Services Resource Center and search for the kernel ID.</p> <important> <p>We recommend that you use PV-GRUB instead of kernels and RAM disks. For more information, see <a href="https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/UserProvidedkernels.html">PV-GRUB</a> in the <i>Amazon EC2 User Guide</i>.</p> </important>', 'required': False}, 'SecurityGroupIds': {'type': 'SecurityGroupIdStringList', 'description': '<p>The IDs of the security groups. You can create a security group using <a href="https://docs.aws.amazon.com/AWSEC2/latest/APIReference/API_CreateSecurityGroup.html">CreateSecurityGroup</a>.</p> <p>If you specify a network interface, you must specify any security groups as part of the network interface.</p>', 'required': False}, 'SecurityGroups': {'type': 'SecurityGroupStringList', 'description': '<p>[EC2-Classic, default VPC] The names of the security groups. For a nondefault VPC, you must use security group IDs instead.</p> <p>If you specify a network interface, you must specify any security groups as part of the network interface.</p> <p>Default: Amazon EC2 uses the default security group.</p>', 'required': False}, 'SubnetId': {'type': 'SubnetId', 'description': '<p>[EC2-VPC] The ID of the subnet to launch the instance into.</p> <p>If you specify a network interface, you must specify any subnets as part of the network interface.</p>', 'required': False}, 'UserData': {'type': 'String', 'description': '<p>The user data to make available to the instance. For more information, see <a href="https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/user-data.html">Running commands on your Linux instance at launch</a> (Linux) and <a href="https://docs.aws.amazon.com/AWSEC2/latest/WindowsGuide/ec2-instance-metadata.html#instancedata-add-user-data">Adding User Data</a> (Windows). If you are using a command line tool, base64-encoding is performed for you, and you can load the text from a file. Otherwise, you must provide base64-encoded text. User data is limited to 16 KB.</p>', 'required': False}, 'AdditionalInfo': {'type': 'String', 'description': '<p>Reserved.</p>', 'required': False}, 'ClientToken': {'type': 'String', 'description': '<p>Unique, case-sensitive identifier you provide to ensure the idempotency of the request. If you do not specify a client token, a randomly generated token is used for the request to ensure idempotency.</p> <p>For more information, see <a href="https://docs.aws.amazon.com/AWSEC2/latest/APIReference/Run_Instance_Idempotency.html">Ensuring Idempotency</a>.</p> <p>Constraints: Maximum 64 ASCII characters</p>', 'required': False}, 'DisableApiTermination': {'type': 'Boolean', 'description': '<p>If you set this parameter to <code>true</code>, you can\'t terminate the instance using the Amazon EC2 console, CLI, or API; otherwise, you can. To change this attribute after launch, use <a href="https://docs.aws.amazon.com/AWSEC2/latest/APIReference/API_ModifyInstanceAttribute.html">ModifyInstanceAttribute</a>. Alternatively, if you set <code>InstanceInitiatedShutdownBehavior</code> to <code>terminate</code>, you can terminate the instance by running the shutdown command from the instance.</p> <p>Default: <code>false</code> </p>', 'required': False}, 'DryRun': {'type': 'Boolean', 'description': '<p>Checks whether you have the required permissions for the action, without actually making the request, and provides an error response. If you have the required permissions, the error response is <code>DryRunOperation</code>. Otherwise, it is <code>UnauthorizedOperation</code>.</p>', 'required': False}, 'EbsOptimized': {'type': 'Boolean', 'description': "<p>Indicates whether the instance is optimized for Amazon EBS I/O. This optimization provides dedicated throughput to Amazon EBS and an optimized configuration stack to provide optimal Amazon EBS I/O performance. This optimization isn't available with all instance types. Additional usage charges apply when using an EBS-optimized instance.</p> <p>Default: <code>false</code> </p>", 'required': False}, 'IamInstanceProfile': {'type': 'IamInstanceProfileSpecification', 'description': '<p>The name or Amazon Resource Name (ARN) of an IAM instance profile.</p>', 'required': False}, 'InstanceInitiatedShutdownBehavior': {'type': 'ShutdownBehavior', 'description': '<p>Indicates whether an instance stops or terminates when you initiate shutdown from the instance (using the operating system command for system shutdown).</p> <p>Default: <code>stop</code> </p>', 'required': False}, 'NetworkInterfaces': {'type': 'InstanceNetworkInterfaceSpecificationList', 'description': '<p>The network interfaces to associate with the instance. If you specify a network interface, you must specify any security groups and subnets as part of the network interface.</p>', 'required': False}, 'PrivateIpAddress': {'type': 'String', 'description': "<p>[EC2-VPC] The primary IPv4 address. You must specify a value from the IPv4 address range of the subnet.</p> <p>Only one private IP address can be designated as primary. You can't specify this option if you've specified the option to designate a private IP address as the primary IP address in a network interface specification. You cannot specify this option if you're launching more than one instance in the request.</p> <p>You cannot specify this option and the network interfaces option in the same request.</p>", 'required': False}, 'ElasticGpuSpecification': {'type': 'ElasticGpuSpecifications', 'description': '<p>An elastic GPU to associate with the instance. An Elastic GPU is a GPU resource that you can attach to your Windows instance to accelerate the graphics performance of your applications. For more information, see <a href="https://docs.aws.amazon.com/AWSEC2/latest/WindowsGuide/elastic-graphics.html">Amazon EC2 Elastic GPUs</a> in the <i>Amazon EC2 User Guide</i>.</p>', 'required': False}, 'ElasticInferenceAccelerators': {'type': 'ElasticInferenceAccelerators', 'description': '<p>An elastic inference accelerator to associate with the instance. Elastic inference accelerators are a resource you can attach to your Amazon EC2 instances to accelerate your Deep Learning (DL) inference workloads.</p> <p>You cannot specify accelerators from different generations in the same request.</p>', 'required': False}, 'TagSpecifications': {'type': 'TagSpecificationList', 'description': '<p>The tags to apply to the resources during launch. You can only tag instances and volumes on launch. The specified tags are applied to all instances or volumes that are created during launch. To tag a resource after it has been created, see <a href="https://docs.aws.amazon.com/AWSEC2/latest/APIReference/API_CreateTags.html">CreateTags</a>.</p>', 'required': False}, 'LaunchTemplate': {'type': 'LaunchTemplateSpecification', 'description': '<p>The launch template to use to launch the instances. Any parameters that you specify in <a>RunInstances</a> override the same parameters in the launch template. You can specify either the name or ID of a launch template, but not both.</p>', 'required': False}, 'InstanceMarketOptions': {'type': 'InstanceMarketOptionsRequest', 'description': '<p>The market (purchasing) option for the instances.</p> <p>For <a>RunInstances</a>, persistent Spot Instance requests are only supported when <b>InstanceInterruptionBehavior</b> is set to either <code>hibernate</code> or <code>stop</code>.</p>', 'required': False}, 'CreditSpecification': {'type': 'CreditSpecificationRequest', 'description': '<p>The credit option for CPU usage of the burstable performance instance. Valid values are <code>standard</code> and <code>unlimited</code>. To change this attribute after launch, use <a href="https://docs.aws.amazon.com/AWSEC2/latest/APIReference/API_ModifyInstanceCreditSpecification.html"> ModifyInstanceCreditSpecification</a>. For more information, see <a href="https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/burstable-performance-instances.html">Burstable performance instances</a> in the <i>Amazon EC2 User Guide</i>.</p> <p>Default: <code>standard</code> (T2 instances) or <code>unlimited</code> (T3/T3a instances)</p>', 'required': False}, 'CpuOptions': {'type': 'CpuOptionsRequest', 'description': '<p>The CPU options for the instance. For more information, see <a href="https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/instance-optimize-cpu.html">Optimizing CPU options</a> in the <i>Amazon EC2 User Guide</i>.</p>', 'required': False}, 'CapacityReservationSpecification': {'type': 'CapacityReservationSpecification', 'description': "<p>Information about the Capacity Reservation targeting option. If you do not specify this parameter, the instance's Capacity Reservation preference defaults to <code>open</code>, which enables it to run in any open Capacity Reservation that has matching attributes (instance type, platform, Availability Zone).</p>", 'required': False}, 'HibernationOptions': {'type': 'HibernationOptionsRequest', 'description': '<p>Indicates whether an instance is enabled for hibernation. For more information, see <a href="https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/Hibernate.html">Hibernate your instance</a> in the <i>Amazon EC2 User Guide</i>.</p> <p>You can\'t enable hibernation and Amazon Web Services Nitro Enclaves on the same instance.</p>', 'required': False}, 'LicenseSpecifications': {'type': 'LicenseSpecificationListRequest', 'description': '<p>The license configurations.</p>', 'required': False}, 'MetadataOptions': {'type': 'InstanceMetadataOptionsRequest', 'description': '<p>The metadata options for the instance. For more information, see <a href="https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-instance-metadata.html">Instance metadata and user data</a>.</p>', 'required': False}, 'EnclaveOptions': {'type': 'EnclaveOptionsRequest', 'description': '<p>Indicates whether the instance is enabled for Amazon Web Services Nitro Enclaves. For more information, see <a href="https://docs.aws.amazon.com/enclaves/latest/user/nitro-enclave.html"> What is Amazon Web Services Nitro Enclaves?</a> in the <i>Amazon Web Services Nitro Enclaves User Guide</i>.</p> <p>You can\'t enable Amazon Web Services Nitro Enclaves and hibernation on the same instance.</p>', 'required': False}}}}  # noqa
        self.assertEqual(
            expected_data_type,
            self.instances.cloudify_resource_config_data_type.to_dict())


if __name__ == '__main__':
    unittest.main()

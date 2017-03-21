.. highlight:: yaml

.. _node types: http://docs.getcloudify.org/latest/blueprints/spec-node-types/

Types
^^^^^


Common Properties
=================

All cloud resource nodes have common properties:

* ``resource_id`` The ID of an existing resource when the
  ``use_external_resource`` property is set to ``true``
  (see the [using existing resources section](#using-existing-resources)).
  Defaults to ``''`` (empty string).

* ``aws_config`` a dictionary that contains values you would like to pass to the connection client.
  For information on values that are accepted, please see
  boto documentation <http://boto.readthedocs.org/en/latest/ref/ec2.html#boto.ec2.connection.EC2Connection>`_

* ``use_external_resource`` a boolean for setting whether to
  create the resource or use an existing one.
  See `using external resources`_. Defaults to ``false``.


.. _using external resources:


Node Types
==========

The following are node type definitions.
Nodes describe resources in your cloud infrastructure.
For more information see `node types`_.


.. cfy:node:: cloudify.aws.nodes.Instance

  The public key which is set for the server needs to match the private key name in your AWS account. The public key may be set in a number of ways:

    * By connecting the instance node to a keypair node using the ``cloudify.aws.relationships.instance_connected_to_keypair`` relationship.
    * By setting it explicitly in the ``key_name`` key under the ``parameters`` property.
    * If the agent's keypair information is set in the provider context, the agents' keypair will serve as the default public key to be used if it was not specified otherwise.


If the server is to have an agent installed on it, it should use the agents security group. If you are using a manager bootstrapped with the standard aws-manager-blueprint, there is a provider context dictionary on the manager that provides this value to the plugin. You can also use other security groups by:
  * ``security_groups``: list of security group names.
  * ``security_group_ids``: a list of security group IDs.

If you want to specify the ``availability_zone`` for your instance, you must use the ``placement`` key.

The create function also sets ``reservation_id`` attribute. For information, see [here](http://boto.readthedocs.org/en/latest/ref/ec2.html#boto.ec2.instance.Reservation)

Four additional ``runtime_properties`` are available on node instances of this type once the ``cloudify.interfaces.lifecycle.start`` operation succeeds:

  * ``ip`` the instance's private IP.
  * ``private_dns_name`` the instance's private FQDN in Amazon.
  * ``public_dns_name`` the instances's public FQDN in Amazon.
  * ``public_ip_address`` the instance's public IP address.

.. tip::
    If you want to use the instance in VPC, then you need to connect this to a Subnet using the `cloudify.aws.relationships.instance_contained_in_subnet` relationship.

.. cfy:node:: cloudify.aws.nodes.WindowsInstance

    Use this type when working with a Windows server.
    It has the same properties and operations-mapping as
    :cfy:node:`cloudify.aws.nodes.Instance`,
    yet it overrides some of the agent and plugin installations operations-mapping derived from
    the :cfy:node:`cloudify.nodes.Compute` type.

    Additionally, the default value for the ``use_password`` property
    is overridden for this type, and is set to ``true``.
    In this case, the password of the windows server will be retrieved,
    decrypted and put under the ``password`` runtime property of this node instance.


.. cfy:node:: cloudify.aws.nodes.KeyPair


.. cfy:node:: cloudify.aws.nodes.SecurityGroup

.. note::
    If you want to create a security group in a VPC,
    you need to connect it to a VPC using the
    :cfy:rel:`cloudify.aws.relationships.security_group_contained_in_vpc`
    relationship.


.. cfy:node:: cloudify.aws.nodes.ElasticIP

.. note::
    the actual IP is available via the ``aws_resource_id`` runtime-property.


.. cfy:node:: cloudify.aws.nodes.VPC

    For more info on VPC, see https://aws.amazon.com/documentation/vpc/

.. note::
    When a VPC is created, it receives several default attachments.
    We assign a runtime property for original dhcp options set,
    called ``default_dhcp_options_id``.
    Note that this is not necessarily the current dhcp options set.


.. cfy:node:: cloudify.aws.nodes.Subnet


.. cfy:node:: cloudify.aws.nodes.InternetGateway


.. cfy:node:: cloudify.aws.nodes.VPNGateway


.. cfy:node:: cloudify.aws.nodes.CustomerGateway


.. cfy:node:: cloudify.aws.nodes.ACL


.. cfy:node:: cloudify.aws.nodes.DHCPOptions


.. cfy:node:: cloudify.aws.nodes.RouteTable
.. cfy:node:: cloudify.aws.nodes.SecurityGroupRule
.. cfy:node:: cloudify.aws.nodes.ElasticLoadBalancer
.. cfy:node:: cloudify.aws.nodes.Volume
.. cfy:node:: cloudify.aws.nodes.Gateway
.. cfy:node:: cloudify.aws.nodes.Interface


Common Behaviours
-----------------

Validations
~~~~~~~~~~~

All types offer the same base functionality for the
``cloudify.interfaces.validation.creation`` interface operation:

  * If it's a new resource (``use_external_resource`` is set to ``false``),
    the basic validation is to verify that the resource doesn't actually exist.

  * When [using an existing resource](#using-existing-resources),
    the validation ensures that the resource does exist.


Runtime Properties
==================

See section on `runtime properties <http://cloudify-plugins-common.readthedocs.org/en/3.3/context.html?highlight=runtime#cloudify.context.NodeInstanceContext.runtime_properties>`_

Node instances of any of the types defined in this plugin
get set with the following runtime properties
during the ``cloudify.interfaces.lifecycle.create`` operation:

* ``aws_resource_id`` the AWS ID of the resource


Using Existing Resources
========================

It is possible to use existing resources on AWS - whether these have been created by a different Cloudify deployment or not via Cloudify at all.

All Cloudify AWS types have a property named ``use_external_resource``, whose default value is ``false``. When set to ``true``, the plugin will apply different semantics for each of the operations executed on the relevant node's instances:

.. note::
    If ``use_external_resource`` is set to true in the blueprint,
    the ``resource_id`` must be that resource's ID in AWS,
    unless the resource type is a keypair,
    in which case the value is the key's name.

This behavior is common to all resource types:

* ``create`` If ``use_external_resource`` is true, the AWS plugin will check if the resource is available in your account. If no such resource is available, the operation will fail, if it is available, it will assign the ``aws_resource_id`` to the instance ``runtime_properties``.
* ``delete`` If ``use_external_resource`` is true, the AWS plugin will check if the resource is available in your account. If no such resource is available, the operation will fail, if it is available, it will unassign the instance ``runtime_properties``.


Relationships
=============

.. cfy:rel:: cloudify.aws.relationships.instance_connected_to_keypair

   The `run_instances` operation looks to see if there are any relationships that define a relationship between the instance and a keypair.
   If so, that keypair will be the keypair for that instance.
   It inserts the key's name property in the ``key_name`` parameter in the `run_instances` function.


.. cfy:rel:: cloudify.aws.relationships.instance_connected_to_security_group

   The `run_instances` operation looks to see if there are any relationships that define a relationship between the instance and a security group.
   If so, that security group's ID will be the included in the list of security groups in the ``security_group_ids`` parameter in the `run_instances` function.


.. cfy:rel:: cloudify.aws.relationships.instance_connected_to_subnet

   The `run_instances` operation looks for any relationships to
   a Subnet and creates the Instance in that Subnet.
   Otherwise, the instance is in the EC2 Classic VPC.

.. cfy:rel:: cloudify.aws.relationships.connected_to_subnet

   TODO: WAT


.. cfy:rel:: cloudify.aws.relationships.instance_contained_in_subnet
.. warning::
   Deprecated! Please use
   :cfy:rel:`cloudify.aws.relationships.instance_connected_to_subnet`
   instead


.. cfy:rel:: cloudify.aws.relationships.instance_connected_to_load_balancer

   This registers and EC2 instance with an Elastic Load Balancer.


.. cfy:rel:: cloudify.aws.relationships.security_group_contained_in_vpc

   A Security Group is created in EC2 classic unless it has this relationship. Then it will be created in the target VPC.


.. cfy:rel:: cloudify.aws.relationships.volume_connected_to_instance

   This attaches an EBS volume to an Instance.


.. cfy:rel:: cloudify.aws.relationships.subnet_contained_in_vpc

    This is required, so that when a Subnet is created, the plugin knows which VPC to create the Subnet in.


.. cfy:rel:: cloudify.aws.relationships.routetable_contained_in_vpc

   This is required, so that when a Route Table is created,
   the plugin knows which VPC to create the Route Table in.
   A Route Table can be created in only one VPC for its entire lifecycle.


.. cfy:rel:: cloudify.aws.relationships.routetable_associated_with_subnet

   A route table can be associated with no more than one subnet at a time.


.. cfy:rel:: cloudify.aws.relationships.route_table_to_gateway

   You can add multiple routes to route tables.
   You can add them as arguments to the create operation of the route table.
   For gateways, this is abstracted into a relationship.
   This adds a route to the source route table to the destination gateway.
   The gateway must have a `cidr_block` node property.


.. cfy:rel:: cloudify.aws.relationships.gateway_connected_to_vpc

   Attach either a VPN gateway or an Internet Gateway to a VPC.


.. cfy:rel:: cloudify.aws.relationships.network_acl_contained_in_vpc

   This is required for Network ACLs.
   A Network ACL must be contained in a VPC,
   otherwise the plugin does not know where to put it.


.. cfy:rel:: cloudify.aws.relationships.network_acl_associated_with_subnet

   This associates a Network ACL with a particular Subnet.


.. cfy:rel:: cloudify.aws.relationships.route_table_of_source_vpc_connected_to_target_peer_vpc

   This creates a VPC Peering Connection.
   A VPC Peering Connection is a connection between two VPCs.
   However, it requires a Route Table to associate the routes with.
   This will add routes to the source Route Table and to the Target VPC route table.
   You should also have a :cfy:rel:`cloudify.relationships.depends_on`
   relationship to the target VPC's route table,
   if you have a `node_template` to create one.


.. cfy:rel:: cloudify.aws.relationships.dhcp_options_associated_with_vpc

   Indicates with VPC to associate a DHCP options set with.

.. cfy:rel:: cloudify.aws.relationships.customer_gateway_connected_to_vpn_gateway

   Represents a VPC connection between a customer gateway and a VPN Gateway.

.. cfy:rel:: cloudify.aws.relationships.instance_connected_to_elastic_ip

    This connects an Instance to an Elastic IP. The source is the instance and the target is the Elastic IP.


.. cfy:rel:: cloudify.aws.relationships.connected_to_elastic_ip
.. cfy:rel:: cloudify.aws.relationships.eni_connected_to_instance
.. cfy:rel:: cloudify.aws.relationships.connected_to_security_group
.. cfy:rel:: cloudify.aws.relationships.security_group_uses_rule
.. cfy:rel:: cloudify.aws.relationships.instance_connected_to_eni
.. cfy:rel:: cloudify.aws.relationships.rule_depends_on_security_group



Data Types
==========

.. cfy:datatype:: cloudify.datatypes.aws.Config

    Some of these properties come from your AWS API access credentials. See
    http://docs.aws.amazon.com/AWSSecurityCredentials/1.0/AboutAWSCredentials.html.


.. cfy:datatype:: cloudify.datatypes.aws.NetworkAclEntry
.. cfy:datatype:: cloudify.datatypes.aws.Route
.. cfy:datatype:: cloudify.datatypes.aws.SecurityGroupRule

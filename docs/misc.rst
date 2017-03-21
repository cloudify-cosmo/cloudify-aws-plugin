
Account Information
===================

Every time you manage a resource with Cloudify,
we create one or more clients with AWS API.
You specify the configuration for these clients using the ``aws_config`` property.
It should be an entry of the type
:cfy:datatype:`cloudify.datatypes.aws.Config`

The plugin needs access to your
``aws_access_key_id`` and ``aws_secret_access_key`` in order to operate.
Please read about your AWS Boto configuration at
http://boto.readthedocs.org/en/latest/boto_config_tut.html.


Tips
====

* It is highly recommended to ensure that AWS names are unique. Many operations will fail if you have existing resources with identical names..
* When packaging blueprints for use with a manager the manager will add the following configurations (you can still override them in your blueprint):
  * ``aws_config``
  * ``agent_keypair``
  * ``agent_security_group``


Terminology
===========

* VPC is a virtual private cloud,
  for more info about VPCs refer to `AWS Documentation <https://aws.amazon.com/documentation/vpc/>`_.
* EC2-Classic is the original release of Amazon EC2.
  With this platform, instances run in a single,
  flat network that is shared with other customers.
* Region refers to a general geographical area,
  such as "Central Europe" or "East US".
* ``availability_zone`` refers to one of many isolated locations within a region,
  such as ``us-west-1b``.
  When specifying an ``availability_zone``,
  you must specify one that is in the region you are connecting to.

  ``availability_zone`` is not part of the AWS configuration.

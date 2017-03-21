
.. highlight: yaml

Examples
========


Simple :cfy:node:`cloudify.aws.nodes.Instance` example
------------------------------------------------------

This example includes shows adding additional parameters, tagging an instance name, and explicitly defining the aws_config::

  my_ec2_instance:
    type: cloudify.aws.nodes.Instance
    properties:
      image_id: ami-abcd1234
      instance_type: t1.micro
      parameters:
        placement: us-east-1
      name: my_ec2_instance
      aws_config:
        aws_access_key_id: ...
        aws_secret_access_key: ...
        ec2_region_name: us-east-1
  ...

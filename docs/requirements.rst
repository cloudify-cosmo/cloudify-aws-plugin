Requirements
============

* Python versions:
  * 2.7.x
* AWS account


Compatibility
=============

.. warning::
    This version of Cloudify is only compatible with AWS Plugin version 1.3 or later

    If you need to use an older AWS Plugin, you can work around this issue in two ways:

    + connect to your manager machine and move the file ```/etc/cloudify/aws_plugin/boto``` to ```/root/boto```

    + In the AWS manager, change this line ```aws_config_path: /etc/cloudify/aws_plugin/boto``` to ```aws_config_path: /root/boto```

The AWS plugin uses the `Boto 2.38 client <https://github.com/boto/boto>`_.

For more information about the Boto library,
please refer to http://boto.readthedocs.org/en/latest/index.html.

.. note::
    This version of Boto EC2 Connection supports (AWS) APIVersion = '2014-10-01'.

    This version of Boto ELB Connecton supports (AWS) APIVersion = '2012-06-01'.

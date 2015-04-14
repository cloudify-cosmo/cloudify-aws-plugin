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


from setuptools import setup

# Replace the place holders with values for your project

setup(

    # Do not use underscores in the plugin name.
    name='cloudify-aws-plugin',
    author='Gigaspaces',
    author_email='cosmo-admin@gigaspaces.com',

    version='1.2rc1',
    description='Cloudify plugin for AWS infrastructure.',

    # This must correspond to the actual packages in the plugin.
    packages=['ec2'],

    license='LICENSE',
    install_requires=[
        'cloudify-plugins-common>=3.2rc1',
        'boto==2.34.0'
    ]
)

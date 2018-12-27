# #######
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
#    * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    * See the License for the specific language governing permissions and
#    * limitations under the License.
"""Cloudify plugin package config"""

from setuptools import setup
from setuptools import find_packages


setup(
    name='cloudify-aws-plugin',
    version='2.0.0',
    license='LICENSE',
    packages=find_packages(exclude=['tests*']),
    description='A Cloudify plugin for AWS',
    install_requires=[
        'cloudify-common',
        'boto3==1.9.57',
        'botocore==1.12.57'
    ]
)

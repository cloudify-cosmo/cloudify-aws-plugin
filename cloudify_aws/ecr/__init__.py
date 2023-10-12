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
"""
    ECR
    ~~~
    AWS ECR base interface
"""
# Cloudify AWS
from cloudify_aws_sdk.client import GenericAWSConnection


class ECRBase(GenericAWSConnection):

    def __init__(self,
                 ctx_node,
                 resource_id=None,
                 logger=None,
                 **kwargs):
        kwargs.update({'service_name': 'ecr'})
        super().__init__(**kwargs)
        self.ctx_node = ctx_node
        self.resource_id = resource_id

    @property
    def properties(self):
        """Gets the properties of an external resource"""
        raise NotImplementedError()

    @property
    def status(self):
        """Gets the status of an external resource"""
        raise NotImplementedError()

    def populate_resource(self, *_, **__):
        pass

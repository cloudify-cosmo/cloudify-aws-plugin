########
# Copyright (c) 2014 GigaSpaces Technologies Ltd. All rights reserved
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

EXTERNAL_RESOURCE_ID = 'aws_resource_id'

INSTANCE_STATE_STARTED = 16
INSTANCE_STATE_TERMINATED = 48
INSTANCE_STATE_STOPPED = 80
INSTANCE_REQUIRED_PROPERTIES = ['image_id', 'instance_type']
INSTANCE_INTERNAL_ATTRIBUTES = ['private_dns_name', 'public_dns_name',
                                'public_ip_address', 'ip']
SECURITY_GROUP_REQUIRED_PROPERTIES = ['description', 'rules']

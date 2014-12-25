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

# ctx is imported and used in operations

from cloudify import ctx

# put the operation decorator on any function that is a task
from cloudify.decorators import operation


@operation
def run(**kwargs):
    ctx.instance.runtime_properties['ami_image_id'] = 'a'

def start(**kwargs):
    return True

def stop(**kwargs):
    return True

def terminate(**kwargs):
    return True

def creation_validation(**kwargs):
    return True
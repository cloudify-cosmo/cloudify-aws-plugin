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

from cloudify.exceptions import NonRecoverableError

# Local imports
from cloudify_aws.common._compat import text_type, reload_module
from cloudify_aws.ec2.resources import image
from cloudify_aws.common.tests.test_base import (
    TestBase,
    mock_decorator)
from cloudify_aws.ec2.resources.image import (
    EC2Image,
    IMAGES,
    IMAGE_ID,
    OWNERS
)


class TestEC2Image(TestBase):

    def setUp(self):
        ctx_node_mock = MagicMock(
            properties={'resource_config': {'Name': 'foo'}})
        mock_client = MagicMock()
        self.image = EC2Image(ctx_node_mock,
                              resource_id=True,
                              client=mock_client,
                              logger=None)
        mock1 = patch('cloudify_aws.common.decorators.aws_resource',
                      mock_decorator)
        mock1.start()
        reload_module(image)
        self.image._describe_image_filters = \
            {'Filters': {
                'name': 'CentOS7-cloudify-examples-image',
                'owner-id': '263721492972'}}

    def test_class_properties(self):
        effect = self.get_client_error_exception(name='EC2 Image')
        self.image.client = self.make_client_function('describe_images',
                                                      side_effect=effect)
        res = self.image.properties
        self.assertIsNone(res)

        value = {}
        self.image.client = self.make_client_function('describe_images',
                                                      return_value=value)
        with self.assertRaises(NonRecoverableError) as e:
            self.image.properties
        self.assertEqual(text_type(e.exception),
                         u"Found no AMIs matching provided filters.")

        value = {IMAGES: [{IMAGE_ID: 'test_name'}]}
        self.image.client = self.make_client_function('describe_images',
                                                      return_value=value)
        res = self.image.properties
        self.assertEqual(res[IMAGE_ID], 'test_name')

    def test_class_status(self):
        value = {}

        self.image.client = self.make_client_function('describe_images',
                                                      return_value=value)
        self.assertIsNone(self.image.status)

        value = {IMAGES: [None]}
        self.image.client = self.make_client_function('describe_images',
                                                      return_value=value)
        res = self.image.status
        self.assertIsNone(res)

        value = {IMAGES: [{IMAGE_ID: 'test_name', 'State': 'available'}]}
        self.image.client = self.make_client_function('describe_images',
                                                      return_value=value)
        res = self.image.status
        self.assertEqual(res, 'available')

    def test_class_create(self):
        value = {'Image': 'test'}
        self.image.client = self.make_client_function('create_image',
                                                      return_value=value)
        res = self.image.create(value)
        self.assertEqual(res['Image'], value['Image'])

    def test_prepare(self):
        ctx = self.get_mock_ctx("Image")
        config = {IMAGE_ID: 'image', OWNERS: 'owner'}
        iface = MagicMock()
        ctx.node.properties['use_external_resource'] = True
        iface.create = self.mock_return(config)
        image.prepare(ctx, iface, config)
        self.assertEqual(ctx.instance.runtime_properties['resource_config'],
                         config)

    def test_delete(self):
        config = {IMAGE_ID: 'image'}
        self.assertIsNone(self.image.delete(config))


if __name__ == '__main__':
    unittest.main()

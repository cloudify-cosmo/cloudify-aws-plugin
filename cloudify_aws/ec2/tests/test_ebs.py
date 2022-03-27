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

# Standard Imports
import unittest

# Third Party Imports
from mock import patch, MagicMock

# Local Imports
from cloudify_aws.common._compat import reload_module
from cloudify_aws.ec2.resources.ebs import (
    EC2Volume,
    EC2VolumeAttachment,
    VOLUME_ID,
    VOLUMES,
    VOLUME_STATE,
    AVAILABLE
)
from cloudify_aws.common.tests.test_base import (
    TestBase,
    mock_decorator
)
from cloudify_aws.ec2.resources import ebs
from cloudify_aws.common import constants


class TestEC2Volume(TestBase):

    def setUp(self):
        self.ebs_volume = EC2Volume("ctx_node", resource_id='test_name',
                                    client=True, logger=None)

        mock1 = patch(
            'cloudify_aws.common.decorators.aws_resource', mock_decorator
        )
        mock2 = patch(
            'cloudify_aws.common.decorators.wait_for_status', mock_decorator
        )
        mock1.start()
        mock2.start()
        reload_module(ebs)

    def test_class_properties(self):
        effect = self.get_client_error_exception(name='EC2 EBS Volume')
        self.ebs_volume.client = \
            self.make_client_function('describe_volumes', side_effect=effect)

        res = self.ebs_volume.properties
        self.assertEqual(res, {})

        value = {}
        self.ebs_volume.client = \
            self.make_client_function('describe_volumes',
                                      return_value=value)
        res = self.ebs_volume.properties
        self.assertEqual(res, {})

        value = {VOLUMES: [{'AvailabilityZone': 'test_zone',
                            VOLUME_ID: 'test_name'}]}

        self.ebs_volume.client = \
            self.make_client_function('describe_volumes', return_value=value)
        res = self.ebs_volume.properties
        self.assertEqual(res[VOLUME_ID], 'test_name')

    def test_class_status(self):
        value = {}
        self.ebs_volume.client = \
            self.make_client_function('describe_volumes',
                                      return_value=value)
        res = self.ebs_volume.status
        self.assertIsNone(res)

        value = {VOLUMES: [{'AvailabilityZone': 'test_zone',
                            VOLUME_ID: 'test_name',
                            VOLUME_STATE: AVAILABLE}]}

        self.ebs_volume.client = \
            self.make_client_function('describe_volumes', return_value=value)

        res = self.ebs_volume.status
        self.assertEqual(res, AVAILABLE)

    def test_class_create(self):
        params =\
            {
                'AvailabilityZone': 'aq-testzone-1a',
                'Size': 6,
                'TagSpecifications':
                    [
                        {
                            'ResourceType': 'volume',
                            'Tags':
                                [
                                    {
                                        'Key': 'test-tag-key-1',
                                        'Value': 'test-tag-value-1',
                                    },
                                    {
                                        'Key': 'test-tag-key-2',
                                        'Value': 'test-tag-value-2',
                                    }
                                ],
                        }
                    ]
            }

        output = \
            {
                'AvailabilityZone': 'aq-testzone-1a',
                'Size': 6,
                'Tags':
                    [
                        {
                            'Key': 'test-tag-key-1',
                            'Value': 'test-tag-value-1',
                        },
                        {
                            'Key': 'test-tag-key-2',
                            'Value': 'test-tag-value-2',
                        }

                    ],
                'VolumeId': 'test_volume_id',
            }
        self.ebs_volume.client = \
            self.make_client_function('create_volume', return_value=output)

        res = self.ebs_volume.create(params)
        self.assertEqual(res[VOLUME_ID], output[VOLUME_ID])

    def test_class_delete(self):
        params = {}
        self.ebs_volume.client = \
            self.make_client_function('delete_volume')

        self.ebs_volume.delete(params)
        self.assertTrue(self.ebs_volume.client.delete_volume.called)

        params = {VOLUME_ID: 'test_volume_id'}
        self.ebs_volume.client = \
            self.make_client_function('delete_volume', return_value={})

        res = self.ebs_volume.delete(params)
        self.assertEqual(res, {})

    def test_prepare(self):
        ctx = self.get_mock_ctx("EBSVolume")
        config = {VOLUME_ID: 'test_volume_id'}
        ebs.prepare(ctx, config)
        self.assertEqual(
            ctx.instance.runtime_properties['resource_config'], config)

    def test_create(self):
        ctx = self.get_mock_ctx("EBSVolume", {'client_config': {
            'region_name': 'aq-testzone-1'
        }})
        config = \
            {
                'AvailabilityZone': 'aq-testzone-1a',
                'Size': 6,
                'Tags':
                    [
                        {
                            'Key': 'test-tag-key-1',
                            'Value': 'test-tag-value-1',
                        },
                        {
                            'Key': 'test-tag-key-2',
                            'Value': 'test-tag-value-2',
                        }

                    ],
                'VolumeId': 'test_volume_id',
            }
        self.ebs_volume.resource_id = config[VOLUME_ID]
        iface = MagicMock()
        iface.create = self.mock_return(config)
        ebs.create(ctx=ctx, iface=iface, resource_config=config)
        self.assertEqual(self.ebs_volume.resource_id, 'test_volume_id')

    def test_delete(self):
        iface = MagicMock()
        ctx = self.get_mock_ctx("EBSVolume")

        ctx.instance.runtime_properties[constants.EXTERNAL_RESOURCE_ID]\
            = 'test_volume_id'
        ctx.instance.runtime_properties['resource_config'] = {'DryRun': False}

        ebs.delete(ctx=ctx, iface=iface, resource_config={})
        self.assertTrue(iface.delete.called)


class TestEC2VolumeAttachment(TestBase):

    def setUp(self):
        self.ebs_volume_attachment = EC2VolumeAttachment(
            "ctx_node",
            resource_id='test_name',
            client=True,
            logger=None)

        mock1 = patch(
            'cloudify_aws.common.decorators.aws_resource', mock_decorator
        )
        mock2 = patch(
            'cloudify_aws.common.decorators.wait_for_status', mock_decorator
        )
        mock1.start()
        mock2.start()
        reload_module(ebs)

    def test_class_properties(self):
        effect = self.get_client_error_exception(name='EC2 EBS Volume '
                                                      'Attachment')
        self.ebs_volume_attachment.client = \
            self.make_client_function('describe_volumes', side_effect=effect)

        res = self.ebs_volume_attachment.properties
        self.assertEqual(res, {})

        value = {}
        self.ebs_volume_attachment.client = \
            self.make_client_function('describe_volumes',
                                      return_value=value)
        res = self.ebs_volume_attachment.properties
        self.assertEqual(res, {})

        value =\
            {
                'Volumes':
                    [
                        {
                            'AvailabilityZone': 'test_zone',
                            'VolumeId': 'test_name',
                            'Attachments':
                                [
                                    {
                                        'Device': 'test_device',
                                        'InstanceId': 'test_instance_id',
                                        'State': 'attached',
                                        'VolumeId': 'test_name',
                                    }
                                ],
                            'State': 'in-use',
                        }
                    ]
            }

        self.ebs_volume_attachment.client = \
            self.make_client_function('describe_volumes', return_value=value)

        res = self.ebs_volume_attachment.properties
        self.assertEqual(res[VOLUME_ID], 'test_name')
        self.assertEqual(res[VOLUME_STATE], 'in-use')
        self.assertEquals(len(res['Attachments']), 1)

    def test_class_status(self):
        value = {}
        self.ebs_volume_attachment.client = \
            self.make_client_function('describe_volumes',
                                      return_value=value)
        res = self.ebs_volume_attachment.status
        self.assertIsNone(res)

        value =\
            {
                'Volumes':
                    [
                        {
                            'AvailabilityZone': 'test_zone',
                            'VolumeId': 'test_name',
                            'Attachments':
                                [
                                    {
                                        'Device': 'test_device',
                                        'InstanceId': 'test_instance_id',
                                        'State': 'attached',
                                        'VolumeId': 'test_volume_id',
                                    }
                                ],
                            'State': 'in-use',
                        }
                    ]
            }
        self.ebs_volume_attachment.client = \
            self.make_client_function('describe_volumes', return_value=value)

        res = self.ebs_volume_attachment.status
        self.assertEqual(res, 'in-use')

    def test_class_create(self):
        params =\
            {
                'Device': 'test_device',
                'InstanceId': 'test_instance_id',
                'VolumeId': 'test_volume_id',
            }

        output = \
            {
                'Device': 'test_device',
                'InstanceId': 'test_instance_id',
                'VolumeId': 'test_volume_id',
                'State': 'attached'
            }
        self.ebs_volume_attachment.client = \
            self.make_client_function('attach_volume', return_value=output)

        res = self.ebs_volume_attachment.create(params)
        self.assertEqual(res[VOLUME_ID], output[VOLUME_ID])
        self.assertEqual(res[VOLUME_STATE], 'attached')

    def test_class_delete(self):
        params = {}
        self.ebs_volume_attachment.client = \
            self.make_client_function('detach_volume')

        self.ebs_volume_attachment.delete(params)
        self.assertTrue(self.ebs_volume_attachment.client.detach_volume.called)

        params = {VOLUME_ID: 'test_volume_id'}

        output = \
            {
                'Device': 'test_device',
                'InstanceId': 'test_instance_id',
                'VolumeId': 'test_volume_id',
                'State': 'detached'
            }

        self.ebs_volume_attachment.client = \
            self.make_client_function('detach_volume', return_value=output)

        res = self.ebs_volume_attachment.delete(params)
        self.assertEqual(res[VOLUME_STATE], 'detached')

    def test_prepare(self):
        ctx = self.get_mock_ctx("EBSVolumeAttachment")
        config = \
            {
                'Device': 'test_device',
                'InstanceId': 'test_instance_id',
                'VolumeId': 'test_volume_id',
            }
        ebs.prepare(ctx, config)
        self.assertEqual(
            ctx.instance.runtime_properties['resource_config'], config)

    def test_create(self):
        ctx = self.get_mock_ctx("EBSVolumeAttachment")
        config = \
            {
                'Device': 'test_device',
                'InstanceId': 'test_instance_id',
                'VolumeId': 'test_volume_id',
            }
        self.ebs_volume_attachment.resource_id = config[VOLUME_ID]
        iface = MagicMock()
        iface.create = self.mock_return(config)
        ebs.attach(ctx, iface, config)
        self.assertEqual(self.ebs_volume_attachment.resource_id,
                         'test_volume_id')

    def test_delete(self):
        iface = MagicMock()
        ctx = self.get_mock_ctx("EBSVolumeAttachment")

        ctx.instance.runtime_properties[constants.EXTERNAL_RESOURCE_ID]\
            = 'test_volume_id'
        ctx.instance.runtime_properties['resource_config'] = {'DryRun': False}

        ebs.detach(ctx, iface, {})
        self.assertTrue(iface.delete.called)


if __name__ == '__main__':
    unittest.main()

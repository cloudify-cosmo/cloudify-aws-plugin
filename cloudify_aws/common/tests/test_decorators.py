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

import unittest

from mock import MagicMock, PropertyMock
from cloudify_aws.common.tests.test_base import TestBase
from cloudify.state import current_ctx
from cloudify.exceptions import OperationRetry, NonRecoverableError

from cloudify_aws.common import decorators


class TestDecorators(TestBase):

    def setUp(self):
        super(TestDecorators, self).setUp()
        self.maxDiff = None

    def _gen_decorators_context(self, _test_name, runtime_prop=None,
                                prop=None, op_name=None):

        op_name = op_name or 'cloudify.interfaces.lifecycle.create'

        _test_node_properties = prop if prop else {
            'use_external_resource': False
        }
        _test_runtime_properties = runtime_prop if runtime_prop else {
            'resource_config': {}
        }
        _ctx = self.get_mock_ctx(
            _test_name,
            test_properties=_test_node_properties,
            test_runtime_properties=_test_runtime_properties,
            type_hierarchy=['cloudify.nodes.Root'],
            ctx_operation_name=op_name
        )
        current_ctx.set(_ctx)
        return _ctx

    def test_wait_for_delete(self):
        _ctx = self._gen_decorators_context(
            'test_wait_for_delete',
            op_name='cloudify.interfaces.lifecycle.delete')

        @decorators.wait_for_delete(status_deleted=['deleted'],
                                    status_pending=['pending'])
        def test_delete(*agrs, **kwargs):
            pass

        # deleted
        mock_interface = MagicMock()
        mock_interface.status = 'deleted'

        test_delete(ctx=_ctx, iface=mock_interface)

        self.assertEqual(_ctx.instance.runtime_properties, {
            '__deleted': True,
        })

        # pending
        mock_interface = MagicMock()
        mock_interface.status = 'pending'

        with self.assertRaises(OperationRetry):
            test_delete(ctx=_ctx, iface=mock_interface)

        # unknow
        mock_interface = MagicMock()
        mock_interface.status = 'unknow'

        with self.assertRaises(NonRecoverableError):
            test_delete(ctx=_ctx, iface=mock_interface)

    def test_wait_for_status(self):

        _ctx = self._gen_decorators_context(
            'test_wait_for_status',
            runtime_prop={
                'aws_resource_id': 'foo',
                'resource_config': {}
            },
            op_name='cloudify.interfaces.lifecycle.create')

        @decorators.wait_for_status(status_good=['ok'],
                                    status_pending=['pending'])
        def test_ok(*agrs, **kwargs):
            pass

        def wait_for_status(*args, **kwargs):
            return False
        # pending
        mock_interface = MagicMock()
        mock_interface.status = 'pending'
        mock_interface.properties = {'status': 'pending'}
        mock_interface.resource_id = 'foo'
        mock_interface.wait_for_status = wait_for_status

        with self.assertRaises(OperationRetry):
            test_ok(ctx=_ctx, iface=mock_interface)

        # ok
        mock_interface = MagicMock()
        mock_interface.status = 'ok'
        mock_interface.properties = {'status': 'ok'}
        mock_interface.resource_id = 'foo'
        mock_interface.wait_for_status = wait_for_status

        test_ok(ctx=_ctx, iface=mock_interface)
        self.assertEqual(_ctx.instance.runtime_properties, {
            'resource_config': {},
            'aws_resource_id': 'foo',
            'create_response': {'status': 'ok'},
        })

        # unknow
        mock_interface = MagicMock()
        mock_interface.status = 'unknown'
        mock_interface.properties = {'status': 'unknown'}

        with self.assertRaises(NonRecoverableError):
            test_ok(ctx=_ctx, iface=mock_interface)

        # empty status
        mock_interface = MagicMock()
        mock_interface.status = None
        mock_interface.properties = {'status': None}
        mock_interface.resource_id = 'foo'
        mock_interface.wait_for_status = wait_for_status

        with self.assertRaises(NonRecoverableError):
            test_ok(ctx=_ctx, iface=mock_interface)

        # empty status but ignore
        mock_interface = MagicMock()
        mock_interface.status = None
        mock_interface.properties = {'status': None}
        mock_interface.resource_id = 'foo'
        mock_interface.wait_for_status = wait_for_status

        @decorators.wait_for_status(status_pending=['pending'],
                                    fail_on_missing=False)
        def test_ignore(*agrs, **kwargs):
            pass

        with self.assertRaises(OperationRetry):
            test_ignore(ctx=_ctx, iface=mock_interface)

    def test_aws_params_default(self):
        """params is in priority"""
        @decorators.aws_params("name")
        def test_default(*args, **kwargs):
            return args, kwargs

        _ctx = self.get_mock_ctx(
            'test_aws_params',
            test_properties={},
            test_runtime_properties={}
        )
        current_ctx.set(_ctx)

        _iface = MagicMock()
        _iface.resource_id = None

        # default name is node name
        self.assertEqual(test_default(ctx=_ctx, iface=_iface),
                         ((), {'ctx': _ctx, 'iface': _iface,
                               'params': {'name': 'test_aws_params'}}))
        self.assertEqual(_ctx.instance.runtime_properties,
                         {'aws_resource_id': 'test_aws_params'})

        # default name is node property
        _ctx = self.get_mock_ctx(
            'test_aws_params',
            test_properties={"resource_id": "property"},
            test_runtime_properties={}
        )
        current_ctx.set(_ctx)

        self.assertEqual(test_default(ctx=_ctx, iface=_iface),
                         ((), {'ctx': _ctx, 'iface': _iface,
                               'params': {'name': 'property'}}))
        self.assertEqual(_ctx.instance.runtime_properties,
                         {'aws_resource_id': "property"})

        # default name is node property
        _ctx = self.get_mock_ctx(
            'test_aws_params',
            test_properties={"resource_id": "property"},
            test_runtime_properties={"aws_resource_id": "runtime"}
        )
        current_ctx.set(_ctx)

        self.assertEqual(test_default(ctx=_ctx, iface=_iface),
                         ((), {'ctx': _ctx, 'iface': _iface,
                               'params': {'name': "runtime"}}))
        self.assertEqual(_ctx.instance.runtime_properties,
                         {'aws_resource_id': "runtime"})

        # default name is interface
        _ctx = self.get_mock_ctx(
            'test_aws_params',
            test_properties={"resource_id": "property"},
            test_runtime_properties={"aws_resource_id": "runtime"},
            ctx_operation_name='foo.foo.foo.create'
        )
        current_ctx.set(_ctx)
        _iface.resource_id = 'interface'

        self.assertEqual(test_default(ctx=_ctx, iface=_iface),
                         ((), {'ctx': _ctx, 'iface': _iface,
                               'params': {'name': "interface"}}))
        self.assertEqual(_ctx.instance.runtime_properties,
                         {'aws_resource_id': "interface"})

        # default name is parameters
        _ctx = self.get_mock_ctx(
            'test_aws_params',
            test_properties={"resource_id": "property"},
            test_runtime_properties={"aws_resource_id": "runtime"}
        )
        current_ctx.set(_ctx)
        _iface.resource_id = 'interface'

        self.assertEqual(test_default(ctx=_ctx, iface=_iface,
                                      resource_config={"name": 'config'}),
                         ((), {'ctx': _ctx, 'iface': _iface,
                               'params': {'name': "config"},
                               'resource_config': {"name": 'config'}}))
        self.assertEqual(_ctx.instance.runtime_properties,
                         {'aws_resource_id': "config"})

    def test_aws_params_runtime(self):
        """runtime is in priority"""
        @decorators.aws_params("name", params_priority=False)
        def test_default(*args, **kwargs):
            return args, kwargs

        _ctx = self.get_mock_ctx(
            'test_aws_params',
            test_properties={},
            test_runtime_properties={}
        )
        current_ctx.set(_ctx)

        _iface = MagicMock()
        _iface.resource_id = None

        # default name is node name
        self.assertEqual(test_default(ctx=_ctx, iface=_iface),
                         ((), {'ctx': _ctx, 'iface': _iface,
                               'params': {'name': 'test_aws_params'}}))
        self.assertEqual(_ctx.instance.runtime_properties,
                         {'name': 'test_aws_params',
                          'aws_resource_id': 'test_aws_params'})

        # default name is parameters, other values is empty
        _ctx = self.get_mock_ctx(
            'test_aws_params',
            test_properties={},
            test_runtime_properties={}
        )
        current_ctx.set(_ctx)
        _iface.resource_id = None

        self.assertEqual(test_default(ctx=_ctx, iface=_iface,
                                      resource_config={"name": 'config'}),
                         ((), {'ctx': _ctx, 'iface': _iface,
                               'params': {'name': "config"},
                               'resource_config': {"name": 'config'}}))
        self.assertEqual(_ctx.instance.runtime_properties,
                         {'name': 'config',
                          'aws_resource_id': 'config'})

        # default name is node property
        _ctx = self.get_mock_ctx(
            'test_aws_params',
            test_properties={"resource_id": "property"},
            test_runtime_properties={}
        )
        current_ctx.set(_ctx)

        self.assertEqual(test_default(ctx=_ctx, iface=_iface),
                         ((), {'ctx': _ctx, 'iface': _iface,
                               'params': {'name': 'property'}}))
        self.assertEqual(_ctx.instance.runtime_properties,
                         {'name': 'property',
                          'aws_resource_id': "property"})

        # default name is runtime
        _ctx = self.get_mock_ctx(
            'test_aws_params',
            test_properties={"resource_id": "property"},
            test_runtime_properties={"aws_resource_id": "runtime"}
        )
        current_ctx.set(_ctx)

        self.assertEqual(test_default(ctx=_ctx, iface=_iface),
                         ((), {'ctx': _ctx, 'iface': _iface,
                               'params': {'name': "runtime"}}))
        self.assertEqual(_ctx.instance.runtime_properties,
                         {'name': 'runtime',
                          'aws_resource_id': "runtime"})

        # default name is interface
        _ctx = self.get_mock_ctx(
            'test_aws_params',
            test_properties={"resource_id": "property"},
            test_runtime_properties={"aws_resource_id": "runtime"}
        )
        current_ctx.set(_ctx)
        _iface.resource_id = 'interface'

        self.assertEqual(test_default(ctx=_ctx, iface=_iface),
                         ((), {'ctx': _ctx, 'iface': _iface,
                               'params': {'name': "interface"}}))
        self.assertEqual(_ctx.instance.runtime_properties,
                         {'aws_resource_id': 'interface',
                          'name': "interface"})

        # default name is interface
        _ctx = self.get_mock_ctx(
            'test_aws_params',
            test_properties={"resource_id": "property"},
            test_runtime_properties={"aws_resource_id": "runtime"},
            ctx_operation_name='foo.foo.foo.precreate'
        )
        current_ctx.set(_ctx)
        _iface.resource_id = 'interface'

        self.assertEqual(test_default(ctx=_ctx, iface=_iface,
                                      resource_config={"name": 'config'}),
                         ((), {'ctx': _ctx, 'iface': _iface,
                               'params': {'name': "interface"},
                               'resource_config': {"name": 'config'}}))
        self.assertEqual(_ctx.instance.runtime_properties,
                         {'aws_resource_id': "interface",
                          'name': 'interface'})

    def test_aws_resource(self):

        fake_class_instance = MagicMock()
        FakeClass = MagicMock(return_value=fake_class_instance)

        @decorators.aws_resource(class_decl=FakeClass)
        def test_func(*agrs, **kwargs):
            pass

        # without resource_id
        _ctx = self._gen_decorators_context('test_aws_resource')

        test_func(ctx=_ctx)

        self.assertEqual(_ctx.instance.runtime_properties,
                         {'resource_config': {}})

        # with resource_id
        _ctx = self._gen_decorators_context('test_aws_resource')

        test_func(ctx=_ctx, aws_resource_id='res_id')

        self.assertEqual(_ctx.instance.runtime_properties,
                         {'aws_resource_arn': 'res_id',
                          'aws_resource_id': 'res_id',
                          'resource_config': {}})

        # set only unexisted id
        _ctx = self._gen_decorators_context('test_aws_resource', runtime_prop={
            'aws_resource_arn': 'res_arn',
            'resource_config': {}
        })

        iface = MagicMock()
        iface.status = None
        test_func(ctx=_ctx, aws_resource_id='res_id', iface=iface)

        self.assertEqual(_ctx.instance.runtime_properties,
                         {'aws_resource_arn': 'res_arn',
                          'aws_resource_id': 'res_id',
                          'resource_config': {}})

        # run delete operation
        _ctx = self._gen_decorators_context('test_aws_resource', runtime_prop={
            'aws_resource_arn': 'res_arn',
            'resource_config': {}
        })
        _operation = MagicMock()
        _operation.name = 'cloudify.interfaces.lifecycle.delete'
        _ctx._operation = _operation
        test_func(ctx=_ctx, aws_resource_id='res_id')

        self.assertEqual(_ctx.instance.runtime_properties,
                         {})

    def test_aws_resource_update_resource_arn(self):

        fake_class_instance = MagicMock()
        FakeClass = MagicMock(return_value=fake_class_instance)

        @decorators.aws_resource(class_decl=FakeClass)
        def test_func(*agrs, **kwargs):
            pass

        _ctx = self._gen_decorators_context('test_aws_resource', runtime_prop={
            'aws_resource_id': 'aws_id',
            'resource_config': {}
        })

        test_func(ctx=_ctx, aws_resource_id='res_id',
                  runtime_properties={'a': 'b'})

        self.assertEqual(_ctx.instance.runtime_properties,
                         {'aws_resource_arn': 'res_id',
                          'aws_resource_id': 'aws_id',
                          'a': 'b',
                          'resource_config': {}})

    def test_aws_resource_update_resource_id(self):

        fake_class_instance = MagicMock()
        FakeClass = MagicMock(return_value=fake_class_instance)

        @decorators.aws_resource(class_decl=FakeClass)
        def test_func(*agrs, **kwargs):
            pass

        _ctx = self._gen_decorators_context('test_aws_resource', runtime_prop={
            'aws_resource_id': 'aws_id',
            'resource_config': {}
        })

        test_func(ctx=_ctx, aws_resource_id='res_id',
                  runtime_properties={'a': 'b'})

        self.assertEqual(_ctx.instance.runtime_properties,
                         {'aws_resource_arn': 'res_id',
                          'aws_resource_id': 'aws_id',
                          'a': 'b',
                          'resource_config': {}})

    def test_aws_resource_remove_kwargs(self):
        # remove kwargs
        fake_class_instance = MagicMock()
        FakeClass = MagicMock(return_value=fake_class_instance)

        _ctx = self._gen_decorators_context('test_aws_resource', runtime_prop={
            'aws_resource_id': 'aws_id',
            'resource_config': {}
        }, prop={
            'resource_config': {
                'kwargs': {
                    'c': 'd'
                }
            },
            'e': 'f'
        })

        mock_func = MagicMock()

        @decorators.aws_resource(class_decl=FakeClass)
        def test_with_mock(*agrs, **kwargs):
            mock_func(*agrs, **kwargs)

        test_with_mock(ctx=_ctx, aws_resource_id='res_id',
                       runtime_properties={'a': 'b'})

        self.assertEqual(_ctx.instance.runtime_properties,
                         {'aws_resource_arn': 'res_id',
                          'aws_resource_id': 'aws_id',
                          'a': 'b',
                          'resource_config': {}})

        mock_func.assert_called_with(
            aws_resource_id='res_id', ctx=_ctx, iface=fake_class_instance,
            resource_config={'c': 'd'}, resource_type='AWS Resource',
            runtime_properties={'a': 'b'})

    def test_aws_resource_use_external_resource(self):
        fake_class_instance = MagicMock()
        FakeClass = MagicMock(return_value=fake_class_instance)

        # use_external_resource=True
        _ctx = self._gen_decorators_context('test_aws_resource', runtime_prop={
            'aws_resource_id': 'aws_id',
            'resource_config': {}
        }, prop={
            'resource_config': {
                'kwargs': {
                    'c': 'd'
                }
            },
            'e': 'f',
            'use_external_resource': True
        }, op_name='cloudify.interfaces.lifecycle.create')
        current_ctx.set(_ctx)

        mock_func = MagicMock()

        @decorators.aws_resource(class_decl=FakeClass, waits_for_status=False)
        def test_with_mock(*args, **kwargs):
            mock_func(*args, **kwargs)

        iface = MagicMock()
        iface.status = PropertyMock(return_value=True)
        test_with_mock(ctx=_ctx, aws_resource_id='res_id',
                       runtime_properties={'a': 'b'}, iface=iface)
        expected = {
            'aws_resource_arn': 'res_id',
            'aws_resource_id': 'aws_id',
            'a': 'b',
            'resource_config': {
                'c': 'd'
            },
            '__cloudify_tagged_external_resource': True
        }
        self.assertDictEqual(_ctx.instance.runtime_properties,
                             expected)

        mock_func.assert_not_called()

        # force call
        test_with_mock(ctx=_ctx, aws_resource_id='res_id',
                       runtime_properties={'a': 'b'}, force_operation=True)

        mock_func.assert_called_with(
            aws_resource_id='res_id', ctx=_ctx, iface=fake_class_instance,
            resource_config={'c': 'd'}, resource_type='AWS Resource',
            force_operation=True, runtime_properties={'a': 'b'})

    def _gen_decorators_realation_context(self, test_properties=None):
        _source_ctx = self.get_mock_ctx(
            'test_source',
            test_properties=test_properties if test_properties else {},
            test_runtime_properties={
                'resource_id': 'prepare_source',
                'aws_resource_id': 'aws_resource_mock_id',
                '_set_changed': True,
                'resource_config': {}
            },
            type_hierarchy=['cloudify.nodes.Root']
        )

        _target_ctx = self.get_mock_ctx(
            'test_target',
            test_properties={'use_external_resource': True},
            test_runtime_properties={
                'resource_id': 'prepare_target',
                'aws_resource_id': 'aws_target_mock_id',
            },
            type_hierarchy=['cloudify.nodes.Root']
        )

        _ctx = self.get_mock_relationship_ctx(
            'test_aws_relationship',
            test_properties={},
            test_runtime_properties={},
            test_source=_source_ctx,
            test_target=_target_ctx
        )

        current_ctx.set(_ctx)
        return _ctx

    def test_aws_relationship(self):
        fake_class_instance = MagicMock()
        FakeClass = MagicMock(return_value=fake_class_instance)

        mock_func = MagicMock()

        @decorators.aws_relationship(class_decl=FakeClass)
        def test_with_mock(*args, **kwargs):
            mock_func(*args, **kwargs)

        _ctx = self._gen_decorators_realation_context()

        test_with_mock(ctx=_ctx)

        mock_func.assert_called_with(
            ctx=_ctx,
            iface=fake_class_instance, resource_config={},
            resource_type='AWS Resource')

    def test_aws_relationship_external(self):
        fake_class_instance = MagicMock()
        FakeClass = MagicMock(return_value=fake_class_instance)

        mock_func = MagicMock()

        @decorators.aws_relationship(class_decl=FakeClass)
        def test_with_mock(*args, **kwargs):
            mock_func(*args, **kwargs)

        _ctx = self._gen_decorators_realation_context(test_properties={
            'use_external_resource': True
        })

        test_with_mock(ctx=_ctx)

        mock_func.assert_not_called()

        # force run
        test_with_mock(ctx=_ctx, force_operation=True)

        mock_func.assert_called_with(
            ctx=_ctx,
            iface=fake_class_instance, resource_config={},
            force_operation=True, resource_type='AWS Resource')


if __name__ == '__main__':
    unittest.main()

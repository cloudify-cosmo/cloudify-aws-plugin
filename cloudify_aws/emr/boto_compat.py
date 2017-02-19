# #######
# Copyright (c) 2017 GigaSpaces Technologies Ltd. All rights reserved
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
'''
    EMR.boto2_compat
    ~~~~~~~~~~~~~~~~
    Boto2 compatibility (extensions) layer
'''
# pylint: disable=R0903


def build_applications_list(app_defs):
    '''
        Creates a Boto-formatted dictionary of EMR
        cluster applications for use with the cluster
        creation process (api_params).

    :param list app_defs: This can either be a list of
        strings (names) or a dict with keys matching
        the requirements of the `cloudify_aws.emr.boto2_compat.Application`
        class.
    '''
    apps = dict()
    label = 'Applications.member.%d'
    app_objs = [Application(**x) for x in [
        dict(name=x) if isinstance(x, basestring) else x
        for x in app_defs]]
    # Update the api_params dict
    for idx, app in enumerate(app_objs):
        apps.update(app.build(label % (idx + 1)))
    return apps


class Application(object):
    '''AWS EMR Application'''
    def __init__(self, name, version=None, args=None, additional_info=None):
        args = args if isinstance(args, list) else [args]
        args = [x for x in args if x is not None]
        self.items = {k: v for k, v in dict(
            Name=name,
            Version=version,
            Args=args,
            AdditionalInfo=additional_info).iteritems() if v}

    def build(self, prefix='Applications.member.0'):
        '''Builds an AWS-formatted dictionary of parameters'''
        params = dict()
        # Make sure prefix ends with a period
        if prefix:
            if not prefix.endswith('.'):
                prefix = prefix + '.'
        # Build the custom mappings
        for key, val in self.items.iteritems():
            if key in ['Name', 'Version']:
                params[key] = val
            elif key in ['Args']:
                for kidx in range(len(val)):
                    params['%s.member.%d' % (key, kidx + 1)] = val
            elif key in ['AdditionalInfo']:
                for skey, sval in val.iteritems():
                    params['%s.%s' % (key, skey)] = sval
        return {'%s%s' % (prefix, k): v for k, v in params.iteritems()}

    def __repr__(self):
        return '%s.%s(%s)' % (
            self.__class__.__module__, self.__class__.__name__,
            ', '.join(['%s=%r' % (k, v) for k, v in self.items.iteritems()]))

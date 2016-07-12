#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
#    * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    * See the License for the specific language governing permissions and
#    * limitations under the License.

# Third-party Imports
from boto import exception
from boto.ec2.elb.healthcheck import HealthCheck

# Cloudify imports
from cloudify_aws import constants, utils, connection
from cloudify import ctx
from cloudify.decorators import operation
from cloudify.exceptions import NonRecoverableError
from cloudify.exceptions import RecoverableError
from cloudify_aws.base import AwsBaseNode, AwsBaseRelationship


@operation
def creation_validation(**_):
    return Elb().creation_validation()


@operation
def create(**_):
    return Elb().created()


@operation
def delete(**_):
    return Elb().deleted()


@operation
def associate(**_):
    return ElbInstanceConnection().associated()


@operation
def disassociate(**_):
    return ElbInstanceConnection().disassociated()


class ElbInstanceConnection(AwsBaseRelationship):

    def __init__(self, client=None):
        super(ElbInstanceConnection, self).__init__(client=client)
        self.not_found_error = 'InvalidInstanceID.NotFound.'
        self.resource_id = None
        self.client = connection.ELBConnectionClient().client()
        self.source_get_all_handler = {
            'function': self.client.get_all_load_balancers,
            'argument':
                '{0}_names'.format(constants.ELB['AWS_RESOURCE_TYPE'])
        }

    def associate(self, **_):

        elb_name = \
            utils.get_external_resource_id_or_raise(
                    'register instance', ctx.target.instance)

        instance_id = \
            utils.get_external_resource_id_or_raise(
                    'register instance', ctx.source.instance)

        ctx.logger.info('Attemping to add instance: {0} to elb {1}'
                        .format(instance_id, elb_name))

        adding_args = dict(
                            load_balancer_name=elb_name,
                            instances=[instance_id]
                        )

        try:
            self.execute(self.client.register_instances, adding_args,
                         raise_on_falsy=True)
        except (exception.EC2ResponseError,
                exception.BotoServerError,
                exception.BotoClientError) as e:
                raise NonRecoverableError('Instance not added to Load '
                                          'Balancer {0}'.format(str(e)))

        ctx.logger.info(
                'Instance {0} added to Load Balancer {1}.'
                .format(instance_id, elb_name))

        self._add_instance_to_elb_list_in_properties(instance_id)

        return True

    def disassociate(self, **_):

        elb_name = \
            utils.get_external_resource_id_or_raise(
                    'deregister instance', ctx.target.instance)

        instance_id = \
            utils.get_external_resource_id_or_raise(
                    'deregister instance', ctx.source.instance)

        instance_list = [instance_id]
        lb = self._get_existing_elb(elb_name)

        ctx.logger.info('Attempting to remove instance: {0} from elb {1}'
                        .format(instance_id, elb_name))

        try:
            lb.deregister_instances(instance_list)
        except (exception.EC2ResponseError,
                exception.BotoServerError,
                exception.BotoClientError) as e:
            if instance_id in self._get_instance_list():
                raise RecoverableError('Instance not removed from Load '
                                       'Balancer {0}'.format(str(e)))

        ctx.logger.info(
                'Instance {0} deregistrated from Load Balancer {1}.'
                .format(instance_id, elb_name))
        self._remove_instance_from_elb_list_in_properties(instance_id)

        return True

    def post_associate(self):

        ctx.logger.info(
                'Instance {0} registrated to Load Balancer {1}.'
                .format(self.source_resource_id, self.target_resource_id))

        self._add_instance_to_elb_list_in_properties(self.source_resource_id)

        return True

    def _get_existing_elb(self, elb_name):
        elbs = self._get_elbs_by_names([elb_name])
        if elbs:
            if elbs[0].name == elb_name:
                return elbs[0]
        return None

    def _get_elbs_by_names(self, list_of_names):

        ctx.logger.info(
                'Attempting to get Load Balancers {0}.'.format(list_of_names))
        total_elb_list = ''

        try:
            total_elb_list = self.client.get_all_load_balancers()
            elb_list = self.client.get_all_load_balancers(
                    load_balancer_names=list_of_names)
        except (exception.EC2ResponseError,
                exception.BotoServerError,
                exception.BotoClientError) as e:
            if 'LoadBalancerNotFound' in e:
                ctx.logger.info('Unable to find load balancers matching: '
                                '{0}'.format(list_of_names))
                ctx.logger.info('load balancers available: '
                                '{0}'.format(total_elb_list))
            raise NonRecoverableError('Error when accessing ELB interface '
                                      '{0}'.format(str(e)))
        return elb_list

    def _add_instance_to_elb_list_in_properties(self, instance_id):

        if 'instance_list' not in \
                ctx.target.instance.runtime_properties.keys():
            ctx.target.instance.runtime_properties['instance_list'] = []

        ctx.target.instance.runtime_properties['instance_list']\
            .append(instance_id)

    def _remove_instance_from_elb_list_in_properties(self, instance_id):
        if instance_id in \
                ctx.target.instance.runtime_properties['instance_list']:
            ctx.target.instance.runtime_properties['instance_list']\
                .remove(instance_id)

    def _get_instance_list(self):

        ctx.logger.info('Attempting to get Load Balancer Instance List.')

        elb_name = ctx.node.properties['elb_name']
        lb = self._get_existing_elb(elb_name)
        list_of_instances = lb.instances
        ctx.instance.runtime_properties[constants.EXTERNAL_RESOURCE_ID] = \
            lb.name

        return list_of_instances


class Elb(AwsBaseNode):

    def __init__(self):
        super(Elb, self).__init__(
                constants.ELB['AWS_RESOURCE_TYPE'],
                constants.ELB['REQUIRED_PROPERTIES']
        )
        self.client = connection.ELBConnectionClient().client()
        self.not_found_error = constants.ELB['NOT_FOUND_ERROR']
        self.get_all_handler = {
            'function': self.client.get_all_load_balancers,
            'argument': '{0}_names'.format(constants.ELB['AWS_RESOURCE_TYPE'])
        }

    def creation_validation(self, **_):
        """ This checks that all user supplied info is valid """

        for property_key in constants.ELB['REQUIRED_PROPERTIES']:
            utils.validate_node_property(property_key, ctx.node.properties)

        if not ctx.node.properties['resource_id']:
            elb = None
        else:
            elb = self._get_existing_elb(
                    ctx.node.properties['resource_id'])

        if ctx.node.properties['use_external_resource'] and not elb:
            raise NonRecoverableError(
                    'External resource, but the supplied '
                    'elb does not exist in the account.')

        if not ctx.node.properties['use_external_resource'] and elb:
            raise NonRecoverableError(
                    'Not external resource, but the supplied '
                    'elb exists.')

        return True

    def create(self, **_):

        lb = self._create_elb()

        health_checks = ctx.node.properties.get('health_checks')

        if health_checks:
            for health_check in health_checks:
                self._add_health_check_to_elb(lb, health_check)

        return True

    def deleted(self):

        ctx.logger.info(
                'Attempting to delete {0} {1}.'
                .format(self.aws_resource_type,
                        self.cloudify_node_instance_id))

        if not self.resource_id or self.is_external_resource:
            return False

        if self.delete_external_resource_naively() or self.delete():
            return self.post_delete()

        raise NonRecoverableError(
                'Neither external resource, nor Cloudify resource, '
                'unable to delete this resource.')

    def _create_elb(self):

        params_dict = self._create_elb_params()

        try:
            lb = self.execute(self.client.create_load_balancer, params_dict,
                              raise_on_falsy=True)
        except (exception.EC2ResponseError,
                exception.BotoServerError,
                exception.BotoClientError) as e:
            raise RecoverableError('Load Balancer not created '
                                   '{0}'.format(str(e)))

        if not lb:
            raise NonRecoverableError(
                    'Load Balancer not created. While the create '
                    'request was completed'
                    ' successfully, verifying the load balancer '
                    'afterwards has failed')

        ctx.logger.info('Load Balancer Created.')

        ctx.instance.runtime_properties['elb_name'] = params_dict['name']
        self.resource_id = params_dict['name']

        return lb

    def delete(self, **_):

        elb_name = ctx.node.properties['elb_name']

        try:
            self.execute(self.client.delete_load_balancer, dict(name=elb_name),
                         raise_on_falsy=True)
        except (exception.EC2ResponseError,
                exception.BotoServerError,
                exception.BotoClientError) as e:
            raise NonRecoverableError('Load Balancer {0} not deleted.'
                                      .format(str(e)))

        if 'elb_name' in ctx.instance.runtime_properties:
            ctx.instance.runtime_properties.pop('elb_name')

        return True

    def _add_health_check_to_elb(self, elb, health_check):

        hc = self._create_health_check(health_check)
        add_hc_args = dict(
                            name=elb.name,
                            health_check=hc
                        )

        try:
            self.execute(self.client.configure_health_check, add_hc_args,
                         raise_on_falsy=True)
        except (exception.EC2ResponseError,
                exception.BotoServerError,
                exception.BotoClientError) as e:
            raise NonRecoverableError('Health check not added to Load '
                                      'Balancer {0}'.format(str(e)))

        ctx.logger.info(
                'Health check added to Load Balancer {0}.'
                .format(elb.name))

    def _create_elb_params(self):
        params_dict = {'listeners': ctx.node.properties['listeners'],
                       'name': ctx.node.properties['elb_name'],
                       'zones': ctx.node.properties['zones']}
        if 'security_groups' in ctx.node.properties.keys():
            params_dict['security_groups'] = \
                ctx.node.properties['security_groups']
        if 'scheme' in ctx.node.properties.keys():
            params_dict['scheme'] = ctx.node.properties['scheme']
        if 'subnets' in ctx.node.properties.keys():
            params_dict['subnets'] = ctx.node.properties['subnets']
        return params_dict

    def _get_existing_elb(self, elb_name):
        elbs = self._get_elbs_by_names([elb_name])
        if elbs:
            if elbs[0].name == elb_name:
                return elbs[0]
        return None

    def _create_health_check(self, user_health_check):

        health_check = {
            'interval': constants.HEALTH_CHECK_INTERVAL,
            'healthy_threshold': constants.HEALTH_CHECK_HEALTHY_THRESHOLD,
            'timeout': constants.HEALTH_CHECK_TIMEOUT,
            'unhealthy_threshold': constants.HEALTH_CHECK_UNHEALTHY_THRESHOLD
        }

        health_check.update(user_health_check)

        try:
            health_check = HealthCheck(**health_check)
        except exception.BotoClientError as e:
            raise NonRecoverableError(
                    'Health Check not created due to bad definition: '
                    '{0}'.format(str(e)))

        return health_check

    def _get_elbs_by_names(self, list_of_names):

        ctx.logger.info(
                'Attempting to get Load Balancers {0}.'.format(list_of_names))
        total_elb_list = ''

        try:
            total_elb_list = self.client.get_all_load_balancers()
            elb_list = self.client.get_all_load_balancers(
                    load_balancer_names=list_of_names)
        except (exception.EC2ResponseError,
                exception.BotoServerError,
                exception.BotoClientError) as e:
            if 'LoadBalancerNotFound' in e:
                ctx.logger.info('Unable to find load balancers matching: '
                                '{0}'.format(list_of_names))
                ctx.logger.info('load balancers available: '
                                '{0}'.format(total_elb_list))
            raise NonRecoverableError('Error when accessing ELB interface '
                                      '{0}'.format(str(e)))
        return elb_list

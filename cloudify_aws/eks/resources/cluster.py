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
    EKSCluster
    ~~~~~~~~~~~~~~
    AWS EKS Cluster interface
"""
import base64
import json

# Boto
import boto3
from botocore.exceptions import ClientError, ParamValidationError, WaiterError

from cloudify.decorators import operation
from cloudify.exceptions import OperationRetry, NonRecoverableError
from cloudify_rest_client.exceptions import CloudifyClientError

# Local imports
from cloudify_aws.eks import EKSBase
from cloudify_aws.common import constants, decorators, utils
from cloudify_aws.common._compat import text_type
from cloudify_aws.ec2.resources.subnet import EC2Subnet

RESOURCE_TYPE = 'EKS Cluster'
CLUSTER_TYPE = 'cloudify.nodes.aws.eks.Cluster'
CLUSTER_NAME = 'name'
CLUSTER_ARN = 'arn'
CLUSTER = 'cluster'
CLUSTERS = 'clusters'

CLUSTER_NAME_HEADER = 'x-k8s-aws-id'
TOKEN_PREFIX = 'k8s-aws-v1.'
TOKEN_EXPIRATION_MINS = 60


def _retrieve_cluster_name(params, context, **kwargs):
    if 'ClusterName' in params:
        context['eks_cluster'] = params.pop('ClusterName')


def _inject_cluster_name_header(request, **kwargs):
    if 'eks_cluster' in request.context:
        request.headers[CLUSTER_NAME_HEADER] = request.context['eks_cluster']


def _register_cluster_name_handlers(sts_client):
        sts_client.meta.events.register(
            'provide-client-params.sts.GetCallerIdentity',
            _retrieve_cluster_name
        )
        sts_client.meta.events.register(
            'before-sign.sts.GetCallerIdentity',
            _inject_cluster_name_header
        )


class EKSCluster(EKSBase):
    """
        EKS Cluster interface
    """
    def __init__(self, ctx_node, resource_id=None, client=None, logger=None):
        EKSBase.__init__(self, ctx_node, resource_id, client, logger)
        self.type_name = RESOURCE_TYPE
        self._id_key = CLUSTER_NAME
        self._type_key = CLUSTER
        self._properties = {}
        self._describe_call = 'describe_cluster'
        self.describe_param = {self._id_key: self.resource_id}

    def wait_for_status(self):
        self.logger.info('Performing wait for cluster.')
        try:
            self.wait_for_cluster(
                self.describe_params, 'cluster_active',
                max_attempt=30)
        except WaiterError:
            raise OperationRetry('Waiting for nodegroup...')

    @property
    def status(self):
        """Gets the status of an external resource"""
        props = self.properties
        if not props:
            return None
        return props.get('status')

    @property
    def check_status(self):
        if self.status in ['ACTIVE']:
            return 'OK'
        return 'NOT OK'

    def describe(self, params=None):
        params = params or self.describe_param
        return self.get_describe_result(params)

    def describe_all(self):
        clusters = []
        for cluster_name in self.list():
            clusters.append(self.describe({'name': cluster_name}))
        return clusters

    def list(self, params=None):
        """
            List AWS EKS clusters.
        """
        try:
            return self.make_client_call('list_clusters', params)[CLUSTERS]
        except (ParamValidationError, ClientError):
            return []

    def create(self, params):
        """
            Create a new AWS EKS cluster.
        """
        self.create_response = self.make_client_call('create_cluster', params)
        self.update_resource_id(self.create_response[CLUSTER].get(
            CLUSTER_NAME, ''))

    @property
    def fargate_profiles(self):
        return self.client.list_fargate_profiles(
            clusterName=self.resource_id)['fargateProfileNames']

    @property
    def nodegroups(self):
        return self.client.list_nodegroups(
            clusterName=self.resource_id)['nodegroups']

    def wait_for_cluster(self, params, status, max_attempt=None):
        """
            wait for AWS EKS cluster.
        """
        max_attempt = max_attempt or 30
        waiter = self.client.get_waiter(status)
        try:
            waiter.wait(
                name=params.get(CLUSTER_NAME),
                WaiterConfig={
                    'Delay': 30,
                    'MaxAttempts': max_attempt
                }
            )
        except WaiterError:
            raise OperationRetry('Waiting for cluster...')

    def get_kubeconf(self, client_config, params):
        """
            get kubernetes configuration for cluster.
        """
        cluster = \
            self.client.describe_cluster(name=params.get(CLUSTER_NAME))
        cluster_cert = cluster["cluster"]["certificateAuthority"]["data"]
        cluster_ep = cluster["cluster"]["endpoint"]
        sts_client = boto3.client('sts', **client_config)
        _register_cluster_name_handlers(sts_client)
        url = sts_client.generate_presigned_url(
            'get_caller_identity',
            {'ClusterName': params.get(CLUSTER_NAME)},
            HttpMethod='GET',
            ExpiresIn=TOKEN_EXPIRATION_MINS)
        encoded = base64.urlsafe_b64encode(url.encode('utf-8'))
        token = TOKEN_PREFIX + \
            encoded.decode('utf-8').rstrip('=')
        # build the cluster config hash
        cluster_config = {
            "apiVersion": "v1",
            "kind": "Config",
            "clusters": [
                {
                    "cluster": {
                        "server": text_type(cluster_ep),
                        "certificate-authority-data": text_type(cluster_cert)
                    },
                    "name": "kubernetes"
                }
            ],
            "contexts": [
                {
                    "context": {
                        "cluster": "kubernetes",
                        "user": "aws"
                    },
                    "name": "aws"
                }
            ],
            "current-context": "aws",
            "preferences": {},
            "users": [
                {
                    "name": "aws",
                    "user": {
                        "token": token
                    }
                }
            ]
        }
        return cluster_config

    def delete(self, params=None):
        """
            Deletes an existing AWS EKS cluster.
        """
        res = self.client.delete_cluster(
            **{CLUSTER_NAME: params.get(CLUSTER_NAME)}
        )
        self.logger.debug('Response: {}'.format(res))
        return res


def prepare_describe_cluster_filter(params, iface):
    iface.describe_param = {
        CLUSTER_NAME: params.get(CLUSTER_NAME),
    }
    return iface


def _store_kubeconfig_in_runtime_properties(node, instance, iface, params):
    try:
        client_config = node.properties['client_config']
        kubeconf = iface.get_kubeconf(client_config, params)
        # check if kubeconf is json serializable or not
        json.dumps(kubeconf)
        instance.runtime_properties['kubeconf'] = kubeconf
    except TypeError as error:
        raise NonRecoverableError(
            'kubeconf not json serializable {0}'.format(text_type(error)))


@decorators.aws_resource(EKSCluster, RESOURCE_TYPE, waits_for_status=False)
def prepare(ctx, iface, resource_config, **_):
    """Prepares an AWS EKS Cluster"""
    name = resource_config.get('name') or \
        ctx.node.properties.get('resource_id')
    if name:
        resource_config['name'] = name
    utils.update_resource_id(ctx.instance, name)
    ctx.instance.runtime_properties['resource_config'] = resource_config


@decorators.aws_resource(EKSCluster, RESOURCE_TYPE, waits_for_status=False)
def create(ctx, iface, resource_config, **_):
    """Creates an AWS EKS Cluster"""
    resource_id = utils.get_resource_id(ctx.node,
                                        ctx.instance,
                                        resource_config.get(CLUSTER_NAME),
                                        use_instance_id=True)

    utils.update_resource_id(ctx.instance, resource_id)
    iface = prepare_describe_cluster_filter(resource_config.copy(), iface)
    iface.create(resource_config)
    if iface.create_response.get(CLUSTER):
        utils.update_resource_arn(
            ctx.instance, iface.create_response.get(CLUSTER).get(CLUSTER_ARN))


@decorators.aws_resource(EKSCluster, RESOURCE_TYPE, waits_for_status=False)
def poststart(ctx, iface, resource_config, **_):
    name = resource_config.get('name') or \
           ctx.node.properties.get('resource_id')
    if name:
        resource_config['name'] = name
    # wait for cluster to be active
    ctx.logger.info("Waiting for Cluster to become Active.")
    iface.wait_for_cluster(resource_config, 'cluster_active')

    store_kube_config_in_runtime = \
        ctx.node.properties['store_kube_config_in_runtime']
    if store_kube_config_in_runtime:
        _store_kubeconfig_in_runtime_properties(ctx.node,
                                                ctx.instance,
                                                iface,
                                                resource_config)
    region_name = ctx.node.properties['client_config']['region_name']
    aws_resource_arn = ctx.instance.runtime_properties.get(
        'aws_resource_arn', iface.properties['arn'])
    fargate = iface.fargate_profiles
    node_group = iface.nodegroups
    if fargate and node_group:
        node_type = 'fargate-nodegroup'
    elif fargate:
        node_type = 'fargate'
    else:
        node_type = 'nodegroup'
    zones = get_zones(
        ctx,
        resource_config.get(
            'resourcesVpcConfig',
            iface.properties['resourcesVpcConfig'])['subnetIds'])
    try:
        utils.add_new_labels(
            {
                'csys-env-type': 'eks',
                'aws-region': region_name,
                'external-id': aws_resource_arn,
                'eks-node-type': node_type,
                'location': ', '.join(zones)
            },
            ctx.deployment.id)
    except CloudifyClientError:
        ctx.logger.warn(
            'Skipping assignment of labels due to '
            'incompatible Cloudify version.')

    try:
        location = constants.LOCATIONS.get(region_name)
        if location:
            utils.assign_site(
                ctx.deployment.id,
                location['coordinates'],
                name
            )
    except ClientError:
        ctx.logger.warn('Skipping assignment of site due to '
                        'incompatible Cloudify version.')
    ctx.instance.runtime_properties['resource'] = utils.JsonCleanuper(
        iface.properties).to_dict()
    utils.update_expected_configuration(iface, ctx.instance.runtime_properties)


@decorators.aws_resource(EKSCluster, RESOURCE_TYPE, waits_for_status=False)
def delete(ctx, iface, resource_config, **_):
    """Deletes an AWS EKS Cluster"""
    iface.delete(resource_config)
    # wait for cluster to be deleted
    ctx.logger.info("Waiting for Cluster to be deleted")
    iface.wait_for_cluster(resource_config, 'cluster_deleted')


@operation
def refresh_kubeconfig(ctx,
                       **_):
    """
    Refresh access token in kubeconfig for cloudify.nodes.aws.eks.Cluster
    target node type.
    """
    if utils.is_node_type(ctx.target.node,
                          CLUSTER_TYPE):
        resource_config = ctx.target.instance.runtime_properties.get(
            'resource_config',
            {})
        iface = EKSCluster(ctx.target.node,
                           logger=ctx.logger,
                           resource_id=utils.get_resource_id(
                               node=ctx.target.node,
                               instance=ctx.target.instance,
                               raise_on_missing=True))
        if ctx.target.node.properties['store_kube_config_in_runtime']:
            _store_kubeconfig_in_runtime_properties(
                node=ctx.target.node,
                instance=ctx.target.instance,
                iface=iface,
                params=resource_config)


def discover_clusters(ctx=None, client_config=None, **_):
    client_config = client_config or {}
    clusters = {}
    clusters.update(client_config)
    return clusters


def get_zones(ctx, subnets):
    zones = []
    for subnet in subnets:
        subnet_iface = EC2Subnet(ctx.node, subnet, logger=ctx.logger)
        availability_zone = subnet_iface.properties.get('AvailabilityZone')
        if availability_zone:
            zones.append(availability_zone)
    return zones


@decorators.aws_resource(class_decl=EKSCluster,
                         resource_type=RESOURCE_TYPE,
                         waits_for_status=False)
def check_drift(ctx, iface=None, **_):
    return utils.check_drift(RESOURCE_TYPE, iface, ctx.logger)


interface = EKSCluster

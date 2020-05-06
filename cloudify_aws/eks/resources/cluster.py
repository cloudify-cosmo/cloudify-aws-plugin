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
from botocore.exceptions import ClientError

# Local imports
from cloudify_aws.common._compat import text_type
from cloudify_aws.eks import EKSBase
from cloudify_aws.common import decorators, utils
from cloudify.exceptions import NonRecoverableError

RESOURCE_TYPE = 'EKS Cluster'
CLUSTER_NAME = 'name'
CLUSTER_ARN = 'arn'
CLUSTER = 'cluster'

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
        self.describe_param = {}

    @property
    def properties(self):
        """Gets the properties of an external resource"""
        try:
            properties = \
                self.client.describe_cluster(
                    **self.describe_param
                )[CLUSTER]
        except ClientError:
            pass
        else:
            return None if not properties else properties

    @property
    def status(self):
        """Gets the status of an external resource"""
        props = self.properties
        if not props:
            return None
        return props.get('status')

    def create(self, params):
        """
            Create a new AWS EKS cluster.
        """
        return self.make_client_call('create_cluster', params)

    def wait_for_cluster(self, params, status):
        """
            wait for AWS EKS cluster.
        """
        waiter = self.client.get_waiter(status)
        waiter.wait(
            name=params.get(CLUSTER_NAME),
            WaiterConfig={
                'Delay': 30,
                'MaxAttempts': 40
            }
        )

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


@decorators.aws_resource(resource_type=RESOURCE_TYPE)
def prepare(ctx, resource_config, **_):
    """Prepares an AWS EKS Cluster"""
    # Save the parameters
    ctx.instance.runtime_properties['resource_config'] = resource_config


@decorators.aws_resource(EKSCluster, RESOURCE_TYPE)
def create(ctx, iface, resource_config, **_):
    """Creates an AWS EKS Cluster"""
    store_kube_config_in_runtime = \
        ctx.node.properties['store_kube_config_in_runtime']
    params = dict() if not resource_config else resource_config.copy()
    resource_id = \
        utils.get_resource_id(
            ctx.node,
            ctx.instance,
            params.get(CLUSTER_NAME),
            use_instance_id=True
        )

    utils.update_resource_id(ctx.instance, resource_id)
    iface = prepare_describe_cluster_filter(resource_config.copy(), iface)
    response = iface.create(params)
    if response and response.get(CLUSTER):
        resource_arn = response.get(CLUSTER).get(CLUSTER_ARN)
        utils.update_resource_arn(ctx.instance, resource_arn)
    # wait for cluster to be active
    ctx.logger.info("Waiting for Cluster to become Active")
    iface.wait_for_cluster(params, 'cluster_active')
    if store_kube_config_in_runtime:
        try:
            client_config = ctx.node.properties['client_config']
            kubeconf = iface.get_kubeconf(client_config, params)
            # check if kubeconf is json serializable or not
            json.dumps(kubeconf)
            ctx.instance.runtime_properties['kubeconf'] = kubeconf
        except TypeError as error:
            raise NonRecoverableError(
                'kubeconf not json serializable {0}'.format(text_type(error)))


@decorators.aws_resource(EKSCluster, RESOURCE_TYPE)
def delete(ctx, iface, resource_config, **_):
    """Deletes an AWS EKS Cluster"""

    params = dict() if not resource_config else resource_config.copy()
    iface.delete(params)
    # wait for cluster to be deleted
    ctx.logger.info("Waiting for Cluster to be deleted")
    iface.wait_for_cluster(params, 'cluster_deleted')

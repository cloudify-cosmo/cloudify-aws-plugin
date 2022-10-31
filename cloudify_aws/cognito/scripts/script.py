import boto3 # noqa

from .params import (
    sns_role_params,
    sns_policy_params,
    cognito_auth_policy,
    get_user_pool_params,
    get_identity_pool_params,
    get_user_pool_client_params,
    get_unauth_role_params,
    get_unauth_policy_params,
    get_identity_pool_provider,
    get_cognito_auth_role_params,
    get_identity_pool_role_params,
)

sns = boto3.client('sns')
iam = boto3.client('iam')
cognito = boto3.client('cognito-idp')
cognito_identity = boto3.client('cognito-identity')


def create_sns_component():
    role = iam.create_role(**sns_role_params)
    pol = iam.create_policy(**sns_policy_params)
    att = iam.attach_role_policy(
        RoleName=role['Role']['RoleName'],
        PolicyArn=pol['Policy']['Arn']
    )
    return role, pol, att


def create_unauth_component(identity_pool_id):
    cognito_unauth_role_params = get_unauth_role_params(identity_pool_id)
    role = iam.create_role(**cognito_unauth_role_params)
    cognito_unauth_policy = get_unauth_policy_params()
    pol = iam.create_policy(**cognito_unauth_policy)
    att = iam.attach_role_policy(
        RoleName=role['Role']['RoleName'],
        PolicyArn=pol['Policy']['Arn']
    )
    return role, pol, att


def create_auth_component(identity_pool_id):
    cognito_auth_role_params = get_cognito_auth_role_params(
        identity_pool_id)
    role = iam.create_role(**cognito_auth_role_params)
    pol = iam.create_policy(**cognito_auth_policy)
    att = iam.attach_role_policy(
        RoleName=role['Role']['RoleName'],
        PolicyArn=pol['Policy']['Arn']
    )
    return role, pol, att


def create_user_pool(sns_role_arn):
    try:
        user_pool_params = get_user_pool_params(sns_role_arn)
        user_pool_response = cognito.create_user_pool(**user_pool_params)
    except:
        return None, None
    try:
        user_pool_client_create = get_user_pool_client_params(
            user_pool_response['UserPool']['Id'])
        user_pool_client_response = cognito.create_user_pool_client(
            **user_pool_client_create)
    except:
        return user_pool_response, None
    return user_pool_response, user_pool_client_response


def create_identity_pool(user_pool_id, client_id, client_secret):
    try:
        identity_provider_params = get_identity_pool_provider(
            user_pool_id, client_id, client_secret)
        identity_provider_response = cognito.create_identity_provider(
            **identity_provider_params)
    except:
        return None, None
    try:
        identity_pool_params = get_identity_pool_params(
            client_id,
            identity_provider_response['IdentityProvider']['UserPoolId'])
        identity_pool_response = cognito_identity.create_identity_pool(
            **identity_pool_params)
    except:
        return identity_provider_response, None
    return identity_provider_response, identity_pool_response


sns_role_response, sns_policy_response, attach_policy_response = \
    create_sns_component()
user_pool_response, user_pool_client_response = \
    create_user_pool(sns_role_response['Role']['Arn']) # This can raise InvalidSmsRoleTrustRelationshipException
identity_provider_response, identity_pool_response = \
    create_identity_pool(
        user_pool_response['UserPool']['Id'],
        user_pool_client_response['UserPoolClient']['ClientId'],
        user_pool_client_response['UserPoolClient']['ClientSecret'],
    )

cognito_unauth_role_response, cognito_unauth_policy_response, attach_policy_response = create_unauth_component(identity_pool_response['IdentityPoolId']) # noqa
cognito_auth_role_response, cognito_auth_policy_response, attach_policy_response = create_auth_component(identity_pool_response['IdentityPoolId']) # noqa

identity_pool_role_params = get_identity_pool_role_params(
    identity_pool_response['IdentityPoolId'],
    cognito_auth_role_response['Role']['Arn'],
    cognito_unauth_role_response['Role']['Arn'],
)

identity_pool_role_response = cognito_identity.set_identity_pool_roles(
    **identity_pool_role_params)

#####
detach_policy_response = iam.detach_role_policy(
    RoleName=cognito_auth_role_response['Role']['RoleName'],
    PolicyArn=cognito_auth_policy_response['Policy']['Arn'])
delete_policy_response = iam.delete_policy(
    PolicyArn=cognito_auth_policy_response['Policy']['Arn'])
delete_role_response = iam.delete_role(RoleName='CognitoAuthRole')

detach_policy_response = iam.detach_role_policy(
    RoleName=cognito_unauth_role_response['Role']['RoleName'],
    PolicyArn=cognito_unauth_policy_response['Policy']['Arn'])
delete_policy_response = iam.delete_policy(
    PolicyArn=cognito_unauth_policy_response['Policy']['Arn'])
delete_role_response = iam.delete_role(
    RoleName='CognitoUnAuthRole')

cognito.delete_identity_provider(
    UserPoolId=user_pool_response['UserPool']['Id'],
    ProviderName=identity_provider_response['IdentityProvider']['ProviderName'])
delete_user_pool_response = cognito.delete_user_pool_client(
    UserPoolId=user_pool_response['UserPool']['Id'],
    ClientId=user_pool_client_response['UserPoolClient']['ClientId'])
delete_user_pool_response = cognito.delete_user_pool(
    UserPoolId=user_pool_response['UserPool']['Id'])

detach_policy_response = iam.detach_role_policy(
    RoleName=sns_role_response['Role']['RoleName'],
    PolicyArn=sns_policy_response['Policy']['Arn'])
delete_policy_response = iam.delete_policy(
    PolicyArn=sns_policy_response['Policy']['Arn'])
delete_role_response = iam.delete_role(RoleName='SNSRole')

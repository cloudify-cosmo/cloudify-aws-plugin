
import json


sns_role_params = {
    'RoleName': 'SNSRole',
    'AssumeRolePolicyDocument': json.dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"Service": ["cognito-idp.amazonaws.com"]},
                    "Action": ["sts:AssumeRole"]
                }
            ]
        }
    ),
}


sns_policy_params = {
  "PolicyName": "CognitoSNSPolicy",
  "PolicyDocument": json.dumps(
      {
          "Version": "2012-10-17",
          "Statement": [
              {
                  "Effect": "Allow",
                  "Action": "sns:publish",
                  "Resource": "*"
              }
          ]
      }
  )
}


def get_user_pool_params(role_arn):
    return {
      "PoolName": "MyUserPoolApp",
      "AutoVerifiedAttributes": [
        "phone_number"
      ],
      "MfaConfiguration": "ON",
      "SmsConfiguration": {
        "ExternalId": "MyUserPoolApp-external",
        "SnsCallerArn": role_arn
      },
      "Schema": [
        {
          "Name": "name",
          "AttributeDataType": "String",
          "Mutable": True,
          "Required": True
        },
        {
          "Name": "email",
          "AttributeDataType": "String",
          "Mutable": False,
          "Required": True
        },
        {
          "Name": "phone_number",
          "AttributeDataType": "String",
          "Mutable": False,
          "Required": True
        },
        {
          "Name": "slackId",
          "AttributeDataType": "String",
          "Mutable": True
        }
      ]
    }


def get_user_pool_client_params(user_pool_id):
    return {
        'ClientName': 'MyUserPoolClient',
        'GenerateSecret': True,
        'UserPoolId': user_pool_id
    }


def get_identity_pool_provider(user_pool_id, client_id, client_secret):
    return {
        'UserPoolId': user_pool_id,
        "ProviderName": "LoginWithAmazon",
        "ProviderDetails": {
            "client_id": client_id,
            "client_secret": client_secret,
            "authorize_scopes": "profile postal_code"
        },
        "ProviderType": "LoginWithAmazon",
        "AttributeMapping": {
            "email": "email", "phone_number": "phone_number", "name": "name",
        }
    }


def get_identity_pool_params(client_id, provider_name=None):
    if not provider_name:
        raise RuntimeError('No valid provider name provided.')
    provider_name_template = 'cognito-idp.{}.amazonaws.com/{}'
    region = provider_name.split('_')[0]
    real_provider_name = provider_name_template.format(region, provider_name)
    return {
        'IdentityPoolName': 'MyUserPoolIdentityPool',
        'AllowUnauthenticatedIdentities': True,
        'SupportedLoginProviders': {
            'www.amazon.com': client_id
        },
        'CognitoIdentityProviders': [
            {
                'ClientId': client_id,
                'ProviderName': real_provider_name,
            }
        ]
    }


def get_unauth_role_params(identity_pool_id):
    return {
        'RoleName': 'CognitoUnAuthRole',
        'PolicyDocument': json.dumps({
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {
                        "Federated": "cognito-identity.amazonaws.com"
                    },
                    "Action": ["sts:AssumeRoleWithWebIdentity"],
                    "Condition": {
                        "StringEquals": {
                            "cognito-identity.amazonaws.com:aud":
                                identity_pool_id,
                        },
                        "ForAnyValue:StringLike": {
                            "cognito-identity.amazonaws.com:amr":
                                "unauthenticated"
                        }
                    }
                }
            ]
        })
    }


def get_unauth_policy_params():
    return {
        "PolicyName": "CognitoUnauthorizedPolicy",
        "PolicyDocument": json.dumps({
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "mobileanalytics:PutEvents",
                        "cognito-sync:*"
                    ],
                    "Resource": "*"
                }
            ]
        })
    }


def get_cognito_auth_role_params(identity_pool_id):
    return {
        'RoleName': 'CognitoAuthRole',
        'AssumeRolePolicyDocument': json.dumps({
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {
                        "Federated": "cognito-identity.amazonaws.com"
                    },
                    "Action": [
                        "sts:AssumeRoleWithWebIdentity"
                    ],
                    "Condition": {
                        "StringEquals": {
                            "cognito-identity.amazonaws.com:aud":
                                identity_pool_id,
                        },
                        "ForAnyValue:StringLike": {
                            "cognito-identity.amazonaws.com:amr":
                                "authenticated"
                        }
                    }
                }
            ]
        })
    }

cognito_auth_policy = {
  "PolicyName": "CognitoAuthorizedPolicy",
  "PolicyDocument": json.dumps({
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": [
          "mobileanalytics:PutEvents",
          "cognito-sync:*"
        ],
        "Resource": "*"
      }
    ]
  })
}


def get_identity_pool_role_params(
        identity_pool_id,
        authenticated_arn,
        unauthenticated_arn):
    return {
        'IdentityPoolId': identity_pool_id,
        'Roles': {
            'authenticated': authenticated_arn,
            'unauthenticated': unauthenticated_arn,
        }
    }



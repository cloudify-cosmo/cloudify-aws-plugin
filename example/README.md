# AWS Elastic MapReduce Example



## Configure Permissions

Before using any AWS service via API calls, you must first have permissions to do so. Beyond needing
the an API ID and key, you'll need to assign permissions to use EMR.

### Create Default Roles

AWS EMR needs 2 roles to allow access to various services (both directly from EMR and indirectly from the EC2 instance underneath EMR). These 2 roles are called _**EMR_DefaultRole**_ and _**EMR_EC2_DefaultRole**_ by default.

If you already have the 2 roles mentioned above, you can skip the rest of this section.

#### Method 1: AWS Console

To create the default roles, simply go to the [EMR console](https://console.aws.amazon.com/elasticmapreduce) and proceed to create a cluster. It will
prompt you (if this is your first time) to automatically create default roles and other items.

Do this, then terminate the cluster and confirm (in IAM) that the new default roles exist.

#### Method 2: AWS CLI

```bash
# Check if the roles exist or not
aws iam list-roles | grep EMR
# Automatically create default roles
aws emr create-default-roles
```

## Configure Storage

EMR requires an S3 bucket to store cluster / instance logs as well as for storing logs and
output of EMR steps.

Simply go to your [S3 console](https://console.aws.amazon.com/s3) and create a new bucket. Use this
bucket name for your inputs file for the example.

## Run The Example

*Note: Running a full install workflow will take approximately 15 minutes to complete all steps including cluster creation, boostrapping, and running a cluster job*

From the root of the `cloudify-aws-plugin` folder, execute the following if using the CLI.

```bash
# Upload the example blueprint
cfy blueprints upload -b mapreduce -p example/blueprint.yaml
# Create a new deployment with inputs
cfy deployments create -d mapreduce -b mapreduce -i example/inputs.yaml
# Run the install workflow
cfy executions start -w install -d mapreduce -l
```

If using the web UI, take the blueprint.yaml file, ZIP it up, and create a new blueprint in the web UI with it. Add your inputs as you normall would.

# Deployment

This document contains instructions for deploying the notifier service to
AWS.

First-time setup for deployment involves the following steps:

1. TODO

Then for redeployment:

1. Create the Lambda ZIP file
1. Upload the Lambda ZIP file to the Lambda

# Redeployment

To create the lambda zip file, execute the `zip_lambda.sh` file in the
project root:

```shell
./zip_lambda.sh
```

This should produce a `lambda.zip`. Upload that to the Lambda.

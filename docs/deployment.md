# Deployment

This document contains instructions for deploying the notifier service to
AWS.

This document assumes enough familiarity with AWS to be able to
navigate the Management Console, but not much more than that, as that was
my experience level before I set out on this project.

It's worth noting that the instructions in this document are more like a
log of what I did to get things set up (with the caveat that if I did
something wrong and then went back and changed it, I don't mention it
&mdash; only the net outcome). That means that if you happen to know any
better than I do, feel free to deviate.

# Estimated costs

Breakdown for the total estimated cost of hosting notifier for a 730-hour
month using the setup method detailed below:

- EventBridge builtin event emission: $0.00
- Lambda execution time: $0.00
  - Safely within permanent free tier &mdash; 750 invocations out of
    1,000,000 and (assuming 5 minutes execution time per function with 200
    MB memory allocated) 45,000 GB-seconds per month out of 400,000.
  - Ignoring free tier: $0.73
- Attaching Elastic IPs to the Lambda network interfaces: $0.00
  - Recommended method of using a NAT gateway would cost $37.50
- Database:
  - Using Aurora Serverless v1:
    - Usage: assuming a limit of 1 ACU, and the database being active for 5
      minutes for the Lambda plus 15 minutes to subsequently shut down:
      $17.50
    - Storage: Unsure yet - need more data
    - Cost can be reduced by switching to v2 (`us-east-1` only)
      - (Note 2023-02-25: As of April 2022, Aurora Serverless v2 is fully
        available. However, it cannot scale to 0, so the minimum cost per month
        is $43.)
  - Using an EC2:
    - With `t3.nano` in unlimited burst mode as the instance type, assuming running once an hour for 15 minutes, with an 8 GB `gp3` EBS:
      - Usage: Assuming $0.0059 per hour: $1.08
      - Compute: Assuming full single-core CPU usage (i.e. 50% of vCPUs for `t3.nano`) for (730 / 4) hours per month at $0.04 per vCPU-hour, and ignoring accumulated CPU credits: $7.30
      - Storage: With an 8GB `gp3`-backed EBS: $0.19

# First-time setup for deployment to AWS

## Creating an IAM user

I recommend following the AWS best practice of using your root AWS account
only to create an IAM user for managing cloud resources for the notifier,
and then using that account for all administrative tasks
thereafter.<sup>1</sup>

Create an IAM user group (I named mine `WikidotNotifierAdministration`),
and attach to it the following permission policies:

- `AmazonRDSFullAccess`
- `SecretsManagerReadWrite`
- `AmazonEventBridgeFullAccess`
- `AWSLambda_FullAccess`
- `AmazonVPCFullAccess`
- `AWSCloud9Administrator`
- `AmazonEC2FullAccess`

Next, create an IAM user (I named mine `WikidotNotifierAdmin`). Set the
credential type to `password` and attach it to the
`WikidotNotifierAdministration` user group. Make a note of its password (I
stored mine in a password manager).

The console should present details about how to log in as this user. Do
that now.

###### References for this section

1. https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html#create-iam-users

## Creating a VPC

We need to create a Virtual Private Cloud to contain everything related to
the notifier, and to sandbox it away from anything else in your AWS
account.

Create a new VPC (the option is in the EC2 section of the management
console):

- We don't need a private subnet,<sup>1</sup> so choose to create a *VPC
  with a Single Public Subnet*.
- Leave the IPv4 CIDR block as its default value of `10.0.0.0/16`. Don't
  add an IPv6 CIDR block.
- Give the VPC a name &mdash; I named mine `WikidotNotifierVPC`. I'll refer
  to this as "the VPC" from now on.
- Leave the IPv4 CIDR block for the public subnet as its default value of
  `10.0.0.0/24`. Its default name is `Public subnet` and I'll refer to it
  as such from now on.

###### References for this section

1. https://stackoverflow.com/questions/22188444/why-do-we-need-private-subnet-in-vpc

### Adding another subnet

At least two subnets are required, but the VPC creation wizard only creates
one. We need to create another one manually.

In the Subnets section of the VPC section of the console, find the subnet
associated with the new VPC. Note its Availability Zone.

Create a new subnet:

- Create it into the new VPC.
- Name it whatever &mdash; I named mine `Public subnet 2`.
  - Note that this new subnet doesn't currently have an Internet Gateway
    attached, so regardless of name, it is actually a private subnet. We
    will be adding an Internet Gateway later.
- Set the Availability Zone to anything *other* than the Availability Zone
  of the other subnet (`Public subnet`).
- Set the IPv4 CIDR block of this new subnet to a range that is contained
  within the VPC's IP range but does not intersect with the other subnet's
  IP range.
  - For example: if the IP range of the VPC is `10.0.0.0/16` and the range
    of `Public subnet` is `10.0.0.0/24`, set the range for `Public subnet
    2` to `10.0.1.0/24`.

`Public subnet 2` is currently a private subnet. To make it public, add an
internet gateway.<sub>1</sub>

###### References for this section

1. https://docs.aws.amazon.com/vpc/latest/userguide/VPC_Internet_Gateway.html

## Creating security groups

We need two security groups, each with a clear purpose, that will be
applied to various entities in the VPC.

To create a security group, find *Security groups* in the EC2 console, and
create a new security group.

Create a new security group:

- Call it `WikidotNotifierDatabaseSecurityGroup`. This is the group that
  will permit entities to access the database.<sup>1</sup>
- Create it into the new VPC.
- Edit the inbound rules:
  - Add a rule of type `MYSQL/Aurora`, and set the source to the ID of
    *this* security group (the `sg-xxxxx` ID of
    `WikidotNotifierDatabaseSecurityGroup`).
- Edit the outbound rules:
  - Leave the default outbound rule in place.
  - Add a rule of type `MYSQL/Aurora`, and set the destination, again, to
    the ID of this security group.

You may be required to create the group first and only add these
self-referential rules afterwards.

Create a second new security group:

- Call it `WikidotNotifierLambdaAccessToInternet`. This is the group that
  permits the Lambda to access the internet (in addition to other factors
  detailed later in this document).
- Create it into the new VPC.
- Edit the inbound rules:
  - Add a rule of type `HTTP`, and set the source to `0.0.0.0/0`.
  - Add a rule of type `HTTPS`, and set the source to `0.0.0.0/0`.
- Edit the outbound rules:
  - Remove the default outbound rule.
  - Add a rule of type `HTTP`, and set the destination to `0.0.0.0/0`.
  - Add a rule of type `HTTPS`, and set the destination to `0.0.0.0/0`.

###### References for this section

1. https://aws.amazon.com/premiumsupport/knowledge-center/connect-lambda-to-an-rds-instance/

## Creating the database

The database for notifier was originally (2021-07-22) designed to run on Amazon Aurora Serverless v1, and the original setup instructions remain below. As of 2023-03-19, the database no longer runs on Aurora Serverless v1, it now runs on an EC2. This is considerably cheaper.

### On Aurora Serverless v1

As discussed in [docs/database.md](/docs/database.md), notifier ~~is~~ was designed
to use Amazon Aurora Serverless v1. notifier only runs once an hour, so it
doesn't make sense to pay for provisioning an always-available database for
the 55 minutes per hour that it's not in use. The notifier codebase is
compatible with MySQL 5.6.10a.

(Note 2023-02-25: The database has been upgraded to MySQL 5.7 as part of a
mandatory Aurora engine upgrade.)

In the RDS section of the console, create a new database with the following
settings:

- Use the *Standard create* creation method. Choose the Amazon Aurora
  database engine, with MySQL 5.7 compatibility. Set the capacity type
  to serverless.
- Give a name to the database cluster &mdash; I named mine
  `wikidotnotifierbdcluster` (it normalises to lowercase).
- Set the minimum ACU to 1, and the maximum ACU to something reasonable (I
  set mine to 1).
- Under *Additional scaling configuration*, check *Scale the capacity to 0
  ACUs when cluster is idle* &mdash; **this is the most important step**
  (unless you don't like having money).
- Create the database into the VPC.
- Add it to the `WikidotNotifierDatabaseSecurityGroup` security group only.
- Do not specify an initial database name &mdash; leave the field blank.
  AWS may tell you that this will cause it not to create a database in the
  cluster. That's fine &mdash; we will do that ourselves later.
- For the DB subnet group, add both of the subnets.
  - You may be required to create a DB subnet group yourself via the RDS
    console before creating the database.

Make a note of the database admin credentials. (I stored mine in Secrets
Manager).

You may notice that the 'database cluster' you've created doesn't actually
contain any 'database instances'. This is apparently normal for serverless
databases.

### On an EC2

It is cheaper to run the database as an EC2 instance rather than using an Aurora RDS database, even if it is 'serverless'.

(Note 2023-06-11: The database has been upgraded to MySQL 8.0.33 and as of the time of writing is set up on a `c6g.medium` instance, as mentioned as a possibility below. Original setup instructions for MySQL 5.7 and `t3.nano` are retained below for posterity.)

In the EC2 section of the console:

- Create a new EC2 instance. I named mine `WDNotifier MySQL database`.
- For the image, a standard Amazon Linux 2 will be fine.
- The notifier database with MySQL 5.7 runs just about fine on a `t3.nano` ($0.0059 / hour),<sup>3</sup> provided that you set the CPU burst limit to unlimited ($0.04 / hour).<sup>4</sup>
  - If you are using MySQL 8, it will work on an ARM chipset, and you could get away with using the even cheaper t4g.nano instance type ($0.0047 / hour).<sup>3</sup>
  - If not comfortable with running a `t` instance in unlimited burst mode, consider that the alternative is picking an instance type with a decent compute capacity, and these do not come in small sizes. The best I found was a `c6a.large` ($0.0909 / hour),<sup>3</sup> the smallest `c6a` and cheapest `c` with a corresponding 'large' price. The `t3.nano` in unlimited mode comes to $0.0459 / hour, which is still the best price.
    - `c6g.medium`, requiring ARM compatibility and therefore MySQL 8, would actually be cheaper at $0.0404 / hour.<sup>3</sup> However, using a `t` instance does mean you can temporarily spin it up for things like testing and migrations at practically no cost.
- Make sure the instance is EBS-backed. No special provisions for data transfer speed are necessary. A `gp3`-type EBS is fine.
- Create the instance in the notifier's VPC.

Note the instance ID; I will refer to mine as `i-<DB INSTANCE ID>`.

The EC2 instance will need to have MySQL installed on it. As explained in the section below ('Accessing the database'), AWS objects in the VPC can only be accessed by other objects in the VPC, so a Cloud9-based terminal is necessary. So, having connected to it by that or some other means:

- Install MySQL on the instance.
  - This can be done by installing media directly from the MySQL website.
  - The instance does not have access to the internet, so it cannot download these things itself. However, you can download them on the Cloud9 instance and then `scp` them over to the database instance. Alternatively, you can temporarily enable internet access by associating an Elastic IP to the instance's network interface. Just make sure to dissociate and release that IP when you're done to avoid incurring charges.
  - The MySQL version can be whatever you like, just make sure it's compatible with the data. I used 5.7 given that I was migrating to EC2 from RDS and didn't want to worry about upgrading the version as well.
- Configure MySQL to start on boot: `systemctl start mysqld`.

For the rest of these instructions, instead of using the Aurora Serverless hostname, use the EC2 instance's internal IP.

## Accessing the database

In order to create the initial database and to set up the notifier's user
identity in MySQL, we need to connect to it via the MySQL client.

However, it's not possible to give an Aurora Serverless DB cluster a public
IP address,<sup>1</sup> and therefore it's not possible to connect to it
except from inside the VPC &mdash; i.e. you cannot connect to it from your
own terminal over the internet. However, you can connect to it from a
Cloud9 instance deployed to the VPC.<sup>2</sup>

###### References for this section

1. https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-serverless.html
2. https://aws.amazon.com/getting-started/hands-on/configure-connect-serverless-mysql-database-aurora/
3. https://aws.amazon.com/ec2/pricing/on-demand/, accessed 2023-03-19
4. https://aws.amazon.com/ec2/pricing/on-demand/#T2.2FT3.2FT4g_Unlimited_Mode_Pricing, accessed 2023-03-19

### Setting up Cloud9

In the Cloud9 section of the management console, create a new Cloud9
environment:

- Give it a name &mdash; I named mine `WikidotNotifierAccess`.
- Set the EC2 instance to the cheapest one possible &mdash; `t3a.nano` at
  the time of writing.
- Under *Network settings (advanced)*, create the environment into the VPC.
  Create it into either subnet.

To give Cloud9 access to the database, we need to edit the
`WikidotNotifierDatabaseSecurityGroup` security group. Add to it a new
inbound rule: set the type to `MYSQL/Aurora`, and the source to the ID of
the Cloud9 security group (which should appear when you type 'cloud9' into
the text box).

### MySQL client via Cloud9

Activate the Cloud9 environment.

While it's booting up, head over to the RDS console. Make a note of the
hostname of your DB cluster (`wikidotnotifierbdcluster`). It should look
something like `<name>.cluster-<hash>.<region>.rds.amazonaws.com`. This
will be used as '`mysql_host`' later.

Open a Bash terminal and enter the following, replacing `<HOST>` with the
hostname of the DB cluster and `<user>` with the cluster's admin username
(and enter the admin password when prompted):

```shell
mysql -h<HOST> -u<user> -p
```

Once connected, confirm the MySQL version.

Use the MySQL client to set up the database and user identity for the
notifier service as instructed in [docs/database.md](/docs/database.md):

- The notifier Lambda will connect to the database from an IP address
  matching `10.0.0.0/255.0.0.0` (assuming the IP range of the VPC is
  `10.0.0.0/16`), so enter that as the user's hostname.
- Set the user password to whatever you like, but keep a note of it. This
  will be used as '`mysql_password`' later.
- Create both databases as instructed and grant that user full access to
  all tables in both databases using `<database name>.*` syntax.

## Adding secrets to Secrets Manager

If you are using Secrets Manager to store and retrieve secrets for the
notifier, now is the time to store them. Create secrets according to your
authentication configuration file as specified in
[docs/auth.md](/docs/auth.md) &mdash; I recommend creating a single secret
named `WikidotNotifier/auth` with the following 5 key-value pairs:

- `wikidot_password`: The Wikidot password of the Notifier account
- `gmail_password`: The Gmail password of the configured Gmail account
- `mysql_host`: The hostname of the Aurora DB cluster
- `mysql_username`: The username of the user identity you created in the
  database
- `mysql_password`: The password of the user identity you created in the
  database

Note that the Lambda by default is not able to access Secrets Manager. I
will cover this later.

## Setting up the Lambda

Create a new Lambda function:

- Use the *Author from scratch* template.
- Give it a good name &mdash; I named mine `WikidotNotifier`.
- Set the runtime to Python 3.8.
- In *Change default execution role*, ensure that *Create a new role with
  basic Lambda permissions* is selected.
- Don't add the Lambda to the VPC yet &mdash; leave that field empty.

After creating the Lambda there are a few other configuration settings to
change:

- The default timeout for a Lambda is 3 seconds. In *General
  configuration*, increase that &mdash; I recommend about 20 seconds for
  initial testing, and then at least 5 minutes once you know everything
  works and you're ready for production.
- In *Concurrency*, select *Edit*. Change the concurrency type to *Reserved
  concurrency* and set the limit to 1. This will make sure only one
  instance of the Lambda can run at a time &mdash; I will cover why this
  setting is necessary later.
- In *Asynchronous invocation*, change the number of retry attempts to 0.
  - It would be pointless to retry the Lambda, because by then the time
    would have changed, and no channels would be activated.
- In the *Test* tab, create a new test event with sample config parameters.
  I used the same value for both the test event and the actual event,
  detailed below.

To upload the notifier codebase to the Lambda, follow the steps in the
Redeployment section below. Note that it feels cooler if you perform this
step right at the very end.

When testing, note that so long as you execute the notifier any time but
the first minute of an hour, no notification channels will be activated.
Feel free to test at any point during those times.

## Start/stop the database using Step Functions

Whether you need to tell the database to start and stop depends on which service is running it: Aurora Serverless or EC2.

### Database running on Aurora Serverless v1

Aurora Serverless will automatically start and stop based on usage. Just beware the long shutdown wait time.

### Database running on EC2

The EC2 instance is stupid and doesn't magically know when to start and stop. We need to:

1. Instruct the instance to boot.
2. Wait for it to boot.
3. Run the notifier.
4. Shut down the instance.

This can be done using Step Functions, and the setup looks like this:

<p align="center"><img width="500" src="https://raw.githubusercontent.com/croque-scp/notifier/master/docs/stepfunctions_graph.svg"></p>

The Step Function must be created in the default VPC &mdash; the one that has access to the internet, __not__ the WikidotNotifier VPC. This is because it does not interface directly with anything in the VPC, but instead uses API calls to ask the EC2 to start/stop and to trigger the Lambda, which is a global AWS service not associated with a VPC.

Note the loop. This pings the database to see if it is running, starts the notifier if so, and waits 5 seconds if not. A counter is incremented that breaks the loop with an error after a few tries. However in practice I've found that the inital 20 second wait is enough for the database to be ready pretty much every time.

The EventBridge trigger needs to be modified to include the database's instance ID, as described below.

The specific payload given to the notifier Lambda from Step Functions needs to be modified to include the Step Function's start time: `"force_current_time.$": "$$.Execution.StartTime"`. This will ensure that even if the Step Function and the database cumulatively take more than a minute to start, the Lambda will still think it is the correct minute to activate a notification channel.

## Adding the Lambda trigger

The Lambda is trigged by an EventBridge cron schedule.

Add a new trigger to the Lambda:

- Select EventBridge.
- Create a new rule. Give it a name e.g. `WikidotNotifierExecutor`.
- For the rule type, choose *Schedule expression*. The expression to use is
  `cron(0 * * * ? *)`, meaning 'execute once at the start of each hour'.

Create the trigger, then find it in the EventBridge console, and edit it:

- Under *Select targets*, open *Configure input*.
- Select *Constant (JSON text)*.
- Enter the execution config parameters. I used the following parameters:

```json
{
  "db_instance_id": "i-<id>",
  "config_path": "config/config.toml",
  "auth_path": "config/auth.lambda.toml",
  "proxy": "https://<id>.execute-api.<region>.amazonaws.com/dev/proxy?target_url="
}
```

- Under *Retry policy*, set the number of retry attempts to 0.

While you're still setting everything up, and especially if you already
uploaded the code, you may wish to disable the event to stop the schedule.
You can do so via the EventBridge console (but not the Lambda console).
Remember to re-enable it once everything else is ready.

## Enabling internet access for the Lambda

A Lambda inside a VPC can only access resources inside that VPC (e.g. EC2
instances, RDS databases). A Lambda outside of a VPC can only access public
resources (e.g. the internet and global AWS services like S3 and Secrets
Manager).<sup>1</sup> This is because a Lambda instance is not assigned a
public IP.<sup>2, 3</sup>

Our Lambda needs to access a VPC resource (in this case the Aurora RDS
database), so it must be inside a VPC. However, it also needs to access
Secrets Manager (a global AWS service) and the internet (to communicate
with Wikidot and Gmail), which it cannot by default do from within a VPC.

You can tell when this is happening to your Lambda when its attempted
outbound HTTP connections simply time out.

There are three ways of enabling a Lambda in a VPC to access the internet,
&mdash; I leave the choice to you:

- You can put the Lambda into multiple private subnets, and create a NAT
  Gateway between the public and private subnets which routes traffic from
  the private subnets (i.e. from the Lambda) to the public subnet's
  internet gateway, thus enabling it to access the internet. AWS recommends
  this method.
  - A NAT Gateway is charged at $0.05 per hour plus transfer fees, with a
    granularity of one hour.<sup>4</sup> The notifier service runs every
    hour, so you will be paying for effective constant usage. Not including
    transfer fees this totals roughly $37.50 per month.
- You can create and host your own a NAT instance using an EC2.<sup>5</sup>
  This is much cheaper, but you are responsible for setting it up and
  maintaining it. AWS considers this method to be deprecated.
  - If you choose `t3a.nano` as the instance type, which at the time of
    writing is charged at $0.0047 per hour,<sup>6</sup> this will cost
    roughly $3.50 per month.
- You can assign Elastic IPs to the Lambda's network interfaces, which
  enables them to access the internet.<sup>7</sup> I don't understand how
  or why this works, but it does. AWS does not recommend this solution
  &mdash; it seems to be widely considered a bad idea.
  - An Elastic IP that is associated with an Elastic Network Interface does
    not incur charges,<sup>8</sup> so this solution is free.
  - The main downside of this solution is that the Lambda will create
    additional ENIs whenever it needs to, which of course not have Elastic
    IPs assigned to them, and thus your Lambda will unpredictably break. We
    have already alleviated this concern by setting the Lambda's
    concurrency limit to 1 &mdash; it *should* never need additional
    interfaces.
    - At the time of writing this bullet point (2023-06-11, almost 2 years after writing the above on 2021-09-18), the above solution has needed maintenance exactly 0 times.
  - To implement this solution:
    - Find *Network interfaces* in the EC2 console. Locate any ENIs that
      are associated with the `WikidotNotifierAccessToInternet` security
      group &mdash; there should be two, one for each subnet that the Lambda
      is associated with. Note their network interface IDs.
    - Find *Elastic IPs* in the EC2 console. Allocate two new Elastic IPs,
      or reuse any old unused ones (remember that you are charged for
      unused Elastic IPs). Click into each new EIP and associate one to
      each of the ENIs you noted.

I chose the third method. If you chose another, I wish you luck with
setting up and configuring the NAT gateway.

###### References for this section

1. https://docs.aws.amazon.com/lambda/latest/dg/configuration-vpc.html#vpc-internet
2. https://aws.amazon.com/premiumsupport/knowledge-center/internet-access-lambda-function/
3. https://stackoverflow.com/q/52992085/4958427
4. https://aws.amazon.com/vpc/pricing/
5. https://docs.aws.amazon.com/vpc/latest/userguide/VPC_NAT_Instance.html
6. https://aws.amazon.com/ec2/pricing/on-demand/
7. https://stackoverflow.com/a/55771444/4958427
8. https://aws.amazon.com/premiumsupport/knowledge-center/elastic-ip-charges/

## Extra permissions for the Lambda

The Lambda additionally needs specific permission to access a Secrets
Manager secret<sup>1</sup> &mdash; if HTTP access was all that was
required, anyone could get it. It also needs a specific permission in order
to be able to be added to a VPC.<sup>2</sup>

I don't know what permission policy is needed to be added to an IAM user
group to perform this next step, so the IAM user group detailed at the
start of this document is unable to perform this next action. I recommend
simply using your root account instead.

In the IAM section of the management console, create a new
Policy:

- Set the service to *Secrets Manager*.
- Give it the action *GetSecretValue*, which is nested under *Read*.
- Configure a *Specific* resource. Select *Add ARN*. Enter the ARN of the
  secret (in this case the secret named `WikidotNotifier/auth`) from the
  Secrets Manager console.
- Give the policy a searchable name &mdash; I named mine
  `WikidotNotifierLambdaAccessToAuthSecret`.

In the *Roles* section of the IAM console, find the role associated with
the Lambda. The Lambda will have created this role itself, so it should
have a recognisable name. Attach to it the following two policies:

- The policy that you just created
  (`WikidotNotifierLambdaAccessToAuthSecret`)
- `AWSLambdaVPCAccessExecutionRole`

###### References for this section

1. https://aws.amazon.com/blogs/networking-and-content-delivery/securing-and-accessing-secrets-from-lambdaedge-using-aws-secrets-manager/
2. https://stackoverflow.com/a/68433719/4958427

## Add the Lambda to the VPC

The Lambda now has permission to be deployed to a VPC, allowing it to
access resources inside it (such as your database).<sup>1</sup>

In the Lambda's configuration, select section *VPC*:

- Add the Lambda to the VPC.
- Add it to both subnets.
- Add it to both `WikidotNotifierDatabaseSecurityGroup` and
  `WikidotNotifierLambdaAccessToInternet` security groups.

###### References for this section

1. https://docs.aws.amazon.com/lambda/latest/dg/vpc.html

# Redeployment

## As a .zip

To create the lambda zip file, execute the `zip_lambda.sh` file in the
project root:

```shell
./zip_lambda.sh
```

This should produce a `lambda.zip`. Upload that to the Lambda.

## As a Docker container

Create a private ECR repository. It must be private for it to be selectable as a Lambda image source.

Create the Docker image using the `execute_lambda` target, making sure to tag it with the correct image tag as provided by ECR:

```shell
docker build --target execute_lambda --tag notifier:execute_lambda --tag public.ecr.aws/<namespace>/rossjrw/notifier:latest .
```

Upload the image to the ECR repository you created.

- ECR has instructions for doing this - I had to use the AWS CLI using a `notifier` profile that was authenticated using an access ID I created on the WikidotNotifierAdmin IAM user. For this I also needed to create a new IAM policy providing access to the specific ECR repositry, which I attached to the WikidotNotifierAdministration IAM group.

If this is replacing a Lambda function created with the .zip method, this new image-based function must be created with a different name. If you want to use the same name (like I did) then you must delete the existing Lambda function (like I did) and recreate it from scratch, this time using the container image as a template, and then follow the instructions from way up above to set it up again.

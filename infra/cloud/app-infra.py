#!/usr/bin/env python
"""Build cloud infrastructure for the environment based on .ini file.

Create virtualenv::

  virtualenv --python=python3 .venv3
  source .venv3/bin/activate
  pip install -r requirements.txt

Create a new stack like::

  ./app-infra.py ../../prod.ini > tttdiazoprod.json
  aws cloudformation create-stack --stack-name TTTDiazoProd  \
      --capabilities CAPABILITY_IAM --template-body file://tttdiazoprod.json

Update the existing stack like::

  ./app-infra.py ../../prod.ini > tttdiazoprod.json
  aws cloudformation update-stack --stack-name TTTDiazoProd  \
      --capabilities CAPABILITY_IAM --template-body file://tttdiazoprod.json

 To Deploy TTTDiazo we need:

- ELB: to own the ASG and HTTPS certificate
- ASG: min=2, max=2
- EC2: under ASG
- SG: ssh, ELB http, https, EC2 app from ELB only
- CodeDeploy; Deployment Group and IAM Policy

Production and Stage environments both deploy from this script. We need minor
differences between environments i.e. no elb or dns record for stage. The 'env'
setting in the .ini file determines which environment we're deploying.
"""

import argparse
import configparser
import logging

from awacs.aws import (
    # Action,
    # AWSPrincipal,
    Allow,
    # ArnEquals,
    # Condition,
    # Everybody,
    # IpAddress,
    Policy,
    Principal,
    # SourceArn,
    Statement,
)
import awacs.acm
import awacs.codedeploy
import awacs.iam
import awacs.s3
import awacs.sts

from troposphere import (
    Base64,
    # FindInMap,
    GetAtt,
    Join,
    # Output,
    # Parameter,
    Ref,
    Tags,
    Template,
    autoscaling,
    cloudwatch as cw,
    codedeploy,
    ec2,
    elasticloadbalancing as elb,
    iam,
    route53,
    s3,
    sns,
    # sqs,
)


class Infra:

    def __init__(self, config):
        self.log = logging.getLogger(__name__)
        self.aws = config['config:aws']

        self.t = Template()
        self.t.add_version('2010-09-09')
        # Set stack decription for each environment
        if self.aws['env'] == 'prod':
            self.t.add_description('TTT Diazo Prod: ELB, ASG, EC2, Route53.Hosts, CodeDeploy.DG')
        elif self.aws['env'] == 'stage':
            self.t.add_description('TTT Diazo Stage: ASG, EC2, Route53.Hosts, CodeDeploy.DG')
        else:
            self.t.add_description('TTT Diazo ' + self.aws['env'] + ': ASG, EC2, Route53.Hosts, CodeDeploy.DG')

        # TODO: add OUTPUTs here too so we can accumulate them in the resources

    def __str__(self):
        # is this a string of json?
        return self.t.to_json()

    def _name_tags(self, component):
        """Return logical name and tags based on short name of component.

        If 'component' is 'vpc', look in config for 'app', 'env', and
        'vpc.name'. Create a LogicalName from app and component, and tags based
        on that and the env.  If app='TTTdiazo', env='prod', component='vpc'
        and 'vpc.name'='VPC' we would return tuple::

          ('TTTdiazoVPC', {'TTTdiazo-VPC-prod', app='TTTdiazo', env='prod'})

        Logical names may not have dashes or underscores, so we use
        punctation-free name for those, but tags are more readable with dashes.

        :param str component: name of the component to use as key in .ini file
        :returns: `tuple` (name, tags)
        """
        app = self.aws['app']
        env = self.aws['env']
        sname = self.aws[component + '.name']
        name = app + sname
        tags = {'Name': '{}-{}-{}'.format(app, sname, env),
                'env': env, 'app': app}
        return (name, tags)

    ###########################################################################
    # SGs

    def add_sg_app(self):
        """Allow access only from ELB. Apply to instances behind the ELB."""
        name, tags = self._name_tags('sg_app')
        sg_rules = []
        for port in self.aws['sg_app.ports'].split(','):
            sg_rules.append(
                ec2.SecurityGroupRule(
                    IpProtocol='tcp',
                    FromPort=port,
                    ToPort=port,
                    SourceSecurityGroupId=self.aws['sg_elb'],
                ),
            )
        self.sg_app = self.t.add_resource(
            ec2.SecurityGroup(
                name,
                VpcId=self.aws['vpc_id'],
                GroupDescription=self.aws['sg_app.desc'],
                SecurityGroupIngress=sg_rules,
                Tags=Tags(**tags)
            ))

    ###########################################################################
    # Role and Policy: allow EC2 to access S3 to get code
    # You must specify at invocation: --capabilities CAPABILITY_IAM

    # Test with python and boto3 in a virtualenv on the instance:
    #   python -c "import boto3; print(boto3.resource('s3').Object('CODEBUCKET.aws.v-studios.com', 'index.html').get())"

    # I want to allow just our role or EC2 profile to be able to get objects
    # via HTTP, e.g., with curl on the static website that's set up. However, I
    # can't see how to do this. This Bucket Policy is accepted, but curl on the
    # instance is denied for index.html. ("Principal":"*" works).

    # {
    #   "Version": "2012-10-17",
    #   "Statement": [
    #     {
    #       "Sid": "TRY role/policy access ",
    #       "Effect": "Allow",
    #       "Principal": {
    #         "AWS": [
    #                 "arn:aws:iam::############:role/tttdiazoprod-TTTdiazoRoleEc2S3-1LR1T7POA0ZL7"
    #         ]
    #       },
    #       "Action": "s3:GetObject",
    #       "Resource": "arn:aws:s3:::code.aws.v-studios.com/*"
    #     }
    #   ]
    # }
    #
    # Trying Instance Profile name is rejected: Invalid principal in policy:
    # "Principal": {
    #    "AWS": ["arn:aws:iam::############:instance-profile/tttdiazoprod-TTTdiazoProfileDiazo-D0A10MLPODFX"]
    # }, ...

    def add_role(self):
        name, tags = self._name_tags('role')
        self.role = self.t.add_resource(
            iam.Role(
                name,
                AssumeRolePolicyDocument=Policy(
                    Statement=[
                        Statement(
                            Action=[awacs.sts.AssumeRole],
                            Effect=Allow,
                            Principal=Principal('Service', 'ec2.amazonaws.com'),
                            Sid=name,  # redundant?
                        ),
                    ],
                ),
                ManagedPolicyArns=['arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess'],
                Path='/',
                Policies=[iam.Policy(
                    name + 'Policy',
                    PolicyDocument=Policy(
                        Statement=[
                            Statement(
                                Action=[
                                    awacs.s3.GetObject,
                                    awacs.s3.ListBucket,
                                ],
                                Effect=Allow,
                                Resource=[awacs.s3.ARN(resource=self.aws['s3.bucket']),
                                          awacs.s3.ARN(resource=self.aws['s3.bucket'] + '/*')],
                            ),
                        ],
                    ),
                    PolicyName=name + 'Policy',
                )],
                # Doesn't support: Tags=Tags(**tags)
            ))

    def add_profile(self):
        name, tags = self._name_tags('profile')
        self.profile = self.t.add_resource(
            iam.InstanceProfile(
                name,
                Path='/',
                Roles=[Ref(self.role.name)],
                # Doesn't support: Tags=Tags(**tags),
            ))

    ###########################################################################
    # ASG with LaunchConfig and ELB: no scale policies nor alarms yet

    def add_launchconfig_prod(self):
        """Create ASG Launchconfig without elb_sg attached, for prod."""
        name, tags = self._name_tags('launchconfig')
        self.launchconfig = self.t.add_resource(
            autoscaling.LaunchConfiguration(
                name,
                AssociatePublicIpAddress=True,
                ImageId=self.aws['launchconfig.image_id'],
                IamInstanceProfile=Ref(self.profile.name),
                InstanceMonitoring=False,  # don't pay for detailed monitor
                InstanceType=self.aws['launchconfig.instance_type'],
                KeyName=self.aws['launchconfig.key_name'],
                SecurityGroups=[self.aws['sg_ssh'],
                                Ref(self.sg_app.name)],
                # Doesn't support: Tags=Tags(**tags),
                UserData=Base64(Join('', [
                    '#!/bin/bash -xe\n',
                    'apt-get update\n',
                    'apt-get install -y python-pip ruby2.0\n',
                    'pip install awscli\n',
                    'cd /home/ubuntu\n',
                    'aws s3 cp s3://aws-codedeploy-us-east-1/latest/install' +
                    ' . --region us-east-1\n',
                    'chmod +x ./install\n',
                    './install auto\n',
                ]))
            ))

    def add_launchconfig(self):
        """Create ASG Launchconfig with elb_sg attached, for non-prod."""
        name, tags = self._name_tags('launchconfig')
        self.launchconfig = self.t.add_resource(
            autoscaling.LaunchConfiguration(
                name,
                AssociatePublicIpAddress=True,
                ImageId=self.aws['launchconfig.image_id'],
                IamInstanceProfile=Ref(self.profile.name),
                InstanceMonitoring=False,  # don't pay for detailed monitor
                InstanceType=self.aws['launchconfig.instance_type'],
                KeyName=self.aws['launchconfig.key_name'],
                SecurityGroups=[self.aws['sg_ssh'],
                                self.aws['sg_elb'],
                                Ref(self.sg_app.name)],
                # Doesn't support: Tags=Tags(**tags),
                UserData=Base64(Join('', [
                    '#!/bin/bash -xe\n',
                    'apt-get update\n',
                    'apt-get install -y python-pip ruby2.0\n',
                    'pip install awscli\n',
                    'cd /home/ubuntu\n',
                    'aws s3 cp s3://aws-codedeploy-us-east-1/latest/install' +
                    ' . --region us-east-1\n',
                    'chmod +x ./install\n',
                    './install auto\n',
                ]))
            ))

    def add_sns(self):
        # From AWS: After you create an Amazon SNS topic, you cannot update its
        #   properties by using AWS CloudFormation. You can modify an Amazon
        #   SNS topic by using the AWS Management Console.
        # You can remove it from the Tropo and update the CloudFormation then
        # add it back with the new settings.
        name, tags = self._name_tags('sns')
        subs = [sns.Subscription(Endpoint=email.strip(), Protocol='email')
                for email in self.aws['sns.emails'].split(',')]
        self.sns = self.t.add_resource(
            sns.Topic(
                name,
                Subscription=subs,
            ))

    def add_elb(self):
        name, tags = self._name_tags('elb')
        region = self.aws['region']
        account = self.aws['account']

        self.elb = self.t.add_resource(
            elb.LoadBalancer(
                name,
                # AccessLoggingPolicy= TODO
                ConnectionDrainingPolicy=elb.ConnectionDrainingPolicy(
                    Enabled=True,
                    Timeout=300,
                ),
                CrossZone=True,
                HealthCheck=elb.HealthCheck(
                    Target='HTTP:80/',
                    HealthyThreshold='3',
                    UnhealthyThreshold='5',
                    Interval='30',
                    Timeout='5',
                ),
                Listeners=[
                    elb.Listener(
                        LoadBalancerPort='80',
                        Protocol='HTTP',
                        InstancePort='80',
                        InstanceProtocol='HTTP',
                    ),
                    elb.Listener(
                        LoadBalancerPort='443',
                        Protocol='HTTPS',
                        InstancePort='443',
                        InstanceProtocol='HTTP',
                        SSLCertificateId=awacs.acm.ARN(region=region, account=account, resource=self.aws['elb.ssl_id']).JSONrepr(),
                    ),
                    # SSL terminated on ELB with cert there,
                    # so direct ELB HTTPS with SSL to instance 443 without SSL.
                    # https://docs.aws.amazon.com/ElasticLoadBalancing/latest/
                    #         DeveloperGuide/ssl-server-cert.html#upload-cert
                    # CertId like:
                    # arn:aws:iam::123456789123:server-certificate/start_certname_com
                    # elb.Listener(
                    #     InstancePort='443',
                    #     InstanceProtocol='HTTP',
                    #     LoadBalancerPort='443',
                    #     Protocol='HTTPS',
                    #     SSLCertificateId=elb_avail_api_ssl_id,
                    # ),
                ],
                LoadBalancerName=name,  # WHAT? needed by AutoScaleGroup
                SecurityGroups=[self.aws['sg_elb']],
                Subnets=[self.aws['pub_subnet_id']],
                Tags=Tags(**tags)
            ))

    def add_asg_w_elb(self):
        """Create ASG with ELB attached, for prod."""
        name, tags = self._name_tags('asg')
        self.asg = self.t.add_resource(
            autoscaling.AutoScalingGroup(
                name,
                Cooldown=self.aws['asg.cooldown'],
                DesiredCapacity=self.aws['asg.scale_min'],
                HealthCheckGracePeriod=self.aws['asg.health_grace'],
                HealthCheckType='EC2',  # or ELB
                LaunchConfigurationName=Ref(self.launchconfig.name),
                LoadBalancerNames=[Ref(self.elb.name)],
                MaxSize=self.aws['asg.scale_max'],
                MinSize=self.aws['asg.scale_min'],
                NotificationConfigurations=[autoscaling.NotificationConfigurations(
                    TopicARN=Ref(self.sns.name),
                    NotificationTypes=[autoscaling.EC2_INSTANCE_LAUNCH,
                                       autoscaling.EC2_INSTANCE_LAUNCH_ERROR,
                                       autoscaling.EC2_INSTANCE_TERMINATE,
                                       autoscaling.EC2_INSTANCE_TERMINATE_ERROR])],
                Tags=autoscaling.Tags(**tags),
                VPCZoneIdentifier=[self.aws['app_subnet_id'],
                                   ],
            ))

    def add_asg(self):
        """Create ASG without ELB attached, for non-prod."""
        name, tags = self._name_tags('asg')
        self.asg = self.t.add_resource(
            autoscaling.AutoScalingGroup(
                name,
                Cooldown=self.aws['asg.cooldown'],
                DesiredCapacity=self.aws['asg.scale_min'],
                HealthCheckGracePeriod=self.aws['asg.health_grace'],
                HealthCheckType='EC2',  # or ELB
                LaunchConfigurationName=Ref(self.launchconfig.name),
                MaxSize=self.aws['asg.scale_max'],
                MinSize=self.aws['asg.scale_min'],
                NotificationConfigurations=[autoscaling.NotificationConfigurations(
                    TopicARN=Ref(self.sns.name),
                    NotificationTypes=[autoscaling.EC2_INSTANCE_LAUNCH,
                                       autoscaling.EC2_INSTANCE_LAUNCH_ERROR,
                                       autoscaling.EC2_INSTANCE_TERMINATE,
                                       autoscaling.EC2_INSTANCE_TERMINATE_ERROR])],
                Tags=autoscaling.Tags(**tags),
                VPCZoneIdentifier=[self.aws['app_subnet_id'],
                                   ],
            ))

    def add_scale_up_policy(self):
        name, tags = self._name_tags('scale_up_policy')
        self.scale_up_policy = self. t.add_resource(
            autoscaling.ScalingPolicy(
                name,
                AdjustmentType='ChangeInCapacity',
                AutoScalingGroupName=Ref(self.asg.name),
                Cooldown=self.aws['scale_up_policy.cooldown'],
                DependsOn=self.asg.name,  # above
                ScalingAdjustment='1',
                # Doesn't support: Tags=Tags(**tags),
            ))

    # TODO: implement these

    def add_scale_down_policy(self):
        name, tags = self._name_tags('scale_down_policy')
        self.scale_down_policy = self.t.add_resource(
            autoscaling.ScalingPolicy(
                name,
                AdjustmentType='ChangeInCapacity',
                AutoScalingGroupName=Ref(self.asg.name),
                Cooldown=self.aws['scale_down_policy.cooldown'],
                DependsOn=self.asg.name,  # above
                ScalingAdjustment='-1',
                # Doesn't support: Tags=Tags(**tags),
            ))

    def add_alarm_high(self):
        name, tags = self._name_tags('alarm_high')
        self.alarm_high = self.t.add_resource(
            cw.Alarm(
                name,
                AlarmDescription=('CPU high or missing due to dead instance'),
                ComparisonOperator='GreaterThanThreshold',
                Dimensions=[cw.MetricDimension(Name='AutoScalingGroupName',
                                               Value=self.asg.name)],
                EvaluationPeriods=3,
                MetricName='CPUUtilization',
                Period='60',
                Namespace='AWS/EC2',
                Statistic='Average',
                Threshold=self.aws['alarm_high.threshold'],
                AlarmActions=[Ref(self.scale_up_policy.name)],
                # Doesn't support: Tags=Tags(**tags),
            ))

    def add_alarm_low(self):
        name, tags = self._name_tags('alarm_low')
        self.alarm_low = self.t.add_resource(
            cw.Alarm(
                name,
                AlarmDescription='CPU low',
                ComparisonOperator='LessThanThreshold',
                Dimensions=[cw.MetricDimension(Name='AutoScalingGroupName',
                                               Value=Ref(self.asg.name))],
                EvaluationPeriods=40,
                MetricName='CPUUtilization',
                Period='60',
                Namespace='AWS/EC2',
                Statistic='Average',
                Threshold=self.aws['alarm_low.threshold'],
                AlarmActions=[Ref(self.scale_down_policy.name)],
                # Doesn't support: Tags=Tags(**tags),
            ))

    def add_alarm_elb_empty(self):
        """"
        Add a CloudWatch Alarm to watch for an empty ELB.

        This alarm will send a message to the attached SNS topic whenever the minimum number of
        instances in the ELB during the sample period is less than the threshold.
        """
        # CloudWatch Alarms don't support tags.
        name, _ = self._name_tags('alarm_elb_empty')
        self.alarm_elb_empty = self.t.add_resource(
            cw.Alarm(
                name,
                AlarmDescription='ELB HealthyHostCount < 1',
                ComparisonOperator='LessThanThreshold',
                Dimensions=[cw.MetricDimension(Name='LoadBalancerName',
                                               Value=Ref(self.elb.name))],
                EvaluationPeriods=1,
                MetricName='HealthyHostCount',
                Period='300',
                Namespace='AWS/ELB',
                Statistic='Minimum',
                Threshold=self.aws['alarm_elb_empty.threshold'],
                AlarmActions=[Ref(self.sns.name)],
                # Doesn't support: Tags=Tags(**tags),
            ))

    ###########################################################################
    # DNS

    def add_dns(self):
        name, tags = self._name_tags('dns')
        self.dns = self.t.add_resource(
            route53.RecordSetType(
                name,
                HostedZoneName=self.aws['dns.zone'],
                Comment='CNAME to public ELB',
                Name=self.aws['dns.record'] + '.' + self.aws['dns.zone'],
                TTL=self.aws['dns.ttl'],
                Type='CNAME',
                ResourceRecords=[GetAtt(self.elb.name, 'DNSName')],
                # Doesn't support: Tags=Tags(**tags),
            ))

    def add_dns2(self):
        name, tags = self._name_tags('dns2')
        self.dns = self.t.add_resource(
            route53.RecordSetType(
                name,
                HostedZoneName=self.aws['dns.zone'],
                Comment='CNAME to public ELB',
                Name=self.aws['dns2.record'] + '.' + self.aws['dns.zone'],
                TTL=self.aws['dns.ttl'],
                Type='CNAME',
                ResourceRecords=[GetAtt(self.elb.name, 'DNSName')],
                # Doesn't support: Tags=Tags(**tags),
            ))

    ###########################################################################
    # S3 bucket for code, with DNS name for HTTP access

    def add_s3(self):
        name, tags = self._name_tags('s3')
        self.s3 = self.t.add_resource(
            s3.Bucket(
                name,
                AccessControl=s3.BucketOwnerFullControl,
                BucketName=self.aws['s3.bucket'],
                Tags=Tags(**tags),
                WebsiteConfiguration=s3.WebsiteConfiguration(IndexDocument='index.html'),
            ))

    def add_s3_dns(self):
        name, tags = self._name_tags('s3_dns')
        self.s3_dns = self.t.add_resource(
            route53.RecordSetType(
                name,
                HostedZoneName=self.aws['s3_dns.zone'],
                Comment='CNAME to public ELB',
                Name=self.aws['s3_dns.record'] + '.' + self.aws['s3_dns.zone'],
                TTL=self.aws['s3_dns.ttl'],
                Type='CNAME',
                ResourceRecords=[GetAtt(self.s3.name, 'DomainName')],
                # Doesn't support: Tags=Tags(**tags),
            ))

    ###########################################################################
    # We need a DNS name for the origin server since we'll take over the
    # canonical name later. Point Diazo at it and use the name we'll take over
    # set to localhost in /etc/hosts for development.

    def add_dns_ttt(self):
        name, tags = self._name_tags('dns_ttt')
        self.dns_ttt = self.t.add_resource(
            route53.RecordSetType(
                name,
                HostedZoneName=self.aws['dns.zone'],
                Comment='A record pointing to TTT origin server',
                Name=self.aws['dns_ttt.record'] + '.' + self.aws['dns.zone'],
                TTL=self.aws['dns.ttl'],
                Type='A',
                ResourceRecords=[self.aws['dns_ttt.ip']]
                # Doesn't support: Tags=Tags(**tags),
            ))

    ###########################################################################
    # CodeDeploy environment which deploys to instances in the ASG
    # from development branch

    def add_cd_role(self):
        name, tags = self._name_tags('cd_role')
        self.cd_role = self.t.add_resource(
            iam.Role(
                name,
                AssumeRolePolicyDocument=Policy(
                    Statement=[
                        Statement(
                            Action=[awacs.sts.AssumeRole],
                            Effect=Allow,
                            Principal=Principal('Service', 'codedeploy.amazonaws.com'),
                            Sid=name,  # redundant?
                        ),
                    ],
                ),
                ManagedPolicyArns=['arn:aws:iam::aws:policy/service-role/AWSCodeDeployRole'],
                Path='/',
            ))

    def add_cd_deploymentgroup(self):
        name, tags = self._name_tags('cd_deploymentgroup')
        self.cd_deploymentgroup = self.t.add_resource(
            codedeploy.DeploymentGroup(
                name,
                ApplicationName=self.aws['cd_application'],
                AutoScalingGroups=[Ref(self.asg.name)],
                DeploymentConfigName=self.aws['cd_deploymentgroup.configname'],
                DeploymentGroupName=self.aws['cd_deploymentgroup.name'],
                ServiceRoleArn=self.aws['cd_role_arn']
            ))

    def add_cd_iam_user_policy(self):
        name, tags = self._name_tags('cd_iam_user_policy')
        region = self.aws['region']
        account = self.aws['account']
        cd_application_arn = 'application:' + self.aws['cd_application']
        cd_iam_user_arn = self.aws['cd_iam_user']
        cd_deployment_group_arn = 'deploymentgroup:' + self.aws['cd_application']
        cd_deployment_config_arn = 'deploymentconfig:' + self.aws['cd_deploymentgroup.configname']
        self.cd_iam_user_policy = self.t.add_resource(
            iam.ManagedPolicy(
                name,
                PolicyDocument=Policy(
                    Version='2012-10-17',
                    Statement=[
                        Statement(
                            Action=[awacs.s3.PutObject],
                            Effect=Allow,
                            Resource=[awacs.s3.ARN(resource=self.aws['s3.bucket'] + '/ttt/*')],
                        ),
                        Statement(
                            Action=[awacs.codedeploy.RegisterApplicationRevision,
                                    awacs.codedeploy.GetApplicationRevision,
                                    ],
                            Effect=Allow,
                            Resource=[
                                awacs.codedeploy.ARN(region=region, account=account, resource=cd_application_arn),
                                awacs.codedeploy.ARN(region=region, account=account, resource=cd_application_arn + '/*')
                                ],
                        ),
                        Statement(
                            Action=[awacs.codedeploy.CreateDeployment,
                                    awacs.codedeploy.GetDeployment,
                                    ],
                            Effect=Allow,
                            Resource=[
                                awacs.codedeploy.ARN(region=region, account=account, resource=cd_deployment_group_arn + '/*')
                                ],
                        ),
                        Statement(
                            Action=[awacs.codedeploy.GetDeploymentConfig],
                            Effect=Allow,
                            Resource=[
                                awacs.codedeploy.ARN(region=region, account=account, resource=cd_deployment_config_arn)
                            ],
                        ),
                    ]
                ),
                Users=[ cd_iam_user_arn, ],
            ))

###############################################################################


def main():
    """Entrypoint to use as command."""
    parser = argparse.ArgumentParser(
        description='Create CloudFormation template.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        usage='%(prog)s $env.ini'
    )
    parser.add_argument('inifile',
                        help='.ini file for configuration settings.'
                        ' i.e. infrastructure.py dev.ini > availdev.json')
    parser.parse_args()
    args = parser.parse_args()
    config = configparser.RawConfigParser()
    # Preserve key case, e.g., for QueueNames
    config.optionxform = lambda option: option
    config.read(args.inifile)
    env = config['config:aws']['env']

    infra = Infra(config)
    infra.add_sg_app()
    infra.add_role()
    infra.add_profile()         # before launchconfig that uses it
    infra.add_sns()             # before asg which Ref's it
    # provision ELBs for Prod env, attach to ASG, set ELB Health Check
    if env == 'prod':
        infra.add_launchconfig_prod()
        infra.add_elb()
        infra.add_asg_w_elb()
    else:
        # Otherwise provision ASG without ELB attach, set EC2 HealthCheck
        infra.add_launchconfig()
        infra.add_asg()

    infra.add_scale_down_policy()
    infra.add_scale_up_policy()
    infra.add_alarm_high()
    infra.add_alarm_low()
    # Only provision DNS Records for Prod env
    if env == 'prod':
        infra.add_alarm_elb_empty()
        infra.add_dns()
        infra.add_dns2()
    infra.add_dns_ttt()
    infra.add_cd_deploymentgroup()
    infra.add_cd_iam_user_policy()

    print(infra)


# TODO: Outputs: see atts your can get:
# http://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/intrinsic-function-reference-getatt.html

if __name__ == '__main__':
    main()

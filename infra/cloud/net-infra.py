#!/usr/bin/env python
"""Build cloud network infrastructure for all environments based on .ini file.

Create virtualenv::

  virtualenv --python=python3 .venv3
  source .venv3/bin/activate
  pip install -r requirements.txt

Create a new stack like::

  ./net-infra.py ../../net-infra.ini > tttinfra.json
  aws cloudformation create-stack --stack-name tttinfra  --capabilities CAPABILITY_IAM --template-body file://tttinfra.json

Update the existing stack like::

  ./net-infra.py ../../net-infra.ini > tttinfra.json
  aws cloudformation update-stack --stack-name tttinfra  --capabilities CAPABILITY_IAM --template-body file://tttinfra.json

This environment can used for all envs for TTT apps. Each app is deployed on top of this parent template.

- VPC
- Subnets
- Routing tables
- Subnet / Routing table association
- SG: ssh, ELB http, https, EC2 app from ELB only

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
import awacs.codedeploy
import awacs.iam
import awacs.s3
import awacs.sts

from troposphere import (
    Base64,
    # FindInMap,
    GetAtt,
    Join,
    Output,
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
        self.t.add_description(
            'TTT Infra: VPC, IGW, RouteTable, DefaultRoute, S3'
            )
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

    def add_vpc(self):
        """Add VPC to template and return the resource."""
        name, tags = self._name_tags('vpc')
        self.vpc = self.t.add_resource(
            ec2.VPC(
                name,
                CidrBlock=self.aws['vpc.cidr_block'],
                EnableDnsHostnames=True,
                Tags=Tags(**tags)
            ))
        self.t.add_output(Output(
            "VpcId", Value=Ref(self.vpc)
            ))

    ###########################################################################
    # SGs

    def add_sg_ssh(self):
        name, tags = self._name_tags('sg_ssh')
        sg_rules = []
        for port in self.aws['sg_ssh.ports'].split(','):
            sg_rules.append(
                ec2.SecurityGroupRule(
                    IpProtocol='tcp',
                    FromPort=port,
                    ToPort=port,
                    CidrIp=self.aws['sg_ssh.cidr_block'],
                ),
            )
        self.sg_ssh = self.t.add_resource(
            ec2.SecurityGroup(
                name,
                VpcId=Ref(self.vpc),
                GroupDescription=self.aws['sg_ssh.desc'],
                SecurityGroupIngress=sg_rules,
                Tags=Tags(**tags)
            ))
        self.t.add_output(Output(
            "SGSSH", Value=Ref(self.sg_ssh)
            ))

    def add_sg_elb(self):
        """Allow world to ELB, then allow priv subnet EC2s from this SG."""
        name, tags = self._name_tags('sg_elb')
        sg_rules = []
        for port in self.aws['sg_elb.ports'].split(','):
            sg_rules.append(
                ec2.SecurityGroupRule(
                    IpProtocol='tcp',
                    FromPort=port,
                    ToPort=port,
                    CidrIp=self.aws['sg_elb.cidr_block'],
                ),
            )
        self.sg_elb = self.t.add_resource(
            ec2.SecurityGroup(
                name,
                VpcId=Ref(self.vpc),
                GroupDescription=self.aws['sg_elb.desc'],
                SecurityGroupIngress=sg_rules,
                Tags=Tags(**tags)
            ))
        self.t.add_output(Output(
            "SGELB", Value=Ref(self.sg_elb)
            ))

    ###########################################################################
    # IGW

    def add_igw_gateway(self):
        name, tags = self._name_tags('igw_gateway')
        self.igw_gateway = self.t.add_resource(
            ec2.InternetGateway(
                name,
                Tags=Tags(**tags),
            ))

    def add_igw_attachment(self):
        name, tags = self._name_tags('igw_attachment')
        self.igw_attachment = self.t.add_resource(
            ec2.VPCGatewayAttachment(
                name,
                VpcId=Ref(self.vpc),
                InternetGatewayId=Ref(self.igw_gateway),
                # Doesn't support: Tags=Tags(**tags),
            ))

    def add_igw_route_table(self):
        name, tags = self._name_tags('igw_route_table')
        self.igw_route_table = self.t.add_resource(
            ec2.RouteTable(
                name,
                VpcId=Ref(self.vpc),
                Tags=Tags(**tags),
            ))
        self.t.add_output(Output(
            "IGWRoute", Value=Ref(self.igw_route_table)
            ))

    def add_igw_default_route(self):
        name, tags = self._name_tags('igw_default_route')
        self.igw_default_route = self.t.add_resource(
            ec2.Route(
                name,
                DependsOn=self.igw_attachment.name,  # above
                GatewayId=Ref(self.igw_gateway),
                DestinationCidrBlock="0.0.0.0/0",
                RouteTableId=Ref(self.igw_route_table),
                # Doesn't support: Tags=Tags(**tags),
            ))

    ###########################################################################
    # Subnets:
    # - public subnet for ELB public access
    # - internal public subnet for EC2 so it can use IGW to get out to TTT
    #   (if on private subnet, needs separate NAT instance to get out: extra
    #   cost and a single point of failure)

    def add_subnet_public(self):
        name, tags = self._name_tags('subnet_public')
        self.subnet_public = self.t.add_resource(
            ec2.Subnet(
                name,
                AvailabilityZone=self.aws['subnet_public.az'],
                CidrBlock=self.aws['subnet_public.cidr_block'],
                VpcId=Ref(self.vpc),
                Tags=Tags(**tags),
            ))
        self.t.add_output(Output(
            "PublicSubnet", Value=Ref(self.subnet_public)
            ))

    def add_subnet_app(self):
        name, tags = self._name_tags('subnet_app')
        self.subnet_app = self.t.add_resource(
            ec2.Subnet(
                name,
                AvailabilityZone=self.aws['subnet_app.az'],
                CidrBlock=self.aws['subnet_app.cidr_block'],
                VpcId=Ref(self.vpc),
                Tags=Tags(**tags),
            ))
        self.t.add_output(Output(
            "AppSubnet", Value=Ref(self.subnet_app)
            ))

    def add_subnet_db1(self):
        name, tags = self._name_tags('subnet_db1')
        self.subnet_db1 = self.t.add_resource(
            ec2.Subnet(
                name,
                AvailabilityZone=self.aws['subnet_db1.az'],
                CidrBlock=self.aws['subnet_db1.cidr_block'],
                VpcId=Ref(self.vpc),
                Tags=Tags(**tags),
            ))
        self.t.add_output(Output(
            "DB1Subnet", Value=Ref(self.subnet_db1)
            ))

    def add_subnet_db2(self):
        name, tags = self._name_tags('subnet_db2')
        self.subnet_db2 = self.t.add_resource(
            ec2.Subnet(
                name,
                AvailabilityZone=self.aws['subnet_db2.az'],
                CidrBlock=self.aws['subnet_db2.cidr_block'],
                VpcId=Ref(self.vpc),
                Tags=Tags(**tags),
            ))
        self.t.add_output(Output(
            "DB2Subnet", Value=Ref(self.subnet_db2)
            ))

    def add_subnet_public_rta(self):
        name, tags = self._name_tags('subnet_public_rta')
        self.subnet_public_rta = self.t.add_resource(
            ec2.SubnetRouteTableAssociation(
                name,
                SubnetId=Ref(self.subnet_public),
                RouteTableId=Ref(self.igw_route_table),
                # Doesn't support: Tags=Tags(**tags),
            ))

    def add_subnet_app_rta(self):
        name, tags = self._name_tags('subnet_app_rta')
        self.subnet_app_rta = self.t.add_resource(
            ec2.SubnetRouteTableAssociation(
                name,
                SubnetId=Ref(self.subnet_app),
                RouteTableId=Ref(self.igw_route_table),
                # Doesn't support: Tags=Tags(**tags),
            ))

    def add_subnet_db1_rta(self):
        name, tags = self._name_tags('subnet_db1_rta')
        self.subnet_db1_rta = self.t.add_resource(
            ec2.SubnetRouteTableAssociation(
                name,
                SubnetId=Ref(self.subnet_db1),
                RouteTableId=Ref(self.igw_route_table),
                # Doesn't support: Tags=Tags(**tags),
            ))

    def add_subnet_db2_rta(self):
        name, tags = self._name_tags('subnet_db2_rta')
        self.subnet_db1_rta = self.t.add_resource(
            ec2.SubnetRouteTableAssociation(
                name,
                SubnetId=Ref(self.subnet_db2),
                RouteTableId=Ref(self.igw_route_table),
                # Doesn't support: Tags=Tags(**tags),
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
                                Resource=[awacs.s3.ARN(self.aws['s3.bucket']),
                                          awacs.s3.ARN(self.aws['s3.bucket'] + '/*')],
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
    # Route53 DNS zones and records

    def add_r53_dns(self):
        zone_name_index = 0
        name, tags = self._name_tags('r53_dns')
        for zone in self.aws['r53_dns.zones'].split(','):
            zone_name = name + str(zone_name_index)
            self.r53_dns = self.t.add_resource(
               route53.HostedZone(
                    zone_name,
                    Name=zone,
                ))
            zone_output_name = "HostedZoneName" + str(zone_name_index)
            self.t.add_output(Output(
                zone_output_name, Value=Ref(self.r53_dns)
                ))
            zone_name_index += 1

    ###########################################################################
    # CodeDeploy environment which deploys to instances in the app ASGs
    #  Iterates over contents of cd_application.names to create multiple
    #  CodeDeploy Apps with an IAM user and role per App

    def add_cd_applications(self):
        cdapp_index = 0
        for cdapp in self.aws['cd_application.names'].split(','):
            name, tags = self._name_tags('cd_application')

            cdapp_name = name + str(cdapp_index)
            self.cd_application = self.t.add_resource(
                codedeploy.Application(
                    cdapp_name,
                    ApplicationName=cdapp,
                    # Doesn't support: Tags=Tags(**tags),
                ))

            cdapp_output_name = "CDApp" + str(cdapp_index)
            self.t.add_output(Output(
                cdapp_output_name, Value=Ref(self.cd_application)
                ))

            cd_role_name = cdapp + "CDRole"
            self.cd_role = self.t.add_resource(
                iam.Role(
                    cd_role_name,
                    AssumeRolePolicyDocument=Policy(
                        Statement=[
                            Statement(
                                Action=[awacs.sts.AssumeRole],
                                Effect=Allow,
                                Principal=Principal('Service', 'codedeploy.amazonaws.com'),
                                Sid=cd_role_name,  # redundant?
                            ),
                        ],
                    ),
                    ManagedPolicyArns=['arn:aws:iam::aws:policy/service-role/AWSCodeDeployRole'],
                    Path='/',
                ))

            cd_role_output_name = "CDRole" + str(cdapp_index)
            self.t.add_output(Output(
                cd_role_output_name, Value=Ref(self.cd_role)
                ))

            cd_iam_user_name = cdapp + "CDUser"
            self.cd_iam_user = self.t.add_resource(
                iam.User(
                    cd_iam_user_name,
                    # Can't attach policy here,
                    # must create policy and attach to user from app stack
                    # ManagedPolicyArns=[Ref(self.cd_iam_user_policy.name)]
                ))

            cd_iam_user_output_name = "CDUser" + str(cdapp_index)
            self.t.add_output(Output(
                cd_iam_user_output_name, Value=Ref(self.cd_iam_user)
                ))

            cdapp_index += 1


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

    infra = Infra(config)
    infra.add_vpc()
    infra.add_sg_ssh()
    infra.add_sg_elb()
    infra.add_igw_gateway()
    infra.add_igw_attachment()
    infra.add_igw_route_table()
    infra.add_igw_default_route()
    infra.add_subnet_public()
    infra.add_subnet_app()
    infra.add_subnet_db1()
    infra.add_subnet_db2()
    infra.add_subnet_public_rta()
    infra.add_subnet_app_rta()
    infra.add_subnet_db1_rta()
    infra.add_subnet_db2_rta()
    infra.add_role()
    infra.add_profile()         # before launchconfig that uses it
    infra.add_s3()
    infra.add_s3_dns()
    infra.add_r53_dns()
    infra.add_cd_applications()



    print(infra)

# TODO: Outputs: see atts your can get:
# http://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/intrinsic-function-reference-getatt.html

if __name__ == '__main__':
    main()

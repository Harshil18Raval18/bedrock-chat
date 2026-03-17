import * as cdk from "aws-cdk-lib";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as iam from "aws-cdk-lib/aws-iam";
import * as s3 from "aws-cdk-lib/aws-s3";
import * as s3n from "aws-cdk-lib/aws-s3-notifications";
import * as ec2 from "aws-cdk-lib/aws-ec2";
import { Construct } from "constructs";

export interface VectorStoreLambdaProps {
  readonly s3Bucket: s3.IBucket;
  readonly botId: string;
  readonly rdsEndpoint: string;
  readonly rdsDatabase: string;
  readonly rdsUser: string;
  readonly rdsPassword: string;
  readonly vpc?: ec2.IVpc;
  readonly securityGroup?: ec2.ISecurityGroup;
}

export class VectorStoreLambda extends Construct {
  public readonly function: lambda.Function;

  constructor(scope: Construct, id: string, props: VectorStoreLambdaProps) {
    super(scope, id);

    // Create Lambda execution role
    const lambdaRole = new iam.Role(this, "VectorStoreLambdaRole", {
      assumedBy: new iam.ServicePrincipal("lambda.amazonaws.com"),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName(
          "service-role/AWSLambdaBasicExecutionRole"
        ),
      ],
    });

    // Add S3 permissions
    props.s3Bucket.grantRead(lambdaRole);

    // Add Bedrock permissions for embeddings
    lambdaRole.addToPrincipalPolicy(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: ["bedrock:InvokeModel"],
        resources: ["arn:aws:bedrock:*::foundation-model/amazon.titan-embed-text-v2:0"],
      })
    );

    // Add VPC permissions if VPC is provided
    if (props.vpc && props.securityGroup) {
      lambdaRole.addToPrincipalPolicy(
        new iam.PolicyStatement({
          effect: iam.Effect.ALLOW,
          actions: [
            "ec2:CreateNetworkInterface",
            "ec2:DescribeNetworkInterfaces",
            "ec2:DeleteNetworkInterface",
          ],
          resources: ["*"],
        })
      );
    }

    // Create Lambda function
    this.function = new lambda.Function(this, "VectorStoreLambda", {
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: "lambda_function.lambda_handler",
      code: lambda.Code.fromAsset("backend", {
        bundling: {
          image: lambda.Runtime.PYTHON_3_11.bundlingImage,
          command: [
            "bash",
            "-c",
            [
              "pip install -r app/vector_store/requirements.txt -t /asset-output",
              "cp -r app /asset-output",
              "cp lambda_function.py /asset-output",
            ].join(" && "),
          ],
        },
      }),
      role: lambdaRole,
      timeout: cdk.Duration.minutes(15),
      memorySize: 1024,
      environment: {
        BOT_ID: props.botId,
        RDS_HOST: props.rdsEndpoint,
        RDS_DATABASE: props.rdsDatabase,
        RDS_USER: props.rdsUser,
        RDS_PASSWORD: props.rdsPassword,
        BEDROCK_REGION: "us-east-1",
      },
      vpc: props.vpc,
      securityGroups: props.securityGroup ? [props.securityGroup] : undefined,
    });

    // Add S3 trigger
    props.s3Bucket.addEventNotification(
      s3.EventType.OBJECT_CREATED,
      new s3n.LambdaDestination(this.function),
      {
        prefix: `bot-files/${props.botId}/`,
        suffix: ".pdf",
      }
    );
  }
}

import * as cdk from "aws-cdk-lib";
import { Construct } from "constructs";
import { APP_NAME } from "./constant";

export class MainStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    const langfuseHost = cdk.aws_ssm.StringParameter.valueForStringParameter(
      this,
      `/${APP_NAME}/LangfuseHost`,
    );
    const langfusePublicKey =
      cdk.aws_ssm.StringParameter.valueForStringParameter(
        this,
        `/${APP_NAME}/LangfusePublicKey`,
      );
    const langfuseSecretKey =
      cdk.aws_ssm.StringParameter.valueForStringParameter(
        this,
        `/${APP_NAME}/LangfuseSecretKey`,
      );
    const pineconeApiKey = cdk.aws_ssm.StringParameter.valueForStringParameter(
      this,
      `/${APP_NAME}/PineconeApiKey`,
    );
    const pineconeIndexName =
      cdk.aws_ssm.StringParameter.valueForStringParameter(
        this,
        `/${APP_NAME}/PineconeIndexName`,
      );
    const slackBotToken = cdk.aws_ssm.StringParameter.valueForStringParameter(
      this,
      `/${APP_NAME}/SlackBotToken`,
    );
    const slackSignSecret = cdk.aws_ssm.StringParameter.valueForStringParameter(
      this,
      `/${APP_NAME}/SlackSigningSecret`,
    );

    const ragDocstoreBucket = new cdk.aws_s3.Bucket(this, "RagDocstoreBucket", {
      bucketName: `${this.account}-rag-docstore`,
      removalPolicy: cdk.RemovalPolicy.RETAIN_ON_UPDATE_OR_DELETE,
    });

    const slackBotFn = new cdk.aws_lambda.Function(this, "SlackBotFn", {
      code: cdk.aws_lambda.Code.fromAssetImage("../server"),
      handler: cdk.aws_lambda.Handler.FROM_IMAGE,
      runtime: cdk.aws_lambda.Runtime.FROM_IMAGE,
      architecture: cdk.aws_lambda.Architecture.ARM_64,
      memorySize: 1769, // 1vCPUフルパワー @see https://docs.aws.amazon.com/ja_jp/lambda/latest/dg/gettingstarted-limits.html
      timeout: cdk.Duration.minutes(15),
      environment: {
        LANGFUSE_HOST: langfuseHost,
        LANGFUSE_PUBLIC_KEY: langfusePublicKey,
        LANGFUSE_SECRET_KEY: langfuseSecretKey,
        PINECONE_API_KEY: pineconeApiKey,
        PINECONE_INDEX_NAME: pineconeIndexName,
        RAG_DOCSTORE_BUCKET_NAME: ragDocstoreBucket.bucketName,
        SLACK_BOT_TOKEN: slackBotToken,
        SLACK_SIGNING_SECRET: slackSignSecret,
      },
    });

    slackBotFn.addFunctionUrl({
      authType: cdk.aws_lambda.FunctionUrlAuthType.NONE,
      cors: {
        allowedMethods: [cdk.aws_lambda.HttpMethod.ALL],
        allowedOrigins: ["*"],
      },
    });

    slackBotFn.addToRolePolicy(
      new cdk.aws_iam.PolicyStatement({
        effect: cdk.aws_iam.Effect.ALLOW,
        actions: [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream",
          "aoss:*",
        ],
        resources: ["*"],
      }),
    );

    // Slack BoltのLazyリスナーでは、内部的に自身のLambda関数を呼び出すためInvokeFunction権限が必要
    // resourcesにslackBotFn.functionArnを指定すると循環参照が発生してしまうため、いったん緩く設定する
    slackBotFn.addToRolePolicy(
      new cdk.aws_iam.PolicyStatement({
        effect: cdk.aws_iam.Effect.ALLOW,
        actions: ["lambda:InvokeFunction"],
        resources: ["*"],
      }),
    );

    ragDocstoreBucket.grantRead(slackBotFn);
  }
}

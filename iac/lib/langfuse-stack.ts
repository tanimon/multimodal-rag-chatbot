import * as apprunner from "@aws-cdk/aws-apprunner-alpha";
import * as cdk from "aws-cdk-lib";
import { Construct } from "constructs";
import { APP_NAME } from "./constant";

/**
 * [Langfuse](https://langfuse.com/)をホストするためのスタック。
 *
 * NOTE: メインのアプリケーションとはライフサイクルが異なるため、別スタックとして定義している。
 */
export class LangfuseStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    const secret = cdk.aws_secretsmanager.Secret.fromSecretNameV2(
      this,
      "Secret",
      `/${APP_NAME}/Langfuse`,
    );

    new apprunner.Service(this, "Service", {
      source: apprunner.Source.fromAsset({
        asset: new cdk.aws_ecr_assets.DockerImageAsset(this, "DockerImage", {
          directory: "./asset/langfuse",
          platform: cdk.aws_ecr_assets.Platform.LINUX_AMD64,
        }),
        imageConfiguration: {
          environmentVariables: {
            // cspell:ignore NEXTAUTH
            NEXTAUTH_URL: "http://localhost:3000",
            PORT: "3000",
            HOSTNAME: "0.0.0.0",
          },
          environmentSecrets: {
            DATABASE_URL: apprunner.Secret.fromSecretsManager(
              secret,
              "DATABASE_URL",
            ),
            DIRECT_URL: apprunner.Secret.fromSecretsManager(
              secret,
              "DIRECT_URL",
            ),
            NEXTAUTH_SECRET: apprunner.Secret.fromSecretsManager(
              secret,
              "NEXTAUTH_SECRET",
            ),
            SALT: apprunner.Secret.fromSecretsManager(secret, "SALT"),
          },
          port: 3000,
        },
      }),
    });
  }
}

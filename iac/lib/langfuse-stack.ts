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

    const langfuseSecret = cdk.aws_secretsmanager.Secret.fromSecretNameV2(
      this,
      "LangfuseSecret",
      `/${APP_NAME}/Langfuse`,
    );

    new apprunner.Service(this, "LangfuseService", {
      source: apprunner.Source.fromAsset({
        asset: new cdk.aws_ecr_assets.DockerImageAsset(
          this,
          "LangfuseDockerImage",
          {
            directory: "./asset/langfuse",
            platform: cdk.aws_ecr_assets.Platform.LINUX_AMD64,
          },
        ),
        imageConfiguration: {
          environmentVariables: {
            // cspell:ignore NEXTAUTH
            NEXTAUTH_URL: "http://localhost:3000",
            PORT: "3000",
            HOSTNAME: "0.0.0.0",
          },
          environmentSecrets: {
            DATABASE_URL: apprunner.Secret.fromSecretsManager(
              langfuseSecret,
              "DATABASE_URL",
            ),
            DIRECT_URL: apprunner.Secret.fromSecretsManager(
              langfuseSecret,
              "DIRECT_URL",
            ),
            NEXTAUTH_SECRET: apprunner.Secret.fromSecretsManager(
              langfuseSecret,
              "NEXTAUTH_SECRET",
            ),
            SALT: apprunner.Secret.fromSecretsManager(langfuseSecret, "SALT"),
          },
          port: 3000,
        },
      }),
    });
  }
}

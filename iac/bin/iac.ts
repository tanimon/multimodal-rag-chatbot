#!/usr/bin/env node

import * as cdk from "aws-cdk-lib";
import "source-map-support/register";
import { LangfuseStack } from "../lib/langfuse-stack";
import { MainStack } from "../lib/main-stack";

const app = new cdk.App();
new MainStack(app, "MainStack");
new LangfuseStack(app, "LangfuseStack");

#!/usr/bin/env node
import "source-map-support/register";
import * as cdk from "aws-cdk-lib";
import { ExampleStack } from "../lib/example-stack";

const app = new cdk.App();
const namespace: string =
  app.node.tryGetContext("namespace") || "undefined-namespace";

new ExampleStack(app, (namespace ? namespace + "-" : "") + "multistack-00", {
  /* For more information, see https://docs.aws.amazon.com/cdk/v2/guide/configure-env.html */
  env: { region: "us-east-1" },
});

new ExampleStack(app, (namespace ? namespace + "-" : "") + "multistack-01", {
  /* For more information, see https://docs.aws.amazon.com/cdk/v2/guide/configure-env.html*/
  env: { region: "us-east-1" },
});

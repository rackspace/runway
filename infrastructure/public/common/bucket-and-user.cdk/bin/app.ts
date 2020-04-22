#!/usr/bin/env node
import cdk = require("@aws-cdk/core");
import "source-map-support/register";

import { AssetsStack } from "../lib/assets-stack";

const app = new cdk.App();
const environment: string = app.node.tryGetContext("environment");

new AssetsStack(
  app,
  // prefix stackname w/ environment
  (environment ? environment + "-" : "") + "runway-assets",
);

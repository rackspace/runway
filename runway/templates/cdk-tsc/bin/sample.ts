#!/usr/bin/env node
import 'source-map-support/register';
import cdk = require('@aws-cdk/core');
import { SampleStack } from '../lib/sample-stack';

const app = new cdk.App();
new SampleStack(app, 'SampleStack');

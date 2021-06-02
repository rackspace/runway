import * as cdk from "@aws-cdk/core";

export class ExampleStack extends cdk.Stack {
  constructor(scope: cdk.Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    new cdk.CfnWaitConditionHandle(this, "Wait");
  }
}

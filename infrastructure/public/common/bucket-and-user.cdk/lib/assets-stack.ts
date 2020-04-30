import iam = require("@aws-cdk/aws-iam");
import s3 = require("@aws-cdk/aws-s3");
import cdk = require("@aws-cdk/core");

export class AssetsStack extends cdk.Stack {
  constructor(scope: cdk.App, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    const bucket = new s3.Bucket(this, "Bucket");
    new cdk.CfnOutput(this, "BucketName", { value: bucket.bucketName });

    const urlShortenerDdbArn: string = this.node.tryGetContext("urlshortener_ddb_arn");

    const policy = new iam.ManagedPolicy(this, "CiPolicy", {
      statements: [
        new iam.PolicyStatement({
          actions: ["s3:PutObject",
                    "s3:PutObjectVersionAcl",
                    "s3:PutObjectTagging",
                    "s3:PutObjectAcl",
                    "s3:GetObject"],
          effect: iam.Effect.ALLOW,
          resources: [bucket.bucketArn + "/runway/*"],
        }),
        /* Needed for CLI sync command */
        new iam.PolicyStatement({
          actions: ["s3:ListBucket"],
          effect: iam.Effect.ALLOW,
          resources: [bucket.bucketArn],
        }),
        // Update URL shortener entries
        new iam.PolicyStatement({
          actions: ["dynamodb:PutItem"],
          effect: iam.Effect.ALLOW,
          resources: [urlShortenerDdbArn],
        }),
      ],
    });

    const user = new iam.User(this, "CiUser", {managedPolicies: [policy]});
    new cdk.CfnOutput(this, "CIUserName", { value: user.userName });
  }
}

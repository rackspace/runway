# NOTE (@ITProKyle): temp patch, revert to `latest` after https://github.com/aws/aws-lambda-base-images/issues/245 is resolved
FROM public.ecr.aws/sam/build-python3.10:1.121.0-20240730174607

RUN yum install libxml2-devel xmlsec1-devel xmlsec1-openssl-devel libtool-ltdl-devel -y

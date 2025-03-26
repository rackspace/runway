FROM public.ecr.aws/sam/build-python3.10:latest

# NOTE (@ITProKyle): temp patch from https://github.com/aws/aws-lambda-base-images/issues/245
RUN <<EOF
cat > /etc/yum.repos.d/amzn2-extras.repo << 'EOREPO'
[amzn2extra-openssl-snapsafe]
name=Amazon Extras repo for openssl-snapsafe
enabled=1
mirrorlist=$awsproto://$amazonlinux.$awsregion.$awsdomain/2/extras/openssl-snapsafe/latest/$basearch/mirror.list
gpgcheck=1
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-amazon-linux-2
priority=10
skip_if_unavailable=1
report_instanceid=yes
EOREPO
EOF

# TODO (@ITProKyle): remove `openssl-snapsafe-libs` when removing temp patch
RUN yum install openssl-snapsafe-libs libxml2-devel xmlsec1-devel xmlsec1-openssl-devel libtool-ltdl-devel -y

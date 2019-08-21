## kiam Demo App

This "app" (just a bare linux container for testing) demonstrates the AssumeRole-by-way-of-intercepted-metadata-service-calls functionality of kiam.

After deployment in the dev runway environment, you can test out the IAM-role authorized API action as follows:

macOS/Linux (requires jq):
```
RUNWAY_ENV=$(runway whichenv)
SELFLINK=$(kubectl get deployment.apps $RUNWAY_ENV-demo-app -n $RUNWAY_ENV-demo-app -o jsonpath={.metadata.selfLink})
SELECTOR=$(kubectl get --raw $SELFLINK/scale | jq -r .status.selector)
PODNAME=$(kubectl get pods -n $RUNWAY_ENV-demo-app --selector $SELECTOR -o jsonpath={.items[0].metadata.name})
kubectl exec -it $PODNAME -n $RUNWAY_ENV-demo-app -- /bin/bash
apt update
apt install -y awscli  # you'll be prompted to configure timezone during install
aws sts get-caller-identity  # see the pod-defined role instead of the instance profile
aws ssm get-parameter --name '/dev/kiam-demo-app/param' --region us-west-2
```

Windows:
```
$RUNWAY_ENV = $(runway whichenv)
$SELFLINK = $(kubectl get deployment.apps $RUNWAY_ENV-demo-app -n $RUNWAY_ENV-demo-app -o jsonpath={.metadata.selfLink})
$SELECTOR = $(kubectl get --raw $SELFLINK/scale | ConvertFrom-Json | $_.status.selector)
$PODNAME = $(kubectl get pods -n $RUNWAY_ENV-demo-app --selector $SELECTOR -o jsonpath={.items[0].metadata.name})
kubectl exec -it $PODNAME -n $RUNWAY_ENV-demo-app -- /bin/bash
apt update
apt install -y awscli  # you'll be prompted to configure timezone during install
aws sts get-caller-identity  # see the pod-defined role instead of the instance profile
aws ssm get-parameter --name '/dev/kiam-demo-app/param' --region us-west-2
```

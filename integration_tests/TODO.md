# Tests to Write

## CloudFormation

### Module-defined Environment Variables

Ensure that modules with defined env_vars work and don't pollute each other:

```
---
deployments:
  - modules:
      - path: module1.cfn
        env_vars:
          "*":
            FOO: BAR
      - module2.cfn
    regions:
      - us-west-2
    environments:
      dev:
        namespace: dev
```

^ `FOO` should only be set in module1, and not module2

(this can almost certainly be incorporated in another test)

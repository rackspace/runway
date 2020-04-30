# urlshortener

Scripts for the URL shortener action.

**Table of Contents**

- [urlshortener](#urlshortener)
  - [Updating Dependencies](#updating-dependencies)
  - [Scripts](#scripts)
    - [update_urls.py](#updateurlspy)

## Updating Dependencies

When making changes to the **Pipfile**, run `make export` to update the **requirements.txt** file.

## Scripts

Before using any of the scripts in this directory, run `make sync` to install required dependencies in a virtualenv.
Or, if being run from an Action, install using `pip install -r requirements.txt`.

### update_urls.py

```
Usage: update_urls.py [OPTIONS]

  Update/add URLs to the URL shortener.

Options:
  -b, --bucket-name <bucket-name>
                                  Name of S3 Bucket where Runway artifact is located.  [required]
  --bucket-region <bucket-region>
                                  AWS region where the S3 Bucket is located.  [required]
  --latest                        Update the "latest" URL.  [default: False]
  --table <table>                 Name of the DynamoDB table containing entries for the URL shortener.  [required]
  --version <version>             Runway version being release.  [required]
  --table-region <table-region>   AWS region where the DynamoDB table is located.  [default: us-east-1]
  -h, --help                      Show this message and exit.  [default: False]
```

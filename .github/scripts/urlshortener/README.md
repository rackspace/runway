# urlshortener

Scripts for the URL shortener action.

Table of Contents

- [urlshortener](#urlshortener)
  - [Scripts](#scripts)
    - [update_urls.py](#update_urlspy)

## Scripts

### update_urls.py

```text
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

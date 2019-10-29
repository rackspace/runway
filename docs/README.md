## Local Testing
Run `make html` (`.\make.bat html` on Windows) to generate the HTML pages
The generated webpages can then be viewed using a web browser

## RTD Dependencies

Python packages for local testing are handled by the Pipfile/Pipfile.lock files.

These are used to generate the requirements.txt used by RTD: `pipenv lock --requirements > requirements.txt`

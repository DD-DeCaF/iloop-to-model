# Iloop-to-model Service for DD-DeCaF

[![Build Status](https://travis-ci.org/DD-DeCaF/iloop-to-model.svg?branch=master)](https://travis-ci.org/DD-DeCaF/iloop-to-model)
[![Codecov](https://codecov.io/gh/DD-DeCaF/iloop-to-model/branch/master/graph/badge.svg)](https://codecov.io/gh/DD-DeCaF/iloop-to-model)
[![Requirements Status](https://requires.io/github/DD-DeCaF/iloop-to-model/requirements.svg?branch=master)](https://requires.io/github/DD-DeCaF/iloop-to-model/requirements/?branch=master)

## Installation

Setup is as easy as typing `make start` in the project
directory. However, the DD-DeCaF upload service depends on a running
instance of the iloop backend. By default it expects a service
`iloop-backend` to accept connections on port `80`, and
`model` on port 8000, on a docker network called
`DD-DeCaF`. You also need to set the `ILOOP_TOKEN` in your `.env`
file (where you can also overide other variables) as this is specific
for your specific user.


| Variable                | Default Value                   | Description                                                                                                            |
|-------------------------|---------------------------------|------------------------------------------------------------------------------------------------------------------------|
| ``ILOOP_TO_MODEL_PORT`` | ``7000``                        | Exposed port of the upload service.                                                                                    |
| ``ILOOP_API``           | ``http://iloop-backend:80/api`` | URL and port for the iloop service.                                                                                    |
| ``ILOOP_TOKEN``         | ``''``                          | Token for the service to  connect to the iloop backend. (Not necessary if connecting  via the metabolica-ui-frontend.) |
| ``MODEL_API``           | ``http://model-backend:80/api`` | URL port of the model service.                                                                                         |
| ``ENVIRONMENT``         | ``development``                 | Set to either `development`, `testing`, or `production`                                                                                 |
| ``SENTRY_DSN``          | ``''``                          | DSN for reporting exceptions to [Sentry](https://docs.sentry.io/clients/python/integrations/flask/).                                                                                 |

## Usage

Type ``make`` in order to see all commonly used commands.

### Testing

To run all tests and QA checks, run `make qa`.

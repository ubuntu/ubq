![PyPI - Version](https://img.shields.io/pypi/v/ubq)
 [![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

# Ubuntu Query
Common Python library interface for interacting with services providing data on Ubuntu

## Architecture

ubq is separated into three sets of components - [models](src/ubq/models/README.md), [providers](src/ubq/providers/README.md), and [services](src/ubq/services/README.md).

The models component contains standardized data types for data that can be extracted from providers.

The providers component provides standardized classes for querying and sending information to external locations hosting Ubuntu-related data.

The services component contains methods and classes for importing and exporting Ubuntu data.

## Scripts

This repository includes a scripts directory for simple tools and examples for interacting with ubq. They can be run using uv:

```bash
uv run scripts/<script_name> [args]
```

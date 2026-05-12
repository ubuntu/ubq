![PyPI - Version](https://img.shields.io/pypi/v/ubq)
 [![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

# Ubuntu Query
Common Python library interface for interacting with services providing data on Ubuntu

## Architecture

ubq is separated into two sets of components - [models](src/ubq/models/README.md) and [providers](src/ubq/providers/README.md).

The models component contains standardized data types for data that can be extracted from providers.

The providers component provides standardized classes for querying and sending information to external locations hosting Ubuntu-related data. It also contains the `ProviderRegistry` for managing provider sessions.

The top-level `ubq` package exposes `QueryService` as the primary entry point for external use.

## Scripts

This repository includes a scripts directory for simple tools and examples for interacting with ubq. They can be run using uv:

```bash
uv run scripts/<script_name> [args]
```

## Testing

Run unit tests and lint using `tox-uv`:

```bash
uvx tox
```

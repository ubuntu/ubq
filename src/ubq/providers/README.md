# ubq providers

The providers component sends and receives Ubuntu data converts it to standardized data types.

## Provider registry

`ProviderRegistry` manages provider registration and authenticated sessions. It is the entry point for obtaining typed provider instances after login.

## Creating a provider

New providers are added as sub-packages of the providers component, implementing a subset of subclasses of `BugProvider`, `MergeRequestProvider`, `PackageProvider`, and `VersionProvider`. Authentication must also be implemented via the `authenticate` method, returning a unified `ProviderSession` object.

## Existing providers
### Launchpad
The launchpad provider transfers data via `launchpadlib` for bugs and packages.

The package includes the following providers
- `LaunchpadProvider` - handles launchpadlib auth
- `LaunchpadBugProvider`
- `LaunchpadPackageProvider`

### Upstream
The upstream provider serves third-party upstream metadata for packages,
derived from a generated data file (`upstream/data/packages.toml`). It does not
cover GitHub- or Launchpad-hosted sources, or sources tracked via the Debian or
Ubuntu archives.

The package includes the following providers
- `UpstreamProvider` - shared base (no authentication required)
- `UpstreamPackageProvider` - upstream project location for a package
- `UpstreamVersionProvider` - latest upstream version for a package

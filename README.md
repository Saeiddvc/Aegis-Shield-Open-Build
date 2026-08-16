# Aegis Shield Open Build

Public CI-only repository for building and testing Aegis Shield Android without publishing the private application source.

The workflow checks out the private source repository at build time using the repository secret `AEGIS_SOURCE_TOKEN`, applies the current Aegis 3.8 patches, builds Xray + HEV dependencies, runs unit/lint/static checks, runs Android 16 instrumentation and cold-launch tests, and publishes tested ARM64 and Universal APKs as workflow artifacts.

Private application source is not committed to this repository.

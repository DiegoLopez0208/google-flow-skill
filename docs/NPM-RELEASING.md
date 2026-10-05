# npm installer releases

The npm package is a launcher/installer for the Python runtime, not a second
implementation. It has no dependencies or install-time scripts. Its published
files are limited to the executable, package metadata, README and MIT license.

Before publishing:

1. Publish and verify the Python wheel in GitHub Releases.
2. Set the npm package version in `package.json`. Set the runtime version,
   release URL and verified wheel SHA-256 in `npm/cli.cjs`.
3. Run `node scripts/check_npm_pack.cjs` and
   `node scripts/smoke_npm.cjs .npm-check/package/npm/cli.cjs`.
4. Review `npm pack --dry-run` and the PR. Merge the tested source to main.
5. Publish the reviewed tarball with
   `npm publish google-flow-skill-2.3.0.tgz --access public` (adjust the filename
   for later releases). Complete npm's authentication challenge if requested.
6. Verify `npm view google-flow-skill version` and install with `npx` from the
   public registry, using a temporary runtime directory for a generation-free
   smoke check.

For automatic releases, configure npm Trusted Publishing for this GitHub
repository and a dedicated release workflow. Do not commit npm tokens. Until
that setup exists, publication is manual with the npm account's authentication.

The first npm version targets Python runtime 2.3.0. Later npm fixes can use
their own patch versions while retaining a fixed runtime version; keep the
wrapper and runtime versions distinct if that happens.

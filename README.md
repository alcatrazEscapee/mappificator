# Mappificator

This is a pile of bodging scripts for playing around with Minecraft modding mappings, including working with Fabric Yarn, Intermediary, Official, and Parchment mappings. The primary purpose is to create an alternate mapping set for Forge mod development. This exists as an alternative to default Parchment mappings for several reasons:

- Parchment mappings (for good reason) include a `p` prefix on every parameter. Mappificator does not apply this, and uses a more targeted system of parameter conflict resolution that can be specifically applied and verified for Forge.
- Parchment does not include mappings for lambda methods or anonymous classes, again due to conflict resolution issues. Mappificator does.
- Mappificator sources parameters names from multiple projects, including Parchment, Crane, and also Fabric Yarn.
- Missing parameter mappings are auto named based on their type for extra readability (e.g. `BlockPos p_28739483` maps to `BlockPos blockPos_`)

All required materials to generate this mapping export are downloaded and cached locally, and the mapping is built and uploaded to the user's local maven repository. This is then able to be referenced by Forge Gradle through using a custom mapping version.

### Running Mappificator

You must install [Maven](https://maven.apache.org/). (Python will invoke `mvn` via command line, so it must be on your path.)

- To check if Maven is functional, run `mvn --version` in a console window.

Run `mappificator.py` with the working directory `/<Mappificator Project Folder>/src/`. There are a number of command line options that can be used and can be found with `mappificator.py --help`. Possibly more information to follow!

### Using in a Mod Dev Environment

In order to use this (or any other custom mcp export) in a mod dev environment, you need to edit your `build.gradle`:

Add `mavenLocal()` to your repositories:

```
repositories {
    mavenLocal()
}
```

And change your mapping version and channel to the one produced by this export, which can be set by the `--version` flag, and will also be printed to the console at the end of a successful export.

```
minecraft {
    mappings channel: 'snapshot', version: '<VERSION>'
```

Note: as this mapping scheme is based on the official mappings, it is possible to use the official mappings in a build server where more readable source is not a concern and the source code will be perfectly cross-compatible. For example, switching to official mappings when an environment variable is present:

```
minecraft {
    def officialVersion = System.getenv("OFFICIAL_MAPPINGS")
    if (officialVersion == null) {
        mappings channel: 'snapshot', version: mappificator_version
    } else {
        mappings channel: 'official', version: mc_version
    }
```
# Mappificator

This is a pile of bodging scripts for playing around with Minecraft modding mappings, including working with Fabric Yarn, Intermediary, Official, and Parchment mappings. The primary purpose is to create an alternate mapping set for Forge mod development. This exists as an alternative to default Parchment mappings for several reasons:

- Parchment mappings (for good reason) include a `p` prefix on every parameter. Mappificator does not apply this, and uses a more targeted system of parameter conflict resolution that can be specifically applied and verified for Forge.
- Parchment does not include mappings for lambda methods or anonymous classes, again due to conflict resolution issues. Mappificator does.
- Missing parameter mappings are auto named based on their type for extra readability (e.g. `BlockPos p_28739483` maps to `BlockPos blockPos_`)
- Parameter names and javadoc comments from Yarn are appended to the mappings, including comments identifying the Yarn field or method by name.

All required materials to generate this mapping export are downloaded and cached locally, and the mapping is built and uploaded to the user's local maven repository. This is then able to be referenced by Forge Gradle through using a custom mapping version. As of time of writing, this is an unfortunate necessity due to 1. a lack of a Forge Gradle API for custom mappings, and 2. legal issues surrounding the official mappings, which means they cannot be distributed.

### Running Mappificator

You must install [Maven](https://maven.apache.org/). (Python will invoke `mvn` via command line, so it must be on your path.)

- To check if Maven is functional, run `mvn --version` in a console window.

Run `mappificator.py` with the working directory `/<Mappificator Project Folder>/src/`. It accepts the following command line arguments:

- `--help` Show a help message with information about the command line arguments
- `--cli` Run a command line interface which takes the output of a generated mapping export, and helps reverse engineer mapping names.
- `--version VERSION` Sets the version of the exported mappings
- `--cache CACHE` Sets the cache folder, to save downloaded mapping files and outputs. Default: `../build/`

Mapping Options:

- `--include-yarn` If the exported mappings should source Fabric Yarn mappings for parameter names in addition to method, field, and parameter comments
- `--include-mapping-comments` If the exported mappings should include auto-generated comments on every method and field, identifying the method in alternative (srg, mcp, intermediary, and yarn) mapping systems.

Version Options:

- `--mc-version VERSION` The Minecraft version used to download official mappings, and MCP Config.
- `--mcp-version VERSION` The Minecraft version used to download mcp mappings.
- `--mcp-date VERSION` The snapshot date for the mcp mappings
- `--intermediary-version VERSION` The Minecraft version used to download Fabric Intermediary, and Yarn mappings
- `--yarn-mappings VERSION` The build number used for Fabric Yarn mappings

When ran, Mappificator will produce a series of informational messages about the mappings it is reading and consuming. At it's successful completion, it will emit a message along the lines of:

```
Maven returned successfully!
MCP Export Built. Version = 'complete-1.16.5-20210309-yarn6-c'
```

If a `--version` flag is not specified, it will be constructed based on the other parameters:

```
complete-<Minecraft Version>-<MCP Snapshot Date>[-yarn<Yarn Build>][-c]
```

- `-yarn<Yarn Build>` is only present in the version with the option `--include-yarn`
- `-c` is only present in the version with the option `--include-mapping-comments`

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
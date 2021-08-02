# Mappificator

This is a pile of bodging scripts for playing around with Minecraft modding mappings, including working with Fabric Yarn, Intermediary, Official, and Parchment mappings. The primary purpose is to create an alternate mapping set for Forge mod development. This exists as an alternative to default Parchment mappings for several reasons:

- Parchment does not include mappings for lambda methods or anonymous classes due to conflict resolution issues. Mappificator does, and uses a number of techniques to avoid conflicts between parameter names (see the `--improved-lambda-conflict-avoidance` argument).
- Mappificator sources parameters names from multiple projects, including Parchment, Crane, and also Fabric Yarn.
- Missing parameter mappings are auto named based on their type for extra readability (e.g. `BlockPos p_28739483` maps to `BlockPos blockPos_`)
- Mappificator adds cross-referencing comments from Yarn, populating methods, fields, and classes with comments identifying their respective Yarn name, if it exists.

All required materials to generate this mapping export are downloaded and cached locally, and the mappings are built and uploaded to the user's local maven repository. This is then able to be referenced by Forge Gradle through using a custom mapping version.

### Setup

You must install [Maven](https://maven.apache.org/). (Python will invoke `mvn` via command line, so it must be on your path.)

- To check if Maven is functional, run `mvn --version` in a console window.

Run `mappificator.py` with the working directory `/<Mappificator Project Folder>/src/`. There are a number of command line options that can be used and can be found with `mappificator.py --help`. In general, there are two that are of note:

- `-p --publish` is required to publish the mappings to the user's maven local.
- `-v --version` sets the output version. 

Mappificator produces a parchment formatted mapping export. As of time of writing, the only way to use this is to use a custom ForgeGradle 5 fork. There are instructions on how to set this up in the [Parchment Discord](https://discord.com/invite/XXHhhPRUxs).

In order to use this in a mod dev environment, you need to edit your `build.gradle`:

Add `mavenLocal()` to your repositories:

```
repositories {
    mavenLocal()
}
```

And change your mapping version and channel to the one produced by this export, which can be set by the `--version` flag, and will also be printed to the console at the end of a successful export.

```
minecraft {
    mappings channel: 'parchment', version: '<VERSION>'
```
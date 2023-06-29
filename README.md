# Mappificator

This is a pile of bodging scripts for playing around with Minecraft modding mappings, and has become a tool to generate custom mappings for mod development, based on the official (mojmap) mappings. It exists for several reasons:

- Mappificator can merge mappings from several sources.
- Unnamed parameters can be auto-named based on their type, such as `BlockPos blockPos_` instead of `BlockPos p_1748392_1_`.
- IF desired, cross referencing comments can be added populating methods with their corresponding name in other mappings, such as MCP or Yarn.
- Mappificator includes more mappings than other sources, including mappings for lambda methods (not included in Parchment, or historically in MCP), and methods in anonymous classes (not included in Parchment).

### Setup

You must install [Maven](https://maven.apache.org/). (Python will invoke `mvn` via command line, so it must be on your path.)

- To check if Maven is functional, run `mvn --version` in a console window.

Run `mappificator.py` with the working directory `/<Mappificator Project Folder>/src/`. There are a number of command line options that can be used and can be found with `mappificator.py --help`. In general, there are two that are of note:

- `-p --publish` is required to publish the mappings to the user's maven local.
- `-v --version` sets the output version. 

Mappificator produces a parchment formatted mapping export. This can be used with Forge Gradle 5+ using [Librarian](https://github.com/ParchmentMC/Librarian/blob/dev/docs/FORGEGRADLE.md).

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
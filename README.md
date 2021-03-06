# sw-version-utility
Minimalist, portable Python script for automatically incrementing software version in files containing a software version, e.g.: C header, and updates it in git as well.

It might be useful for CI/CD.

It uses only stock python libraries, like os, sys, subprocess.

Works with Python version 3.3 and above.

Tested with Python 3.7.

# what it can do
- can read or update the desired version type in the version file passed as argument
- can commit and push the version file
- can creates a git tag with the version
- can check if the current version tag is on the current commit in order to prevent from unnecessary increments.
- can output the version string to `stdout` or a file

It works with:
- C header files with  `#define` macros
- Android `version.properties` file

TODO
  - C++ `const` and `constexpr`
  - text file with a version string

# how to use
The script only works with C `#define` macros.
e.g: `#define APP_VERSION_MAJOR 3`
- create a preferably separate version file, e.g.: `version.h`
- create a config file (add it to your project's repository)
- run the script with the desired arguments

The script prints the version string to `stdout`, so the version string can be captured in a shell variable. See example.

## how to run
`
python version.py version_file_path config_file_path [--update | --git | --output]
`
- when no extra args provided, it reads the version file
reads the version file

version file will not be updated if present

- --update:
updates the version file

this is the default if no extra args are provided

- --commit
commits the version file

- --tag
git tag is created with the version

- --git
same as --tag --commit

- --output:
creates output file containing the version string

- --check:
checks if the current version tag is on the current commit


## how to configure
- setup your version file, e.g `version.h`
```C
#ifndef _VERSION_H_
#define _VERSION_H_
#define APP_VERSION_MAJOR 0
#define APP_VERSION_MINOR 0
#define APP_VERSION_PATCH 0
#define APP_VERSION_BUILD 0
#endif // _VERSION_H_
```

- setup your config to match your version file.

NOTE: all config parameters must be present, otherwise the script will fail. This is a TODO

```json
{
  "version_tags" : [
    "APP_VERSION_MAJOR",
    "APP_VERSION_MINOR",
    "APP_VERSION_PATCH",
    "APP_VERSION_BUILD"
  ],
  "increment" : ["APP_VERSION_PATCH", "APP_VERSION_BUILD"],
  "language" : "C",
  "git_tag_prefix": "V",
  "output_file" : "version.txt",
  "commit_message" : "version ",
  "append_version" : true
}
```
- version_tags: the macro definitionss present in your version file. dd the name of your macro definitions to `version_tags`.
- increment: version tags to be incremented in the version file.
- language:
  - C
  - android 
  
The default git tag is the version string, e.g.: `1.0.0`
- git_tag_prefix: adds this prefix to the git tag, e.g.: `V1.0.0`
- output_file: if `--output` is provided as argument, the output file with this name, containing the version string is created
- commit_message: commit message when commiting the version file. e.g.: `"version: "`
- append_version: appends the version string to the commit message

The output of this config is as follows:
- version string: `1.0.24.111`
- git tag:  `V1.0.24.111`
- commit message:  `version 1.0.24.111`



# example
In shell or a Jenkins job:

```bash
cd <your project>

# pre-build step: update version file
git clone https://github.com/blacix/sw-version-utility.git
python sw-version-utility/version.py app_version.h version_config.json --update

# build project

# post-build steps:
# update project repo
version=$(python sw-version-utility/version.py app_version.h version_config.json --git)
# add the version to the build output file name
mv <your_build_output> <your_build_output>_V$(version)
```


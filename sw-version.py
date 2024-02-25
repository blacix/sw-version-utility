import os
import sys
import git_utils
from version_file_parser import VersionFileParser
from regex_parser import RegexParser
from ros_package_parser import RosPackageParser
import semver
import argparse
from common import *


class SoftwareVersion:
    VALID_BUMPS = [Common.TAG_MAJOR, Common.TAG_MINOR, Common.TAG_PATCH, Common.TAG_PRERELEASE, Common.TAG_BUILD]

    def __init__(self):
        args = self._parse_arguments()

        self.language: str = args.lang
        self.version_file: str = args.file
        self.bump: str = args.bump
        self.commit: bool = args.commit
        self.tag: bool = args.tag
        self.tag_prefix = args.tag_prefix
        self.version: semver.Version = None

        if self.language in RegexParser.LANGUAGES:
            self.parser = RegexParser(self.language, self.version_file)
        elif self.language in RosPackageParser.LANGUAGES:
            self.parser = RosPackageParser(self.version_file)
        else:
            self.parser: VersionFileParser = VersionFileParser()
            print(f'no parser for language: {self.language}')

    def _parse_arguments(self):
        parser = argparse.ArgumentParser(description='Command-line arguments example')

        # Mandatory arguments
        parser.add_argument('--file', required=True, help='Specify the filename')
        parser.add_argument('--lang', required=True, help='Specify the language')

        # Optional arguments without values
        parser.add_argument('--commit', action='store_true', help='commit the updated version file')
        parser.add_argument('--tag', action='store_true', help='add a tag with the version to git')
        parser.add_argument('--tag_prefix', default='', help='Prefix for git tag')

        parser.add_argument('--bump', choices=self.VALID_BUMPS, help='Specify the tag to bump')

        return parser.parse_args()

    def _bump(self):
        if self.version is None:
            return
        elif Common.TAG_MAJOR.lower() == self.bump.lower():
            self.version = self.version.bump_major()
        elif Common.TAG_MINOR.lower() == self.bump.lower():
            self.version = self.version.bump_minor()
        elif Common.TAG_PATCH.lower() == self.bump.lower():
            self.version = self.version.bump_patch()
        elif Common.TAG_PRERELEASE.lower() == self.bump.lower():
            self.version = self.version.bump_prerelease()
        elif Common.TAG_BUILD.lower() in self.bump.lower():
            self.version = self.version.bump_build()
        else:
            print(f'unknown bump: {self.version}')
            pass

    def execute(self) -> int:
        self.version = self.parser.parse()
        if self.version is None:
            print('Parse error')
            return -1

        if self.bump:
            self._bump()
            self.parser.update(self.version)

        result = str(self.tag_prefix + str(self.version))
        print(result)
        return 0


if __name__ == '__main__':
    sys.exit(SoftwareVersion().execute())

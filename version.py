import os
import sys
import re
import subprocess
import json

MIN_ARG_CNT = 3

# [^\S] matches any char that is not a non-whitespace = any char that is whitespace
C_DEFINE_PATTERN = r"(.*#define)([^\S]+)(\S+)([^\S]+)(\d+)([^\S]*\n|$)"
C_VERSION_TYPE_GROUP = 3
C_VERSION_VALUE_GROUP = 5

ANDROID_DEFINE_PATTERN = r"([^\S]*)(\S+)(=)([^\S]*)(\d+)([^\S]*\n|$)"
ANDROID_VERSION_TYPE_GROUP = 2
ANDROID_VERSION_VALUE_GROUP = 5

C_REGEX = (C_DEFINE_PATTERN, C_VERSION_TYPE_GROUP, C_VERSION_VALUE_GROUP)
ANDROID_REGEX = (ANDROID_DEFINE_PATTERN, ANDROID_VERSION_TYPE_GROUP, ANDROID_VERSION_VALUE_GROUP)


class VersionManager:
    def __init__(self):
        self.version_file = None
        self.version_file_content = []
        self.config_json = None
        # all tags from config
        self.version_tags = []
        # tags to increment from config
        self.increment_tags = []
        # holds version info, created from self.version_tags
        self.version_map = {}
        self.update_version_file = False
        self.commit_version_file = False
        self.increment_version = False
        self.create_git_tag = False
        self.git_tag_prefix = ""
        self.git_tag = ""
        self.version_string = ""
        self.version_output_file = None
        self.commit_message_base = ""
        self.commit_message = ""
        self.append_version = True
        self.create_output_files = False
        # check if current commit has the current version tag
        # if it is so, no update is needed
        self.check_git_tag = False

        # tuple for parser, which contains regex and regex grouping info, set based on language
        self.parser_data = None
        # function for creating a line with the version, set to a specific method based on language
        self._create_line_dynamic = None

    # can throw FileNotFoundError
    def _load_config(self):
        self.version_file = sys.argv[1]
        self.config_json = sys.argv[2]
        config_json = json.load(open(self.config_json))
        self.version_tags = config_json["version_tags"]
        self.increment_tags = config_json["increment"]
        self.git_tag_prefix = config_json["git_tag_prefix"]
        self.version_output_file = config_json["output_file"]
        self.commit_message_base = config_json["commit_message"]
        self.append_version = config_json["append_version"]
        self.version_map = {self.version_tags[i]: 0 for i in range(0, len(self.version_tags))}

        # language setup
        self.language = str(config_json["language"]).strip().lower()
        if self.language == 'c':
            self.parser_data = C_REGEX
            self._create_line_dynamic = self._create_c_line
        elif self.language == 'cpp':
            pass
        elif self.language == 'android':
            self.parser_data = ANDROID_REGEX
            self._create_line_dynamic = self._create_android_line
        else:
            raise Exception(f'unknown language: {self.language}')

        # apply arguments
        # Note: arguments can override settings
        self.increment_version = '--update' in sys.argv
        self.update_version_file = self.increment_version
        self.commit_version_file = '--commit' in sys.argv or '--git' in sys.argv
        self.create_git_tag = '--tag' in sys.argv or '--git' in sys.argv
        self.create_output_files = '--output' in sys.argv
        self.check_git_tag = '--check' in sys.argv

    def execute(self):
        if len(sys.argv) < MIN_ARG_CNT:
            self.print_usage()
            return -1
        try:
            self._load_config()
            self._check_version_tags()
            self._parse_version_file()
            # create strings to have git tag of current version
            self._create_strings()
            self._check_git_tag()
            self._update_versions()
            # update strings
            self._create_strings()
            self._update_version_file()
            self._git_update()
            self._create_output_files()
            # print output
            print(f'{self.version_string}')
        except subprocess.CalledProcessError as se:
            print(se, file=sys.stderr)
            return -2
        except json.JSONDecodeError as je:
            print('config JSON parse error!', file=sys.stderr)
            print(je, file=sys.stderr)
            return -3
        except FileNotFoundError as fe:
            print(fe, file=sys.stderr)
            return -4
        except Exception as e:
            print(e, file=sys.stderr)
            return -5
        return 0

    # throws exception on error
    def _check_version_tags(self):
        # check if every tag to be incremented are valid
        filtered_versions_to_increment = [item for item in
                                          self.increment_tags if item in self.version_tags]
        if len(filtered_versions_to_increment) != len(self.increment_tags):
            invalid_versions = [item for item in
                                self.increment_tags if item not in self.version_tags]
            print(f'invalid version type(s) to increment: {invalid_versions}')
            raise Exception("invalid version type(s) found. Check your config!")

    # TODO error when valid version tag is missing from the version file
    def _parse_version_file(self):
        with open(self.version_file, 'r') as file:
            for line in file:
                version_type, version_value = self._parse_line(line, self.parser_data)
                if version_type is not None and version_value is not None:
                    self.version_map[version_type] = version_value
                self.version_file_content.append(line)

    def _update_versions(self):
        if not self.increment_version:
            return

        for tag in self.increment_tags:
            if tag in self.version_map.keys():
                self.version_map[tag] += 1

    def _update_version_file(self):
        if self.update_version_file:
            new_lines = []
            for line in self.version_file_content:
                version_type, version_value = self._parse_line(line, self.parser_data)
                if version_type is not None and version_value is not None:
                    new_lines.append(self._create_line_dynamic(line, self.version_map[version_type]))
                else:
                    new_lines.append(line)

            with open(self.version_file, 'w') as file:
                file.writelines(new_lines)

    @staticmethod
    def _parse_line(line: str, parser_data: ()):
        pattern, version_type_group, version_value_group = parser_data
        result = re.search(pattern, line)
        if result is not None:
            version_type = result[version_type_group]
            version_value = int(result[version_value_group])
            return version_type, version_value
        return None, None

    # TODO does not work with inline comments
    @staticmethod
    def _create_c_line(line: str, version: int):
        return re.sub(pattern=C_DEFINE_PATTERN,
                      repl=fr'\g<1>\g<2>\g<3>\g<4>{version}\g<6>',
                      string=line)

    @staticmethod
    def _create_android_line(line: str, version: int):
        return re.sub(pattern=ANDROID_DEFINE_PATTERN,
                      repl=fr'\g<1>\g<2>\g<3>{str(version)}\n',
                      string=line)

    def _create_strings(self):
        # iterate through self.version_tags so the order will be correct
        self.version_string = ".".join([str(self.version_map[item]) for item in self.version_tags])
        self.git_tag = f'{self.git_tag_prefix}{self.version_string}'
        if self.append_version:
            self.commit_message = f'{self.commit_message_base}{self.version_string}'
        else:
            self.commit_message = f'{self.commit_message_base}'

    def _check_git_tag(self):
        if self.check_git_tag:
            if self._tag_on_current_commit(self.git_tag):
                self.increment_version = False
                self.update_version_file = False
                self.commit_version_file = False
                self.create_git_tag = False

    @staticmethod
    def _tag_on_current_commit(git_tag: str):
        tag_on_commit = False
        tag_commit_hash = subprocess.run(f'git rev-list -n 1 {git_tag}', check=False, shell=True, capture_output=True)
        if tag_commit_hash.returncode == 0:
            current_commit_hash = subprocess.run(f'git rev-parse HEAD', check=True, shell=True, capture_output=True)
            tag_on_commit = tag_commit_hash.stdout == current_commit_hash.stdout
        return tag_on_commit

    # can throw subprocess.CalledProcessError, FileNotFoundError, Exception
    def _git_update(self):
        # TODO push only when both were successful
        if self.commit_version_file:
            self._commit_version_file(self.version_file, self.commit_message)
        if self.create_git_tag:
            self._update_git_tag(self.git_tag)

    # can throw subprocess.CalledProcessError
    @staticmethod
    def _commit_version_file(version_file: str, commit_message: str):
        subprocess.run(f'git add {version_file}', check=True, shell=True, stdout=subprocess.DEVNULL)
        # check if added
        # returns non-zero if there is something to commit
        proc = subprocess.run(f'git diff-index --cached --quiet HEAD', check=False, shell=True,
                              stdout=subprocess.DEVNULL)
        if proc.returncode == 0:
            raise Exception(f'git add {version_file} failed')
        commit_cmd = f'git commit -m "{commit_message}"'
        subprocess.run(commit_cmd, check=True, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(f'git push', check=True, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # can throw subprocess.CalledProcessError
    @staticmethod
    def _update_git_tag(tag_name):
        subprocess.run(f'git tag {tag_name}', check=True, shell=True, stdout=subprocess.DEVNULL)
        # subprocess.run(f'git push origin tag {tag_name}', check=True, shell=True)
        subprocess.run(f'git push origin --tags', check=True, shell=True, stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL)

    def _create_output_files(self):
        if self.create_output_files:
            with open(self.version_output_file, 'w') as file:
                file.write(self.version_string)

    @staticmethod
    def print_usage():
        print(f'usage:')
        print(f'python {os.path.basename(sys.argv[0])} version_file_path config_file_path [--update | --git | --output]')
        print('\t--read: ')
        print('\t\treads the version file')
        print('\t\tversion file will not be updated if present')
        print('\t--update:')
        print('\t\tupdates the version file')
        print('\t\tthis is the default if no extra args are provided')
        print('\t--git:')
        print('\t\tcreates and pushes a git tag if configured')
        print('\t\tcommits and pushes the version file')
        print('\t\tversion file update will only be updated if --update is present')
        print('\t--output:')
        print('\t\tcreates output file containing the version string')


if __name__ == '__main__':
    sys.exit(VersionManager().execute())

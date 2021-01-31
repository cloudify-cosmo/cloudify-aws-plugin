from os import path, pardir
from ecosystem_tests.dorkl import replace_plugin_package_on_manager
from ecosystem_cicd_tools.validations import validate_plugin_version

abs_path = path.join(
    path.abspath(path.join(path.dirname(__file__), pardir)))

if __name__ == '__main__':
    version = validate_plugin_version(abs_path)
    for package in ['cloudify_aws']:
        replace_plugin_package_on_manager(
            'cloudify-aws-plugin', version, package, )

"""pyinstaller spec file to build a single-binary distribution of runway.

This file should be considered a python file and linted as such.

"""
# pylint: disable=undefined-variable,wrong-import-order,invalid-name
# pylint: disable=wrong-import-position,import-self
import os
import pkgutil
from pkg_resources import get_distribution, get_entry_info

from PyInstaller.utils.hooks import copy_metadata

# distutils not included with virtualenv < 20 so we have to import it here
# can be removed once we can upgrade virtualenv and pyinstaller
import distutils

if distutils.distutils_path.endswith('__init__.py'):
    distutils.distutils_path = os.path.dirname(distutils.distutils_path)

CLI_PATH = os.path.join(os.path.dirname(os.path.dirname(workpath)),  # noqa
                        'runway')


def get_submodules(package):
    """Get submodules of a package to add to hiddenimports.

    Package must be installed and imported for this to be used.

    This is needed for dependencies that do not have a
    native pyinstaller hook. This may not find everything that
    needs to be included.

    Args:
        package: An import package to inspect.

    Returns:
        List of submodules.

    """
    return [name for _, name, _ in
            pkgutil.walk_packages(path=package.__path__,
                                  prefix=package.__name__+'.',
                                  onerror=lambda x: None)]


def Entrypoint(dist, group, name, **kwargs):  # noqa
    """Get entrypoint info for packages using setuptools."""
    ep = get_entry_info(dist, group, name)
    # script name must not be a valid module name to avoid name clashes on import
    script_path = os.path.join(workpath, name + '-script.py')  # noqa: F821
    print("creating script for entry point", dist, group, name)
    with open(script_path, 'w') as fh:
        print("import", ep.module_name, file=fh)
        print("%s.%s()" % (ep.module_name, '.'.join(ep.attrs)), file=fh)

    return Analysis([script_path] + kwargs.get('scripts', []), **kwargs)  # noqa: F821


# files that are not explicitly imported but consumed at runtime
# need to be included as data_files.
data_files = [
    (os.path.join(CLI_PATH, 'templates'), './runway/templates/'),
    (os.path.join(CLI_PATH, 'blueprints'), './runway/blueprints/'),
    (os.path.join(CLI_PATH, 'hooks'), './runway/hooks/')
]

data_files.append(('{}/yamllint/conf'.format(get_distribution('yamllint').location),
                   'yamllint/conf/'))
data_files.append(('{}/cfnlint/data'.format(get_distribution('cfn-lint').location),
                   'cfnlint/data/'))
data_files.append(('{}/botocore/data'.format(get_distribution('botocore').location),
                   'botocore/data/'))
data_files.append(('{}/awscli/data'.format(get_distribution('awscli').location),
                   'awscli/data/'))
data_files.append(copy_metadata('runway')[0])  # support scm version

# pyinstaller is not able to find dependencies of dependencies
# unless a hook already exists for pyinstaller so we have to
# add their dependencies here.
hiddenimports = []
# these packages do not have pyinstaller hooks so we need to import
# them to collect a list of submodules to include as hidden imports.
import runway  # noqa
import troposphere  # noqa
import awacs  # noqa
import awscli  # noqa
import botocore  # noqa
hiddenimports.extend(get_submodules(runway))
hiddenimports.extend(get_submodules(troposphere))
hiddenimports.extend(get_submodules(awacs))
hiddenimports.extend(get_submodules(awscli))
hiddenimports.extend(get_submodules(awscli))
hiddenimports.extend(get_submodules(botocore))
# needed due to pkg_resources dropping python2 support
# can be removed on the next pyinstaller release
# https://github.com/pypa/setuptools/issues/1963#issuecomment-582084099
hiddenimports.append('pkg_resources.py2_warn')

a = Entrypoint('runway',
               'console_scripts',
               'runway',
               pathex=[CLI_PATH],
               datas=data_files,
               hiddenimports=hiddenimports,
               win_no_prefer_redirects=False,
               win_private_assemblies=False,
               cipher=None,
               noarchive=False,
               binaries=[])
pyz = PYZ(a.pure, a.zipped_data,  # noqa: F821
          cipher=None)
exe = EXE(pyz,  # noqa: F821
          a.scripts,
          [],
          exclude_binaries=True,
          # for some reason pyinstaller won't create the correct dir
          # structure if this is the same name as a dir used in datas
          name='runway-cli',
          strip=False,
          upx=True,
          console=True)
coll = COLLECT(exe,  # noqa: F821
               a.binaries,
               a.zipfiles,
               a.datas,
               name='runway',
               strip=False,
               upx=True)

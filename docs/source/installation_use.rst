Installation
============
Installing Python
^^^^^^^^^^^^^^^^^
- On Linux (assuming default Bash shell; adjust for others appropriately):
    - Setup your shell for user-installed (non-root) pip packages::
        
        echo 'export PATH=$HOME/.local/bin:$PATH' >> ${HOME}/.bashrc
        source ${HOME}/.bashrc

    - Install Python/pip:
        - Debian-family (e.g. Ubuntu): 
          ``sudo apt-get -y install python-pip python-minimal``
        - Amazon Linux should should work out of the box
        - RHEL-family:
            - If easy_install is available: ``easy_install --user pip``
            - Otherwise, enable EPEL and ``sudo yum install python-pip``

- On macOS (assuming default Bash shell; adjust for others appropriately)::

    if ! which pip > /dev/null; then easy_install --user pip; fi
    echo 'export PATH="${HOME}/Library/Python/2.7/bin:${PATH}"' >> ${HOME}/.bash_profile
    source ${HOME}/.bash_profile

- On Windows:
    - This can be done via the Chocolately package manager (e.g. ``choco install python2``), or manually from their website
        - If installing via Chocolately, default options will be sufficient. Close/reopen terminals after installation to use the updated PATH
        - If installing manually, use the default options with the exception of the "Add python to Path" (it should be enabled).
    - Add ``%USERPROFILE%\AppData\Roaming\Python\Scripts`` to PATH environment variable

Installing runway 
^^^^^^^^^^^^^^^^^
(doesn't require sudo/admin permissions)

- ``pip install --user runway``
    - If this produces an error like ``Unknown distribution option: 'python_requires'``, 
      upgrade setuptools first ``pip install --user --upgrade setuptools``

How To Use
==========
- ``runway test`` (aka ``runway preflight``) - execute this in your environment to catch errors; if it exits ``0``, you're ready for...
- ``runway plan`` (aka ``runway taxi``) - this optional step will show the diff/plan of what will be changed. With a satisfactory plan you can...
- ``runway deploy`` (aka ``runway takeoff``) - if running interactively, you can choose which deployment to run; otherwise (i.e. on your CI system) each deployment will be run in sequence.

Removing Deployments
^^^^^^^^^^^^^^^^^^^^
- ``runway destroy`` (aka ``runway dismantle``) - if running interactively, you can choose which deployment to remove; otherwise (i.e. on your CI system) every deployment will be run in reverse sequence (use with caution).
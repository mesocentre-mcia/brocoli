Brocoli: Browse Collections for iRODS
======================================

Brocoli application allows users to browse iRODS catalog collections in a simple
Tkinter GUI.

Install Brocoli
---------------

Pre-requisites
^^^^^^^^^^^^^^

For now, Brocoli runs on Linux platforms. There may be Microsoft Windows support
in a not-so-far future.

Brocoli needs a Python installation with Tkinter. Under
`Ubuntu <http://www.ubuntu.com>`, you may have to install a specific package to
get Tkinter.

Python 2.7+ and 3.5+ are expected to work.

Dependencies
^^^^^^^^^^^^

Brocoli depends on the following packages:

- six: https://pypi.python.org/pypi/six
- python-irodsclient: https://pypi.python.org/pypi/python-irodsclient

Installing with pip
^^^^^^^^^^^^^^^^^^^

From a command shell, run:

    ``pip install brocoli [--user]``

If you don't have administrative privileges, you may need to use the ``--user``
optional argument, in order to install Brocoli in your user account.

Installing from source
^^^^^^^^^^^^^^^^^^^^^^

#) Download Brocoli from https://github.com/mesocentre-mcia/brocoli
#) from distribution directory, run ``python setup.py install [--user]``

If you don't have administrative privileges, you may need to use the ``--user``
optional argument, in order to install Brocoli in your user account.

Using Brocoli
-------------

Run brocoli from a command shell:

    ``$ brocoli``

Connections
^^^^^^^^^^^

At first run, Brocoli will appear empty. You will want to create a more
useful connection with an iRODS catalog. Just configure it following the menus:

    Settings -> New Connection

This will open a dialog where you can set the connection configuration. The
configuration fields are:

* ``Connection name`` - choose a name to identify the connection
* ``Catalog type`` - choose ``os`` or ``irods3``. Currently, ``irods3`` is the
  only useful catalog available (``os`` is used for testing purposes only)
* ``Root path`` - enter the catalog path you want to base your display from
* ``Make default connection`` - check if you want Brocoli to open this
  connection at startup

``irosd3`` specific configuration fields:

* ``Use irods environment file`` - check if you want to use iRODS v3 iCommands
  configuration file (usually ``~/.irods/.irodsEnv``)
* ``iRODS host`` - the iRODS server DNS name you want to connect to (usually
  your iCAT Enabled Server)
* ``iRODS port`` - depending on your iRODS instance (1247 is the default)
* ``iRODS zone`` - the name of your iRODS zone
* ``iRODS user name`` - your iRODS account name
* ``iRODS default resource`` - the iRODS resource to use (optional)
* ``Remember password`` - check if you want Brocoli to store your iRODS password
  (**dangerous**: although Brocoli scrambles the stored password, it may be easy
  to unscramble for someone who gained access to that value)
* ``iRODS password``

Now, you should be able to switch to the newly created connection by following:

    Settings -> Switch connection -> Your new connection name

Navigating
^^^^^^^^^^

Sub-directories can be opened by clicking on the triangle icon before their
name.

You can base the display from a sub-directory by choosing ``Go to`` in the popup
menu or entering its path directly in the navigation bar.

The ``.`` special entry refers to the currently displayed directory (the path
displayed in the navigation bar).

The ``..`` special entry appears when visiting a subdirectory of the connection
root path. It refers to the current path parent directory.

File operations
^^^^^^^^^^^^^^^

Operations on files and directories are accessible in a popup menu shown when
right clicking on the target.

File/directory operations

* ``Download to local disk`` - download selected entry (recursively) to your
  local computer
* ``Delete`` - delete selected entry (recursively) from the catalog
* ``Properties`` - displays catalog specific properties of the selected entry

Directory only operations

* ``New directory`` - creates a subdirectory of the selected directory
* ``Upload local files`` - uploads local files into the catalog under the
  selected directory
* ``Recursive upload`` - recursively uploads the contents of a local directory
  to the catalog
* ``Go to`` - rebase Brocoli navigation bar to the selected directory

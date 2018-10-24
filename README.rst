Brocoli: Browse Collections for iRODS
======================================

Brocoli_ application allows users to browse iRODS catalog collections in a simple
Tkinter GUI.

.. _Brocoli: https://github.com/mesocentre-mcia/brocoli

Install Brocoli
---------------

Pre-requisites
^^^^^^^^^^^^^^

Brocoli runs on Linux platforms. Windows and MacOS support is experimental.

Brocoli needs a Python installation with Tkinter. Under
`Ubuntu <http://www.ubuntu.com>`, you may have to install a specific package to
get Tkinter.

Python 2.7+ and 3.5+ are expected to work.

Dependencies
^^^^^^^^^^^^

Brocoli depends on the following packages:

- six: https://pypi.python.org/pypi/six
- python-irodsclient >= 0.8.0: https://pypi.python.org/pypi/python-irodsclient

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
* ``Catalog type`` - choose ``os``, ``irods3`` or ``irods4``. Currently,
  ``irods*`` are the only useful catalogs available (``os`` is used for testing
  purposes only)
* ``Root path`` - enter the catalog path you want to base your display from
* ``Make default connection`` - check if you want Brocoli to open this
  connection at startup
* ``Perform local checksum`` - configures brocoli to verify checksum of
  downloaded/uploaded files against catalog registered checksum if preset

``irosd3`` specific configuration fields:

* ``Use irods environment file`` - check if you want to use iRODS iCommands
  configuration file (usually ``~/.irods/.irodsEnv`` fr v3 instances and
  ``~/.irods/irods_environment.json`` for v4)
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

``irods4`` connections have a few extra configuration fields:

* ``Default hash scheme`` - choose checksum hash method among available
  algorithms
* ``irods_client_server_policy`` - iRODS client/server negociation behaviour
* ``Use irods SSL transfer`` - check if you need SSL communication with your
  catalog
* ``irods_encryption_algorithm`` - SSL specific setting depending on your
  catalog configuration
* ``irods_encryption_key_size`` - SSL specific setting depending on your catalog
  configuration
* ``irods_encryption_num_hash_rounds`` - SSL specific setting depending on your
  catalog configuration
* ``irods_encryption_salt_size`` - SSL specific setting depending on your
  catalog configuration
* ``irods_ssl_ca_certificate_file`` - SSL specific setting depending on your
  catalog configuration

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

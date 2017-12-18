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

Not available yet...

Installing from source
^^^^^^^^^^^^^^^^^^^^^^

#) Download Brocoli from https://github.com/mesocentre-mcia/brocoli
#) from distribution directory, run ``python setup.py install [--user]``

Using Brocoli
-------------

Run brocoli from a command shell:

    ``$ brocoli``

Connections
^^^^^^^^^^^

At first run, Brocoli will use a default ``os`` connection that does nothing
interesting except displaying a local directory. You will want to create a more
useful connection with an iRODS catalog. Just configure it following the menus:

    Settings -> New Connection

This will open a dialog where you can set the connection configuration.

Now, you should be able to switch to the newly created connections by following:

    Settings -> Switch connection -> Your new connection name

Navigating
^^^^^^^^^^

Sub-directories can be opened by clicking on the triangle icon before their
name.

File operations
^^^^^^^^^^^^^^^

Operations on files and directories are accessible by right clicking on the
target.

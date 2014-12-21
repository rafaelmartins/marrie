marrie
======

``marrie`` is a simple podcast client that runs on the Command Line Interface.
It is pretty simple and just does the basic tasks: fetch and play podcast
chapters listed on a feed.


Installation
------------

.. _`PyPI Package Index`: http://pypi.python.org/pypi
.. _Gentoo: http://www.gentoo.org/

``marrie`` is available on the `PyPI Package Index`_, and you can install it
using ``pip``::

    # pip install marrie

If you are a Gentoo_ user, you can install it using your favorite package
manager::

    # emerge -av media-sound/marrie


Configuration
-------------

With ``marrie`` installed, you'll need a configuration file, with your list of
feeds and the commands to be used to fetch and play the podcast chapters.

To create it, just run the main script without arguments::

    $ marrie

This command will raise an error, but will create a sample configuration file
for you at ``~/.marrie``. Edit it as follows.

``[config]`` section
~~~~~~~~~~~~~~~~~~~~

The main section of the configuration file.

- ``fetch_command``: The command used to fetch the chapters. The default
  command will use ``wget``. If you want to change it, make sure that the
  variables ``%(file)s`` and ``%(url)s`` are correctly used on your command.
- ``player_command``: The command used to play the chapters. The default
  command will use ``mplayer``. If you want to change it, make sure that the
  variable ``%(file)s`` is correctly used on your command.
- ``media_dir``: The directory where the chapters will be stored. Defaults to
  ``~/podcasts``. A subfolder will be created for each feed.

``[podcast]`` section
~~~~~~~~~~~~~~~~~~~~~

The section with the URLs of your feeds. Each ``key=value`` pair represents
a feed URL. The key is the identifier of the feed (it will be used later
to choose the feed to be used by ``marrie``) and the value is the URL of
the feed. ::

    [podcast]
    my_podcast = http://example.org/feed.rss

You can add as many feeds as you want.


Basic usage
-----------

After having ``marrie`` installed and configured, you should syncronize your
feeds::

    $ marrie --sync

If you want to sync a single feed, you just need to provide its identifier::

    $ marrie --sync my_podcast

``marrie`` will not provide any auto-sync feature. It is simple! If you want
to syncronize periodically, feel free to create a cron job on your system.

With a fresh list of feeds in cache, you'll want to download a chapter. If
you just want to get the latest chapter published in a feed, type::

    $ marrie --get my_podcast

If you want to download a specific chapter, you'll need to list all the
available chapters first::

    $ marrie --list my_podcast
    ...

    Remote files available for "my_podcast" (reverse sorted by date):

        1: chapter_100.mp3 (Fri, 19 Dec 2014 03:00:00 +0000)
        2: chapter_99.mp3 (Fri, 19 Dec 2014 02:00:00 +0000)
        3: chapter_98.mp3 (Fri, 19 Dec 2014 01:00:00 +0000)
    ...

If you want to download the ``chapter_99.mp3``, just type::

    $ marrie --get my_podcast 2

Where ``2`` is the numeric identifier of the wanted chapter.

After the download, you'll want to play the chapter. To play the latest
chapter fetched by ``marrie`` (that isn't exactly the latest chapter published
on the feed, it is actually the latest chapter that was downloaded to your
filesystem), just type::

    $ marrie --play my_podcast

To play a specific chapter (after download it, obviously), you'll need to list
the chapters available on your disk::

    $ marrie --list my_podcast
    Fetched files available for "nageral" (sorted by name):

        1: chapter_1.mp3
        2: chapter_2.mp3
        3: chapter_2.mp3
    ...

This is the same command used to list the available chapters to download. The
output will contains both lists.

If you want to play ``chapter_2.mp3``, just type::

    $ marrie --play my_podcast 2

Where ``2`` is the numeric identifier of the wanted chapter.

If you are bored with the absence of new chapters of your favorite podcast,
you can ask ``marrie`` to play a random old chapter for you. It will pick any
of the chapters that were previously fetched and will play for you::

    $ marrie --play-random my_podcast

That's it. This is pretty much everything that ``marrie`` can do for you!


Contributions
-------------

You can send patches to my email address:

rafael@rafaelmartins.eng.br .

Patches should be created against the Git repository:

https://github.com/rafaelmartins/marrie/

Any patch that heavily increases the complexity of the script will be rejected!


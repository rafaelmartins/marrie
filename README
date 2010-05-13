marrie
------

**marrie** is a simple podcast client that runs on the CLI (bash).


Command Line options
~~~~~~~~~~~~~~~~~~~~

--version      show program's version number and exit
-h, --help     show this help message and exit
--list         list all the feeds available
--list-files   list all the downloaded files available from podcast_id
--get-latest   fetch the latest chapter availeble from podcast_id
--play=FILE    play a given chapter from podcast_id
--play-latest  play a the latest chapter from podcast_id
--play-random  play a random chapter from podcast_id


Configuration
~~~~~~~~~~~~~

* Section config:

  - fetch_command: command used to download the podcast files, e.g. using wget.
  - player_command: command used to play the podcast files, e.g using mplayer.
  - media_dir: directory path where the podcast files will be saved, in sub
    directories with the podcast_id as the name of the sub directory.

* Section podcast:

  - syntax: podcast_id = url of the RSS feed

Please see the default config file (generated in the first run) for examples.

The config file will be found at **~/.marrie** and the config is only in a per-user
basis.

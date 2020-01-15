# -*- coding: utf-8 -*-

"""
    marrie
    ~~~~~~

    A simple podcast client that runs on the Command Line Interface.

    :copyright: (c) 2010-2013 by Rafael Goncalves Martins
    :license: BSD, see LICENSE for more details.
"""

__all__ = ['MarrieError', 'Config', 'Podcast', 'Cli', 'main']
__version__ = '0.4'

import argparse
import codecs
import feedparser
import json
import os
import posixpath
import random
import shutil
import subprocess
import sys
from collections import OrderedDict
from configparser import ConfigParser

config_file = '''\
[config]

# Fetch command to download the files.
#
# Examples:
#   wget --limit-rate=30k -c -O %(file)s %(url)s
#   curl --limit-rate 30K -C - -o %(file)s %(url)s
fetch_command = wget -c -O "%(file)s" "%(url)s"

# Player command to play the files
#
# Examples:
#   mpv %(file)s
#   mpg123 %(file)s
player_command = mpv %(file)s

# Media directory to store the files
media_dir = ~/podcasts

[podcast]

# List of feeds of your podcasts, in the format:
#   podcast_id = http://example.org/rss/feed.xml

'''


class MarrieError(Exception):
    pass


class Config(object):

    _raw_options = ('fetch_command', 'player_command')
    _options = ('media_dir',)
    _expanduser = ('media_dir',)

    def __init__(self, my_file):
        my_file = os.path.expanduser(my_file)
        if not os.path.exists(my_file):
            with codecs.open(my_file, 'w', encoding='utf-8') as fp:
                fp.write(config_file)
            raise MarrieError(
                'Missing config file: %s. It will be created for you.' % my_file)
        self._cp = ConfigParser()
        self._cp.read(my_file)
        for opt in (self._raw_options + self._options):
            if not self._cp.has_option('config', opt):
                raise MarrieError('Missing needed config option: config:%s' \
                                  % opt)

    def __getattr__(self, attr):
        opt = None
        if attr in self._raw_options:
            opt = self._cp.get('config', attr, raw=True)
        elif attr in self._options:
            opt = self._cp.get('config', attr)
        elif attr == 'podcast':
            opt = OrderedDict(self._cp.items('podcast'))
        if opt is None:
            raise AttributeError(attr)
        if attr in self._expanduser and not isinstance(opt, dict):
            return os.path.expanduser(opt)
        return opt


class Podcast(object):

    def __init__(self, config, pid):
        self.config = config
        if pid not in self.config.podcast:
            raise MarrieError('Invalid podcast ID: %s' % pid)
        self.pid = pid
        self.media_dir = os.path.join(self.config.media_dir, self.pid)
        if not os.path.exists(self.media_dir):
            os.makedirs(self.media_dir)
        self._cache_file = os.path.join(self.media_dir, '.cache')
        self._latest_file = os.path.join(self.media_dir, '.latest')

    ### Subprocess wrappers ###

    def _fetch(self, url):
        filepath = os.path.join(self.media_dir, posixpath.basename(url))
        part_file = filepath + '.part'
        rv = subprocess.call(self.config.fetch_command % \
                             dict(url=url, file=part_file), shell=True)
        if rv != os.EX_OK:
            raise MarrieError('Failed to download the file (%s): %i' % \
                              (url, rv))
        try:
            shutil.move(part_file, filepath)
        except Exception as err:
            raise MarrieError('Failed to save the file (%s): %s' % \
                              (filepath, str(err)))
        else:
            self.set_latest(filepath)

    def _play(self, filename):
        filepath = os.path.join(self.media_dir, os.path.basename(filename))
        rv = subprocess.call(self.config.player_command % dict(file=filepath),
                             shell=True)
        if rv != os.EX_OK:
            raise MarrieError('Failed to play the file (%s): %i' % \
                              (filepath, rv))

    ### Internal helpers ###

    def _load_cache(self):
        try:
            with codecs.open(self._cache_file, encoding='utf-8') as fp:
                return json.load(fp)
        except Exception as err:
            raise MarrieError('Failed to load cache (%s): %s' % \
                              (self._cache_file, str(err)))

    def _convert_oldstyle_latest(self):
        old_latest = os.path.join(self.media_dir, 'LATEST')
        if os.path.exists(old_latest):
            try:
                with codecs.open(old_latest, encoding='utf-8') as fp:
                    os.symlink(fp.read().strip(), self._latest_file)
            except Exception as err:
                raise MarrieError('Failed to convert old-style LATEST file ' \
                                  'to symlink: %s' % str(err))
            else:
                os.unlink(old_latest)

    ### Action helpers ###

    def list_chapters(self):
        if os.path.exists(self._cache_file):
            return self._load_cache()
        return []

    def list_fetched_chapters(self):
        chapters = os.listdir(self.media_dir)
        mylist = []
        for chapter in chapters:
            if chapter not in ('.cache', '.latest') and \
               not chapter.endswith('.part'):
                mylist.append(os.path.join(self.media_dir, chapter))
        return mylist

    def sync(self):
        self._convert_oldstyle_latest()
        purl = self.config.podcast[self.pid]
        try:
            rss = feedparser.parse(purl)
        except Exception as err:
            raise MarrieError('Failed to parse the feed (%s): %s' % \
                              (purl, str(err)))
        chapters = []
        for entry in rss.entries:
            published = entry.get('published')
            for link in entry.links:
                if link.rel == 'enclosure' and hasattr(link, 'type'):
                    category = link.type.split('/')[0]
                    if category in ('audio', 'video'):
                        chapters.append((link.href, published))
        try:
            with codecs.open(self._cache_file, 'w', encoding='utf-8') as fp:
                json.dump(chapters, fp)
        except Exception as err:
            raise MarrieError('Failed to save cache (%s): %s' % \
                              (self._cache_file, str(err)))

    def fetch(self, chapter_id):
        chapters = self.list_chapters()
        chapter_id = chapter_id - 1
        try:
            chapter = chapters[chapter_id]
            if not isinstance(chapter, str):
                chapter = chapter[0]
        except IndexError:
            raise MarrieError('Invalid chapter identifier.')
        else:
            self._fetch(chapter)

    def fetch_latest(self):
        chapters = self.list_chapters()
        if len(chapters) == 0:
            raise MarrieError('No chapters available.')
        chapter = chapters[0]
        if not isinstance(chapter, str):
            chapter = chapter[0]
        if os.path.exists(os.path.join(self.media_dir,
                                       posixpath.basename(chapter))):
            raise MarrieError('No newer podcast available.')
        self._fetch(chapter)

    def play(self, chapter_id):
        if isinstance(chapter_id, int):
            chapters = self.list_fetched_chapters()
            chapter_id = chapter_id - 1
            try:
                chapter = chapters[chapter_id]
            except IndexError:
                raise MarrieError('Invalid chapter identifier.')
        else:
            chapter = chapter_id
        self._play(chapter)

    def play_latest(self):
        self._play(self.get_latest())

    def play_random(self):
        chapters = self.list_fetched_chapters()
        if not len(chapters):
            raise MarrieError('No chapters available.')
        self.play(random.choice(chapters))

    def get_latest(self):
        if not os.path.exists(self._latest_file):
            raise MarrieError('No podcast file registered as latest.')
        latest_file = os.path.realpath(self._latest_file)
        if not os.path.exists(latest_file):
            raise MarrieError('Broken symlink: %s -> %s' % (self._latest_file,
                                                            latest_file))
        return latest_file

    def set_latest(self, url):
        try:
            if os.path.exists(self._latest_file):
                os.unlink(self._latest_file)
            os.symlink(posixpath.basename(url), self._latest_file)
        except Exception as err:
            raise MarrieError('Failed to create the .latest symlink: %s' % \
                              str(err))


class Cli(object):

    _required_pid = ('get', 'play', 'play_random')

    def __init__(self):
        self.parser = argparse.ArgumentParser(
            description=('A simple podcast client that runs on the Command '
                         'Line Interface.'))
        self.parser.add_argument('podcast_id', nargs='?', metavar='PODCAST_ID',
                                 help='podcast identifier, from the '
                                 'configuration file')
        self.parser.add_argument('chapter_id', nargs='?', metavar='CHAPTER_ID',
                                 help='chapter identifier, local for '
                                 '`--play\', remote for `--get\'. This '
                                 'identifier is variable and is available on '
                                 '`--list CHAPTER_ID\'', type=int)
        self.parser.add_argument('-v', '--version', action='version',
                                 version='%%(prog)s %s' % __version__)
        self.parser.add_argument('--config-file', metavar='FILE',
                                 dest='config_file', help='configuration file '
                                 'to be used. It will override the default '
                                 'file `~/.marrie\'')
        self.parser.add_argument('--all', action='store_true',
                                dest='all_podcasts',
                                help='with --get, download all configured '
                                'podcasts')
        self.group = self.parser.add_mutually_exclusive_group()
        self.group.add_argument('-s', '--sync', action='store_const',
                                dest='callback', const=self.cmd_sync,
                                help='syncronize the local cache of podcast '
                                'chapters available for download, for a given '
                                'PODCAST_ID, or for all available feeds')
        self.group.add_argument('-l', '--list', action='store_const',
                                dest='callback', const=self.cmd_list,
                                help='list all the feeds available or all the '
                                'chapters available for a given PODCAST_ID')
        self.group.add_argument('-g', '--get', action='store_const',
                                dest='callback', const=self.cmd_get,
                                help='fetch the latest chapter available for '
                                'a given PODCAST_ID, if no CHAPTER_ID is '
                                'provided')
        self.group.add_argument('-p', '--play', action='store_const',
                                dest='callback', const=self.cmd_play,
                                help='play the latest chapter fetched for '
                                'a given PODCAST_ID, if no CHAPTER_ID is '
                                'provided')
        self.group.add_argument('-r', '--play-random', action='store_const',
                                dest='callback', const=self.cmd_play_random,
                                help='play a random chapter from the fetched '
                                'for a given PODCAST_ID')

    def run(self):
        self.args = self.parser.parse_args()
        self.config = Config(self.args.config_file or '~/.marrie')
        callback = self.args.callback
        if callback is None:
            self.parser.print_help()
            return os.EX_USAGE
        if callback.__name__.lstrip('cmd_') in self._required_pid:
            if self.args.podcast_id is None and \
                    not self.args.all_podcasts:
                self.parser.error('one argument is required.')
        if self.args.podcast_id is not None:
            self.podcast = Podcast(self.config, self.args.podcast_id)
        return callback()

    ### Commands ###

    def cmd_sync(self):
        if self.args.podcast_id is not None:
            print('Syncronizing feed "%s".' % self.args.podcast_id)
            self.podcast.sync()
            return os.EX_OK
        for pid in self.config.podcast:
            print('Syncronizing feed "%s".' % pid)
            podcast = Podcast(self.config, pid)
            podcast.sync()

    def cmd_list(self):
        if self.args.podcast_id is None:
            print('Podcast feeds available:')
            print()
            for pid in self.config.podcast:
                print('    %s - %s' % (pid, self.config.podcast[pid]))
            print()
            return os.EX_OK
        else:
            print('Fetched files available for "%s" (sorted by name):'
                  % self.args.podcast_id)
            print()
            count = 1
            for filepath in self.podcast.list_fetched_chapters():
                print('    %i: %s' % (count, os.path.basename(filepath)))
                count += 1
            if count == 1:
                print('    **** No fetched files.')
            print()
            print('Remote files available for "%s" (reverse sorted by date):'
                  % self.args.podcast_id)
            print()
            count = 1
            for url in self.podcast.list_chapters():
                if isinstance(url, str):
                    print('    %i: %s' % (count, posixpath.basename(url)))
                else:
                    print('    %i: %s (%s)' % (count,
                                               posixpath.basename(url[0]),
                                               url[1]))
                count += 1
            if count == 1:
                print('    **** No remote files. Try running this script '
                      'with `--sync\'')
            print()

    def cmd_get(self):
        if self.args.all_podcasts:
            pids = self.config.podcast
        else:
            pids = [self.args.podcast_id]
        err = None
        for pid in pids:
            try:
                podcast = Podcast(self.config, pid)
                if self.args.chapter_id is None:
                    print('Fetching the latest chapter available for "%s"' % pid)
                    print()
                    podcast.fetch_latest()
                else:
                    print('Fetching chapter "%i" for "%s"' % (self.args.chapter_id, pid))
                    print()
                    podcast.fetch(self.args.chapter_id)
            except MarrieError as e:
                sys.stderr.write("%s\n" % str(e))
                err = e
        if err:
            sys.exit(1)

    def cmd_play(self):
        if self.args.chapter_id is None:
            print('Playing the latest chapter fetched for "%s"' %
                  self.args.podcast_id)
            print()
            self.podcast.play_latest()
            return os.EX_OK
        print('Playing chapter "%i" for "%s"' % (self.args.chapter_id,
                                                 self.args.podcast_id))
        print()
        self.podcast.play(self.args.chapter_id)

    def cmd_play_random(self):
        print('Playing a random chapter available for "%s"' %
              self.args.podcast_id)
        print()
        self.podcast.play_random()


def main():
    cli = Cli()
    try:
        return cli.run()
    except KeyboardInterrupt:
        print('Interrupted', file=sys.stderr)
    except MarrieError as err:
        print('error: %s' % err, file=sys.stderr)
    return 1

if __name__ == '__main__':
    sys.exit(main())

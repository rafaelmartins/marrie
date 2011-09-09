# -*- coding: utf-8 -*-

"""
    marrie
    ~~~~~~

    marrie is a simple podcast client that runs on the CLI (bash).

    :copyright: (c) 2010-2011 by Rafael Goncalves Martins
    :license: BSD, see LICENSE for more details.
"""

__all__ = ['Config', 'Podcast', 'Cli', 'main']

__author__ = 'Rafael Goncalves Martins'
__email__ = 'rafael@rafaelmartins.eng.br'

__description__ = 'A simple podcast client that runs on the CLI.'
__url__ = 'http://rafaelmartins.eng.br/en-us/projects/marrie/'
__copyright__ = '(c) 2010 %s <%s>' % (__author__, __email__)
__license__ = 'BSD'

__version__ = '0.2.1+'

import argparse
import codecs
import json
import os
import posixpath
import random
import shutil
import subprocess
import sys
import urllib2
from collections import OrderedDict
from ConfigParser import ConfigParser
from contextlib import closing
from xml.dom.minidom import parse as parseXML

config_file = '''\
[config]

# Fetch command to download the files.
#
# Examples:
#   wget --limit-rate=30k -c -O %(file)s %(url)s
#   curl --limit-rate 30K -C - -o %(file)s %(url)s
fetch_command = wget -c -O %(file)s %(url)s

# Player command to play the files
#
# Examples:
#   mplayer %(file)s
#   mpg123 %(file)s
player_command = mplayer %(file)s

# Media directory to store the files
media_dir = ~/podcasts

[podcast]

# List of RSS feeds of your podcasts, in the format:
#   podcast_id = http://url.to/the/rss/feed.xml

'''


class Config(object):

    _raw_options = ('fetch_command', 'player_command')
    _options = ('media_dir',)
    _expanduser = ('media_dir',)

    def __init__(self, my_file):
        my_file = os.path.expanduser(my_file)
        if not os.path.exists(my_file):
            with codecs.open(my_file, 'w', encoding='utf-8') as fp:
                fp.write(config_file)
            raise RuntimeError(
                'Missing config file: %s. Will be created for you.' % my_file)
        self._cp = ConfigParser()
        self._cp.read(my_file)
        for opt in (self._raw_options + self._options):
            if not self._cp.has_option('config', opt):
                raise RuntimeError('Missing needed config option: config:%s' \
                                   % opt)

    def __getattr__(self, attr):
        opt = None
        if attr in self._raw_options:
            opt = self._cp.get('config', attr, True)
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
            raise RuntimeError('Invalid podcast ID: %s' % pid)
        self.pid = pid
        self.media_dir = os.path.join(self.config.media_dir, self.pid)
        if not os.path.exists(self.media_dir):
            os.makedirs(self.media_dir)
        self._cache_file = os.path.join(self.media_dir, '.cache')
        self._latest_file = os.path.join(self.media_dir, '.latest')

    def fetch(self, url):
        filepath = os.path.join(self.media_dir, posixpath.basename(url))
        part_file = filepath + '.part'
        rv = subprocess.call(self.config.fetch_command % \
                             dict(url=url, file=part_file), shell=True)
        if rv != os.EX_OK:
            raise RuntimeError('Failed to download the file (%s): %i' % \
                               (url, rv))
        try:
            shutil.move(part_file, filepath)
        except Exception, err:
            raise RuntimeError('Failed to save the file (%s): %s' % \
                               (filepath, str(err)))
        else:
            self.podcast.set_latest(filepath)

    def play(self, filename):
        filepath = os.path.join(self.media_dir, os.path.basename(filename))
        rv = subprocess.call(self.config.player_command % dict(file=filepath),
                             shell=True)
        if rv != os.EX_OK:
            raise RuntimeError('Failed to play the file (%s): %i' % \
                               (filepath, rv))

    def sync(self):
        self._convert_oldstyle_latest()
        purl = self.config.podcast[self.pid]
        try:
            with closing(urllib2.urlopen(purl)) as fp:
                rss = parseXML(fp)
        except Exception, err:
            raise RuntimeError('Failed to parse the feed (%s): %s' % \
                               (purl, str(err)))
        enclosure = rss.getElementsByTagName('enclosure')
        chapters = []
        for chapter in enclosure:
            if chapter.getAttribute('type').startswith('audio/'):
                url = chapter.getAttribute('url')
                chapters.append(url.strip())
        try:
            with codecs.open(self._cache_file, 'w', encoding='utf-8') as fp:
                json.dump(chapters, fp)
        except Exception, err:
            raise RuntimeError('Failed to save cache (%s): %s' % \
                               (self._cache_file, str(err)))

    def _load_cache(self):
        try:
            with codecs.open(self._cache_file, encoding='utf-8') as fp:
                return json.load(fp)
        except Exception, err:
            raise RuntimeError('Failed to load cache (%s): %s' % \
                               (self._cache_file, str(err)))

    def _convert_oldstyle_latest(self):
        old_latest = os.path.join(self.media_dir, 'LATEST')
        if os.path.exists(old_latest):
            try:
                with codecs.open(old_latest, encoding='utf-8') as fp:
                    os.symlink(fp.read().strip(), self._latest_file)
            except Exception, err:
                raise RuntimeError('Failed to convert old-style LATEST file ' \
                                   'to symlink: %s' % str(err))
            else:
                os.unlink(old_latest)

    def list_chapters(self):
        if os.path.exists(self._cache_file):
            return self._load_cache()
        return []

    def fetch_latest(self):
        chapters = self.list_chapters()
        if len(chapters) == 0:
            raise RuntimeError('No chapters available.')
        if os.path.exists(os.path.join(self.media_dir,
                                       posixpath.basename(chapters[0]))):
            raise RuntimeError('No newer podcast available.')
        self.fetch(chapters[0])

    def play_latest(self):
        self.play(self.get_latest())

    def play_random(self):
        chapters = list(self.list_fetched_chapters())
        if not len(chapters):
            raise RuntimeError('No chapters available.')
        self.play(random.choice(chapters))

    def get_latest(self):
        if not os.path.exists(self._latest_file):
            raise RuntimeError('No podcast file registered as latest.')
        latest_file = os.path.realpath(self._latest_file)
        if not os.path.exists(latest_file):
            raise RuntimeError('Broken symlink: %s -> %s' % (self._latest_file,
                                                             latest_file))
        return latest_file

    def set_latest(self, url):
        try:
            os.symlink(posixpath.basename(url), self._latest_file)
        except Exception, err:
            raise RuntimeError('Failed to create the .latest symlink: %s' % \
                               str(err))

    def list_fetched_chapters(self):
        chapters = os.listdir(self.media_dir)
        if len(chapters) == 0:
            raise RuntimeError('No chapter available!')
        for chapter in chapters:
            if chapter not in ('.cache', '.latest') and \
               not chapter.endswith('.part'):
                yield os.path.join(self.media_dir, chapter)


class Cli(object):

    _required_id = ('get_latest', 'play_latest', 'play_random')

    def __init__(self):
        self.parser = argparse.ArgumentParser(description=__description__)
        self.parser.add_argument('podcast_id', nargs='?', metavar='PODCAST_ID',
                                 help='podcast identifier, from the '
                                 'configuration file')
        self.parser.add_argument('-c', '--config-file', metavar='FILE',
                                 dest='config_file', help='configuration file '
                                 'to be used. It will override the default '
                                 'file `~/.marrie\'')
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
        self.group.add_argument('--get-latest', action='store_const',
                                dest='callback', const=self.cmd_get_latest,
                                help='fetch the latest chapter available for '
                                'a given PODCAST_ID')
        self.group.add_argument('--play-latest', action='store_const',
                                dest='callback', const=self.cmd_play_latest,
                                help='play the latest chapter fetched for '
                                'a given PODCAST_ID')
        self.group.add_argument('--play-random', action='store_const',
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
        if callback.__name__.lstrip('cmd_') in self._required_id:
            if self.args.podcast_id is None:
                self.parser.error('one argument is required.')
        if self.args.podcast_id is not None:
            self.podcast = Podcast(self.config, self.args.podcast_id)
        return callback()

    ### Commands ###

    def cmd_sync(self):
        if self.args.podcast_id is not None:
            print 'Syncronizing feed "%s".' % self.args.podcast_id
            self.podcast.sync()
            return os.EX_OK
        for pid in self.config.podcast:
            print 'Syncronizing feed "%s".' % pid
            podcast = Podcast(self.config, pid)
            podcast.sync()

    def cmd_list(self):
        if self.args.podcast_id is None:
            print 'Available feeds:'
            print
            for pid in self.config.podcast:
                print '    %s - %s' % (pid, self.config.podcast[pid])
            print
            return os.EX_OK
        else:
            print 'Available fetched files for "%s" (sorted by name):' \
                  % self.args.podcast_id
            print
            count = 1
            for filepath in self.podcast.list_fetched_chapters():
                print '    %i: %s' % (count, os.path.basename(filepath))
                count += 1
            if count == 1:
                print '    **** No fetched files.'
            print
            print 'Available remote files for "%s" (reverse sorted by date):' \
                  % self.args.podcast_id
            print
            count = 1
            for url in self.podcast.list_chapters():
                print '    %i: %s' % (count, posixpath.basename(url))
                count += 1
            if count == 1:
                print '    **** No remote files. Try running this script ' \
                      'with `--sync\''
            print

    def cmd_get_latest(self):
        print 'Fetching the latest chapter available for "%s"' % \
              self.args.podcast_id
        print
        self.podcast.fetch_latest()

    def cmd_play_latest(self):
        print 'Playing the latest chapter fetched for "%s"' % \
              self.args.podcast_id
        print
        self.podcast.play_latest()

    def cmd_play_random(self):
        print 'Playing a random chapter available for "%s"' % \
              self.args.podcast_id
        print
        self.podcast.play_random()


def main():
    cli = Cli()
    try:
        return cli.run()
    except KeyboardInterrupt:
        print >> sys.stderr, 'Interrupted'
        return 1
    except RuntimeError, err:
        cli.parser.error('%s' % err)
    except Exception, err:
        cli.parser.error('Unknown error - %s' % err)

if __name__ == '__main__':
    sys.exit(main())

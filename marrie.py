# -*- coding: utf-8 -*-

"""
    marrie
    ~~~~~~

    marrie is a simple podcast client that runs on the CLI (bash).

    :copyright: (c) 2010-2011 by Rafael Goncalves Martins
    :license: BSD, see LICENSE for more details.
"""

__all__ = ['Config', 'Podcast', 'main']

__author__ = 'Rafael Goncalves Martins'
__email__ = 'rafael@rafaelmartins.eng.br'

__description__ = 'A simple podcast client that runs on the CLI.'
__url__ = 'http://rafaelmartins.eng.br/en-us/projects/marrie/'
__copyright__ = '(c) 2010 %s <%s>' % (__author__, __email__)
__license__ = 'BSD'

__version__ = '0.2.1+'

import codecs
import json
import optparse
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
            raise RuntimeError('Invalid podcast ID: %s' % id)
        self.pid = pid
        self.media_dir = os.path.join(self.config.media_dir, self.pid)
        if not os.path.exists(self.media_dir):
            os.makedirs(self.media_dir)
        self._cache_file = os.path.join(self.media_dir, '.cache')
        self._latest_file = os.path.join(self.media_dir, '.latest')

    def _downloader(self, url, filepath):
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

    def _player(self, filepath):
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
        else:
            raise RuntimeError('Cache not found, please run this script ' \
                               'with `--sync` option before try to list ' \
                               'chapters.')

    def latest_available(self):
        chapters = self.list_chapters()
        if len(chapters) == 0:
            raise RuntimeError('No chapters available.')
        filepath = posixpath.basename(chapters[0])
        if os.path.exists(filepath):
            raise RuntimeError('No newer podcast available.')
        return chapters[0], os.path.join(self.media_dir, filepath)

    def get_latest(self):
        if not os.path.exists(self._latest_file):
            raise RuntimeError('No podcast file registered as latest.')
        latest_file = os.path.realpath(self._latest_file)
        if not os.path.exists(latest_file):
            raise RuntimeError('Broken symlink: %s -> %s' % (self._latest_file,
                                                             latest_file))
        return latest_file

    def set_latest(self, filename):
        try:
            os.symlink(os.path.basename(filename), self._latest_file)
        except Exception, err:
            raise RuntimeError('Failed to create the .latest symlink: %s' % \
                               str(err))

    def list_fetched(self):
        chapters = os.listdir(self.media_dir)
        if len(chapters) == 0:
            raise RuntimeError('No chapter available!')
        for chapter in chapters:
            if chapter not in ('.cache', '.latest') and \
               not chapter.endswith('.part'):
                yield os.path.join(self.media_dir, chapter)


def main():
    parser = optparse.OptionParser(
        usage = '%prog [options] <podcast_id>',
        version = '%prog ' + __version__,
        description = __description__
    )
    parser.add_option(
        '--list',
        action = 'store_true',
        dest = 'list',
        default = False,
        help = 'list all the feeds available'
    )
    parser.add_option(
        '--list-files',
        action = 'store_true',
        dest = 'list_files',
        default = False,
        help = 'list all the downloaded files available from podcast_id'
    )
    parser.add_option(
        '--get-latest',
        action = 'store_true',
        dest = 'get',
        default = False,
        help = 'fetch the latest chapter availeble from podcast_id'
    )
    parser.add_option(
        '--play',
        action = 'store',
        type = 'string',
        metavar = 'FILE',
        dest = 'play',
        default = None,
        help = 'play a given chapter from podcast_id'
    )
    parser.add_option(
        '--play-latest',
        action = 'store_true',
        dest = 'play_latest',
        default = False,
        help = 'play a the latest chapter from podcast_id'
    )
    parser.add_option(
        '--play-random',
        action = 'store_true',
        dest = 'play_random',
        default = False,
        help = 'play a random chapter from podcast_id'
    )
    parser.add_option(
        '--sync',
        action = 'store_true',
        dest = 'sync',
        default = False,
        help = 'synchronize podcast feeds'
    )
    options, args = parser.parse_args()
    try:
        config = Config('~/.marrie')
        if options.list:
            print 'Available feeds:'
            print
            for id in config.podcast:
                print '    %s - %s' % (id, config.podcast[id])
            return 0
        if len(args) != 1:
            parser.error('One argument is required!')
        podcast_id = args[0]
        podcast = Podcast(config, podcast_id)
        if options.sync:
            print 'Synchronizing feed for %s' % podcast_id
            podcast.sync()
            return 0
        if options.list_files:
            print 'Available chapters for %s' % podcast_id
            print
            for filepath in podcast.list_fetched():
                print '    %s' % os.path.basename(filepath)
            return 0
        if options.get:
            rv = podcast.latest_available()
            if rv is not None:
                url, filepath = rv
            print 'Downloading: %s' % url
            print 'Saving to: %s' % filepath
            print
            podcast._downloader(url, filepath)
            podcast.set_latest(os.path.basename(filepath))
            return 0
        if options.play is not None:
            filepath = os.path.join(podcast.media_dir, options.play)
        elif options.play_latest:
            filepath = podcast.get_latest()
        elif options.play_random:
            filepath = random.choice(podcast.list_fetched())
        if not os.path.exists(filepath):
            parser.error('File not found - %s' % filepath)
        print 'Playing: %s' % filepath
        print
        podcast._player(filepath)
        return 0
    except KeyboardInterrupt:
        print >> sys.stderr, 'Interrupted'
        return 1
    except RuntimeError, err:
        print >> sys.stderr, 'marrie error - %s' % err
        return 1
    except Exception, err:
        print >> sys.stderr, 'Unknown error - %s' % err
        return 1
    return 0

if __name__ == '__main__':
    sys.exit(main())

# -*- coding: utf-8 -*-

"""
    marrie
    ~~~~~~
    
    marrie is a simple podcast client that runs on the CLI (bash).
    
    :copyright: (c) 2010 by Rafael Goncalves Martins
    :license: BSD, see LICENSE for more details.
"""

__all__ = ['Config', 'Client', 'Marrie', 'main']

__author__ = 'Rafael Goncalves Martins'
__email__ = 'rafael@rafaelmartins.eng.br'

__description__ = 'A simple podcast client that runs on the CLI.'
__url__ = 'http://rafaelmartins.eng.br/en-us/projects/marrie/'
__copyright__ = '(c) 2010 %s <%s>' % (__author__, __email__)
__license__ = 'BSD'

__version__ = '0.2'

import optparse
import os
import random
import shutil
import subprocess
import sys
import urllib2
from ConfigParser import ConfigParser
from xml.dom.minidom import parse as parseXML

config_file = '''\
[config]

# Fetch command to download the files.
#
# Examples:
#   wget --limit-rate=30k -c -O %(file)s %(url)s
fetch_command = wget --limit-rate=30k -c -O %(file)s %(url)s

# Player command to play the files
#
# Examples:
#   mplayer %(file)s
#   mpg123 %(file)s
player_command = mplayer %(file)s

# Media directory to store the files
media_dir = /multimedia/podcasts

[podcast]

# List of RSS feeds of your podcasts, in the format:
#   podcast_id = http://url.to/the/rss/feed

'''

class Config(object):
    
    _raw_options = ('fetch_command', 'player_command')
    _options = ('media_dir', )
    
    def __init__(self, my_file):
        my_file = os.path.expanduser(my_file)
        if not os.path.exists(my_file):
            with open(my_file, 'w') as fp:
                fp.write(config_file)
            raise RuntimeError(
                'Missing config file: %s. ' % my_file +
                'The file will be created for you.'
            )
        config = ConfigParser()
        config.read(my_file)
        for opt in (self._raw_options + self._options):
            if not config.has_option('config', opt):
                raise RuntimeError(
                    'Missing needed config option: config:%s' % opt
                )
        for opt in self._raw_options:
            setattr(self, opt, config.get('config', opt, True))
        for opt in self._options:
            setattr(self, opt, config.get('config', opt))
        self.podcast = {}
        for id, url in config.items('podcast'):
            self.podcast[id] = url


class Client:
    
    def __init__(self, config):
        self.fetch_command = config.fetch_command
        self.player_command = config.player_command
    
    def fetch(self, url, filepath):
        return_code = subprocess.call(self.fetch_command % dict(
            url = url,
            file = filepath + '.part'
        ), shell = True)
        if return_code != 0:
            raise RuntimeException('Failed to save the file: %s' % filepath)
        shutil.move(filepath + '.part', filepath)

    def player(self, filepath):
        return_code = subprocess.call(self.player_command % dict(
            file = filepath
        ), shell = True)
        if return_code != 0:
            raise RuntimeException('Failed to play the file: %s' % filepath)


class Marrie:
    
    def __init__(self, config, id):
        self.podcast = config.podcast
        self.id = id
        self.media_dir = os.path.join(config.media_dir, self.id)
        if not os.path.exists(self.media_dir):
            os.makedirs(self.media_dir)

    def list_chapters(self):
        url = self.podcast[self.id]
        try:
            fp = urllib2.urlopen(url)
            rss = parseXML(fp)
            fp.close()
        except:
            raise RuntimeError('Failed to parse the RSS feed: %s' % url)
        enclosure = rss.getElementsByTagName('enclosure')
        chapters = []
        for chapter in enclosure:
            if chapter.getAttribute('type').startswith('audio/'):
                url = chapter.getAttribute('url')
                chapters.append((
                    url.strip(),
                    os.path.join(self.media_dir, url.split('/')[-1])
                ))
        return chapters
    
    def latest_available(self):
        chapters = self.list_chapters()
        url, filepath = chapters[0]
        if os.path.exists(filepath):
            raise RuntimeError('No newer podcast available.')
        return url, filepath

    def get_latest(self):
        latest_file = os.path.join(self.media_dir, 'LATEST')
        if not os.path.exists(latest_file):
            raise RuntimeError('No chapter available to play.')
        with open(latest_file) as fp:
            latest = fp.read().strip()
        return os.path.join(self.media_dir, latest)

    def set_latest(self, filename):
        with open(os.path.join(self.media_dir, 'LATEST'), 'w') as fp:
            fp.write(filename)

    def list_fetched(self):
        chapters = os.listdir(self.media_dir)
        if len(chapters) == 0:
            raise RuntimeError('No chapter available!')
        f_chapters = []
        for chapter in chapters:
            if chapter != 'LATEST' and not chapter.endswith('.part'):
                f_chapters.append(os.path.join(self.media_dir, chapter))
        return f_chapters


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
        marrie = Marrie(config, podcast_id)
        if options.list_files:
            list_fetched = marrie.list_fetched()
            list_fetched.sort()
            print 'Available chapters for %s' % podcast_id
            print
            for filepath in list_fetched:
                print '    %s' % os.path.basename(filepath)
            return 0
        client = Client(config)
        if options.get:
            url, filepath = marrie.latest_available()
            print 'Downloading: %s' % url
            print 'Saving to: %s' % filepath
            print
            client.fetch(url, filepath)
            marrie.set_latest(os.path.basename(filepath))
            return 0
        if options.play is not None:
            filepath = os.path.join(marrie.media_dir, options.play)
        elif options.play_latest:
            filepath = marrie.get_latest()
        elif options.play_random:
            list_fetched = marrie.list_fetched()
            filepath = random.choice(list_fetched)
        if not os.path.exists(filepath):
            parser.error('File not found - %s' % filepath)
        print 'Playing: %s' % filepath
        print
        client.player(filepath)
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

#!/usr/bin/env python
""" Gleefully stolen and modified from https://github.com/seporaitis/yum-s3-iam/blob/master/s3iam.py
    This module enables yum to use s3 bucket repositories, sourcing credentials via boto3
"""

import os
import re
import logging

import boto3
import yum
import yum.config
import yum.Errors
import yum.plugins

from yum.yumRepo import YumRepository

__author__ = "Brian Auron"
__email__ = "briauron@gmail.com"
__copyright__ = "N/A"
__license__ = "Apache 2.0"
__version__ = "2.0.0"


__all__ = ['requires_api_version', 'plugin_type', 'CONDUIT',
           'config_hook', 'prereposetup_hook']

requires_api_version = '2.5'  # pylint: disable=invalid-name
plugin_type = yum.plugins.TYPE_CORE  # pylint: disable=invalid-name
CONDUIT = None
DEFAULT_DELAY = 3
DEFAULT_BACKOFF = 2
BUFFER_SIZE = 1024 * 1024
OPTIONAL_ATTRIBUTES = ['priority', 'base_persistdir', 'metadata_expire',
                       'skip_if_unavailable', 'keepcache', 'priority']
UNSUPPORTED_ATTRIBUTES = ['mirrorlist']

LOGGER = logging.getLogger(__name__)
LOGGER.addHandler(logging.StreamHandler())
LOGGER.setLevel(logging.WARNING)


def init_hook(conduit):
    """ Update yum command line arguments to allow specifying AWS profile
    """
    parser = conduit.getOptParser()
    parser.add_option('--profile',
                      help='AWS credentials profile to use for authentication to S3 yum repos',
                      default='default')

def config_hook(conduit):  # pylint: disable=unused-argument
    """ Yum config hook; invoked by yum when loading plugin from config
    """
    yum.config.RepoConf.s3_enabled = yum.config.BoolOption(False)
    yum.config.RepoConf.region = yum.config.Option()
    yum.config.RepoConf.profile = yum.config.Option()
    yum.config.RepoConf.baseurl = yum.config.UrlListOption(
        schemes=('http', 'https', 's3', 'ftp', 'file')
    )
    yum.config.RepoConf.backoff = yum.config.Option()
    yum.config.RepoConf.delay = yum.config.Option()

def replace_repo(repos, repo):
    """ Replace ordinary yum repos with S3-based repos, below
    """
    LOGGER.info('Replacing repo (%s) with S3Repository!', repo.name)
    repos.delete(repo.id)
    repos.add(S3Repository(repo.id, repo))
    LOGGER.info('Replaced repo (%s) with S3Repository!', repo.name)

def prereposetup_hook(conduit):
    """ Plugin init hook. Setup the S3 repos.
    """
    if 'DISABLE_YUM_S3' in os.environ and os.environ['DISABLE_YUM_S3']:
        return
    opts, _ = conduit.getCmdLine()
    repos = conduit.getRepos()
    for repo in repos.listEnabled():
        repo.profile = repo.profile or opts.profile
        url = repo.baseurl
        if isinstance(url, list):
            if not url:
                continue
            url = url[0]
        if re.match(r'^s3://', url):
            repo.s3_enabled = 1
        if isinstance(repo, YumRepository) and repo.s3_enabled:
            replace_repo(repos, repo)


class S3Repository(YumRepository):  # pylint: disable=too-many-instance-attributes
    """Repository object for Amazon S3, using IAM Roles."""

    def __init__(self, repoid, repo):
        super(S3Repository, self).__init__(repoid)

        self.name = repo.name
        self.region = repo.region if repo.region else 'us-west-2'
        self.basecachedir = repo.basecachedir
        self.gpgcheck = repo.gpgcheck
        self.gpgkey = repo.gpgkey
        self.profile = repo.profile or 'default'
        baseurl = repo.baseurl[0].rstrip('/')
        self.bucket = baseurl.split('/')[-2]
        self.bucket = self.bucket.split('.')[0]
        self.arch = baseurl.split('/')[-1]  # Yum requires the arch to be part of the baseurl but won't attach it to
                                            # the files it downloads
        self.baseurl = 'https://%s.s3.amazonaws.com' % self.bucket
        self.enablegroups = repo.enablegroups

        self.retries = repo.retries
        self.backoff = repo.backoff
        self.delay = repo.delay

        for attr in OPTIONAL_ATTRIBUTES:
            if hasattr(repo, attr):
                setattr(self, attr, getattr(repo, attr))

        for attr in UNSUPPORTED_ATTRIBUTES:
            if getattr(repo, attr):
                msg = "%s: Unsupported attribute: %s." % (__file__, attr)
                raise yum.plugins.PluginYumExit(msg)

        self.iamrole = None
        self.grabber = None
        self.enable()
        LOGGER.info('Initialized S3Repository! Will use profile "%s" against bucket "%s"', self.profile, self.bucket)

    @property
    def grabfunc(self):
        """ Placeholder from old code?
        """
        raise NotImplementedError("grabfunc called, when it shouldn't be!")

    @property
    def grab(self):
        """ Invoked by yum to download files
        """
        if not self.grabber:
            self.grabber = S3Grabber(self)
        return self.grabber


class S3Grabber(object):  # pylint: disable=too-many-instance-attributes
    """ Grab packages from s3
    """

    def __init__(self, repo):
        """Initialize file grabber.
            Note: currently supports only single repository. So in case of a list
                  only the first item will be used.
        """
        self.id = repo.id  # pylint: disable=invalid-name
        self.region = repo.region
        self.retries = repo.retries
        self.backoff = DEFAULT_BACKOFF if repo.backoff is None else repo.backoff
        self.delay = DEFAULT_DELAY if repo.delay is None else repo.delay
        self.bucket = repo.bucket
        self.profile = repo.profile or 'default'
        self.arch = repo.arch
        self.client = boto3.Session(profile_name=self.profile).client('s3')
        LOGGER.info('Initialized S3Grabber! Will use profile "%s" against bucket "%s"', self.profile, self.bucket)

    def urlgrab(self, path, filename=None, **kwargs):  # pylint: disable=unused-argument
        """urlgrab(url) copy the file to the local filesystem."""
        key = "%s/%s" % (self.arch, path.split(self.bucket)[-1])
        LOGGER.info('Calling boto3.Session().client("s3").download_file(%s, %s, %s)', self.bucket, key, filename)
        self.client.download_file(self.bucket, key, filename)
        return filename

    def urlopen(self, path, **kwargs):  # pylint: disable=unused-argument
        """urlopen(url) open the remote file and return a file object."""
        key = "%s/%s" % (self.arch, path.split(self.bucket)[-1])
        LOGGER.info('Calling boto3.Session().client("s3").get_object(Bucket=%s, Key=%s)', self.bucket, key)
        return self.client.get_object(Bucket=self.bucket, Key=key)['Body']

    def urlread(self, path, limit=None, **kwargs):  # pylint: disable=unused-argument
        """urlread(url) return the contents of the file as a string."""
        key = "%s/%s" % (self.arch, path.split('/', 1)[-1])
        return self.client.get_object(Bucket=self.bucket, Key=key)['Body'].read().encode('utf-8')

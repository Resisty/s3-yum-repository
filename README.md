---

# What

This repository is essentially a fork of [seporaitis/yum-s3-iam](https://github.com/seporaitis/yum-s3-iam) but won't be
submitted as a feature request because of the hard requirement on [boto3](https://pypi.org/project/boto3/) being installed.

It defines a CentOS 7 Docker image which augments its yum installation in the following ways:

1. Adds the ability to specify the HTTPS address of an S3 bucket as a repository source
1. Adds the ability (and only this ability) to authenticate to the S3 buckets via [AWS cli profiles.](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-profiles.html)
1. Adds a yum command line option to specify the profile instead of 'hardcoding' it into the yum config under /etc/yum.repos.d

# Notes

As of this writing, only python2 is supported because of how yum works.

# Examples

## Yum Config

See `s3.conf`

## Repository Config

See `s3.repo`

## Command line

```
yum --profile=${profile_name} list available
```

or

```
docker run -it -v $HOME/.aws:/root/.aws ${image_name} -c 'yum --profile=${profile_name} list available'
```

## Coming Soon

A pyproject.toml to allow for direct installation (hopefully)

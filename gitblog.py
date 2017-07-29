# -*- coding: utf-8 -*-
# gitblog.py
"""
This Python program handles HTTP requests when it is loaded by mod_python and
returns different types of output formats like HTML or markdown from a git repository.
The program can be used to deliver multiple sites from different repository sources.
The source repository is set by the Apache option "PythonOption gitblog.www_repo <path to git repo>".
Markdown is the excepted format of files commited into the repository. The Markdown
syntax can be converted to several output formats.

Copyright (c) 2013, 2014, 2017 Armin Pech <gitblog.py (at) arminpech (dot) de>, Duesseldorf, Germany.

Request for different output formats:
/about/me            -- Default output is HTML
/about/me?html       -- Return HTML output
/about/me?markdown   -- Return markdown syntax from file
/about/me?md         -- Return markdown syntax from file
/about/imprint?acsii -- Plain, syntax-free output
/about/imprint?plain -- Plain, syntax-free output

Request content in a particular version:
/about/me               -- Default git reference is HEAD
/about/me?ref=<git_ref> -- Return content in specific version
/about/me?ref=HEAD~10   -- Return content in specific version
/about/me?ref=7431a3ca6 -- Return content in specific version

# TODO: Diff support
Request unified diff for a content:
/about/me?diff=<commit>[:HEAD] -- Return diff of a resource between commit and HEAD
/about/imprint?diff=<commit1>:<commit2> -- Return diff of a resource between two defined commits

TODO
* return 404er if commit not found
* get last modified information from commit of requested path not of current commit
* print last commit of current path in footer
* special index page / homepage
"""

### Import required modules
# Handle HTTP requests via mod_python
from mod_python import apache
# Read python error
import sys
# Normalize symlink pathnames for git tree
from os.path import normpath
# Regular Expression manipulation of contents with placeholders
import re
# Read content from git repository
import git
# Date formatting
from datetime import datetime
# Output formatting
from markdown2 import markdown
from BeautifulSoup import BeautifulSoup

# Available output text encodings (request parameter key => output format)
available_output_type = {   'html':     'html',
                            'ascii':    'plain',
                            'plain':    'plain',
                            'markdown': 'markdown',
                            'md':       'markdown',
                        }

### Handle HTTP requests
def handler(req):
    # Set PythonOption configurations
    config = {
     'gitblog.report_errors': 'False',
     'gitblog.www_repo': '/dev/null',
     'gitblog.default_ref': 'HEAD',
     'gitblog.default_output_type': 'html',
     'gitblog.footer': 'True',
     'gitblog.date_format': '%Y-%m-%d %H:%M',
     'gitblog.markdown2_extras': 'toc',
     'gitblog.max_age_blob': '1800',
     'gitblog.max_age_tree': '600',
     'gitblog.denied_path': 'private,templates',
     'gitblog.redirect_code': 'HTTP_MOVED_PERMANENTLY',
    }

    for k in config.keys():
        if k in req.get_options().keys() and \
          not req.get_options()[k] is None and \
          not req.get_options()[k] == '':
            config[k] = req.get_options()[k]

    for c in ['report_errors',
              'footer']:
        if config['gitblog.' + c] == 'True':
            config['gitblog.' + c] = True
        else:
            config['gitblog.' + c] = False

    for c in ['markdown2_extras',
              'denied_path']:
        config['gitblog.' + c] = config['gitblog.' + c].split(',')

    for c in ['max_age_blob',
              'max_age_tree']:
        config['gitblog.' + c] = int(config['gitblog.' + c])

    if not config['gitblog.redirect_code'] in [ \
      'HTTP_MOVED_PERMANENTLY',
      'HTTP_MOVED_TEMPORARILY',
      'HTTP_TEMPORARY_REDIRECT']:
        config['gitblog.redirect_code'] = 'HTTP_MOVED_PERMANENTLY'

    # Get request path as list
    requested_path = req.uri.strip('/').split('/')
    requested_path = list(filter(None, requested_path))

    # Get request parameter as list
    args = {}
    if not req.args is None and len(req.args) > 0:
        _args = req.args.split('&')
        if len(_args) > 0:
            for a in _args:
                t = a.split('=')
                t[0] = ''.join(filter(str.isalnum, t[0]))
                try:
                    t[1] = ''.join(filter(str.isalnum, t[1]))
                except:
                    # Parameter has no value
                    pass
                if len(t) > 1:
                    args[t[0]] = t[1]
                else:
                    args[t[0]] = None
        del(_args, t)

    # Set generation options
    output_type = config['gitblog.default_output_type']
    for o in available_output_type:
        if o in args:
            output_type = available_output_type[o]
            break

    # Set Git commit
    git_ref = config['gitblog.default_ref']
    if 'ref' in args.keys():
        git_ref = args['ref'][0:39]

    # Read data from repo
    repo = git.Repo(config['gitblog.www_repo'], odbt=git.GitDB)

    # Get requested commit
    try:
        git_obj = repo.commit(git_ref)
    except:
        return(apache.HTTP_NOT_FOUND)

    # Read object and get content
    try:
        if len(requested_path) > 0:
            requested_object = git_obj.tree['/'.join(requested_path)]
        else:
            requested_object = git_obj.tree

        # Resolve symlink
        while requested_object.type == 'blob' and requested_object.mode == requested_object.link_mode:
            try:
                link_requested_path = normpath('/'.join(requested_path[:-1]) + '/' + \
                                      requested_object.data_stream.read().decode('utf-8'))
                requested_path = link_requested_path.strip('/').split('/')
                requested_path = list(filter(None, requested_path))

                redirect_target = '/'.join(requested_path)
                # TODO: Moved protocol values for verfication
                #       to program parameters
                if not redirect_target[0:7] == 'http://' and \
                   not redirect_target[0:8] == 'https://':
                    redirect_target = '/' + redirect_target

                req.headers_out.add('Location', redirect_target)
                return(getattr(apache, config['gitblog.redirect_code']))
            except:
                return(apache.HTTP_NOT_FOUND)

        # Check if resource should NOT be delivered
        for p in config['gitblog.denied_path']:
            if p.strip('/') == requested_path[0:len(p)+1]:
                return(apache.HTTP_FORBIDDEN)

        # Read blob object's content
        if requested_object.type == 'blob':
            req.headers_out.add('Cache-Control', 'max-age=%i' % config['gitblog.max_age_blob'])

            # Return non text blobs directly
            if not requested_object.mime_type == 'text/plain':
                req.content_type = requested_object.type
                req.write(requested_object.data_stream.read())
                return(apache.OK)

            # Get text blob content
            content = requested_object.data_stream.read()
            content = content.decode('utf-8')

        # Generate directory listing for tree objects
        elif requested_object.type == 'tree':
            req.headers_out.add('Cache-Control', 'max-age=%i' % config['gitblog.max_age_tree'])

            content = []
            for e in requested_object.trees:
                content += [ str('* [/%s/](/%s/)' % (e.path, e.path)) ]
            for e in requested_object.blobs:
                content += [ str('* [/%s](/%s)' % (e.path, e.path)) ]
            content.sort()
            content = '# Directory Tree\n' + '\n'.join(content)
        else:
            return(apache.HTTP_UNSUPPORTED_MEDIA_TYPE)
    except:
        return(apache.HTTP_NOT_FOUND)

    # Add footer
    if config['gitblog.footer'] == True:
        breadcrumb = '/'
        last_path_entry = ''
        if len(requested_path) > 0:
            last_path_entry = requested_path[-1]
            for i, l in enumerate(requested_path[0:-1]):
                breadcrumb += '[%s](/%s)/' % (l, '/'.join(requested_path[:i+1]))

        content += '\n\n---\n'
        if not output_type == 'plain':
            content += '[Home](/) - '
        content += '%s%s - Updated on %s by %s - Git Reference [%s](?ref=%s)\n' % \
                   (breadcrumb, last_path_entry,
                    datetime.fromtimestamp(git_obj.committed_date).strftime(
                      config['gitblog.date_format']),
                    git_obj.author.name,
                    git_obj, git_obj)

    # Return markdown
    if output_type == 'markdown':
        req.headers_out.add('Content-Type', 'text/markdown; charset=UTF-8')
        req.headers_out.add('Content-Length', str(len(content)))
        req.write(content)
        return(apache.OK)

    # Convert markdown to html
    content = markdown(content, extras=config['gitblog.markdown2_extras'])

    # Return plain
    if output_type == 'plain':
        content = ''.join(BeautifulSoup(content).findAll(text=True))
        req.headers_out.add('Content-Type', 'text/plain; charset=UTF-8')
        req.headers_out.add('Content-Length', str(len(content)))
        req.write(content)
        return(apache.OK)

    # Return html
    req.headers_out.add('Content-Type', 'text/html; charset=UTF-8')
    req.headers_out.add('Content-Length', str(len(content)))
    req.write(content.encode('utf-8'))
    return(apache.OK)

# vim: set syntax=python tabstop=4 expandtab:

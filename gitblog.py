# -*- coding: utf-8 -*-
# gitblog.py
"""
This Python program gitblog.py handles HTTP requests when it is loaded by mod_python and
returns different types of output formats from a git repository as web site basis.
The program can be used to deliver multiple sites/sources. The repository source is
set by the Apache option "PythonOption gitblog.www_repo <path to git repo>".

Copyright (c) 2013, 2014 Armin Pech <gitblog.py (at) arminpech (dot) de>, Duesseldorf, Germany.

Request for different output formats:
/about/me -- Default output is HTML
/about/imprint?acsii or /about/imprint?plain -- for unformatted output
/index?xml -- output in XML format

Request content in a particular version:
/about/me -- Default version is HEAD
/about/blogroll?ref=<git_ref> -- Return content in specific version

# TODO: Versions

Request unified diff for a content:
/about/me?diff=<commit>[:HEAD] -- Return diff of a resource between commit and HEAD
/about/imprint?diff=<commit1>:<commit2> -- Return diff of a resource between two defined commits


Available PyhtonOption configurations:
gitblog.www_repo             Base git repository to deliver content from


TODO
* return 404er if commit not found
* get last modified information from commit of requested path not of current commit
* print last commit of path in footer
* special index page / homepage
"""

### Import required modules
# Handle HTTP requests via mod_python
from mod_python import apache
# Read python error
import sys
# Regular Expression manipulation of contents with placeholders
import re
# Read content from git repository
import git
# Date formatting
from datetime import datetime
# Output formatting
from markdown2 import markdown
from BeautifulSoup import BeautifulSoup


### Set configuration options
# Default output text encoding
default_output_type = 'html'
# Available output text encodings (request parameter key => output format)
available_output_type = {   'html': 'html',
                            'ascii': 'plain',
                            'plain': 'plain',
                        }
# Pathes that should not be delivered by gitblog.py, without leading and trailing slashes
nondelivery_paths = ['.git', 'gitblog.py']
# Default Git commit for delivery
default_git_commit = 'HEAD'
# Default Git diff versions for comparsion delivery
# TODO


### Handle HTTP requests
def handler(req):
    # Set PythonOption configurations
    config = {
     'gitblog.www_repo': '/dev/null',
     'gitblog.default_output_type': 'html',
     'gitblog.report_errors': False,
     # Pathes that are delivered directly by gitblog.py, without leading and trailing slashes
     'gitblog.direct_delivery': 'static',
     'gitblog.markdown2_extras': 'toc',
    }

    for k in config.keys():
        if k in req.get_options().keys() and \
          not req.get_options()[k] is None and \
          not req.get_options()[k] == '':
            if req.get_options()[k] == 'True':
                config[k] = True
            elif req.get_options()[k] == 'False':
                config[k] = False
            else:
                config[k] = req.get_options()[k]

    for ac in ['gitblog.direct_delivery',
               'gitblog.markdown2_extras']:
        config[ac] = config[ac].split(',')


    # Get request path as list
    requested_path = req.uri.split('/')
    del(requested_path[0])
    requested_git_path = '/'.join(requested_path)
    if len(requested_git_path) > 1 and requested_git_path[-1] == '/':
        requested_git_path = requested_git_path[:-1]


    # Check if resource should NOT be delivered
    for p in nondelivery_paths:
        if '/' + p == req.uri[0:len(p)]:
            return(apache.HTTP_FORBIDDEN)


    # Get request parameter as list
    args = {}
    if not req.args is None and len(req.args) > 0:
        _args = req.args.split('&')
        if len(_args) > 0:
            for a in req.args.split('&'):
                t = a.split('=')
                if len(t) > 1:
                    args[t[0]] = t[1]
                else:
                    args[t[0]] = None
        del(_args, t)


    # Set generation options
    output_type = default_output_type
    for o in available_output_type:
        if o in args:
            output_type = available_output_type[o]

    # Set Git commit
    user_git_commit = default_git_commit
    if 'ref' in args.keys():
        user_git_commit = args['ref'][0:39]


    # Read data from repo
    repo = git.Repo(config['gitblog.www_repo'], odbt=git.GitDB)

    # Delivery some ressources directly
    for p in config['gitblog.direct_delivery']:
        if '/' + p == req.uri[0:len(p)+1]:
            try:
                req.content_type = repo.heads.master.commit.tree[req.uri[1:]].mime_type
                return(apache.OK)
            except:
                return(apache.HTTP_NOT_FOUND)

    # Build up breadcrumb and check if ressource is available and deliverable
    repo_tree = []
    user_tree = ''
    try:
        curr_tree = repo.tree(user_git_commit)
        for j, p in enumerate(requested_path):
            elem_found = False
            for i, e in enumerate(curr_tree):
                # Check if delivery of path is allowed
                if not e.path in nondelivery_paths:
                    # Add directory to breadcrumb
                    repo_tree += [ e.path ]
                    if p == e.path[len(p)*-1:]:
                        curr_tree = curr_tree[i]
                        elem_found = True
            if p == '' and j == len(requested_path)-1:
                elem_found = True
            if elem_found is False:
                return(apache.HTTP_NOT_FOUND)
        if elem_found is False:
            return(apache.HTTP_NOT_FOUND)
        repo_tree.sort()
    except:
        return(apache.HTTP_NOT_FOUND)


    # Get reference to Git by commit
    try:
        git_commit = repo.commit(user_git_commit)
    except:
        return(apache.HTTP_NOT_FOUND)


    # Get youngest commit of ressource by Git log
    #req.write('refs: %s\n' % repo.refs)
    #req.write('log: %s\n' % repo.head.reference.log())
    #for i in repo.head.reference.log():
    #    req.write('log entry: %s\n' % i)
    # TODO


    # Read object and get content
    try:
        requested_object = git_commit.tree[requested_git_path]

        # read blob object's content
        if requested_object.type == 'blob':
            content = requested_object.data_stream.read()
            content = content.decode("utf-8")
            # Add footer
            breadcrumb = '/'
            for i, l in enumerate(requested_path[0:-1]):
                breadcrumb += '[%s](/%s)/' % (l, '/'.join(requested_path[:i+1]))
            content += "\n---\n[Home](/) - %s - Reference [%s](?ref=%s)\n" % \
                       (breadcrumb, git_commit, git_commit)

        # generate directory listing for tree objects
        elif requested_object.type == 'tree':
            content = ''
            for e in requested_object.trees:
                content += str('* [/%s/](/%s/)\n' % (e.path, e.path))
            for e in requested_object.blobs:
                content += str('* [/%s](/%s)\n' % (e.path, e.path))
        else:
            return(apache.HTTP_UNSUPPORTED_MEDIA_TYPE)
    except:
        return(apache.HTTP_NOT_FOUND)

    # Convert content to UTF-8
    content = markdown(content, extras=config['gitblog.markdown2_extras'])

    # Return plain content directly
    if output_type == 'plain':
        content = ''.join(BeautifulSoup(content).findAll(text=True))
        req.headers_out.add('Content-Type', 'text/plain')
        req.headers_out.add('Content-Length', str(len(content)))
        req.write(content)
        return(apache.OK)

    # Return output
    req.headers_out.add('Content-Type', 'text/html')
    req.headers_out.add('Content-Length', str(len(content)))
    req.write(content.encode('utf-8'))
    return(apache.OK)

# vim: set syntax=python tabstop=4 expandtab:

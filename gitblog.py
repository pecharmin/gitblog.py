#!/usr/lib/apache2/modules/mod_python.so
# -*- coding: utf-8 -*-
# <htdocs root>/gitblog.py
"""
This Python program gitblog.py handles HTTP requests when it is loaded by mod_python and
returns different types of output formats from a git repository as web site basis.
The program can be used to deliver multiple sites/sources. The repository source is
set by the Apache option "PythonOption gitblog.wwwroot <path to git repo>".

Copyright (c) 2013 Armin Pech <gitblog.py (at) arminpech (dot) de>, Duesseldorf, Germany.

Request for different output formats:
/about/me -- Default output is HTML
/about/imprint?acsii or /about/imprint?plain -- for unformatted output
/index?xml -- output in XML format

Request content in a particular version:
/about/me -- Default version is HEAD
/about/blogroll?version=<commit> -- Return content in specific version

Request unified diff for a content:
/about/me?diff=<commit>[:HEAD] -- Return diff of a resource between commit and HEAD
/about/imprint?diff=<commit1>:<commit2> -- Return diff of a resource between two defined commits


Available PyhtonOption configurations:
gitblog.wwwroot             Base git repository to deliver content from
gitblog.default_output_type Default output type/template format


Changelog
14.09.2013: Basic idea and concept

TODO
* return 404er if commit not found
* get last modified information from commit of requested path not of current commit
* print last commit of path in footer
* special index page / homepage
"""

### Import required modules
# Handle HTTP requests via mod_python
from mod_python import apache
# Read content from git repository
import git
# Date formatting
from datetime import datetime
# Templating module
from string import Template
# Regular Expression manipulation of contents with placeholders
import re
# Read python error
import sys


### Set configuration options
# Default output text encoding
default_output_type = 'html'
# Available output text encodings (request parameter key => output format)
available_output_type = { 'html': 'html', 'xml': 'xml', 'ascii': 'plain', 'plain': 'plain' }
# Pathes that should not be delivered by gitblog.py, without leeding and trailing slashes
nondelivery_paths = [ '.git', 'gitblog.py', 'templates' ]
# Pathes that are delivered directly by gitblog.py, without leeding and trailing slashes
directdelivery_paths = [ 'static' ]
# Default Git commit for delivery
default_git_commit = 'HEAD'
# Default Git diff versions for comparsion delivery
# TODO


### Handle HTTP requests
def handler(req):
    # Set PythonOption configurations
    config = { \
     'gitblog.wwwroot': '/dev/null', \
     'gitblog.default_output_type': 'html', \
     'gitblog.report_errors': False \
    }

    for k in config.keys():
        if req.get_options().has_key(k) and \
          not req.get_options()[k] is None and \
          not req.get_options()[k] == '':
            if req.get_options()[k] == 'True':
                config[k] = True
            elif req.get_options()[k] == 'False':
                config[k] = False
            else:
                config[k] = req.get_options()[k]


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
    if args.has_key('commit'):
        user_git_commit = args['commit'][0:39]


    # Read data from repo
    repo = git.Repo(req.get_options()['gitblog.wwwroot'], odbt=git.GitDB)

    # Delivery some ressources directly
    for p in directdelivery_paths:
        if '/' + p == req.uri[0:len(p)+1]:
            try:
                req.content_type = repo.heads.master.commit.tree[req.uri[1:]].mime_type
                req.write(repo.heads.master.commit.tree[req.uri[1:]].data_stream.read())
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
    #for i in repo.head.reference.log:
    #    req.write('log entry: %s\n' % i)
    # TODO


    # Read object and get content
    try:
        requested_object = git_commit.tree[requested_git_path]
        # read blob object's content
        if requested_object.type == 'blob':
            content = requested_object.data_stream.read()
        # generate directory listing for tree objects
        elif requested_object.type == 'tree':
            content = ''
            for e in requested_object.trees:
                content += str('{a:/%s/}\n' % e.path)
            for e in requested_object.blobs:
                content += str('{a:/%s}\n' % e.path)
        else:
            return(apache.HTTP_UNSUPPORTED_MEDIA_TYPE)
    except:
        return(apache.HTTP_NOT_FOUND)


    # Return plain content directly
    if output_type == 'plain':
        req.headers_out.add('Content-Length', str(len(content)))
        req.write(content)
        return(apache.OK)


    # Convert content to UTF-8
    content = content.decode("utf-8")

    # Extract meta data of content
    meta_data = re.search('^\s*title\.\s*(?P<title>[^\n]*)', content)
    meta_data_content = { \
     'title': ''
    }
    if not meta_data is None:
        for g, r in meta_data.groupdict().iteritems():
            meta_data_content[g] = r
    del(meta_data)

    # Remove meta data from content
    content = re.sub('^\s*title\.\s+.*\n', '', content, 1)

    # Replace newlines
    content = re.sub('^\n*', '', content)
    content = re.sub('\n', r'<br />\n', content)

    # Replace lists placeholders
    content = re.sub('(?ms)(^\*\s+.*?<br />)\n^<br />\n', r'<ul>\n\1\n</ul>\n', content)
    content = re.sub('(?ms)(^#\s+.*?<br />)\n^<br />\n', r'<ol>\n\1\n</ol>\n', content)
    # TODO: Fix multiline
    #content = re.sub('(?m)^[\*#]\s+(.*)<br />?', r'<li>\1</li>', content)
    content = re.sub(r'(?m)^[\*#]\s+(.*)(?=<br />\n([\*#]|</ul>|</ol>))<br />', r'<li>\1</li>', content)

    # Headings
    content = re.sub('(?m)^h([1-6])\.\s+(.*)<br />', r'<h\1>\2</h\1>', content)


    # Set response HTTP headers
    req.content_type = 'text/' + output_type

    # Return content with applied templates
    try:
        # TODO: handle directory listings?
        template = repo.heads.master.commit.tree['templates/' + output_type].data_stream.read()
        content = Template(template).safe_substitute( \
          path=requested_object.path, \
          title=meta_data_content['title'], \
          body=content, \
          charset=git_commit.encoding, \
          commit=git_commit, \
          author=git_commit.author, \
          date=datetime.fromtimestamp(git_commit.committed_date)
        )
    except:
        if config['gitblog.report_errors'] is True:
            etype, evalue, etb = sys.exc_info()
            req.write('An error occured on line %i while delivering content path /%s: %s' % \
              (etb.tb_lineno, requested_object.path, evalue))
            req.status = apache.HTTP_INTERNAL_SERVER_ERROR
            return(apache.DONE)
        return(apache.HTTP_INTERNAL_SERVER_ERROR)


    # Replace placeholders
    if content.find('{toc}'):
        # TODO: insert anchors
        content = re.sub(r'(?m)^{toc}', r'<u>Inhaltsverzeichnis | Table of contents</u><br />TODO', content, 1)

    # Text decoration
    content = re.sub(r'(?<!\\){i(?<!\\)}(.*)(?<!\\){i(?<!\\)}', r'<i>\1</i>', content)
    content = re.sub(r'(?<!\\){b(?<!\\)}(.*)(?<!\\){b(?<!\\)}', r'<b>\1</b>', content)
    content = re.sub(r'(?<!\\){u(?<!\\)}(.*)(?<!\\){u(?<!\\)}', r'<u>\1</u>', content)

    # Code blocks
    content = re.sub(r'(?ms)^{code[^}]*}<br />\n(.*?(?!{code}))<br />\n{code}<br />\n', r'<pre><code>\1</code></pre>', content)
    # TODO: run over all matches
    #content = re.sub(r'(?m)(<pre><code>.*(?!</code></pre>))<br />', r'\1', content)
    content = re.sub(r'(?m)(?<=<pre><code>)(.*)<br />', r'\1', content)

    # Text formatting
    content = re.sub(r' -- ', r' &ndash; ', content)
    content = re.sub(r' --- ', r' &mdash; ', content)

    # Hyperlinks
    content = re.sub('{a:([^}:]*)}', r'<a href="\1">\1</a>', content)
    content = re.sub('{a:([^}:]*):([^}]*)}', r'<a href="\1">\2</a>', content)

    # Images
    content = re.sub('{img:([^:]+)}', r'<p><img src="\1"/></p>', content)
    content = re.sub('{img:([^:]+):([^}]*)}', r'<p><img src="\1" alt="\2"/><br />\2</p>', content)

    # Remove escapes
    content = re.sub(r'\\{(i|b|u|img|a|toc)\\}', r'{\1}', content)

    # Cleanup content
    content = re.sub('</p><br />', '</p>', content)
    #content = re.sub('<br />$|\n', '', content)
    content = re.sub('<br />$', '', content)


    # Return output
    req.headers_out.add('Content-Length', str(len(content)))
    req.write(content.encode('utf-8'))
    return(apache.OK)

# vim: set syntax=python tabstop=4 expandtab:

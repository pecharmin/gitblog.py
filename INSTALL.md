# Setup

## Setup with Apache2
1. Install mod_python for Apache2 webserver

1. Install required Python modules
   * git -- (https://pypi.python.org/pypi/GitPython)
   * BeautifulSoup -- (https://pypi.python.org/pypi/BeautifulSoup)
   * markdown2 -- (https://pypi.python.org/pypi/markdown2)

   Example on a Debian 9 system:

   ```
   apt-get install python-git python-beautifulsoup
   apt-get install pip python-setuptools
   pip install markdown2
   ```

1. Clone gitblog.py as webroot on your server

   ```
   INSTALL_DIR=/var/www/gitblog.py
   git clone https://github.com/pecharmin/gitblog.py.git $INSTALL_DIR
   # Checkout a reference you would like to run
   cd $INSTALL_DIR
   git checkout stable # <-- or whatever reference you prefer
   ```

1. Setup a git bare repository on your server and push your local content to it

   ```
   BLOG_DOMAIN=gitblog.tld
   mkdir -p /var/git
   git init --bare /var/git/${BLOG_DOMAIN}.git
   ```

1. Ensure that the run-user of the Apache2 Webserver is able to read
   the git repository (and not be able to write to it).

1. Setup a local git repository on your desktop and create a directory structure

   ```
   BLOG_DOMAIN=gitblog.tld
   # cd wherever you place your git repositories
   git init $BLOG_DOMAIN
   cd $BLOG_DOMAIN
   echo '# Hello World' > hello
   git add hello
   git commit -m 'First git blog entry'
   git remote add origin ssh://user@webserver:22/var/git/gitblog.tld.git
   git push -u origin master
   ```

1. Create a virtual host for your webserver configuration

   ```
   <VirtualHost *:80>
   	ServerName gitblog.tld
   	ServerAdmin hostmaster@gitblog.tld
   
   	LogLevel warn
   	ErrorLog /var/log/apache2/error_log-%{SERVER_NAME}
   	CustomLog /var/log/apache2/access_log-%{SERVER_NAME} vhost
   
   	DocumentRoot /var/www/gitblog.py
   
   	<Location />
   		Require all granted
   		SetHandler mod_python
   		PythonHandlerModule gitblog
   		PythonPath "sys.path + ['/var/www/gitblog.py']" # <-- adjust here
   		PythonOptimize On
   		PythonAutoReload Off
   		PythonDebug Off
   		PythonOption gitblog.wwwroot /var/git/gitblog.tld.git # <-- adjust here
   		#PythonOption gitblog.footer False
   	</Location>
   
   	# Compress output by filter
   	<IfModule mod_deflate.c>
   		SetOutputFilter DEFLATE
   	</IfModule>
   
   	# Cache website responses
   	<IfModule mod_cache.c>
   		<IfModule mod_disk_cache.c>
   			CacheRoot /var/cache/apache2/gitblog.tld/
   			CacheEnable disk /
   			CacheDirLevels 5
   			CacheDirLength 3
   		</IfModule>
   	</IfModule>
   </VirtualHost>
   ```

## gitblog configuration options

The behavior of gitblog.py can be configured by passing key/value pairs
from Apache2 using PythonOption directives:

| Option name                 | Default                | Description                                 | Possible values                               |
|-----------------------------|------------------------|---------------------------------------------|-----------------------------------------------|
| gitblog.report_errors       | False                  | Should errors be returned to users?         | Boolean                                       |
| gitblog.www_repo            | /dev/null              | Path to the content git base repository     | Filesystem path                               |
| gitblog.default_ref         | HEAD                   | Default git reference to display            | Any git reference                             |
| gitblog.default_output_type | html                   | Output format for called site               | html, plain, markdown                         |
| gitblog.footer              | True                   | Display footer meta information             | Boolean                                       |
| gitblog.date_format         | %Y-%m-%d %H:%M         | Date format in footer                       | String, see datetime                          |
| gitblog.markdown2_extras    | toc                    | Extra options when parsing content source   | String, comma separated values, see markdown2 |
| gitblog.max_age_blob        | 1800                   | Cache-Control max-age for non-text elements | Integer                                       |
| gitblog.max_age_tree        | 600                    | Cache-Control max-age for directory lising  | Integer                                       |
| gitblog.denied_path         | private,templates      | Paths not to deliver (without leeding /)    | String, comma separated values                |
| gitblog.redirect_code       | HTTP_MOVED_PERMANENTLY | HTTP response code for redirects on links   | HTTP_MOVED_PERMANENTLY, HTTP_MOVED_TEMPORARILY, HTTP_TEMPORARY_REDIRECT |

# Setup

## Setup with Apache2
1. Install mod_python for Apache2 webserver
1. Clone gitblog.py as webroot on your server

   ```
   git clone https://github.com/pecharmin/gitblog.py.git /var/www/gitblog.py
   ```

1. Setup a git bare repository on your server and push your local content to it

   ```
   git init --bare /var/git/gitblog.tld.git
   ```

1. Setup a local git repository on your desktop and create a directory structure

   ```
   git init gitblog.tld
   cd gitblog.tld
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
   		PythonPath "sys.path + ['/var/www/gitblog.py']"
   		PythonOptimize On
   		PythonAutoReload Off
   		PythonDebug Off
   		PythonOption gitblog.wwwroot /var/git/gitblog.tld.git
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
TODO

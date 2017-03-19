# gitblob.py
This program renders websites from a bare git repository.
It's a handler for mod_python in the Apache2 webserver.

Author: Armin Pech <github (at) arminpech (dot) de>

[Copyright & License](/LICENSE)

## Description
You manage your website content hierachically in a local git repository
based on normal files and directories:

```
/
|
`-- /about
|   |
|   `-- /about/me
|   `-- /about/imprint
`-- /blog
    |
    `-- /blog/2017-01-01-happy-new-year
```

After content modifications you push your local repository content
to a remote base repository on your webserver.
The gitblog.py handler serves client requests from the base repo.
The URI of the request matches the file and directory structure of
your repository content.

```
Client --> Apache --> mod_python --> gitblog.py <--.
                                                   |
Desktop --> Local Repo --> Server Bare Repo -------´
```

## Features
* History and permanent links based on git commits/references

  `/blog/1?ref=93faf2001885d7292c1d757bd21da9b10e786b42`

  `/blog/1?ref=mytag1`

* Multiple branches

  `/blog/2?ref=HEAD`

  `/blog/2?ref=master`

  `/blog/2?ref=preview`

## Setup
see [SETUP](/SETUP)

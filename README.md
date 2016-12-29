
Record has an associated dataset series, associated dataset id, deleted flag, (merged into record?), a list of modifications

Each dataset series has a name, a description, a license, a number of associated datasets, a number of attribute types, a number of display plugins

Each modification has a user, time stamp, associated record, attribute type (optional), a field name (if no attribute) and value

Attribute types can be: shape (WKB), description, access rights, operator, photos, fosm/osm database object info, name, representitive position

Plugins take a number of attributes and change how they are displayed to the user

Useful commands
===============

To configure nginx, uWSGI, systemd: https://gist.github.com/TimSC/0193fa92d7fe5b63769eeca5c42fd5d5

* python manage.py migrate
* python manage.py collectstatic



# -*- coding: utf-8 -*-
"""
An example of Dropbox App linking with Flask.
"""

import os
import posixpath
import json

from sqlite3 import dbapi2 as sqlite3
from flask import Flask, request, session, g, redirect, url_for, abort, \
     render_template, flash, _app_ctx_stack, jsonify

from dropbox.client import DropboxClient, DropboxOAuth2Flow

# configuration
DEBUG = True
DATABASE = 'myapp.db'
SECRET_KEY = 'development key'

# Fill these in!
DROPBOX_APP_KEY = os.environ.get('DROPBOX_APP_KEY', '')
DROPBOX_APP_SECRET = os.environ.get('DROPBOX_APP_SECRET', '')

# create our little application :)
app = Flask(__name__)
app.config.from_object(__name__)
app.config.from_envvar('FLASKR_SETTINGS', silent=True)
# Disable prettyprint of JSON response
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False

# Ensure instance directory exists.
try:
    os.makedirs(app.instance_path)
except OSError:
    pass

def init_db():
    """Creates the database tables."""
    with app.app_context():
        db = get_db()
        with app.open_resource("schema.sql", mode="r") as f:
            db.cursor().executescript(f.read())
        db.commit()


def get_db():
    """
    Opens a new database connection if there is none yet for the current application context.
    """
    top = _app_ctx_stack.top
    if not hasattr(top, 'sqlite_db'):
        sqlite_db = sqlite3.connect(os.path.join(app.instance_path, app.config['DATABASE']))
        sqlite_db.row_factory = sqlite3.Row
        top.sqlite_db = sqlite_db

    return top.sqlite_db

def get_access_token():
    username = session.get('user')
    if username is None:
        return None
    db = get_db()
    row = db.execute('SELECT access_token FROM users WHERE username = ?', [username]).fetchone()
    if row is None:
        return None
    return row[0]

@app.route('/')
def home():
    if 'user' not in session:
        return redirect(url_for('login'))
    access_token = get_access_token()
    real_name = None
    quota = None
    app.logger.info('access token = %r', access_token)
    if access_token is not None:
        client = DropboxClient(access_token)
        account_info = client.account_info()
        real_name = account_info["display_name"]
        quota_info = client.account_info()['quota_info']
        quota = "Normal: " + str(filesize_readable(quota_info['normal'])) + " | Shared: " + str(filesize_readable(quota_info['shared']))
    return render_template('index.html', real_name=real_name, quota=quota)

@app.route('/view/<vis>')
def show_visualiser(vis):

    return render_template('visualisers/' + vis + '.html')

@app.route('/tree.json')
def get_folder_tree():
    # Check authentication
    if 'user' not in session:
        return redirect(url_for('login'))
    access_token = get_access_token()
    #sizes = {}
    delta_metadatas = {}
    cursor = None
    if access_token is not None:
        client = DropboxClient(access_token)    #folder_metadata = client.metadata(path)
        #metadata = json.dumps(folder_metadata, sort_keys=True, indent=4, separators=(',', ': '))
        while cursor is None or result['has_more']:
            result = client.delta(cursor)
            # delta_metadatas = parse_delta(result)
            for path, metadata in result['entries']:
                #sizes[path] = metadata['bytes'] if metadata else 0
                delta_metadatas[path] = metadata if metadata else None
            cursor = result['cursor']

            # Disable complete fetch
            result['has_more'] = False

    return jsonify(parse_delta(delta_metadatas))

@app.route('/tree-raw.json')
def get_folder_tree_raw():

    """Returns the raw data retrieved from Drobox"""

    # Check authentication
    if 'user' not in session:
        return redirect(url_for('login'))
    access_token = get_access_token()
    #sizes = {}
    delta_metadatas = {}
    cursor = None
    if access_token is not None:
        client = DropboxClient(access_token)    #folder_metadata = client.metadata(path)
        #metadata = json.dumps(folder_metadata, sort_keys=True, indent=4, separators=(',', ': '))
        print ("Fetching results...")
        i = 0
        while cursor is None or result['has_more']:
            i = i + 1
            print ("Fetching result set %d." % i)
            result = client.delta(cursor)
            # delta_metadatas = parse_delta(result)
            for path, metadata in result['entries']:
                #sizes[path] = metadata['bytes'] if metadata else 0
                delta_metadatas[path] = metadata if metadata else None
            cursor = result['cursor']

            # Disable complete fetch
            result['has_more'] = False

    return jsonify(delta_metadatas)

@app.route('/tree-sample.json')
def get_folder_tree_TEST():

    """Non-authenticated request returning sample data"""

    delta_metadatas = {}
    delta_metadatas['/photos'] = {
        "bytes":0,
        "icon":"folder",
        "is_dir": True,
        "modified":"Thu, 29 Mar 2012 21:19:51 +0000",
        "path":"/Photos",
        "rev":"106cda493",
        "revision":1,
        "root":"dropbox",
        "size":"0 bytes",
        "thumb_exists": False
    }

    delta_metadatas["/public"] = {
        "bytes": 0,
        "icon": "folder_public",
        "is_dir": True,
        "modified":"Thu, 29 Mar 2012 21:19:51 +0000",
        "path":"/Public",
        "rev":"206cda493",
        "revision":2,
        "root":"dropbox",
        "size":"0 bytes",
        "thumb_exists":False
    }

    delta_metadatas["/public/myfolder"] = {
        "bytes":0,
        "icon":"folder",
        "is_dir":True,
        "modified":"Thu, 29 Mar 2012 21:57:31 +0000",
        "path":"/Public/myfolder",
        "rev":"9d06cda493",
        "revision":157,
        "root":"dropbox",
        "size":"0 bytes",
        "thumb_exists": False
    }

    delta_metadatas["/public/myfolder/myimagefile.png"] = {
        "bytes":5575,
        "client_mtime":"Tue, 29 Apr 2014 01:26:20 +0000",
        "icon":"page_white_picture",
        "is_dir": False,
        "mime_type":"image/png",
        "modified":"Tue, 29 Apr 2014 01:26:20 +0000",
        "path":"/Public/myfolder/MyImageFile.PNG",
        "rev":"9f06cda493",
        "revision":159,
        "root":"dropbox",
        "size":"5.4 KB",
        "thumb_exists":True
    }

    delta_metadatas["/mycssfile.css"] = {
        "bytes":919,
        "client_mtime":"Tue, 29 Apr 2014 01:17:44 +0000",
        "icon":"page_white_code",
        "is_dir": False,
        "mime_type":"text/css",
        "modified":"Tue, 29 Apr 2014 01:17:44 +0000",
        "path":"/MyCssFile.css",
        "rev":"9e06cda493",
        "revision":158,
        "root":"dropbox",
        "size":"919 bytes",
        "thumb_exists": False
    }

    data = parse_delta(delta_metadatas)

    return jsonify(data)

@app.route('/tree-file.json')
def get_folder_tree_from_file():

    # filename = 'static/data/raw_delta_metadata.json'
    filename = 'static/data/raw_delta_metadata-full.json'
    json_data=open(filename)
    delta_metadatas = json.load(json_data)
    json_data.close()
    data = parse_delta(delta_metadatas)
    return jsonify(data)

def matches_id(child_dict, search_id):

    x = child_dict["_id"] == search_id
    # print ("is search_id %s in child_dict (shown on next line)? %s" % (search_id, ("yes" if x else "no")))
    # print (child_dict)
    return x

def parse_delta(d):

    dropbox = {
        "name": "Dropbox",
        "children": [],
        "_id": "dropbox"
    }

    for path, metadata in d.iteritems():

        # Trim leading "/" from path
        path = path[1:]

        path_sections = path.split("/")

        # Reset node 'pointer' to the full dict
        node = dropbox["children"]

        # print ("")
        #print ("Processing: " + metadata["path"])
        #print ("Processing: " + path)

        # Process each level in turn, to ensure parents exist where necessary.

        for depth, path_section in enumerate(path_sections):

            # print ("Processing sub-section (%d of %d): %s" % (depth+1, len(path_sections), path_section))

            # Search for existing node (via ancestors)
            # print ("Node length: %d" % len(node))
            matches = [x for x in node if matches_id(x, path_section)]

            # Build the required hierarchy
            if (len(matches) is 0):
                # print("No matches found - create a necessary section")
                new = {
                    "_id": path_section
                }

                # Specify either children (empty list) or name
                # Item will have children only if either:
                # - it's not the deepest element.
                # - it's the lowest (deepest) element and is_dir.
                if depth is not len(path_sections) - 1 or metadata["is_dir"]:
                    new["children"] = []

                # Add any metadata that we know
                # - We only (currently) have metadata for the deepest-nested element
                if depth is len(path_sections) - 1:
                    new["name"] = metadata["path"]
                    # Size is only relevent for files
                    if not metadata["is_dir"]:
                        new["size"] = metadata["bytes"]
                        new["icon"] = metadata["icon"]

                # print ("Appended new item:")
                # print (new)
                node.append(new)

                # print ("Resulting full node:")
                # print (node)

                # Update 'node' reference
                if depth is not len(path_sections) - 1 or metadata["is_dir"]:
                    node = new["children"]

            else:
                #print ("%d matches found!" % len(matches))

                match = matches[0]

                # We may not have the name yet (if it's the deepest node)
                if depth is len(path_sections) - 1:
                    match["name"] = metadata["path"]

                # print ("First match found: ")
                # print (match)
                
                # Update reference to node (for subsequent iterations)
                # try:
                node = match["children"]
                # except KeyError:
                #     pass

            # print ("current full dropbox dict:")
            # print (dropbox)

    return dropbox

def parse_delta_partially_working_nested_named(d):

    #print ("Parsing delta data: " + d)

    dropbox = {
        "name": "Dropbox",
        "children": [],
        "_id": "dropbox"
    }

    for path, metadata in d.iteritems():

        # Trim leading "/" from path
        path = path[1:]

        path_sections = path.split("/")

        # Reset node 'pointer' to the full dict
        node = dropbox["children"]

        print ("")
        print ("Processing: " + metadata["path"])

        # Process each level in turn, to ensure parents exist where necessary.

        for depth, path_section in enumerate(path_sections):

            print ("Processing sub-section (%d of %d): %s" % (depth+1, len(path_sections), path_section))

            # Handle intermediate-depth items
            if depth is not len(path_sections) - 1:

                # Search for existing node (via ancestors)
                # print ("Node length: %d" % len(node))
                matches = [x for x in node if matches_id(x, path_section)]                

                # Build the required hierarchy
                if (len(matches) is 0):
                    print("No matches found - create a necessary children section")
                    new = {
                        "_id": path_section,
                        "children": []
                    }
                    node.append(new)
                    print (node)

                    node = new["children"]

                else:
                    print ("%d matches found!" % len(matches))

                    match = matches[0]
                    
                    # Update reference to node (for subsequent iterations)
                    node = match["children"]

            # Handle the "lowest" (end) item.
            else:

                print ("Handling lowest-level path_section - adding it to list")

                # Add this file/folder's details.
                if metadata["is_dir"]:
                    node.append({
                        "_id": path_section,
                        "name": metadata["path"],
                        "children": []
                    })
                else:
                    node.append({
                        "_id": path_section,
                        "name": metadata["path"],
                        "size": metadata["bytes"]
                    })
                print (node)
                print (dropbox)

    return dropbox

def parse_delta_alt(d):

    """Return JSON object structure with filename as keys (not name/children keys)"""

    #print ("Parsing delta data: " + d)

    metadatas = {}

    for path, metadata in d.iteritems():

        # Trim leading "/" from path
        path = path[1:]

        path_sections = path.split("/")

        local = metadatas
        if len(path_sections) == 1 and metadata['is_dir']:
            continue
        for depth, path_section in enumerate(path_sections):
            if path_section not in local:
                local[path_section] = {}
            if len(path_sections) != depth + 1:
                local = local[path_section]
        else:
            if not metadata['is_dir']:
                local[path_section] = metadata

    return metadatas

def filesize_readable(size):
    for x in ['B','KB','MB','GB']:
        if size < 1024.0:
            return "%3.0f %s" % (size, x)
        size /= 1024.0
    return "%3.1f%s" % (size, 'TB')

@app.route('/dropbox-auth-finish')
def dropbox_auth_finish():
    username = session.get('user')
    if username is None:
        abort(403)
    try:
        print(request.args)
        access_token, user_id, url_state = get_auth_flow().finish(request.args)
    except DropboxOAuth2Flow.BadRequestException as e:
        abort(400)
    except DropboxOAuth2Flow.BadStateException as e:
        abort(400)
    except DropboxOAuth2Flow.CsrfException as e:
        abort(403)
    except DropboxOAuth2Flow.NotApprovedException as e:
        flash('Not approved?  Why not')
        return redirect(url_for('home'))
    except DropboxOAuth2Flow.ProviderException as e:
        app.logger.exception("Auth error" + e)
        abort(403)
    db = get_db()
    data = [access_token, username]
    db.execute('UPDATE users SET access_token = ? WHERE username = ?', data)
    db.commit()
    return redirect(url_for('home'))

@app.route('/dropbox-auth-start')
def dropbox_auth_start():
    if 'user' not in session:
        abort(403)
    return redirect(get_auth_flow().start())

@app.route('/dropbox-logout')
def dropbox_logout():
    username = session.get('user')
    if username is None:
        abort(403)
    db = get_db()
    db.execute('UPDATE users SET access_token = NULL WHERE username = ?', [username])
    db.commit()
    return redirect(url_for('home'))

def get_auth_flow():
    redirect_uri = url_for('dropbox_auth_finish', _external=True)
    return DropboxOAuth2Flow(DROPBOX_APP_KEY, DROPBOX_APP_SECRET, redirect_uri,
                                       session, 'dropbox-auth-csrf-token')

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        if username:
            db = get_db()
            db.execute('INSERT OR IGNORE INTO users (username) VALUES (?)', [username])
            db.commit()
            session['user'] = username
            flash('You were logged in')
            return redirect(url_for('home'))
        else:
            flash("You must provide a username")
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.pop('user', None)
    flash('You were logged out')
    return redirect(url_for('home'))


def main():
    init_db()
    app.run()


if __name__ == '__main__':
    main()

import json
import psycopg2
import psycopg2.extras
import sys
import os
import zipfile

import config

def setup_databases(con, cursor):

    cursor.execute("DROP TABLE IF EXISTS RSVPS")
    cursor.execute("DROP TABLE IF EXISTS Events")
    cursor.execute("DROP TABLE IF EXISTS Venues")

    cursor.execute("CREATE TABLE Events(\
                    id VARCHAR(32) PRIMARY KEY,\
                    event_url VARCHAR(255),\
                    name VARCHAR(255),\
                    time BIGINT\
                   )")

    cursor.execute("CREATE TABLE Venues(\
                    city VARCHAR(64),\
                    name VARCHAR(255),\
                    zip VARCHAR(32),\
                    repinned BOOLEAN,\
                    lon FLOAT,\
                    state VARCHAR(8),\
                    address_1 VARCHAR(255),\
                    country VARCHAR(8),\
                    lat FLOAT,\
                    id VARCHAR(32) PRIMARY KEY\
                   )")

    cursor.execute("CREATE TABLE RSVPS(\
                    group_id INT,\
                    FOREIGN KEY (group_id) REFERENCES Groups(id) ON DELETE CASCADE,\
                    venue_id VARCHAR(32),\
                    FOREIGN KEY (venue_id) REFERENCES Venues(id) ON DELETE CASCADE,\
                    created BIGINT,\
                    id VARCHAR(32) PRIMARY KEY,\
                    mtime BIGINT,\
                    response VARCHAR(8),\
                    member_id INT,\
                    FOREIGN KEY (member_id) REFERENCES Members(id) ON DELETE CASCADE,\
                    guest INT,\
                    photo_id INT,\
                    FOREIGN KEY (photo_id) REFERENCES Photos(id) ON DELETE SET NULL,\
                    event_id VARCHAR(32),\
                    FOREIGN KEY (event_id) REFERENCES Events(id) ON DELETE CASCADE\
                   )")

    con.commit()

def write_rsvps(con, cursor):

    counter = 1;
    file_count = len(os.listdir('./data/rsvps/'))

    for zip_files in os.listdir('./data/rsvps/'):

        print "Inserting file " + str(counter) + " of " + str(file_count) + " files..."
        counter += 1

        zip_file = zipfile.ZipFile('./data/rsvps/' + zip_files)
        for file_name in zip_file.namelist():

                data = zip_file.read(file_name)
                rsvps = json.loads(data)

                for rsvp in rsvps:

                    # Todo Tallies?!

                    # Update member
                    member = rsvp["member"]
                    cursor.execute("INSERT INTO Members(name, id) SELECT %s,%s WHERE NOT EXISTS (SELECT id FROM Members WHERE id=%s)", (member["name"], int(member["member_id"]), member["member_id"]))

                    # Update group
                    group = rsvp["group"]
                    cursor.execute("INSERT INTO Groups(urlname, lon, id, lat, join_mode) SELECT %s,%s,%s,%s,%s WHERE NOT EXISTS (SELECT id FROM Groups WHERE id=%s)", (group["urlname"], group["group_lon"], group["id"], group["group_lat"], group["join_mode"], group["id"]))

                    # Update venue
                    if "venue" in rsvp:
                        venue = rsvp["venue"]
                        if not "zip" in venue:
                            venue["zip"] = None
                        if not "state" in venue:
                            venue["state"] = None
                        if not "city" in venue:
                            venue["city"] = None
                        cursor.execute("INSERT INTO Venues(city, name, zip, repinned, lon, state, address_1, country, lat, id) SELECT %s,%s,%s,%s,%s,%s,%s,%s,%s,%s WHERE NOT EXISTS (SELECT id FROM Venues WHERE id=%s)", (venue["city"], venue["name"], venue["zip"], venue["repinned"], venue["lon"], venue["state"], venue["address_1"], venue["country"], venue["lat"], str(venue["id"]), str(venue["id"])))
                    else:
                        venue = {"id": None}

                    # Update photo
                    if "member_photo" in rsvp:
                        photo = rsvp["member_photo"]
                        if not "highres_link" in photo:
                            photo["highres_link"] = ""
                        cursor.execute("INSERT INTO Photos(thumb_link, id, photo_link, highres_link) SELECT %s,%s,%s,%s WHERE NOT EXISTS (SELECT id FROM Photos WHERE id=%s)", (photo["thumb_link"], photo["photo_id"], photo["photo_link"], photo["highres_link"], photo["photo_id"]))
                    else:
                        photo = {"photo_id": None}

                    # Update event
                    event = rsvp["event"]
                    cursor.execute("INSERT INTO Events(event_url, id, name, time) SELECT %s,%s,%s,%s WHERE NOT EXISTS (SELECT id FROM Events WHERE id=%s)", (event["event_url"], event["id"], event["name"], event["time"], event["id"]))

                    # Insert RSVPS
                    if not "guest" in rsvp:
                        rsvp["guest"] = None
                    cursor.execute("INSERT INTO RSVPS(group_id, venue_id, created, id, mtime, response, member_id, guest, photo_id, event_id) SELECT %s,%s,%s,%s,%s,%s,%s,%s,%s,%s WHERE NOT EXISTS (SELECT id FROM RSVPS WHERE id=%s)", (group["id"], venue["id"], rsvp["created"], rsvp["rsvp_id"], rsvp["mtime"], rsvp["response"], member["member_id"], rsvp["guest"], photo["photo_id"], event["id"], str(rsvp["rsvp_id"])))

                con.commit()

if __name__ == "__main__":

    try:
        con = psycopg2.connect(database=config.db, user=config.user, password=config.password, host=config.host)
        cursor = con.cursor()

        setup_databases(con, cursor)
        write_rsvps(con, cursor)

    except psycopg2.DatabaseError, e:

        print 'Error %s' % e
        sys.exit(1)

    finally:
        if con:
            con.close()


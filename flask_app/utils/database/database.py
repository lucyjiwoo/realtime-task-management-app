import mysql.connector
import glob
import json
import csv
from io import StringIO
import itertools
import hashlib
import os
import cryptography
from cryptography.fernet import Fernet
from math import pow

class database:

    def __init__(self, purge = False):

        # Read DB connection from environment variables (production)
        # Falls back to local dev defaults when env vars are not set
        self.database       = os.environ.get('DB_NAME',     'db')
        self.host           = os.environ.get('DB_HOST',     '127.0.0.1')
        self.user           = os.environ.get('DB_USER',     'master')
        self.port           = int(os.environ.get('DB_PORT') or '3306')
        self.password       = os.environ.get('DB_PASSWORD', 'master')
        self.tables         = ['users','boards', 'board_members', 'lists', 'cards']
        
        # NEW IN HW 3-----------------------------------------------------------------
        self.encryption     =  {   'oneway': {'salt' : b'averysaltysailortookalongwalkoffashortbridge',
                                                 'n' : int(pow(2,5)),
                                                 'r' : 9,
                                                 'p' : 1
                                             },
                                'reversible': { 'key' : '7pK_fnSKIjZKuv_Gwc--sZEMKn2zc8VvD6zS96XcNHE='}
                                }
        #-----------------------------------------------------------------------------

    def query(self, query = "SELECT * FROM users", parameters = None):

        cnx = mysql.connector.connect(host     = self.host,
                                      user     = self.user,
                                      password = self.password,
                                      port     = self.port,
                                      database = self.database,
                                      charset  = 'latin1'
                                     )


        if parameters is not None:
            cur = cnx.cursor(dictionary=True)
            cur.execute(query, parameters)
        else:
            cur = cnx.cursor(dictionary=True)
            cur.execute(query)

        # Fetch one result
        row = cur.fetchall()
        cnx.commit()

        if "INSERT" in query:
            cur.execute("SELECT LAST_INSERT_ID()")
            row = cur.fetchall()
            cnx.commit()
        cur.close()
        cnx.close()
        return row


    def createTables(self, purge=False, data_path = 'flask_app/database/'):
        ''' FILL ME IN WITH CODE THAT CREATES YOUR DATABASE TABLES.'''

        #should be in order or creation - this matters if you are using forign keys.
         
        if purge:
            for table in self.tables[::-1]:
                self.query(f"""DROP TABLE IF EXISTS {table}""")

        # Execute all SQL queries in the /database/create_tables directory.
        for table in self.tables:
            
            #Create each table using the .sql file in /database/create_tables directory.
            with open(data_path + f"create_tables/{table}.sql") as read_file:
                create_statement = read_file.read()
            self.query(create_statement)


    def insertRows(self, table='table', columns=['x','y'], parameters=[['v11','v12'],['v21','v22']]):
        
        # Check if there are multiple rows present in the parameters
        has_multiple_rows = any(isinstance(el, list) for el in parameters)
        keys, values      = ','.join(columns), ','.join(['%s' for x in columns])
        
        # Construct the query we will execute to insert the row(s)
        query = f"""INSERT IGNORE INTO {table} ({keys}) VALUES """
        if has_multiple_rows:
            for p in parameters:
                query += f"""({values}),"""
            query     = query[:-1] 
            parameters = list(itertools.chain(*parameters))
        else:
            query += f"""({values}) """                      
        
        insert_id = self.query(query,parameters)[0]['LAST_INSERT_ID()']         
        return insert_id
#######################################################################################
# AUTHENTICATION RELATED
#######################################################################################
    def createUser(self, email='me@email.com', password='password'):
        # Not existed in our database
        existing_user = self.query("SELECT * FROM users WHERE email=%s", [email])
        if existing_user:
            return {'success': 0, "message":"User already exists."}
        

         # Encrypt the password
        encrypted_password = self.onewayEncrypt(password)

        # Insert the new user into the database
        query = "INSERT INTO users (password, email) VALUES (%s, %s)"
        parameters = (encrypted_password, email)

        try:
            self.query(query, parameters)
            return {'success': 1, "message": "User created successfully."}
        except Exception as e:
            print("Error creating user:", e)
            return {'success': 0, "message": "Error occurred while creating the user."}
        

    def authenticate(self, email='me@email.com', password='password'):
        
        print(email)
        user = self.query("SELECT * FROM users WHERE email = %s", [email])

        if not user:
            return {'success': 0, "message":"User not exists."}
        
        stored_password = user[0]['password']

        if self.onewayEncrypt(password) == stored_password:
            return {"success": 1, "message":"Authentication success"}
        else:
            return {"success": 0, "message":"Incorrect Password"}


    def onewayEncrypt(self, string):
        encrypted_string = hashlib.scrypt(string.encode('utf-8'),
                                          salt = self.encryption['oneway']['salt'],
                                          n    = self.encryption['oneway']['n'],
                                          r    = self.encryption['oneway']['r'],
                                          p    = self.encryption['oneway']['p']
                                          ).hex()
        return encrypted_string


    def reversibleEncrypt(self, type, message):
        fernet = Fernet(self.encryption['reversible']['key'])
        
        if type == 'encrypt':
            message = fernet.encrypt(message.encode())
        elif type == 'decrypt':
            message = fernet.decrypt(message).decode()

        return message
    #######################################################################################
    # Interface Related
    #######################################################################################

    def getUserBoards(self, email):
        query = """
            SELECT DISTINCT b.board_id, b.name
            FROM boards b
            JOIN board_members bm ON b.board_id = bm.board_id
            JOIN users u ON bm.user_id = u.user_id
            WHERE u.email = %s
        """
        return self.query(query, [email])
    
    def createBoards(self, board_name, creator_email, members_email):

        user_id_query = "SELECT user_id FROM users WHERE email = %s"
        creator = self.query(user_id_query, [creator_email])
        if not creator:
            return {"success": 0, "message": "Creator email not found in the database."}
        creator_id = creator[0]['user_id']
        try:
            board_id = self.insertRows(table="boards", columns=["name", "creator_id"], parameters=[[board_name, creator_id]])
            # Add members of the board
            self.insertRows(table="board_members", columns=["board_id", "user_id"], parameters=[[board_id, creator_id]])
            for email in members_email:
                member = self.query(user_id_query, [email])
                if not member:
                    print(f"Skipping email: {email}. User not found.")
                    continue  # Skip if user does not exist
                member_id = member[0]['user_id']
                self.insertRows(table="board_members", columns=["board_id", "user_id"], parameters=[[board_id, member_id]])            
            
            # Create lists in the board
            default_lists = ["To Do", "In Process", "Completed"]
            for list_name in default_lists:
                self.insertRows(table="lists", columns=["name", "board_id"], parameters=[[list_name, board_id]])

            return {"success": 1, "message": "Board created successfully.", "board_id": board_id}
        except Exception as e:
            print("Error creating board:", e)
            return {"success": 0, "message": "Error occurred while creating the board."}
        
    def createCard(self, list_id, card_name, card_description):
        try:
            # Insert the new card and fetch the last inserted ID
            result = self.insertRows(
                table="cards",
                columns=["list_id", "name", "description"],
                parameters=[[list_id, card_name, card_description]]
            )

            print("Card created successfully:", result)  # Debug log

            # Assuming `insertRows` returns the last inserted ID
            if result:
                return {
                    "success": 1,
                    "message": "Card created successfully.",
                    "card_id": result  # Include the new card ID
                }
            else:
                return {
                    "success": 0,
                    "message": "Failed to retrieve the card ID after insertion."
                }
        except Exception as e:
            print("Error creating card:", e)
            return {"success": 0, "message": "Error occurred while creating the card."}

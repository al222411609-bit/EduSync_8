from pymongo import MongoClient
import os

def get_db():
    # link directo 
    uri = "mongodb+srv://al222411609_db_user:Leo2505280606_edusync@cluster0.hujbcuw.mongodb.net/EdusyncDB?retryWrites=true&w=majority"
    
    try:
        
        client = MongoClient(uri, tlsAllowInvalidCertificates=True, serverSelectionTimeoutMS=5000)
      
        client.admin.command('ping')
        print("¡Conexión exitosa a MongoDB Atlas!")
        return client['EdusyncDB']
    except Exception as e:
        print(f"Error de conexión: {e}")
        return None

db = get_db()
if db is not None:
    users_col = db['usuarios']
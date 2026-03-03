from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from app.database import users_col, db
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from bson.objectid import ObjectId
from datetime import datetime
import re
import os
import smtplib
import secrets
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- CONFIGURACIÓN INICIAL ---
app = Flask(__name__, template_folder='../templates', static_folder='../static')
app.secret_key = "clave_secreta_edusync"

# Configuración de carpetas
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'chats'), exist_ok=True)

# Colecciones
tasks_col = db['tareas']
messages_col = db['mensajes']
groups_col = db['grupos']
files_col = db['archivos']

# --- CONFIGURACIÓN SMTP GMAIL ---
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = "al222411609@gmail.com" 
SENDER_PASSWORD = "mhjgswvrnuwipmmi" 

def enviar_verificacion(email_usuario, token):
    # IMPORTANTE: Cambia esta URL por tu link de Render cuando lo subas
    url_verificacion = f"https://edusync-8-gug8.onrender.com/verificar/{token}"
    
    mensaje = MIMEMultipart()
    mensaje["From"] = f"EsuSync <{SENDER_EMAIL}>"
    mensaje["To"] = email_usuario
    mensaje["Subject"] = "Verifica tu cuenta - EsuSync"

    cuerpo = f"""
    <html>
      <body style="font-family: sans-serif; border: 1px solid #ddd; padding: 20px; border-radius: 10px;">
        <h2 style="color: #6366f1;">¡Hola! Bienvenido a EsuSync</h2>
        <p>Estás a un paso de activar tu cuenta. Haz clic en el botón de abajo:</p>
        <br>
        <a href="{url_verificacion}" 
           style="background-color: #6366f1; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; font-weight: bold;">
           Verificar mi correo
        </a>
        <br><br>
        <p style="font-size: 0.8em; color: #777;">Si el botón no funciona, copia este enlace: {url_verificacion}</p>
      </body>
    </html>
    """
    mensaje.attach(MIMEText(cuerpo, "html"))

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, email_usuario, mensaje.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"Error SMTP: {e}")
        return False

# --- RUTAS DE NAVEGACIÓN ---

@app.route('/')
def index():
    return render_template('login.html')

@app.route('/register_page')
def register_page():
    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/')
    return render_template('deshboard.html', rol=session.get('rol'), nombre=session.get('nombre'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# --- API DE AUTENTICACIÓN ---

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    email = data.get('email')
    matricula = data.get('matricula')

    if not email or not email.endswith('@gmail.com'):
        return jsonify({"msg": "Solo se permiten correos @gmail.com"}), 400
    
    if users_col.find_one({"$or": [{"email": email}, {"matricula": matricula}]}):
        return jsonify({"msg": "El correo o la matrícula ya están registrados"}), 400

    # Generamos token y hash de contraseña
    token_verificacion = secrets.token_hex(16)
    hashed_pw = generate_password_hash(data['password'])

    user_doc = {
        "nombres": data['nombres'],
        "apellidos": data['apellidos'],
        "email": email,
        "matricula": matricula,
        "password": hashed_pw,
        "rol": data['rol'],
        "foto_perfil": "default.png",
        "fecha_registro": datetime.now(),
        "verificado": False,
        "token_registro": token_verificacion 
    }
    
    users_col.insert_one(user_doc)
    
    if enviar_verificacion(email, token_verificacion):
        return jsonify({"msg": "Registro exitoso. Revisa tu correo."}), 201
    else:
        return jsonify({"msg": "Usuario creado, pero falló el envío del correo de verificación."}), 201

@app.route('/verificar/<token>')
def verificar_cuenta(token):
    user = users_col.find_one({"token_registro": token})
    if user:
        users_col.update_one(
            {"_id": user['_id']},
            {"$set": {"verificado": True}, "$unset": {"token_registro": ""}}
        )
        return render_template('verificacion_exitosa.html')
    return render_template('verificacion_fallida.html'), 400

@app.route('/api/login', methods=['POST'])
def login():
    # Usamos .form porque tu HTML envía un formulario tradicional
    email = request.form.get('email')
    password = request.form.get('password')

    user = users_col.find_one({"email": email}) 
    
    if user and check_password_hash(user['password'], password):
        if not user.get('verificado', False):
            return "⚠️ Cuenta no verificada. Revisa tu correo.", 403
            
        session['user_id'] = str(user['_id'])
        session['rol'] = user['rol']
        session['nombre'] = user['nombres']
        return redirect(url_for('dashboard'))
    
    return "Correo o contraseña incorrectos", 401

# --- API DE TAREAS Y OTROS ---

@app.route('/api/crear_tarea', methods=['POST'])
def crear_tarea():
    if session.get('rol') != 'docente':
        return jsonify({"msg": "Acceso denegado"}), 403
    data = request.json
    nueva_tarea = {
        "titulo": data['titulo'],
        "descripcion": data['descripcion'],
        "fecha_entrega": data['fecha'],
        "docente_id": session['user_id'],
        "creado_at": datetime.now()
    }
    tasks_col.insert_one(nueva_tarea)
    return jsonify({"msg": "Tarea publicada"}), 201


if __name__ == '__main__':
    app.run(debug=True, port=5000)

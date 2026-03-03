from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from database import users_col, db  # Importamos db para acceder a otras colecciones
from werkzeug.utils import secure_filename
from bson.objectid import ObjectId
from datetime import datetime
import re
import os
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from database import users_col, db 
from werkzeug.utils import secure_filename
from bson.objectid import ObjectId
from datetime import datetime
import re
import os
import smtplib
import secrets
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- CONFIGURACIÓN SMTP GMAIL ---
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = "al222411609@gmail.com" 
SENDER_PASSWORD = "mhjgswvrnuwipmmi" 

def enviar_verificacion(email_usuario, token):
    url_verificacion = f"http://127.0.0.1:5000/verificar/{token}"
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

app = Flask(__name__, template_folder='../templates', static_folder='../static')
app.secret_key = "clave_secreta_edusync"

UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'chats'), exist_ok=True)

tasks_col = db['tareas']
messages_col = db['mensajes']
groups_col = db['grupos']
files_col = db['archivos']

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
    return render_template('deshboard.html', rol=session.get('rol'))

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

    if not email.endswith('@gmail.com'):
        return jsonify({"msg": "Solo se permiten correos @gmail.com"}), 400
    if not re.match(r"^\d{9}$", str(matricula)):
        return jsonify({"msg": "La matrícula debe ser de 9 dígitos"}), 400

    if users_col.find_one({"$or": [{"email": email}, {"matricula": matricula}]}):
        return jsonify({"msg": "El correo o la matrícula ya están registrados"}), 400

    
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
        return jsonify({"msg": "Usuario creado, pero falló el envío del correo."}), 201

@app.route('/verificar/<token>')
def verificar_cuenta(token):
    user = users_col.find_one({"token_registro": token})
    if user:
        users_col.update_one(
            {"_id": user['_id']},
            {"$set": {"verificado": True}, "$unset": {"token_registro": ""}}
        )
        return "<html><body><h1>✅ ¡Cuenta verificada!</h1><p>Ya puedes entrar a EsuSync.</p><a href='/'>Ir al Login</a></body></html>"
    return "<html><body><h1>❌ Enlace no válido</h1></body></html>", 400

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    user = users_col.find_one({"email": data['email']})
    
    if user and check_password_hash(user['password'], data['password']):
        if not user.get('verificado', False):
            return jsonify({"msg": "⚠️ Tu cuenta aún no está verificada. Revisa tu correo."}), 403
            
        session['user_id'] = str(user['_id'])
        session['rol'] = user['rol']
        session['nombre'] = user['nombres']
        return jsonify({"msg": "Bienvenido", "rol": user['rol']}), 200
    
    return jsonify({"msg": "Correo o contraseña incorrectos"}), 401

# --- OTRAS RUTA DE API (TAREAS, GRUPOS, ETC) ---

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

app = Flask(__name__, template_folder='../templates', static_folder='../static')
app.secret_key = "clave_secreta_edusync"

# Configuración de subida de archivos
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'chats'), exist_ok=True)

# Referencias a colecciones adicionales
tasks_col = db['tareas']
messages_col = db['mensajes']



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
    # Pasamos el rol para mostrar diferentes opciones en el mismo HTML o redirigir
    return render_template('deshboard.html', rol=session.get('rol'))

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

    # Validaciones estrictas
    if not email.endswith('@gmail.com'):
        return jsonify({"msg": "Solo se permiten correos @gmail.com"}), 400
    if not re.match(r"^\d{9}$", str(matricula)):
        return jsonify({"msg": "La matrícula debe ser de exactamente 9 dígitos"}), 400

    # Verificar duplicados
    if users_col.find_one({"$or": [{"email": email}, {"matricula": matricula}]}):
        return jsonify({"msg": "El correo o la matrícula ya están registrados"}), 400

    password_plana = data['password']
    user_doc = {
        "nombres": data['nombres'],
        "apellidos": data['apellidos'],
        "email": email,
        "matricula": matricula,
        "password": password_plana,
        "rol": data['rol'],
        "foto_perfil": "default.png",
        "fecha_registro": datetime.now()
    }
    users_col.insert_one(user_doc)
    return jsonify({"msg": "Usuario creado correctamente"}), 201

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    user = users_col.find_one({"email": data['email']})
    
    if user and check_password_hash(user['password'], data['password']):
        session['user_id'] = str(user['_id'])
        session['rol'] = user['rol']
        session['nombre'] = user['nombres']
        return jsonify({"msg": "Bienvenido", "rol": user['rol']}), 200
    
    return jsonify({"msg": "Correo o contraseña incorrectos"}), 401

# --- API DE PERFIL Y ARCHIVOS ---

@app.route('/api/update_profile', methods=['POST'])
def update_profile():
    if 'user_id' not in session:
        return jsonify({"msg": "Sesión expirada"}), 401
    
    user_id = session['user_id']
    nombres = request.form.get('nombres')
    file = request.files.get('foto')
    update_data = {"nombres": nombres}

    if file:
        filename = secure_filename(f"{user_id}_{file.filename}")
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        update_data["foto_perfil"] = filename

    users_col.update_one({"_id": ObjectId(user_id)}, {"$set": update_data})
    return jsonify({"msg": "Datos actualizados"})

# --- API DE TAREAS (DOCENTES) ---

@app.route('/api/crear_tarea', methods=['POST'])
def crear_tarea():
    if session.get('rol') != 'docente':
        return jsonify({"msg": "Acceso denegado"}), 403
    
    data = request.json
    nueva_tarea = {
        "titulo": data['titulo'],
        "descripcion": data['descripcion'],
        "fecha_entrega": data['fecha'],
        "clase": data.get('clase', 'General'),
        "docente_id": session['user_id'],
        "creado_at": datetime.now()
    }
    tasks_col.insert_one(nueva_tarea)
    return jsonify({"msg": "Tarea publicada con éxito"}), 201

@app.route('/api/get_tareas')
def get_tareas():
    tareas = tasks_col.find()
    eventos = []
    for t in tareas:
        eventos.append({
            "title": t['titulo'],
            "start": t['fecha_entrega'],
            "color": "#6366f1", # Color índigo para el calendario
            "extendedProps": {"description": t['descripcion']}
        })
    return jsonify(eventos)

# --- API DE CHAT (ESTUDIANTES) ---

@app.route('/api/enviar_mensaje', methods=['POST'])
def enviar_mensaje():
    if session.get('rol') != 'estudiante':
        return jsonify({"msg": "Solo estudiantes pueden chatear"}), 403
    
    file = request.files.get('archivo')
    texto = request.form.get('texto')
    
    mensaje_doc = {
        "remitente": session['nombre'],
        "remitente_id": session['user_id'],
        "texto": texto,
        "fecha": datetime.now().strftime("%H:%M"),
        "archivo_url": None
    }

    if file:
        filename = secure_filename(file.filename)
        path = os.path.join(app.config['UPLOAD_FOLDER'], 'chats', filename)
        file.save(path)
        mensaje_doc["archivo_url"] = f"/static/uploads/chats/{filename}"

    messages_col.insert_one(mensaje_doc)
    return jsonify({"msg": "Enviado"})
    groups_col = db['grupos']
files_col = db['archivos'] # Para que aparezcan en "Mis Archivos"
# --- API DE GRUPOS Y GESTIÓN ---

@app.route('/api/crear_grupo', methods=['POST'])
def crear_grupo():
    if 'user_id' not in session:
        return jsonify({"msg": "Inicia sesión"}), 401
    
    data = request.json
    nombre_grupo = data.get('nombre')
    primer_invitado = data.get('invitado') # Correo del compañero

    # Creamos el documento del grupo
    nuevo_grupo = {
        "nombre": nombre_grupo,
        "admin_id": session['user_id'],
        "admin_nombre": session['nombre'],
        "miembros": [session['user_id']], # Empezamos con el creador
        "miembros_correos": [session.get('email')], # Opcional para facilitar búsqueda
        "fecha_creacion": datetime.now(),
        "mensajes": []
    }

    # Si invitó a alguien, buscamos su ID por correo
    invitado_doc = users_col.find_one({"email": primer_invitado})
    if invitado_doc:
        nuevo_grupo["miembros"].append(str(invitado_doc['_id']))
    
    result = groups_col.insert_one(nuevo_grupo)
    return jsonify({"msg": "Grupo creado", "id": str(result.inserted_id)}), 201

@app.route('/api/mis_grupos')
def mis_grupos():
    if 'user_id' not in session: return jsonify([]), 401
    
    # Buscamos grupos donde el ID del usuario esté en la lista de miembros
    mis_grupos = groups_col.find({"miembros": session['user_id']})
    
    lista = []
    for g in mis_grupos:
        lista.append({
            "id": str(g['_id']),
            "nombre": g['nombre'],
            "es_admin": g['admin_id'] == session['user_id'],
            "admin_nombre": g['admin_nombre']
        })
    return jsonify(lista)

@app.route('/api/agregar_miembro', methods=['POST'])
def agregar_miembro():
    data = request.json
    grupo_id = data.get('grupo_id')
    correo_nuevo = data.get('email')

    # Solo el admin puede agregar (validación de seguridad)
    grupo = groups_col.find_one({"_id": ObjectId(grupo_id)})
    if grupo['admin_id'] != session['user_id']:
        return jsonify({"msg": "No eres el administrador"}), 403

    usuario_nuevo = users_col.find_one({"email": correo_nuevo})
    if not usuario_nuevo:
        return jsonify({"msg": "Usuario no encontrado"}), 404

    groups_col.update_one(
        {"_id": ObjectId(grupo_id)},
        {"$addToSet": {"miembros": str(usuario_nuevo['_id'])}}
    )
    return jsonify({"msg": "Miembro agregado"})

@app.route('/api/eliminar_grupo/<id>', methods=['DELETE'])
def eliminar_grupo(id):
    grupo = groups_col.find_one({"_id": ObjectId(id)})
    if grupo['admin_id'] == session['user_id']:
        groups_col.delete_one({"_id": ObjectId(id)})
        return jsonify({"msg": "Grupo eliminado"})
    return jsonify({"msg": "No tienes permiso"}), 403

@app.route('/verificar/<token>')
def verificar_cuenta(token):
    # Buscamos al usuario por su token
    user = users_col.find_one({"token_registro": token})
    
    if user:
        # Activamos la cuenta en MongoDB
        users_col.update_one(
            {"_id": user['_id']},
            {"$set": {"verificado": True}, "$unset": {"token_registro": ""}}
        )
        # ESTA ES LA LÍNEA CLAVE: Renderiza el archivo HTML con estilos
        return render_template('verificacion_exitosa.html')
    else:
        # Si el token no sirve, puedes mandar a una página de error o al login
        return render_template('verificacion_fallida.html'), 400

    
if __name__ == '__main__':
    app.run(debug=True, port=5000)


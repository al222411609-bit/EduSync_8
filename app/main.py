from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from app.database import users_col, db 
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from bson.objectid import ObjectId
from datetime import datetime
import os
import smtplib
import secrets
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- CONFIGURACIÓN DE RUTAS ---
base_dir = os.path.abspath(os.path.dirname(_file_))
app = Flask(_name_, 
            template_folder=os.path.join(base_dir, 'templates'), 
            static_folder=os.path.join(base_dir, 'static'))

app.secret_key = "clave_secreta_edusync"

# --- CONFIGURACIÓN DE CARPETAS ---
UPLOAD_BASE = os.path.join(base_dir, 'static/uploads')
app.config['UPLOAD_FILES'] = os.path.join(UPLOAD_BASE, 'mis_archivos')
app.config['UPLOAD_TAREAS'] = os.path.join(UPLOAD_BASE, 'entregas_tareas')
app.config['UPLOAD_PERFILES'] = os.path.join(UPLOAD_BASE, 'perfiles')

os.makedirs(app.config['UPLOAD_FILES'], exist_ok=True)
os.makedirs(app.config['UPLOAD_TAREAS'], exist_ok=True)
os.makedirs(app.config['UPLOAD_PERFILES'], exist_ok=True)
os.makedirs(os.path.join(UPLOAD_BASE, 'chats'), exist_ok=True)

# --- COLECCIONES MONGODB ---
tasks_col = db['tareas']
messages_col = db['mensajes']
groups_col = db['grupos']
files_col = db['archivos_usuario']
comments_col = db['comentarios_privados']
submissions_col = db['entregas_tareas']

# --- CONFIGURACIÓN SMTP GMAIL ---
SENDER_EMAIL = "al222411609@gmail.com" 
SENDER_PASSWORD = "mhjgswvrnuwipmmi" 

def enviar_correo(receptor, asunto, cuerpo_html):
    mensaje = MIMEMultipart()
    mensaje["From"] = f"EsuSync <{SENDER_EMAIL}>"
    mensaje["To"] = receptor
    mensaje["Subject"] = asunto
    mensaje.attach(MIMEText(cuerpo_html, "html"))
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, receptor, mensaje.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"Error SMTP: {e}")
        return False

# --- RUTAS DE NAVEGACIÓN (VISTAS) ---

@app.route('/')
def index():
    return render_template('login.html')

@app.route('/register_page')
def register_page():
    return render_template('register.html')

@app.route('/forgot_password_page')
def forgot_password_page():
    return render_template('forgot_password.html')

@app.route('/reset_password/<token>')
def reset_password_page(token):
    user = users_col.find_one({"token_recuperacion": token})
    if user:
        return render_template('reset_password_form.html', token=token)
    return "<h1>Enlace inválido o expirado</h1>", 400

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session: return redirect('/')
    
    # Obtener datos frescos del usuario para mostrar en el Dashboard
    user = users_col.find_one({"_id": ObjectId(session['user_id'])})
    if not user: return redirect('/logout')
    
    foto_perfil = user.get('foto_perfil', 'default.png')
    # Construir la URL de la foto
    if not foto_perfil.startswith('http'):
        foto_url = url_for('static', filename='uploads/perfiles/' + foto_perfil)
    else:
        foto_url = foto_perfil

    return render_template('deshboard.html', 
                           rol=user.get('rol'), 
                           nombre=user.get('nombres'), 
                           email=user.get('email'),
                           foto=foto_url)

@app.route('/mis_archivos')
def vista_archivos():
    if 'user_id' not in session: return redirect('/')
    return render_template('mis_archivos.html', rol=session.get('rol'), nombre=session.get('nombre'))

@app.route('/clase/<id_grupo>')
def vista_clase(id_grupo):
    if 'user_id' not in session: return redirect('/')
    try:
        grupo = groups_col.find_one({"_id": ObjectId(id_grupo)})
        if not grupo: return "Clase no encontrada", 404
        return render_template('clase_detalle.html', grupo=grupo, rol=session.get('rol'), nombre=session.get('nombre'))
    except: return "ID de Clase inválido", 400

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# --- API DE PERFIL ---

@app.route('/api/update_profile', methods=['POST'])
def update_profile():
    if 'user_id' not in session: return jsonify({"msg": "No autorizado"}), 401
    
    user_id = session['user_id']
    nuevo_nombre = request.form.get('nombre')
    nuevo_email = request.form.get('email')
    foto = request.files.get('foto')
    
    update_data = {
        "nombres": nuevo_nombre,
        "email": nuevo_email
    }

    if foto and foto.filename != '':
        filename = secure_filename(f"profile_{user_id}_{foto.filename}")
        foto.save(os.path.join(app.config['UPLOAD_PERFILES'], filename))
        update_data["foto_perfil"] = filename

    users_col.update_one({"_id": ObjectId(user_id)}, {"$set": update_data})
    session['nombre'] = nuevo_nombre # Actualizar nombre en sesión
    
    return jsonify({"msg": "Perfil actualizado correctamente", "nombre": nuevo_nombre})

# --- API DE AUTENTICACIÓN ---

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    email = data.get('email')
    matricula = data.get('matricula')
    password_plana = data.get('password')

    if not email.endswith('@gmail.com'): return jsonify({"msg": "Solo correos @gmail.com"}), 400
    if users_col.find_one({"$or": [{"email": email}, {"matricula": matricula}]}):
        return jsonify({"msg": "Correo o matrícula ya registrados"}), 400

    hashed_pw = generate_password_hash(password_plana)
    token_verificacion = secrets.token_urlsafe(32)

    user_doc = {
        "nombres": data['nombres'], "apellidos": data.get('apellidos', ''),
        "email": email, "matricula": matricula, "password": hashed_pw,
        "rol": data['rol'], "verificado": False, "token_registro": token_verificacion,
        "foto_perfil": "default.png", "fecha_registro": datetime.now()
    }
    users_col.insert_one(user_doc)
    
    link = f"http://127.0.0.1:5000/verificar/{token_verificacion}"
    html = f"<h2>Bienvenido</h2><p>Verifica tu cuenta aquí:</p><a href='{link}'>Verificar cuenta</a>"
    enviar_correo(email, "Verifica tu cuenta - EsuSync", html)
    return jsonify({"msg": "Registro exitoso. Revisa tu correo."}), 201

@app.route('/verificar/<token>')
def verificar_cuenta(token):
    user = users_col.find_one({"token_registro": token})
    if user:
        users_col.update_one({"_id": user['_id']}, {"$set": {"verificado": True}, "$unset": {"token_registro": ""}})
        return "<h1>Cuenta verificada correctamente. Ya puedes iniciar sesión.</h1>"
    return "<h1>Token inválido</h1>", 400

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    user = users_col.find_one({"email": data['email']})
    if user and check_password_hash(user['password'], data['password']):
        if not user.get('verificado', False):
            return jsonify({"msg": "⚠️ Cuenta no verificada.", "needs_verification": True}), 403
        session['user_id'] = str(user['_id'])
        session['rol'] = user['rol']
        session['nombre'] = user['nombres']
        return jsonify({"msg": "Bienvenido", "rol": user['rol']}), 200
    return jsonify({"msg": "Correo o contraseña incorrectos"}), 401

@app.route('/api/forgot_password', methods=['POST'])
def forgot_password():
    data = request.json
    email = data.get('email')
    user = users_col.find_one({"email": email})
    if user:
        token = secrets.token_urlsafe(32)
        users_col.update_one({"_id": user['_id']}, {"$set": {"token_recuperacion": token}})
        link = f"http://127.0.0.1:5000/reset_password/{token}"
        html = f"<h2>Recuperación</h2><p>Haz clic para cambiar tu clave:</p><a href='{link}'>Restablecer Contraseña</a>"
        enviar_correo(email, "Recupera tu contraseña - EsuSync", html)
    return jsonify({"msg": "Si el correo existe, recibirás un enlace pronto."}), 200

@app.route('/api/reset_password', methods=['POST'])
def reset_password_action():
    data = request.json
    token = data.get('token')
    nueva_pass = data.get('password')
    user = users_col.find_one({"token_recuperacion": token})
    if user:
        hashed_pw = generate_password_hash(nueva_pass)
        users_col.update_one({"_id": user['_id']}, {"$set": {"password": hashed_pw}, "$unset": {"token_recuperacion": ""}})
        return jsonify({"msg": "Contraseña actualizada."}), 200
    return jsonify({"msg": "Error: Token inválido"}), 400

# --- API DE ARCHIVOS PERSONALES ---

@app.route('/api/subir_archivo', methods=['POST'])
def subir_archivo():
    if 'user_id' not in session: return jsonify({"msg": "No autorizado"}), 401
    file = request.files.get('archivo')
    if not file: return jsonify({"msg": "No se seleccionó archivo"}), 400
    filename = secure_filename(file.filename)
    user_id = session['user_id']
    user_folder = os.path.join(app.config['UPLOAD_FILES'], user_id)
    os.makedirs(user_folder, exist_ok=True)
    file_path = os.path.join(user_folder, filename)
    file.save(file_path)
    file_doc = {
        "user_id": user_id, "nombre": filename, "extension": filename.split('.')[-1].lower(),
        "tamano": os.path.getsize(file_path), "fecha": datetime.now(),
        "url": f"/static/uploads/mis_archivos/{user_id}/{filename}"
    }
    files_col.insert_one(file_doc)
    return jsonify({"msg": "Archivo subido correctamente"}), 200

@app.route('/api/get_mis_archivos')
def get_mis_archivos():
    if 'user_id' not in session: return jsonify([]), 401
    archivos = list(files_col.find({"user_id": session['user_id']}).sort("fecha", -1))
    for a in archivos:
        a['_id'] = str(a['_id'])
        a['fecha_fmt'] = a['fecha'].strftime("%d/%m/%Y %H:%M")
        a['tamano_fmt'] = f"{round(a['tamano']/1024, 1)} KB"
    return jsonify(archivos)

@app.route('/api/eliminar_archivo/<id>', methods=['DELETE'])
def eliminar_archivo(id):
    if 'user_id' not in session: return jsonify({"msg": "No autorizado"}), 401
    file_data = files_col.find_one({"_id": ObjectId(id), "user_id": session['user_id']})
    if file_data:
        try:
            ruta_relativa = file_data['url'].lstrip('/')
            ruta_fisica = os.path.join(base_dir, ruta_relativa)
            if os.path.exists(ruta_fisica): os.remove(ruta_fisica)
        except Exception as e: print(f"Error borrar físico: {e}")
        files_col.delete_one({"_id": ObjectId(id)})
        return jsonify({"msg": "Archivo eliminado"}), 200
    return jsonify({"msg": "No se encontró el archivo"}), 404

# --- SISTEMA DE CLASES, TAREAS Y COMUNICACIÓN ---

@app.route('/api/crear_grupo', methods=['POST'])
def crear_grupo():
    if session.get('rol') != 'docente': return jsonify({"msg": "No autorizado"}), 401
    data = request.json
    res = groups_col.insert_one({
        "nombre": data.get('nombre'), "admin_id": session['user_id'],
        "miembros": [session['user_id']], "fecha_creacion": datetime.now()
    })
    return jsonify({"msg": "Grupo creado", "id": str(res.inserted_id)})

@app.route('/api/unirse_grupo', methods=['POST'])
def unirse_grupo():
    if 'user_id' not in session: return jsonify({"msg": "No autorizado"}), 401
    codigo = request.json.get('codigo', '').strip()
    try:
        grupo = groups_col.find_one({"_id": ObjectId(codigo)})
        if not grupo: return jsonify({"msg": "Clase no encontrada"}), 404
        groups_col.update_one({"_id": ObjectId(codigo)}, {"$addToSet": {"miembros": session['user_id']}})
        return jsonify({"msg": f"¡Te has unido a {grupo['nombre']}!"}), 200
    except: return jsonify({"msg": "Código inválido"}), 400

@app.route('/api/mis_grupos')
def mis_grupos():
    if 'user_id' not in session: return jsonify([]), 401
    grupos = list(groups_col.find({"miembros": session['user_id']}))
    resultado = []
    for g in grupos:
        resultado.append({
            "id": str(g['_id']), 
            "nombre": g['nombre'],
            "autor": "Docente Titular"
        })
    return jsonify(resultado)

@app.route('/api/crear_tarea', methods=['POST'])
def crear_tarea():
    if session.get('rol') != 'docente': return jsonify({"msg": "No autorizado"}), 401
    data = request.json
    tasks_col.insert_one({
        "grupo_id": data['grupo_id'], "titulo": data['titulo'],
        "descripcion": data['descripcion'], "fecha_entrega": data['fecha'],
        "docente_id": session['user_id'], "creado_at": datetime.now()
    })
    return jsonify({"msg": "Tarea publicada"})

@app.route('/api/get_tareas/<id_grupo>')
def get_tareas(id_grupo):
    tareas = list(tasks_col.find({"grupo_id": id_grupo}).sort("creado_at", -1))
    for t in tareas: t['_id'] = str(t['_id'])
    return jsonify(tareas)

@app.route('/api/chat/enviar', methods=['POST'])
def enviar_chat():
    data = request.json
    messages_col.insert_one({
        "grupo_id": data['grupo_id'], "remitente": session['nombre'],
        "user_id": session['user_id'], "texto": data['texto'],
        "fecha": datetime.now().strftime("%H:%M"), "timestamp": datetime.now()
    })
    return jsonify({"status": "ok"})

@app.route('/api/chat/get/<id_grupo>')
def get_chat(id_grupo):
    msgs = list(messages_col.find({"grupo_id": id_grupo}).sort("timestamp", 1))
    for m in msgs: m['_id'] = str(m['_id'])
    return jsonify(msgs)

@app.route('/api/comentario/privado', methods=['POST'])
def comentario_privado():
    data = request.json
    comments_col.insert_one({
        "tarea_id": data['tarea_id'], "user_id": session['user_id'],
        "nombre": session['nombre'], "texto": data['texto'], "fecha": datetime.now()
    })
    return jsonify({"msg": "Comentario enviado"})

@app.route('/api/tarea/subir', methods=['POST'])
def subir_tarea():
    file = request.files.get('archivo')
    tarea_id = request.form.get('tarea_id')
    if file and tarea_id:
        filename = secure_filename(file.filename)
        folder = os.path.join(app.config['UPLOAD_TAREAS'], tarea_id)
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, f"{session['user_id']}_{filename}")
        file.save(path)
        submissions_col.update_one(
            {"tarea_id": tarea_id, "user_id": session['user_id']},
            {"$set": {"archivo": filename, "fecha": datetime.now(), "url": path}}, upsert=True
        )
        return jsonify({"msg": "Tarea entregada correctamente"})
    return jsonify({"msg": "Error al subir archivo"}), 400

if _name_ == '_main_':
    app.run(debug=True, port=5000)
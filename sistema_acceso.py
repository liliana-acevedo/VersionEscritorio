import customtkinter as ctk
from cliente_supabase import supabase
import tkinter as tk
from datetime import datetime, timedelta
import threading
import pandas as pd
from tkinter import filedialog, messagebox
from openpyxl import Workbook
from openpyxl.drawing.image import Image as OpenpyxlImage 
from openpyxl.utils import get_column_letter
from openpyxl.styles import Font, Border, Side, Alignment, PatternFill
from openpyxl.styles.borders import BORDER_THIN
import os
from PIL import Image as PILImage 


# Referencias Globales de la Interfaz 
cedula_entry = None
notificacion = None
app_root = None

# Referencias para la Pantalla 'Agregar Usuario' 
registro_entries = {}
registro_notificacion = None

# Referencias para la Pantalla 'Agregar Departamento'
depto_entry = None
depto_notificacion = None


# Funciones de Utilidad
def _clear_widgets(root):
    for widget in root.winfo_children():
        widget.destroy()


def formatear_fecha(iso_fecha_str):
    if not iso_fecha_str:
        return "Pendiente"
    try:
        dt_obj = datetime.fromisoformat(iso_fecha_str)
        return dt_obj.strftime("%d/%m/%Y %H:%M")
    except Exception:
        return str(iso_fecha_str)


#  Carga de Datos Estructurales (Departamentos y Roles)
def obtener_departamentos():
    departamentos_map = {}
    try:
        resp = supabase.table("Departamento").select("id_departamento, nombre_departamento").execute()
        for item in resp.data or []:
            nombre = item.get("nombre_departamento") or ""
            idd = item.get("id_departamento")
            if nombre and idd is not None:
                departamentos_map[str(nombre)] = idd
    except Exception as e:
        print("Error al obtener departamentos:", e)
    return departamentos_map


def obtener_roles():
    roles_map = {}
    try:
        resp = supabase.table("Rol").select("id_rol, nombre_rol").execute()
        for item in resp.data or []:
            nombre = item.get("nombre_rol") or ""
            idd = item.get("id_rol")
            if nombre and idd is not None:
                roles_map[str(nombre)] = idd
    except Exception as e:
        print("Error al obtener roles:", e)
    return roles_map


# Manejo Seguro de Notificaciones
def _set_registro_notificacion(text, color):
    global registro_notificacion, app_root
    if not registro_notificacion or not app_root:
        print("Aviso: registro_notificacion o app_root no inicializado.")
        return
    app_root.after(0, lambda: registro_notificacion.configure(text=text, text_color=color))

def _set_depto_notificacion(text, color):
    global depto_notificacion, app_root
    if not depto_notificacion or not app_root:
        print("Aviso: depto_notificacion o app_root no inicializado.")
        return
    app_root.after(0, lambda: depto_notificacion.configure(text=text, text_color=color))

def _clear_registro_campos():
    global registro_entries, app_root
    if not app_root:
        return
    def _clear():
        for k in ['cedula', 'nombre', 'apellido']:
            ent = registro_entries.get(k)
            if ent:
                try:
                    ent.delete(0, 'end')
                except Exception:
                    pass
    app_root.after(0, _clear)


# PANTALLA: AGREGAR NUEVO DEPARTAMENTO

def agregar_departamento_db(root, nombre_depto):
    
    global depto_entry
    
    _set_depto_notificacion("Guardando...", "#1E3D8F")
    
    try:
        # Intenta insertar el nuevo departamento en la tabla "Departamento"
        response = supabase.table('Departamento').insert({'nombre_departamento': nombre_depto}).execute()

        if response.data:
            _set_depto_notificacion("Departamento agregado con éxito!", "#16A34A")
            root.after(0, lambda: depto_entry.delete(0, 'end'))
        else:
            print("Respuesta inserción depto:", response)
            _set_depto_notificacion("Error al agregar departamento (respuesta vacía).", "red")

    except Exception as e:
        error_msg = str(e)
        print("Error DB al agregar departamento:", error_msg)
        if "Duplicate key value" in error_msg or "unique constraint" in error_msg:
             _set_depto_notificacion("Error: El departamento ya existe.", "red")
        else:
            _set_depto_notificacion(f"Error DB: {error_msg[:50]}...", "red")

def _on_agregar_depto(root):
    global depto_entry
    if not depto_entry:
        return
        
    nombre_depto = (depto_entry.get() or "").strip()
    
    if not nombre_depto:
        _set_depto_notificacion("El nombre no puede estar vacío.", "orange")
        return
        

    threading.Thread(target=agregar_departamento_db, args=(root, nombre_depto,), daemon=True).start()


def mostrar_pantalla_agregar_departamento(root):
    
    """Configura y muestra la interfaz para agregar un nuevo departamento."""
    
    global depto_entry, depto_notificacion, app_root
    app_root = root
    _clear_widgets(root)
    root.title("Agregar Nuevo Departamento")


    main_frame = ctk.CTkFrame(root, fg_color="#F7F9FB")
    main_frame.pack(expand=True, fill="both")
    main_frame.grid_rowconfigure(1, weight=1)
    main_frame.grid_columnconfigure(0, weight=1)

    
    header_frame = ctk.CTkFrame(main_frame, fg_color="#0C4A6E", corner_radius=0, height=70)
    header_frame.grid(row=0, column=0, sticky="ew")
    header_frame.grid_columnconfigure(1, weight=1) 
    header_frame.grid_columnconfigure(2, weight=0) 

    ctk.CTkLabel(header_frame, text="Agregar Nuevo Departamento",
                 font=ctk.CTkFont(size=22, weight="bold"),
                 text_color="white").grid(row=0, column=1, padx=(30, 20), pady=15, sticky="w")

    # Botón VOLVER (Vuelve a la pantalla principal)
    ctk.CTkButton(header_frame, text="VOLVER", fg_color="#3D89D1",
                  hover_color="#1E3D8F",
                  font=ctk.CTkFont(size=13, weight="bold"),
                  corner_radius=8, width=120, height=40,
                  command=lambda: mostrar_pantalla_principal(root)).grid(row=0, column=2, padx=(10, 20), pady=12, sticky="e")

    # Formulario central
    form_frame = ctk.CTkFrame(main_frame, fg_color="#FFFFFF", corner_radius=10)
    form_frame.grid(row=1, column=0, pady=20, padx=20, ipadx=20, ipady=20, sticky="n")

    ctk.CTkLabel(form_frame, text="Ingrese el nombre del departamento", font=ctk.CTkFont(size=16, weight="bold"), text_color="#1E3D8F").pack(pady=(10, 15))

    # Entrada para el nombre del departamento
    depto_entry = ctk.CTkEntry(
        form_frame,
        placeholder_text="Nombre del Departamento",
        width=320,
        height=38,
        font=ctk.CTkFont(size=14)
    )
    depto_entry.pack(pady=8, padx=20)

    depto_notificacion = ctk.CTkLabel(form_frame, text="", font=ctk.CTkFont(size=13, weight="bold"))
    depto_notificacion.pack(pady=8)

    # Botón de agregar departamento
    ctk.CTkButton(
        form_frame,
        text="AGREGAR DEPARTAMENTO",
        fg_color="#16A34A", 
        hover_color="#15803D",
        font=ctk.CTkFont(size=14, weight="bold"),
        width=320,
        height=42,
        command=lambda: _on_agregar_depto(root)
    ).pack(pady=(10, 10))


# REGISTRO DE USUARIO
def registrar_usuario(root, roles_map, departamentos_map):
  
    global registro_entries

    cedula_val = (registro_entries.get('cedula').get() or "").strip()
    nombre_val = (registro_entries.get('nombre').get() or "").strip()
    apellido_val = (registro_entries.get('apellido').get() or "").strip()
    rol_nombre = (registro_entries.get('rol').get() or "").strip()
    depto_nombre = (registro_entries.get('departamento').get() or "").strip()


    if not cedula_val or not nombre_val or not apellido_val:
        _set_registro_notificacion("Faltan campos obligatorios (Cédula, Nombre, Apellido).", "orange")
        return

    if not cedula_val.isdigit() or len(cedula_val) < 4:
        _set_registro_notificacion("Cédula inválida o muy corta.", "orange")
        return

    if rol_nombre not in roles_map or depto_nombre not in departamentos_map:
        _set_registro_notificacion("Rol/Departamento no válido. Intente recargar.", "red")
        return

    # Verificar si la cédula ya existe 
    try:
        dup_resp = supabase.table("Usuario").select("cedula").eq("cedula", cedula_val).execute()
        if dup_resp.data:
            _set_registro_notificacion("Error: La cédula ya está registrada.", "red")
            return
    except Exception as e:
        print("Error comprobando duplicado de cédula:", e)
        _set_registro_notificacion("Error en verificación de cédula.", "red")
        return

    # Preparar datos y ejecutar la inserción
    datos_usuario = {
        'cedula': cedula_val,
        'nombre': nombre_val,
        'apellido': apellido_val,
        'departamento': departamentos_map[depto_nombre],
        'rol': roles_map[rol_nombre],
    }

    _set_registro_notificacion("Registrando usuario...", "#1E3D8F")

    try:
        resp = supabase.table("Usuario").insert([datos_usuario]).execute()
        
        if resp.data:
            _set_registro_notificacion("Usuario registrado con éxito!", "#16A34A")
            _clear_registro_campos()
        else:
            print("Respuesta inserción:", resp)
            _set_registro_notificacion("Error al registrar usuario (respuesta vacía).", "red")
    except Exception as e:
        print("Error al insertar usuario:", e)
        msg = str(e)
        if "duplicate" in msg.lower() or "duplicate key" in msg.lower():
            # Error de duplicado capturado durante la inserción (doble chequeo)
            _set_registro_notificacion("Error: La cédula ya existe.", "red")
        else:
            _set_registro_notificacion(f"Error DB: {msg[:80]}", "red")


# VALIDACIÓN DE CÉDULA (Login)
def validar_cedula():
    global cedula_entry, notificacion, app_root
    if not cedula_entry or notificacion is None or app_root is None:
        print("Error: UI no inicializada correctamente.")
        return

    cedula = cedula_entry.get().strip()
    
    if not cedula:
        notificacion.configure(text="Ingrese la cédula", text_color="orange")
        return

    if not cedula.isdigit() or len(cedula) < 4:
        notificacion.configure(text="Cédula inválida o muy corta.", text_color="orange")
        return

    threading.Thread(target=_async_validar_cedula, args=(cedula,), daemon=True).start()


def _async_validar_cedula(cedula):

    global notificacion, app_root
    if not app_root:
        return

    app_root.after(0, lambda: notificacion.configure(text="Verificando credenciales...", text_color="#1E3D8F"))

    try:
        # Consulta la tabla "Usuario"
        resp = supabase.table("Usuario").select("cedula, rol").eq("cedula", cedula).execute()
        usuarios = resp.data or []
        
        if not usuarios:
            app_root.after(0, lambda: notificacion.configure(text="Usuario incorrecto", text_color="red"))
            return

        # Si todo es correcto, pasa a la pantalla principal
        app_root.after(0, lambda: notificacion.configure(text="Ingresando...", text_color="#16A34A"))
        app_root.after(1200, lambda: mostrar_pantalla_principal(app_root))

    except Exception as e:
        print("Error validando cédula:", e)
        app_root.after(0, lambda: notificacion.configure(text="Error de conexión o base de datos", text_color="purple"))

def cerrar_sesion(root):
    setup_login_app(root)


# Mapas de Datos y Lógica de Servicios
def map_usuarios_por_cedula():
    """Crea un mapa que relaciona la cédula con el nombre completo (para mostrar en la lista de servicios)."""
    try:
        resp = supabase.table("Usuario").select("cedula, nombre, apellido").execute()
        usuarios = resp.data or []
        mapa = {}
        for u in usuarios:
            ced = u.get("cedula")
            nombre = (u.get("nombre") or "").strip()
            apellido = (u.get("apellido") or "").strip()
            if ced:
                mapa[str(ced)] = f"{nombre} {apellido}".strip() or str(ced)
        return mapa
    except Exception as e:
        print("Error al obtener usuarios:", e)
        return {}


def traducir_estado(valor):
    return {1: "Pendiente", 2: "Completado", 3: "Recibido"}.get(int(valor), "Desconocido") if valor else "Desconocido"


def obtener_servicios_filtrados_base(query_builder):
    try:
        resp = query_builder.execute()
        servicios = resp.data or []

        # Obtener todos los departamentos (id → nombre)
        departamentos = supabase.table("Departamento").select("id_departamento, nombre_departamento").execute().data or []
        dep_map = {str(d["id_departamento"]): d["nombre_departamento"] for d in departamentos}

        for s in servicios:
            dep_val = s.get("departamento")

            if isinstance(dep_val, (int, float)) or (isinstance(dep_val, str) and dep_val.isdigit()):
                s["Departamento"] = dep_map.get(str(dep_val), "Desconocido")

            elif isinstance(dep_val, str):
                s["Departamento"] = dep_val.strip()

            else:
                s["Departamento"] = "Desconocido"

        return servicios

    except Exception as e:
        print("Error obtener servicios:", e)
        
        return []



# --- PANTALLA DE REGISTRO DE USUARIO ---
def mostrar_pantalla_registro(root):
 
    global registro_entries, registro_notificacion, app_root
    app_root = root
    _clear_widgets(root)
    root.title("Registro de Usuario")

    departamentos_map = obtener_departamentos()  # {nombre: id}
    roles_map = obtener_roles()  # {nombre: id}
    departamento_names = list(departamentos_map.keys())
    rol_names = list(roles_map.keys())

    main_frame = ctk.CTkFrame(root, fg_color="#F7F9FB")
    main_frame.pack(expand=True, fill="both")
    main_frame.grid_rowconfigure(1, weight=1)
    main_frame.grid_columnconfigure(0, weight=1)

    header_frame = ctk.CTkFrame(main_frame, fg_color="#0C4A6E", corner_radius=0, height=70)
    header_frame.grid(row=0, column=0, sticky="ew")
    header_frame.grid_columnconfigure(1, weight=1) # Título
    header_frame.grid_columnconfigure(2, weight=0) # Botón VOLVER

    ctk.CTkLabel(header_frame, text="Registro de Nuevo Usuario",
                 font=ctk.CTkFont(size=22, weight="bold"),
                 text_color="white").grid(row=0, column=1, padx=(30, 20), pady=15, sticky="w")

    # Botón VOLVER
    ctk.CTkButton(header_frame, text="VOLVER", fg_color="#3D89D1",
                  hover_color="#1E3D8F",
                  font=ctk.CTkFont(size=13, weight="bold"),
                  corner_radius=8, width=120, height=40,
                  command=lambda: mostrar_pantalla_principal(root)).grid(row=0, column=2, padx=(10, 20), pady=12, sticky="e")

    # Formulario central
    form_frame = ctk.CTkFrame(main_frame, fg_color="#FFFFFF", corner_radius=10)
    form_frame.grid(row=1, column=0, pady=20, padx=20, ipadx=20, ipady=20, sticky="n")

    ctk.CTkLabel(form_frame, text="Complete los campos", font=ctk.CTkFont(size=16, weight="bold"), text_color="#1E3D8F").pack(pady=10)

    # Entradas de datos (Cédula, Nombre, Apellido)
    registro_entries = {}
    cedula_ent = ctk.CTkEntry(form_frame, placeholder_text="Cédula de Identidad", width=320, height=38, font=ctk.CTkFont(size=14))
    cedula_ent.pack(pady=8)
    registro_entries['cedula'] = cedula_ent

    nombre_ent = ctk.CTkEntry(form_frame, placeholder_text="Nombre", width=320, height=38, font=ctk.CTkFont(size=14))
    nombre_ent.pack(pady=8)
    registro_entries['nombre'] = nombre_ent

    apellido_ent = ctk.CTkEntry(form_frame, placeholder_text="Apellido", width=320, height=38, font=ctk.CTkFont(size=14))
    apellido_ent.pack(pady=8)
    registro_entries['apellido'] = apellido_ent

   
    ctk.CTkLabel(form_frame, text="Departamento:", text_color="#1E1E1E").pack(pady=(10, 0))
    departamento_vals = departamento_names if departamento_names else ["-- Sin departamentos --"]
    depto_combo = ctk.CTkComboBox(form_frame, values=departamento_vals, width=320)
    if departamento_names:
        depto_combo.set(departamento_names[0])
    else:
        depto_combo.set("-- Sin departamentos --")
    depto_combo.pack(pady=(4, 10))
    registro_entries['departamento'] = depto_combo

 
    ctk.CTkLabel(form_frame, text="Rol:", text_color="#1E1E1E").pack(pady=(10, 0))
    rol_vals = rol_names if rol_names else ["-- Sin roles --"]
    rol_combo = ctk.CTkComboBox(form_frame, values=rol_vals, width=320)
    if rol_names:
        default_rol = "Usuario Estándar" if "Usuario Estándar" in rol_names else rol_names[0]
        rol_combo.set(default_rol)
    else:
        rol_combo.set("-- Sin roles --")
    rol_combo.pack(pady=(4, 10))
    registro_entries['rol'] = rol_combo


    registro_notificacion = ctk.CTkLabel(form_frame, text="", font=ctk.CTkFont(size=13, weight="bold"))
    registro_notificacion.pack(pady=8)

  
    def _on_registrar():
        deps = obtener_departamentos()
        roles = obtener_roles()
        threading.Thread(target=registrar_usuario, args=(root, roles, deps), daemon=True).start()

    # Botón REGISTRAR
    ctk.CTkButton(form_frame, text="REGISTRAR", fg_color="#16A34A", hover_color="#15803D",
                  font=ctk.CTkFont(size=14, weight="bold"), width=320, height=42,
                  command=_on_registrar).pack(pady=(10, 6))


#===================================================================================================================================0000000000000000000000000000000
#==================================================================================================================================================================
# PANTALLA PRINCIPAL (Lista de Servicios) 
def mostrar_pantalla_principal(root):
    _clear_widgets(root)

    filtro_estado = tk.StringVar(value="Todos")
    filtro_fecha = tk.StringVar(value="Todos")
    
    filtros_especiales = {'tecnico_id': None, 'depto_id': None}

    # Configuración de la Interfaz 
    main_frame = ctk.CTkFrame(root, fg_color="#F7F9FB")
    main_frame.pack(expand=True, fill="both")
    main_frame.grid_rowconfigure(1, weight=1)
    main_frame.grid_columnconfigure(0, weight=1)


    header_frame = ctk.CTkFrame(main_frame, fg_color="#0C4A6E", corner_radius=0, height=70)
    header_frame.grid(row=0, column=0, sticky="ew")
    header_frame.grid_columnconfigure(0, weight=1) # Título
    header_frame.grid_columnconfigure(1, weight=0) # Botón Agregar Departamento
    header_frame.grid_columnconfigure(2, weight=0) # Botón Agregar Usuario
    header_frame.grid_columnconfigure(3, weight=0) # Botón Cerrar Sesión

    ctk.CTkLabel(header_frame, text="GESTIÓN DE SERVICIOS",
                 font=ctk.CTkFont(size=22, weight="bold"), text_color="white").grid(
        row=0, column=0, padx=20, pady=15, sticky="w")

    # Botones de navegación/acción 
    ctk.CTkButton(header_frame, text="AGREGAR DEPARTAMENTO", fg_color="#16A34A",
                  hover_color="#15803D",
                  font=ctk.CTkFont(size=13, weight="bold"),
                  corner_radius=8, width=180, height=40,
                  command=lambda: mostrar_pantalla_agregar_departamento(root)
                  ).grid(row=0, column=1, padx=(10, 5), pady=12, sticky="e")

    ctk.CTkButton(header_frame, text="AGREGAR USUARIO", fg_color="#3D89D1",
                  hover_color="#1E3D8F",
                  font=ctk.CTkFont(size=13, weight="bold"),
                  corner_radius=8, width=140, height=40,
                  command=lambda: mostrar_pantalla_registro(root)
                  ).grid(row=0, column=2, padx=(10, 5), pady=12, sticky="e")

    ctk.CTkButton(header_frame, text="CERRAR SESIÓN", fg_color="#C82333",
                  hover_color="#A31616", command=lambda: cerrar_sesion(root),
                  font=ctk.CTkFont(size=13, weight="bold"),
                  corner_radius=8, width=130, height=40).grid(row=0, column=3, padx=10, pady=12, sticky="e")

    # Contenedor principal de la tabla/lista
    table_card = ctk.CTkFrame(main_frame, fg_color="white", corner_radius=15)
    table_card.grid(row=1, column=0, padx=15, pady=15, sticky="nsew")
    table_card.grid_rowconfigure(1, weight=1) # Fila del scrollable (lista)
    table_card.grid_columnconfigure(0, weight=1)

    # Contenedor de filtros y logo
    title_frame = ctk.CTkFrame(table_card, fg_color="transparent")
    title_frame.grid(row=0, column=0, sticky="ew", padx=18, pady=(15, 5))
    title_frame.grid_columnconfigure(0, weight=1) # Columna del logo/título

    # --- INICIO: CARGA DE IMÁGENES ---
    # Mover todas las cargas de imágenes aquí, al inicio de la función

    # Carga de Logo
    try:
        logo_img = ctk.CTkImage(PILImage.open("imagen/aragua1.png"), size=(140, 60))
        ctk.CTkLabel(title_frame, image=logo_img, text="").grid(row=0, column=0, sticky="w", padx=(10, 0))
    except Exception as e:
        print("No se pudo cargar el logo:", e)
        ctk.CTkLabel(title_frame, text="[Logo no encontrado]",
                      text_color="red", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, sticky="w")

    # Carga del ícono de recargar
    try:
        reload_icon = ctk.CTkImage(PILImage.open("imagen/recargar.png"), size=(25, 25))
    except Exception:
        reload_icon = None

    # --- INICIO: CÓDIGO CORREGIDO PARA IMAGEN DE BOTÓN EXPORTAR ---
    try:
        # Usar os.path.join para construir la ruta de forma segura
        base_dir = os.path.dirname(os.path.abspath(__file__))
        
        # --- ¡CORRECCIÓN IMPORTANTE! El archivo se llama 'bnexcel.png' ---
        ruta_imagen_boton_exportar = os.path.join(base_dir, "imagen", "btn_exportar.png") 
        
        export_button_image = ctk.CTkImage(
            PILImage.open(ruta_imagen_boton_exportar), 
            size=(113, 37) # Ajustado a un tamaño más similar a un botón
        )
    except FileNotFoundError:
        print(f"ADVERTENCIA: No se encontró la imagen del botón de exportar en '{ruta_imagen_boton_exportar}'. Se usará un botón de texto.")
        export_button_image = None
    except Exception as e:
        print(f"Error al cargar la imagen del botón de exportar: {e}. Se usará un botón de texto.")
        export_button_image = None
    # --- FIN: CÓDIGO CORREGIDO PARA IMAGEN DE BOTÓN EXPORTAR ---

    # --- FIN: CARGA DE IMÁGENES ---

    scrollable = ctk.CTkScrollableFrame(table_card, corner_radius=10)
    scrollable.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")

    # Funciones de Lógica de la Lista
    
    
    
    
  #===================================================================================================================================0000000000000000000000000000000
#==================================================================================================================================================================
# PANTALLA PRINCIPAL (Lista de Servicios) 
# ... (Aquí va todo tu código anterior de 'mostrar_pantalla_principal') ...

    # Funciones de Lógica de la Lista
    def obtener_servicios_filtrados():
        # ... (Esta función no necesita cambios, se queda igual) ...
        query = supabase.table("Servicio").select("*").order("id_servicio", desc=True)
        estado_map = {"Pendiente": 1, "Completado": 2, "Recibido": 3}
        estado_val = filtro_estado.get()
        
        # Aplicar filtro de estado
        if estado_val in estado_map:
            query = query.eq("estado", estado_map[estado_val])
            
        
        # Aplicar filtro de técnico o departamento
        tecnico_id_val = filtros_especiales.get('tecnico_id')
        depto_id_val = filtros_especiales.get('depto_id')# <--- CORREGIDO (decía 'id_departamento')

               # Son exclusivos: O filtra por técnico, o por depto
                # Son exclusivos: O filtra por técnico, o por depto
        if tecnico_id_val:
            query = query.eq("tecnico", tecnico_id_val)
        elif depto_id_val:
            # Obtener el nombre real del departamento desde el mapa
            departamentos_map = obtener_departamentos()
            nombre_depto = None
            for nombre, idd in departamentos_map.items():
                if idd == depto_id_val:
                    nombre_depto = nombre.strip().lower()
                    break

            if nombre_depto:
                # Intentar filtrar tanto por nombre como por ID (por compatibilidad)
                try:
                    query = query.or_(f"departamento.ilike.%{nombre_depto}%,departamento.eq.{depto_id_val}")
                except Exception:
                    query = query.ilike("departamento", f"%{nombre_depto}%")



      

        # Aplicar filtro de fecha
        fecha_val = filtro_fecha.get()
        
        hoy_date = datetime.now().date()
        
        if fecha_val == "Hoy":
            inicio_str = hoy_date.isoformat() 
            fin_date = hoy_date + timedelta(days=1)
            fin_str = fin_date.isoformat()
            query = query.gte("fecha", inicio_str).lt("fecha", fin_str)
            
        elif fecha_val == "Ayer":
            ayer_date = hoy_date - timedelta(days=1)
            inicio_str = ayer_date.isoformat()
            fin_date = hoy_date
            fin_str = fin_date.isoformat()
            query = query.gte("fecha", inicio_str).lt("fecha", fin_str)

        elif fecha_val == "Esta semana anterior":
            inicio_esta_semana = hoy_date - timedelta(days=hoy_date.weekday())
            inicio_semana_anterior = inicio_esta_semana - timedelta(days=7)
            fin_semana_anterior = inicio_esta_semana
            inicio_str = inicio_semana_anterior.isoformat()
            fin_str = fin_semana_anterior.isoformat()
            query = query.gte("fecha", inicio_str).lt("fecha", fin_str)
            
        elif fecha_val == "Personalizado" and hasattr(obtener_servicios_filtrados, "rango_personalizado"):
            desde_str, hasta_str = obtener_servicios_filtrados.rango_personalizado
            hasta_obj = datetime.fromisoformat(hasta_str).date()
            fin_rango_exclusivo = hasta_obj + timedelta(days=1)
            query = query.gte("fecha", desde_str).lt("fecha", fin_rango_exclusivo.isoformat())

        return obtener_servicios_filtrados_base(query)

    def renderizar_servicios():
        """
        Limpia el scrollable y renderiza las nuevas tarjetas de servicio.
        ¡VERSIÓN CON 1 TARJETA POR FILA Y 3 COLUMNAS INTERNAS!
        """

        for w in scrollable.winfo_children():
            w.destroy()

        cargando_lbl = ctk.CTkLabel(scrollable, text="Cargando servicios...", font=ctk.CTkFont(size=14, weight="bold"), text_color="#0C4A6E")
        cargando_lbl.pack(pady=20)
        
        def tarea():
            try:
                servicios = obtener_servicios_filtrados()
                usuarios_map = map_usuarios_por_cedula()
            except Exception as e:
                servicios = []
                usuarios_map = {}
                print("Error en carga:", e)

            
            def _render():
                cargando_lbl.destroy()
                scrollable._parent_canvas.yview_moveto(0.0)
                scrollable.grid_columnconfigure(0, weight=1)

                # --- CAMBIO IMPORTANTE ---
                # Ya no se configura grid de 2 columnas en 'scrollable'
                # -------------------------

                if not servicios:
                    ctk.CTkLabel(scrollable, text="No hay servicios registrados.", font=ctk.CTkFont(size=14)).pack(pady=20)
                    return

                # --- INICIO: Definiciones de Diseño de la Nueva Tarjeta ---
                
                COLOR_HEADER_BG = "#0A2B4C"
                COLOR_BODY_BG = "#F5F5ED"
                COLOR_HEADER_TEXT = "#FFFFFF"
                COLOR_TITLE_TEXT = "#2E2E2E"
                COLOR_DETAIL_TEXT = "#4A4A4A"
                CARD_CORNER_RADIUS = 8
                COLOR_SEPARATOR = "#DCDCDC" # Color para las líneas

                FONT_HEADER = ctk.CTkFont(size=18, weight="bold")
                FONT_TITLE = ctk.CTkFont(size=16, weight="bold")
                FONT_DETAIL = ctk.CTkFont(size=14) 
                FONT_PILL = ctk.CTkFont(size=11, weight="bold")

                colores_estado = {
                    "Completado": ("#D1FAE5", "#047857", "#047857"),
                    "Pendiente":  ("#FEF3C7", "#92400E", "#92400E"),
                    "Recibido":   ("#DBEAFE", "#1E3A8A", "#1E3A8A"),
                    "Desconocido": ("#F3F4F6", "#374151", "#374151")
                }
                # --- FIN: Definiciones de Diseño ---


                # --- INICIO: Bucle de Renderizado con Nuevo Diseño ---
                
                # Se elimina la lógica de 'index' y 'current_row_frame'
                
                for index, s in enumerate(servicios):
                    estado_text = traducir_estado(s.get("estado"))
                    color_bg, color_border, color_text = colores_estado.get(estado_text, colores_estado["Desconocido"])

                    # 1. Contenedor principal
                    card_main = ctk.CTkFrame(
                        scrollable, # El padre vuelve a ser 'scrollable'
                        fg_color=COLOR_BODY_BG, 
                        corner_radius=CARD_CORNER_RADIUS,
                        border_color="#DCDCDC",
                        border_width=1
                    )
                    
                    # --- CAMBIO: Se vuelve a usar .pack() ---
                    card_main.grid(row=index, column=0, sticky="ew", padx=15, pady=5)

                    # --- Configuración interna de la tarjeta ---
                    card_main.grid_columnconfigure(0, weight=1) 
                    # Fila 0: Encabezado (no se estira)
                    card_main.grid_rowconfigure(0, weight=0)
                    # Fila 1: Cuerpo (se estira)
                    card_main.grid_rowconfigure(1, weight=0) 

                    # 2. Encabezado (Azul)
                    header_frame = ctk.CTkFrame(card_main, fg_color=COLOR_HEADER_BG, corner_radius=0)
                    header_frame.grid(row=0, column=0, sticky="ew")
                    ctk.CTkLabel(
                        header_frame, 
                        text=f" SERVICIO #{s.get('id_servicio')}", 
                        font=FONT_HEADER, 
                        text_color=COLOR_HEADER_TEXT,
                        anchor="w"
                    ).pack(fill="x", padx=15, pady=10) 

                    # 3. Contenedor del Cuerpo (Grid)
                    body_container = ctk.CTkFrame(card_main, fg_color="transparent")
                    body_container.grid(row=1, column=0, sticky="nsew", padx=15, pady=(5, 5))

                    
                    # Columna de texto (con las 3 sub-columnas)
                    body_container.grid_columnconfigure(0, weight=1) 
                    # Columna de insignia
                    body_container.grid_columnconfigure(1, weight=0) 
                    
                    # --- CAMBIO: Se elimina la lógica de centrado vertical ---
                    # El contenido vuelve a la Fila 0
                    
                    # 3a. Frame de detalles (se coloca en la fila 0)
                    details_frame = ctk.CTkFrame(body_container, fg_color="transparent")
                    details_frame.grid(row=0, column=0, sticky="nsew") # Fila 0

                    # Título (arriba)
                    ctk.CTkLabel(
                        details_frame, 
                        text=(s.get('descripcion') or "Sin descripción").capitalize(), 
                        font=FONT_TITLE, 
                        text_color=COLOR_TITLE_TEXT, 
                        anchor="w"
                    ).pack(fill="x", pady=(0, 4)) # Espacio después del título

                    # Frame para las 3 columnas de abajo
                    columns_frame = ctk.CTkFrame(details_frame, fg_color="transparent")
                    columns_frame.pack(fill="x")
                    columns_frame.grid_columnconfigure((0, 2, 4), weight=1)
                    columns_frame.grid_columnconfigure((1, 3), weight=0)
                    columns_frame.grid_rowconfigure(0, weight=0)

                    # --- Columna 1 ---
                    col1_frame = ctk.CTkFrame(columns_frame, fg_color="transparent")
                    col1_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
                    
                    ctk.CTkLabel(
                        col1_frame, 
                        text=f"Usuario: {usuarios_map.get(str(s.get('usuario')), 'Desconocido')}", 
                        font=FONT_DETAIL, 
                        text_color=COLOR_DETAIL_TEXT, 
                        anchor="w"
                    ).pack(fill="x", pady=0)
                    ctk.CTkLabel(
                        col1_frame, 
                        text=f"Departamento: {s.get('Departamento', 'Desconocido')}", 
                        font=FONT_DETAIL, 
                        text_color=COLOR_DETAIL_TEXT, 
                        anchor="w"
                    ).pack(fill="x")

                    # --- Separador 1 ---
                    ctk.CTkFrame(columns_frame, width=2, fg_color=COLOR_SEPARATOR).grid(row=0, column=1, sticky="ns", pady=2)

                    # --- Columna 2 ---
                    col2_frame = ctk.CTkFrame(columns_frame, fg_color="transparent")
                    col2_frame.grid(row=0, column=2, sticky="nsew", padx=5)
                    
                    ctk.CTkLabel(
                        col2_frame, 
                        text=f"Técnico: {usuarios_map.get(str(s.get('tecnico')), 'Sin asignar')}", 
                        font=FONT_DETAIL, 
                        text_color=COLOR_DETAIL_TEXT, 
                        anchor="w"
                    ).pack(fill="x")
                    
                    reporte_valor = s.get("reporte")
                    if not reporte_valor or str(reporte_valor).strip().lower() in ["none", "null", ""]:
                        reporte_valor = "Sin reporte"
                    ctk.CTkLabel(
                        col2_frame, 
                        text=f"Reporte: {reporte_valor}",
                        font=FONT_DETAIL, 
                        text_color=COLOR_DETAIL_TEXT, 
                        anchor="w"
                    ).pack(fill="x")

                    # --- Separador 2 ---
                    ctk.CTkFrame(columns_frame, width=2, fg_color=COLOR_SEPARATOR).grid(row=0, column=3, sticky="ns", pady=2)

                    # --- Columna 3 ---
                    col3_frame = ctk.CTkFrame(columns_frame, fg_color="transparent")
                    col3_frame.grid(row=0, column=4, sticky="nsew", padx=(5, 0))

                    ctk.CTkLabel(
                        col3_frame, 
                        text=f"Fecha creación: {formatear_fecha(s.get('fecha'))}", 
                        font=FONT_DETAIL, 
                        text_color=COLOR_DETAIL_TEXT, 
                        anchor="w"
                    ).pack(fill="x")
                    ctk.CTkLabel(
                        col3_frame, 
                        text=f"Fecha de culminación: {formatear_fecha(s.get('fecha_culminado'))}", 
                        font=FONT_DETAIL, 
                        text_color=COLOR_DETAIL_TEXT, 
                        anchor="w"
                    ).pack(fill="x")
                    

                    # 3b. Insignia (Pill)
                    pill = ctk.CTkFrame(
                        body_container, 
                        fg_color=color_bg, 
                        border_color=color_border, 
                        border_width=1, 
                        corner_radius=14 
                    )
                    # Vuelve a la Fila 0, alineado a la esquina inferior derecha
                    pill.grid(row=0, column=1, padx=(10, 0), pady=(0,3), sticky="se") 
                    
                    ctk.CTkLabel(
                        pill, 
                        text=estado_text.upper(), 
                        text_color=color_text, 
                        font=FONT_PILL
                    ).pack(padx=12, pady=5) 


                # --- FIN: Bucle de Renderizado ---

            scrollable.after(0, _render)

        threading.Thread(target=tarea, daemon=True).start()
    
   
    
 

    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    # --- INICIO: CÓDIGO CORREGIDO PARA EXPORTAR ---
    # La función 'exportar_a_excel' debe estar definida aquí
    
    def exportar_a_excel():
        """
        Prepara y ejecuta la exportación a Excel en un hilo separado
        para no bloquear la interfaz.
        """
        
        def tarea_exportar():
            """Función que se ejecuta en el hilo para preparar los datos."""
            try:
                # 1. REUTILIZAMOS tu lógica de filtrado existente
                servicios = obtener_servicios_filtrados()
                
                # 2. REUTILIZAMOS tu mapa de usuarios
                usuarios_map = map_usuarios_por_cedula()
                
                if not servicios:
                    # Si no hay datos, informamos en el hilo principal
                    root.after(0, lambda: messagebox.showwarning("Sin datos", "No hay servicios filtrados para exportar."))
                    return

                # 3. PROCESAMOS los datos para el Excel
                datos_para_excel = []
                columnas_excel = [
                    'ID Servicio', 'Estado', 'Descripción', 'Usuario', 'Técnico', 
                    'Departamento', 'Fecha Creación', 'Reporte', 'Fecha Culminado'
                ]
                
                for s in servicios:
                    estado_text = traducir_estado(s.get("estado"))
                    
                    reporte_valor = s.get("reporte")
                    if not reporte_valor or str(reporte_valor).strip().lower() in ["none", "null", ""]:
                        reporte_valor = "No registrado"
                        
                    usuario_nombre = usuarios_map.get(str(s.get('usuario')), 'Desconocido')
                    tecnico_nombre = usuarios_map.get(str(s.get('tecnico')), 'Sin asignar')
                    
                    # El depto ya viene como nombre gracias a 'obtener_servicios_filtrados_base'
                    depto_nombre = s.get('Departamento', 'Desconocido') # <--- CORREGIDO (usar 'Departamento' con mayúscula)
                    
                    fila = [
                        s.get('id_servicio'),
                        estado_text,
                        s.get('descripcion'),
                        usuario_nombre,
                        tecnico_nombre,
                        depto_nombre,
                        formatear_fecha(s.get('fecha')),
                        reporte_valor,
                        formatear_fecha(s.get('fecha_culminado'))
                    ]
                    datos_para_excel.append(fila)
                
                # 4. Creamos el DataFrame de Pandas
                df = pd.DataFrame(datos_para_excel, columns=columnas_excel)
                
                # 5. Pasamos el DataFrame al hilo principal para guardarlo
                root.after(0, lambda: _guardar_excel_en_hilo_principal(df))
            
            except Exception as e:
                print(f"Error en hilo de exportación: {e}")
                root.after(0, lambda: messagebox.showerror("Error", f"Ocurrió un error al preparar los datos:\n{e}"))

        
        def _guardar_excel_en_hilo_principal(df):
            """
            Esta función se ejecuta en el hilo principal para mostrar el diálogo de guardado
            y aplicar el diseño.
            """
            try:
                ruta_archivo = filedialog.asksaveasfilename(
                    defaultextension=".xlsx",
                    filetypes=[("Archivos Excel", "*.xlsx"), ("Todos los archivos", "*.*")],
                    title="Guardar reporte de servicios"
                )

                if not ruta_archivo:
                    return

                wb = Workbook()
                ws = wb.active
                ws.title = "Servicios"

                try:
                    base_dir = os.path.dirname(os.path.abspath(__file__))
                    ruta_imagen = os.path.join(base_dir, "imagen", "exportar.png")

                    if os.path.exists(ruta_imagen):
                        img = OpenpyxlImage(ruta_imagen)
                        img.width = 290
                        img.height = 73
                        ws.add_image(img, "A1")

                        # 📍 Ajustar posición del logo (ligeramente más a la izquierda)
                        # openpyxl no permite desplazamiento directo, pero podemos reducir el margen en la columna B
                        ws.column_dimensions['A'].width = 10   # margen más fino
                        ws.column_dimensions['B'].width = 20   # deja la imagen más cerca del borde visualmente
                        ws.column_dimensions['C'].width = 2

                        # Bloquear la imagen (no mover ni redimensionar)
                        try:
                            piclocks = img.drawing._graphic.graphicData.pic.nonVisualPictureProperties.cNvPicPr.picLocks
                            piclocks.noMove = True
                            piclocks.noResize = True
                        except Exception:
                            pass

                        fila_titulo = 1
                    else:
                        print("Advertencia: no se encontró exportar.png en carpeta imagen.")
                        fila_titulo = 1
                except Exception as e:
                    print(f"Error al insertar la imagen: {e}")
                    fila_titulo = 1


                # === TÍTULO Y SUBTÍTULO CENTRADO PERFECTO ===
                # Vamos a centrar el texto respecto a todo el rango de columnas con datos
                ultima_columna_letra = get_column_letter(df.shape[1])

                # Combinar desde la columna C (más centrado) hasta la última
                ws.merge_cells(f'C{fila_titulo}:{ultima_columna_letra}{fila_titulo}')

                ws[f'C{fila_titulo}'] = "GESTIÓN DE SERVICIOS DGTSP\nARAGUA"
                ws[f'C{fila_titulo}'].font = Font(name='Arial', size=14, bold=True, color="000000")
                ws[f'C{fila_titulo}'].alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)

                # Altura equilibrada
                ws.row_dimensions[1].height = 45

                # === LIMPIAR VISUALMENTE EL ÁREA DEL LOGO ===
                for col in ['A', 'B', 'C']:
                    cell = ws[f"{col}1"]
                    cell.border = Border(left=None, right=None, top=None, bottom=None)
                    cell.fill = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")

                ws.sheet_view.showGridLines = False  # sin cuadrículas visibles

                # === ENCABEZADOS DE TABLA ===
                header_row = fila_titulo + 2
                for col_idx, col_name in enumerate(df.columns, 1):
                    cell = ws.cell(row=header_row, column=col_idx, value=col_name)
                    cell.font = Font(name='Arial', size=10, bold=True, color="FFFFFF")
                    cell.fill = PatternFill(start_color="1F497D", end_color="1F497D", fill_type="solid")
                    cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
                    cell.border = Border(left=Side(style=BORDER_THIN), right=Side(style=BORDER_THIN),
                                        top=Side(style=BORDER_THIN), bottom=Side(style=BORDER_THIN))

                # === ESCRIBIR DATOS ===
                for r_idx, row in enumerate(df.values, header_row + 1):
                    for c_idx, value in enumerate(row, 1):
                        cell = ws.cell(row=r_idx, column=c_idx, value=value)
                        cell.font = Font(name='Arial', size=9, color="000000")
                        cell.alignment = Alignment(vertical='top', wrap_text=True)
                        cell.border = Border(left=Side(style=BORDER_THIN), right=Side(style=BORDER_THIN),
                                            top=Side(style=BORDER_THIN), bottom=Side(style=BORDER_THIN))
                        
                        

                # 5. Autoajuste del ancho de las columnas (con la corrección para "Estado")
                for column in ws.columns:
                    max_length = 0
                    column_letter = get_column_letter(column[0].column)
                    
                    for cell in column[3:]: 
                        try:
                            if cell.value:
                                max_length = max(max_length, len(str(cell.value)))
                        except:
                            pass
                    
                    adjusted_width = (max_length + 2)

                    if column_letter == 'A': # ID Servicio
                        ws.column_dimensions[column_letter].width = max(adjusted_width, 12)
                    
                    elif column_letter == 'B': # Estado
                        ws.column_dimensions[column_letter].width = min(max(adjusted_width, 13), 18)

                    elif column_letter == 'C': # Descripción
                        ws.column_dimensions[column_letter].width = max(adjusted_width, 40)
                    elif column_letter == 'D': # Usuario
                        ws.column_dimensions[column_letter].width = max(adjusted_width, 20)
                    elif column_letter == 'E': # Técnico
                        ws.column_dimensions[column_letter].width = max(adjusted_width, 20)
                    elif column_letter == 'F': # Departamento
                        ws.column_dimensions[column_letter].width = max(adjusted_width, 25)
                    elif column_letter == 'G': # Fecha Creación
                        ws.column_dimensions[column_letter].width = max(adjusted_width, 18)
                    elif column_letter == 'H': # Reporte
                        ws.column_dimensions[column_letter].width = max(adjusted_width, 30)
                    elif column_letter == 'I': # Fecha Culminado
                        ws.column_dimensions[column_letter].width = max(adjusted_width, 18)
                    else:
                        ws.column_dimensions[column_letter].width = adjusted_width

                wb.save(ruta_archivo)
                os.startfile(ruta_archivo)
                

            except Exception as e:
                messagebox.showerror("Error al guardar", f"No se pudo guardar el archivo:\n{e}")
        
        # Inicia el hilo de exportación
        threading.Thread(target=tarea_exportar, daemon=True).start()
    # --- FIN: CÓDIGO CORREGIDO PARA EXPORTAR ---


    def abrir_ventana_seleccionar_tecnico():
        """Abre una ventana emergente para seleccionar un técnico."""
        
        ventana = ctk.CTkToplevel(root)
        ventana.title("Seleccionar Técnico")
        ventana.configure(fg_color="#F7F9FB")
        ventana.grab_set()
        ventana.focus_force()
        ventana.resizable(False, False)
        
        contenido = ctk.CTkFrame(ventana, fg_color="#FFFFFF")
        contenido.pack(padx=20, pady=20, fill="both", expand=True)

        ctk.CTkLabel(contenido, text="Seleccione un Técnico", font=ctk.CTkFont(size=18, weight="bold"), text_color="#0C4A6E").pack(pady=(10, 15))

        tecnicos_map = {}
        
        combo = ctk.CTkComboBox(
            contenido, 
            values=["Cargando..."],
            width=300,
            height=35
        )
        combo.pack(pady=10, padx=10)

        def _cargar_tecnicos():
            try:
                # Filtra solo usuarios donde el rol es 1 (Técnico)
                resp = supabase.table("Usuario").select("cedula, nombre, apellido").eq("rol", 1).order("nombre").execute()
                
                tecnicos = resp.data or []
                
                if not tecnicos:
                    root.after(0, lambda: combo.configure(values=["-- No hay técnicos --"]))
                    return
                
                tecnicos_map.clear()
                display_names = []
                
                for u in tecnicos:
                    nombre = f"{u.get('nombre') or ''} {u.get('apellido') or ''}".strip()
                    cedula = u.get('cedula')
                    if not nombre: nombre = f"Técnico ({cedula})"
                    
                    display = f"{nombre} ({cedula})"
                    tecnicos_map[display] = cedula
                    display_names.append(display)
                
                root.after(0, lambda: combo.configure(values=display_names))
                root.after(0, lambda: combo.set(display_names[0]))
                
            except Exception as e:
                print(f"Error cargando técnicos: {e}")
                root.after(0, lambda: combo.configure(values=["-- Error al cargar --"]))

        def _aplicar():
            display_seleccionado = combo.get()
            id_tecnico = tecnicos_map.get(display_seleccionado)
            
            if id_tecnico:
                filtros_especiales['tecnico_id'] = id_tecnico
                filtros_especiales['depto_id'] = None # Resetea el otro filtro
                
                nombre_corto = display_seleccionado.split('(')[0].strip()
                filtro_estado.set(f"Técnico: {nombre_corto[:20]}...")
                
                ventana.destroy()
                renderizar_servicios()

        ctk.CTkButton(contenido, text="Aplicar Filtro", fg_color="#0C4A6E", hover_color="#155E75", corner_radius=10, width=200, height=40, command=_aplicar).pack(pady=(15, 10))
        
        threading.Thread(target=_cargar_tecnicos, daemon=True).start()


    def abrir_ventana_seleccionar_departamento():
        """Abre una ventana emergente para seleccionar un departamento."""
        
        ventana = ctk.CTkToplevel(root)
        ventana.title("Seleccionar Departamento")
        ventana.configure(fg_color="#F7F9FB")
        ventana.grab_set()
        ventana.focus_force()
        ventana.resizable(False, False)
        
        contenido = ctk.CTkFrame(ventana, fg_color="#FFFFFF")
        contenido.pack(padx=20, pady=20, fill="both", expand=True)

        ctk.CTkLabel(contenido, text="Seleccione un Departamento", font=ctk.CTkFont(size=18, weight="bold"), text_color="#0C4A6E").pack(pady=(10, 15))

        deptos_map = {}
        
        combo = ctk.CTkComboBox(
            contenido, 
            values=["Cargando..."],
            width=300,
            height=35
        )
        combo.pack(pady=10, padx=10)

        def _cargar_deptos():
            try:
                resp = supabase.table("Departamento").select("id_departamento, nombre_departamento").order("nombre_departamento").execute()
                deptos = resp.data or []
                
                if not deptos:
                    root.after(0, lambda: combo.configure(values=["-- No hay deptos --"]))
                    return
                
                deptos_map.clear()
                display_names = []
                
                for d in deptos:
                    nombre = d.get('nombre_departamento')
                    id_depto = d.get('id_departamento')
                    if nombre and id_depto:
                        deptos_map[nombre] = id_depto
                        display_names.append(nombre)
                
                root.after(0, lambda: combo.configure(values=display_names))
                root.after(0, lambda: combo.set(display_names[0]))
                
            except Exception as e:
                print(f"Error cargando departamentos: {e}")
                root.after(0, lambda: combo.configure(values=["-- Error al cargar --"]))

        def _aplicar():
            display_seleccionado = combo.get()
            id_depto = deptos_map.get(display_seleccionado)
            
            if id_depto:
                filtros_especiales['depto_id'] = id_depto
                filtros_especiales['tecnico_id'] = None # Resetea el otro filtro
                
                filtro_estado.set(f"Depto: {display_seleccionado[:20]}...")
                
                ventana.destroy()
                renderizar_servicios()

        ctk.CTkButton(contenido, text="Aplicar Filtro", fg_color="#0C4A6E", hover_color="#155E75", corner_radius=10, width=200, height=40, command=_aplicar).pack(pady=(15, 10))
        
        threading.Thread(target=_cargar_deptos, daemon=True).start()


    def manejar_filtro_fecha(opcion):
        if opcion == "Personalizado":
            try:
                from tkcalendar import Calendar
            except ImportError:
                print("Error: tkcalendar no está disponible. No se puede usar el filtro personalizado.")
                filtro_fecha.set("Todos") 
                renderizar_servicios()
                return

            ventana = ctk.CTkToplevel(root)
            ventana.title("Seleccionar rango de fechas")
            ventana.configure(fg_color="#F7F9FB")
            ventana.grab_set()
            ventana.focus_force()
            ventana.resizable(False, False)

            contenido = ctk.CTkFrame(ventana, fg_color="#F7F9FB")
            contenido.pack(padx=20, pady=20, fill="both", expand=True)

            ctk.CTkLabel(contenido, text="Seleccione el rango de fechas", font=ctk.CTkFont(size=18, weight="bold"), text_color="#0C4A6E").grid(row=0, column=0, columnspan=2, pady=(10, 15))
            ctk.CTkLabel(contenido, text="Desde:", text_color="#2E3A59", font=ctk.CTkFont(size=13, weight="bold")).grid(row=1, column=0, pady=(5, 0))
            ctk.CTkLabel(contenido, text="Hasta:", text_color="#2E3A59", font=ctk.CTkFont(size=13, weight="bold")).grid(row=1, column=1, pady=(5, 0))

            cal_desde = Calendar(contenido, date_pattern="dd-mm-yyyy", selectmode="day")
            cal_hasta = Calendar(contenido, date_pattern="dd-mm-yyyy", selectmode="day")
            cal_desde.grid(row=2, column=0, padx=15, pady=(0, 10))
            cal_hasta.grid(row=2, column=1, padx=15, pady=(0, 10))

            def aplicar():
                desde_str, hasta_str = cal_desde.get_date(), cal_hasta.get_date()
                try:
                    desde_obj = datetime.strptime(desde_str, "%d-%m-%Y").date()
                    hasta_obj = datetime.strptime(hasta_str, "%d-%m-%Y").date()
                except ValueError:
                    return
                if desde_obj > hasta_obj:
                    return
                obtener_servicios_filtrados.rango_personalizado = (str(desde_obj), str(hasta_obj))
                ventana.destroy()
                renderizar_servicios()

            ctk.CTkButton(contenido, text="Aplicar filtro", fg_color="#0C4A6E", hover_color="#155E75", corner_radius=10, width=200, height=40, command=aplicar).grid(row=3, column=0, columnspan=2, pady=(15, 5))

            contenido.grid_columnconfigure(0, weight=1)
            contenido.grid_columnconfigure(1, weight=1)
            ventana.update_idletasks()
            w = contenido.winfo_reqwidth() + 40
            h = contenido.winfo_reqheight() + 40
            ventana.geometry(f"{w}x{h}")
            ventana.minsize(w, h)
        else:
            renderizar_servicios()

    def manejar_filtro_principal(opcion):
        """Maneja el menú de filtro principal (estado, tecnico, depto)."""
        
        if opcion == "Por Técnico...":
            abrir_ventana_seleccionar_tecnico()
        elif opcion == "Por Departamento...":
            abrir_ventana_seleccionar_departamento()
        else:
            filtros_especiales['tecnico_id'] = None
            filtros_especiales['depto_id'] = None
            renderizar_servicios()

    # --- INICIO: CORRECCIÓN DE BOTONES DE FILTRO ---
    
    # Filtro de Estado
    filtro_estado_menu = ctk.CTkOptionMenu(
        title_frame, 
        values=["Todos", "Pendiente", "Recibido", "Completado", "Por Técnico...", "Por Departamento..."], 
        variable=filtro_estado, 
        command=manejar_filtro_principal, 
        fg_color="#0C4A6E", 
        button_color="#155E75", 
        text_color="white", 
        width=200,
        height=35, 
        dropdown_fg_color="#E5E7EB", 
        dropdown_text_color="black"
    )
    filtro_estado_menu.grid(row=0, column=1, padx=5, sticky="e")

    # Filtro de Fecha
    filtro_fecha_menu = ctk.CTkOptionMenu(
        title_frame, 
        values=["Todos", "Hoy", "Ayer", "Esta semana anterior", "Personalizado"], 
        variable=filtro_fecha, 
        command=manejar_filtro_fecha, 
        fg_color="#0C4A6E", 
        button_color="#155E75", 
        text_color="white", 
        width=180, 
        height=35, 
        dropdown_fg_color="#E5E7EB", 
        dropdown_text_color="black"
    )
    filtro_fecha_menu.grid(row=0, column=2, padx=5, sticky="e")

    # Botón de Exportar (MODIFICADO PARA USAR IMAGEN)
    if export_button_image: # Si la imagen se cargó correctamente
        ctk.CTkButton(
            title_frame, 
            text="", # Sin texto
            image=export_button_image, # Usar la imagen
            width=100, # Ancho de la imagen (ajustado)
            height=35, # Alto de la imagen (ajustado)
            fg_color="transparent", # Fondo transparente
            hover_color="#C3DBB9", # Un leve hover para que se vea como botón
            command=exportar_a_excel
        ).grid(row=0, column=3, padx=4, sticky="e")
    else: # Si la imagen falla, mostrar un botón de texto
         ctk.CTkButton(
            title_frame, 
            text="Exportar", 
            width=100,
            height=35,
            fg_color="#107C41", 
            hover_color="#0B532B", 
            corner_radius=8, 
            command=exportar_a_excel
        ).grid(row=0, column=3, padx=5, sticky="e")
    
    # Botón de Recargar (Columna 4)
    ctk.CTkButton(
        title_frame, 
        text="", 
        image=reload_icon, 
        width=45, 
        height=35, # Ajustado al alto de los otros botones
        fg_color="#E5E7EB", 
        hover_color="#CBD5E1", 
        corner_radius=8, # Redondeado como los otros
        command=renderizar_servicios
    ).grid(row=0, column=4, padx=5, sticky="e")
    
    # --- FIN: CORRECCIÓN DE BOTONES DE FILTRO ---

    renderizar_servicios()

# Pantalla de Login / Configuración Inicial
def setup_login_app(root):
    
    _clear_widgets(root)
    
    ctk.set_appearance_mode("light")
    root.configure(fg_color="#FFFFFF")
    root.title("Sistema de Acceso")

    main_frame = ctk.CTkFrame(root, fg_color="#FFFFFF")
    
    main_frame.pack(expand=True, fill="both") 
    
    content_frame = ctk.CTkFrame(main_frame, fg_color="#FFFFFF")
    content_frame.place(relx=0.5, rely=0.5, anchor="center") 

    try:
        logo_img = ctk.CTkImage(PILImage.open("imagen/aragua1.png"), size=(250, 180))
        ctk.CTkLabel(content_frame, image=logo_img, text="").pack(pady=(10, 25))
    except Exception:
        ctk.CTkLabel(content_frame, text="[Logo no encontrado]", text_color="red").pack(pady=20)

    global cedula_entry, notificacion, app_root
    app_root = root 

    cedula_entry = ctk.CTkEntry(content_frame, placeholder_text="Cédula de Identidad", width=300, height=45, corner_radius=10, border_width=1, fg_color="white", border_color="#A1A1A1", text_color="black", font=ctk.CTkFont(size=14))
    cedula_entry.pack(pady=(10, 15))

    ctk.CTkButton(content_frame, text="INGRESAR", width=300, height=50, fg_color="#002D64", hover_color="#1A4E91", corner_radius=10, font=ctk.CTkFont(size=16, weight="bold"), text_color="white", command=validar_cedula).pack(pady=(5, 15))

    # Etiqueta para mostrar mensajes de error/notificación
    notificacion = ctk.CTkLabel(content_frame, text="", text_color="red", font=ctk.CTkFont(size=13, weight="bold"))
    notificacion.pack(pady=(5, 5))
import customtkinter as ctk
from cliente_supabase import supabase
import tkinter as tk
from datetime import datetime, timedelta
import threading


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
        departamentos = supabase.table("Departamento").select("id_departamento, nombre_departamento").execute().data or []
        dep_map = {str(d["id_departamento"]): d["nombre_departamento"] for d in departamentos}
        
        for s in servicios:
            dep_id = s.get("departamento")
            s["departamento_nombre"] = dep_map.get(str(dep_id), "Desconocido")
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


# PANTALLA PRINCIPAL (Lista de Servicios) 
def mostrar_pantalla_principal(root):
    from PIL import Image
    _clear_widgets(root)


    filtro_estado = tk.StringVar(value="Todos")
    filtro_fecha = tk.StringVar(value="Todos")

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

    ctk.CTkLabel(header_frame, text="Gestión de Servicios",
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

    # Carga de Logo
    try:
        logo_img = ctk.CTkImage(Image.open("imagen/aragua1.png"), size=(140, 60))
        ctk.CTkLabel(title_frame, image=logo_img, text="").grid(row=0, column=0, sticky="w", padx=(10, 0))
    except Exception as e:
        print("No se pudo cargar el logo:", e)
        ctk.CTkLabel(title_frame, text="[Logo no encontrado]",
                      text_color="red", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, sticky="w")

    # Carga del ícono de recargar
    try:
        reload_icon = ctk.CTkImage(Image.open("imagen/recargar.png"), size=(25, 25))
    except Exception:
        reload_icon = None

    scrollable = ctk.CTkScrollableFrame(table_card, corner_radius=10)
    scrollable.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")

    # Funciones de Lógica de la Lista
    def obtener_servicios_filtrados():
        query = supabase.table("Servicio").select("*").order("id_servicio", desc=True)
        estado_map = {"Pendiente": 1, "Completado": 2, "Recibido": 3}
        estado_val = filtro_estado.get()
        
        # Aplicar filtro de estado
        if estado_val in estado_map:
            query = query.eq("estado", estado_map[estado_val])

        # Aplicar filtro de fecha
        fecha_val = filtro_fecha.get()
        
        # Obtenemos la fecha de hoy, pero solo la parte DATE (sin hora)
        hoy_date = datetime.now().date()
        
        # --- BLOQUE DE CÓDIGO CORREGIDO PARA FILTRAR CAMPO DE TIPO TEXTO ---
        
        if fecha_val == "Hoy":
            # Inicio: YYYY-MM-DD (Compara desde la primera hora del día)
            inicio_str = hoy_date.isoformat() 
            # Fin: YYYY-MM-DD (Usamos el inicio del día siguiente para el filtro < )
            fin_date = hoy_date + timedelta(days=1)
            fin_str = fin_date.isoformat()
            
            # Filtra: fecha >= 'YYYY-MM-DD' AND fecha < 'YYYY-MM-DD del día siguiente'
            query = query.gte("fecha", inicio_str).lt("fecha", fin_str)
            
        elif fecha_val == "Ayer":
            ayer_date = hoy_date - timedelta(days=1)
            
            inicio_str = ayer_date.isoformat()
            fin_date = hoy_date # Inicio del día siguiente (Hoy)
            fin_str = fin_date.isoformat()

            query = query.gte("fecha", inicio_str).lt("fecha", fin_str)

        elif fecha_val == "Esta semana anterior":
            
            # Inicio de la semana actual (Lunes)
            inicio_esta_semana = hoy_date - timedelta(days=hoy_date.weekday())
            
            # Inicio de la semana anterior (Lunes)
            inicio_semana_anterior = inicio_esta_semana - timedelta(days=7)
            
            # Fin de la semana anterior (Inicio del Lunes de esta semana)
            fin_semana_anterior = inicio_esta_semana
            
            inicio_str = inicio_semana_anterior.isoformat()
            fin_str = fin_semana_anterior.isoformat()
            
            # Filtra por el rango de cadenas de fecha [inicio de la semana pasada, inicio de esta semana)
            query = query.gte("fecha", inicio_str).lt("fecha", fin_str)
            
        elif fecha_val == "Personalizado" and hasattr(obtener_servicios_filtrados, "rango_personalizado"):
            
            # Los valores guardados son cadenas 'YYYY-MM-DD'
            desde_str, hasta_str = obtener_servicios_filtrados.rango_personalizado
            
            # Para cubrir el día 'hasta' por completo, necesitamos el inicio del día siguiente.
            # Convertimos a objeto date para sumar el día, luego a string para la consulta.
            hasta_obj = datetime.fromisoformat(hasta_str).date()
            fin_rango_exclusivo = hasta_obj + timedelta(days=1)
            
            # Filtra: fecha >= 'desde' AND fecha < 'inicio del día siguiente a hasta'
            query = query.gte("fecha", desde_str).lt("fecha", fin_rango_exclusivo.isoformat())

        # --- FIN DEL BLOQUE DE CÓDIGO CORREGIDO ---

        return obtener_servicios_filtrados_base(query)

    def renderizar_servicios():

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
                if not servicios:
                    ctk.CTkLabel(scrollable, text="No hay servicios registrados.", font=ctk.CTkFont(size=14)).pack(pady=20)
                    return

            
                for s in servicios:
                    estado_text = traducir_estado(s.get("estado"))
                    color_estado = {
                        "Pendiente": ("#FEF3C7", "#92400E"),
                        "Completado": ("#D1FAE5", "#047857"),
                        "Recibido": ("#DBEAFE", "#1E3A8A")
                    }.get(estado_text, ("#F3F4F6", "#374151"))

                    card = ctk.CTkFrame(scrollable, fg_color="#FBFAFF", corner_radius=12, border_width=1, border_color="#E6E6E6")
                    card.pack(fill="x", padx=20, pady=10, expand=True)

                    header = ctk.CTkFrame(card, fg_color="transparent")
                    header.pack(fill="x", padx=12, pady=(10, 6))
                    ctk.CTkLabel(header, text=f"Servicio #{s.get('id_servicio')}", font=ctk.CTkFont(size=16, weight="bold")).pack(side="left")

                    
                    pill = ctk.CTkFrame(header, fg_color=color_estado[0], corner_radius=20)
                    pill.pack(side="right")
                    ctk.CTkLabel(pill, text=estado_text, text_color=color_estado[1], font=ctk.CTkFont(size=11, weight="bold")).pack(padx=12, pady=4)

                    reporte_valor = s.get("reporte")
                    if not reporte_valor or str(reporte_valor).strip().lower() in ["none", "null", ""]:
                        reporte_valor = "No registrado"

                    # Bloque de información del servicio
                    info_text = (
                        f"Descripción: {s.get('descripcion')}\n"
                        f"Usuario: {usuarios_map.get(str(s.get('usuario')), 'Desconocido')}\n"
                        f"Técnico: {usuarios_map.get(str(s.get('tecnico')), 'Sin asignar')}\n"
                        f"Departamento: {s.get('departamento', 'Desconocido')}\n"
                        f"Fecha creación: {formatear_fecha(s.get('fecha'))}\n"
                        f"Fecha culminación: {formatear_fecha(s.get('fecha_culminado'))}\n"
                        f"Reporte: {reporte_valor}"
                    )

                    ctk.CTkLabel(card, text=info_text, justify="left", anchor="w", text_color="#1F2937",
                                 font=ctk.CTkFont(size=12), wraplength=1000).pack(fill="x", padx=20, pady=(0, 12))

            scrollable.after(0, _render)

        threading.Thread(target=tarea, daemon=True).start()


    def manejar_filtro_fecha(opcion):
        if opcion == "Personalizado":
            try:
                # Importación local para asegurar que la app funcione si tkcalendar no está
                from tkcalendar import Calendar
            except ImportError:
                print("Error: tkcalendar no está disponible. No se puede usar el filtro personalizado.")
                filtro_fecha.set("Todos") 
                renderizar_servicios()
                return

            # Ventana TopLevel para seleccionar el rango de fechas
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
                # Guardamos la fecha en formato YYYY-MM-DD para el filtro de texto
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

    filtro_estado_menu = ctk.CTkOptionMenu(title_frame, values=["Todos", "Pendiente", "Recibido", "Completado"], variable=filtro_estado, command=lambda _: renderizar_servicios(), fg_color="#0C4A6E", button_color="#155E75", text_color="white", width=140, height=35, dropdown_fg_color="#E5E7EB", dropdown_text_color="black")
    filtro_estado_menu.grid(row=0, column=1, padx=5, sticky="e")

    filtro_fecha_menu = ctk.CTkOptionMenu(title_frame, values=["Todos", "Hoy", "Ayer", "Esta semana anterior", "Personalizado"], variable=filtro_fecha, command=manejar_filtro_fecha, fg_color="#0C4A6E", button_color="#155E75", text_color="white", width=180, height=35, dropdown_fg_color="#E5E7EB", dropdown_text_color="black")
    filtro_fecha_menu.grid(row=0, column=2, padx=5, sticky="e")

    # Botón de Recargar
    ctk.CTkButton(title_frame, text="", image=reload_icon, width=45, height=45, fg_color="#E5E7EB", hover_color="#CBD5E1", corner_radius=50, command=renderizar_servicios).grid(row=0, column=3, padx=5, sticky="e")

    renderizar_servicios()


# Pantalla de Login / Configuración Inicial
def setup_login_app(root):

    from PIL import Image
    
    _clear_widgets(root)
    
    ctk.set_appearance_mode("light")
    root.configure(fg_color="#FFFFFF")
    root.title("Sistema de Acceso")

    main_frame = ctk.CTkFrame(root, fg_color="#FFFFFF")
    
    main_frame.pack(expand=True, fill="both") 
    
    content_frame = ctk.CTkFrame(main_frame, fg_color="#FFFFFF")
    content_frame.place(relx=0.5, rely=0.5, anchor="center") 

    try:
        logo_img = ctk.CTkImage(Image.open("imagen/aragua1.png"), size=(250, 180))
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
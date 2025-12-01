import customtkinter as ctk
from cliente_supabase import supabase
import tkinter as tk
import threading
import pandas as pd
from tkinter import messagebox
import os
from PIL import Image as PILImage 
from datetime import datetime

# Variables globales específicas para Gestión de Usuarios
registro_entries = {}
registro_notificacion = None
usuario_seleccionado = None
app_root = None
btn_bloqueo_global = None 
btn_historial_global = None 

# --- Funciones Utilitarias Internas ---

def _clear_widgets(root):
    for widget in root.winfo_children():
        widget.destroy()

def _set_registro_notificacion(text, color):
    global registro_notificacion, app_root
    if not registro_notificacion or not app_root:
        return
    app_root.after(0, lambda: registro_notificacion.configure(text=text, text_color=color))

# --- Consultas a BD ---

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

def obtener_usuarios_completos():
    try:
        response = (
            supabase.table('Usuario')
            .select('nombre, apellido, cedula, correo, bloqueado, Departamento(nombre_departamento), Rol(nombre_rol)')
            .execute()
        )
        datos = response.data

        if not datos:
            return pd.DataFrame(columns=['nombre', 'apellido', 'cedula', 'correo', 'departamento', 'rol', 'bloqueado'])

        usuarios_procesados = []
        for usuario in datos:
            usuario_procesado = {
                'nombre': usuario.get('nombre', ''),
                'apellido': usuario.get('apellido', ''),
                'cedula': usuario.get('cedula', ''),
                'correo': usuario.get('correo', ''),
                'bloqueado': usuario.get('bloqueado', False),
                'departamento': 'Sin departamento',
                'rol': 'Sin rol'
            }
            
            depto_data = usuario.get('Departamento')
            if depto_data and isinstance(depto_data, list) and len(depto_data) > 0:
                usuario_procesado['departamento'] = depto_data[0].get('nombre_departamento', 'Sin departamento')
            elif depto_data and isinstance(depto_data, dict):
                usuario_procesado['departamento'] = depto_data.get('nombre_departamento', 'Sin departamento')
            
            rol_data = usuario.get('Rol')
            if rol_data and isinstance(rol_data, list) and len(rol_data) > 0:
                usuario_procesado['rol'] = rol_data[0].get('nombre_rol', 'Sin rol')
            elif rol_data and isinstance(rol_data, dict):
                usuario_procesado['rol'] = rol_data.get('nombre_rol', 'Sin rol')
                
            usuarios_procesados.append(usuario_procesado)

        df_usuarios = pd.DataFrame(usuarios_procesados)

        # Ordenamiento personalizado (Admin primero, etc)
        if not df_usuarios.empty:
            def asignar_prioridad(row):
                rol = str(row.get('rol', '')).lower()
                depto = str(row.get('departamento', '')).lower()
                if 'administrador' in rol: return 0
                elif 'soporte' in rol or 'soporte' in depto: return 1
                else: return 2

            df_usuarios['_orden'] = df_usuarios.apply(asignar_prioridad, axis=1)
            df_usuarios = df_usuarios.sort_values(by=['_orden', 'nombre'], ascending=[True, True])

        return df_usuarios

    except Exception as e:
        print(f"Ocurrió un error al obtener datos de Supabase: {e}")
        return pd.DataFrame(columns=['nombre', 'apellido', 'cedula', 'correo', 'departamento', 'rol', 'bloqueado'])

# --- FUNCIONES DE HISTORIAL ---

def registrar_historial_bd(cedula, accion, detalles):
    """Inserta un registro en la tabla HistorialUsuario vinculada por Cédula"""
    def _insertar():
        try:
            datos = {
                "cedula_usuario": int(cedula),
                "accion": accion,
                "detalles": detalles
            }
            supabase.table("HistorialUsuario").insert(datos).execute()
            print(f"Historial registrado: {accion} - {cedula}")
        except Exception as e:
            print(f"Error registrando historial: {e}")
    
    threading.Thread(target=_insertar, daemon=True).start()

def ver_historial_popup(root, cedula, nombre_completo):
    """Muestra ventana emergente con historial"""
    ventana = ctk.CTkToplevel(root)
    ventana.title(f"Historial")
    ventana.geometry("700x450")
    ventana.grab_set() 
    ventana.resizable(False, False)
    
    ventana.update_idletasks()
    x = (ventana.winfo_screenwidth() // 2) - (700 // 2)
    y = (ventana.winfo_screenheight() // 2) - (450 // 2)
    ventana.geometry(f"+{x}+{y}")

    ctk.CTkLabel(ventana, text=f"HISTORIAL DE MOVIMIENTOS", font=ctk.CTkFont(size=18, weight="bold"), text_color="#1E3D8F").pack(pady=(15, 5))
    ctk.CTkLabel(ventana, text=f"Usuario: {nombre_completo} (C.I: {cedula})", font=ctk.CTkFont(size=14), text_color="gray").pack(pady=(0, 15))

    header = ctk.CTkFrame(ventana, fg_color="#E5E7EB", height=30)
    header.pack(fill="x", padx=20)
    
    ctk.CTkLabel(header, text="FECHA/HORA", width=150, font=("Arial", 11, "bold"), text_color="black").pack(side="left", padx=5)
    ctk.CTkLabel(header, text="ACCIÓN", width=120, font=("Arial", 11, "bold"), text_color="black").pack(side="left", padx=5)
    ctk.CTkLabel(header, text="DETALLES", font=("Arial", 11, "bold"), text_color="black").pack(side="left", padx=5, fill="x", expand=True)

    scroll = ctk.CTkScrollableFrame(ventana, fg_color="white", corner_radius=0)
    scroll.pack(fill="both", expand=True, padx=20, pady=(0, 20))

    def renderizar_filas(data):
        for widget in scroll.winfo_children(): widget.destroy()
        
        if not data:
            ctk.CTkLabel(scroll, text="Sin movimientos registrados.", text_color="gray").pack(pady=20)
            return

        for i, item in enumerate(data):
            color_bg = "#F9FAFB" if i % 2 != 0 else "white"
            row = ctk.CTkFrame(scroll, fg_color=color_bg, corner_radius=0)
            row.pack(fill="x", pady=1)

            fecha_raw = item.get("fecha", "")
            try:
                fecha_obj = datetime.fromisoformat(fecha_raw.replace('Z', '+00:00'))
                fecha_str = fecha_obj.strftime("%d/%m/%Y %I:%M %p")
            except:
                fecha_str = fecha_raw[:16]

            ctk.CTkLabel(row, text=fecha_str, width=150, text_color="#4B5563", font=("Arial", 11)).pack(side="left", padx=5)
            
            accion = item.get("accion", "").upper()
            color_acc = "#16A34A" if "CREA" in accion else "#D97706" if "EDI" in accion else "#DC2626"
            ctk.CTkLabel(row, text=accion, width=120, text_color=color_acc, font=("Arial", 11, "bold")).pack(side="left", padx=5)
            
            # Label de detalles con wraplength para que no se corte si es largo
            detalles_lbl = ctk.CTkLabel(row, text=item.get("detalles", ""), text_color="#374151", font=("Arial", 11), anchor="w", justify="left")
            detalles_lbl.pack(side="left", padx=5, fill="x", expand=True)

    def cargar_datos():
        try:
            resp = supabase.table("HistorialUsuario").select("*").eq("cedula_usuario", int(cedula)).order("fecha", desc=True).execute()
            ventana.after(0, lambda: renderizar_filas(resp.data or []))
        except Exception as e:
            print(e)
            ventana.after(0, lambda: ctk.CTkLabel(scroll, text="Error de conexión.", text_color="red").pack(pady=20))

    threading.Thread(target=cargar_datos, daemon=True).start()

# ---------------------------------------------
    
def alternar_bloqueo_usuario(cedula, estado_actual, nombre_completo, funcion_recarga):
    nuevo_estado = not estado_actual
    accion_texto = "BLOQUEO" if nuevo_estado else "DESBLOQUEO"
    
    if not tk.messagebox.askyesno("Confirmar Bloqueo", f"¿Desea realizar {accion_texto} al usuario {nombre_completo}?"):
        return

    def _update():
        try:
            cedula_int = int(cedula)
            supabase.table("Usuario").update({"bloqueado": nuevo_estado}).eq("cedula", cedula_int).execute()
            
            # REGISTRO HISTORIAL BLOQUEO
            registrar_historial_bd(cedula, accion_texto, f"Estado cambiado a {'Bloqueado' if nuevo_estado else 'Activo'}")

            app_root.after(0, funcion_recarga)
            app_root.after(0, lambda: messagebox.showinfo("Éxito", f"Usuario actualizado correctamente."))
        except Exception as e:
            print(f"Error cambiando bloqueo: {e}")
            app_root.after(0, lambda: messagebox.showerror("Error", f"No se pudo actualizar el estado: {e}"))
            
    threading.Thread(target=_update, daemon=True).start()

# --- Componentes de UI Específicos ---

def abrir_ventana_seleccion_depto(root, display_entry, nombre_var):
    deptos_map = obtener_departamentos()
    all_deptos = sorted(list(deptos_map.keys())) 

    ventana = ctk.CTkToplevel(root)
    ventana.title("Seleccionar Departamento")
    ventana.configure(fg_color="#F7F9FB")
    ventana.grab_set()
    ventana.focus_force()
    ventana.geometry("500x500") 
    ventana.resizable(False, False) 
    
    contenido = ctk.CTkFrame(ventana, fg_color="#FFFFFF")
    contenido.pack(padx=20, pady=20, fill="both", expand=True) 
    contenido.grid_columnconfigure(0, weight=1)

    ctk.CTkLabel(contenido, text="Buscar Departamento", font=ctk.CTkFont(size=18, weight="bold"), text_color="#0C4A6E").grid(row=0, column=0, pady=(10, 15), sticky="w")
    
    search_entry = ctk.CTkEntry(contenido, placeholder_text="Escriba para buscar...", width=450, height=35)
    search_entry.grid(row=1, column=0, pady=(0, 10), sticky="ew")
    
    scroll_frame = ctk.CTkScrollableFrame(contenido, fg_color="#F9FAFB")
    scroll_frame.grid(row=2, column=0, sticky="nsew", pady=(0, 0)) 
    scroll_frame.grid_columnconfigure(0, weight=1)

    contenido.grid_rowconfigure(2, weight=1)

    def seleccionar_depto(nombre):
        display_entry.configure(state="normal")
        display_entry.delete(0, 'end')
        display_entry.insert(0, nombre)
        display_entry.configure(state="readonly")
        nombre_var.set(nombre)
        ventana.destroy()

    def render_list(filtro=""):
        for widget in scroll_frame.winfo_children():
            widget.destroy()
        
        filtro_lower = filtro.lower().strip()
        deptos_filtrados = []
        
        if filtro_lower:
            deptos_filtrados = [nombre for nombre in all_deptos if nombre.lower().startswith(filtro_lower)]
        else:
            deptos_filtrados = all_deptos
    
        if not deptos_filtrados:
            lbl = ctk.CTkLabel(scroll_frame, text="No se encontraron departamentos", text_color="#6B7280", font=ctk.CTkFont(size=12))
            lbl.grid(row=0, column=0, sticky="ew", pady=10)
            return
        
        for i, nombre in enumerate(deptos_filtrados):
            btn = ctk.CTkButton(
                scroll_frame, text=nombre, fg_color="transparent", hover_color="#E0F2FE", 
                text_color="black", corner_radius=0, anchor="w",
                command=lambda n=nombre: seleccionar_depto(n)
            )
            btn.grid(row=i, column=0, sticky="ew", pady=(1, 1))

    def filtrar_lista(event=None):
        texto_busqueda = search_entry.get()
        render_list(texto_busqueda)
        
    search_entry.bind("<KeyRelease>", filtrar_lista)
    search_entry.focus_set()
    render_list()
    
    ctk.CTkButton(contenido, text="CANCELAR", fg_color="#6B7280", hover_color="#4B5563", width=150, height=35, command=ventana.destroy).grid(row=3, column=0, pady=(10, 0))


# --- PANTALLA PRINCIPAL DE REGISTRO DE USUARIO ---
def mostrar_pantalla_registro(root):
    global registro_entries, registro_notificacion, app_root, usuario_seleccionado, btn_bloqueo_global, btn_historial_global
    
    last_row_selected_widget = None 
    last_row_selected_color = None

    from sistema_acceso import mostrar_pantalla_principal
    
    app_root = root
    usuario_seleccionado = None
    _clear_widgets(root)
    root.title("Gestión de Usuarios")

    departamentos_map = obtener_departamentos()
    roles_map = obtener_roles()
    departamento_names = list(departamentos_map.keys())
    rol_names = list(roles_map.keys())

    main_frame = ctk.CTkFrame(root, fg_color="#F7F9FB")
    main_frame.pack(expand=True, fill="both")
    main_frame.grid_rowconfigure(1, weight=1)
    main_frame.grid_columnconfigure(0, weight=1)

    # --- HEADER SUPERIOR ---
    header_frame = ctk.CTkFrame(main_frame, fg_color="#0C4A6E", corner_radius=0, height=70)
    header_frame.grid(row=0, column=0, sticky="ew")
    header_frame.grid_columnconfigure(1, weight=1)
    header_frame.grid_columnconfigure(2, weight=0)

    ctk.CTkLabel(header_frame, text="GESTIÓN DE USUARIOS", font=ctk.CTkFont(size=22, weight="bold"), text_color="white").grid(row=0, column=1, padx=(30, 20), pady=15, sticky="w")

    try:
        ruta_volver_reg = os.path.join("imagen", "volver.png")
        icono_volver_reg = ctk.CTkImage(light_image=PILImage.open(ruta_volver_reg), size=(20, 20))
        text_reg = ""
        width_reg = 50
    except Exception:
        icono_volver_reg = None
        text_reg = "VOLVER"
        width_reg = 120

    ctk.CTkButton(header_frame, text=text_reg, image=icono_volver_reg, fg_color="#3D89D1", hover_color="#1E3D8F", corner_radius=8, width=width_reg, height=40, command=lambda: mostrar_pantalla_principal(root)).grid(row=0, column=2, padx=(10, 20), pady=12, sticky="e")

    content_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
    content_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
    content_frame.grid_rowconfigure(0, weight=1)
    content_frame.grid_columnconfigure(0, weight=4) 
    content_frame.grid_columnconfigure(1, weight=1) 

    col_vacia_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
    col_vacia_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
    
    COL_CONF = [
        (0, "NOMBRE", 1, 87),
        (1, "APELLIDO", 1, 78),
        (2, "CÉDULA", 1, 80),         
        (3, "CORREO", 1, 173),
        (4, "DEPARTAMENTO", 5, 280),  
        (5, "ROL", 0, 73),            
        (6, "ESTADO", 0, 100)          
    ]

    def obtener_padding_columna(indice):
        if indice == 5: return (5, 5)  
        elif indice == 6: return (5, 10) 
        else: return 5 

    def recargar_tabla_usuarios():
        mostrar_pantalla_registro(root)

    try:
        df_usuarios_completo = obtener_usuarios_completos()

        botones_superior_frame = ctk.CTkFrame(col_vacia_frame, fg_color="transparent")
        botones_superior_frame.pack(fill="x", padx=20, pady=(0, 10))
        
        def _accion_bloqueo():
            if not usuario_seleccionado: return
            alternar_bloqueo_usuario(usuario_seleccionado['cedula'], usuario_seleccionado['data']['bloqueado'], usuario_seleccionado['nombre_completo'], recargar_tabla_usuarios)

        def _accion_historial():
            if not usuario_seleccionado: return
            ver_historial_popup(root, usuario_seleccionado['cedula'], usuario_seleccionado['nombre_completo'])

        btn_bloqueo_global = ctk.CTkButton(botones_superior_frame, text="BLOQUEAR USUARIO", fg_color="#D97706", hover_color="#FFFFFF", font=ctk.CTkFont(size=12, weight="bold"), width=140, height=35, state="disabled", command=_accion_bloqueo)
        btn_bloqueo_global.pack(side="left", padx=(5, 10))

        # --- BOTÓN HISTORIAL (NUEVO) ---
        btn_historial_global = ctk.CTkButton(botones_superior_frame, text="VER HISTORIAL", fg_color="#4B5563", hover_color="#374151", font=ctk.CTkFont(size=12, weight="bold"), width=140, height=35, state="disabled", command=_accion_historial)
        btn_historial_global.pack(side="left", padx=(0, 10))

        # --- Campo de Búsqueda ---
        search_entry = ctk.CTkEntry(botones_superior_frame, placeholder_text="Buscar por nombre, cédula o depto...", width=230, height=35)
        search_entry.pack(side="left", padx=(10, 10))

        seleccion_label = ctk.CTkLabel(botones_superior_frame, text="NINGÚN USUARIO SELECCIONADO", text_color="white", fg_color="#0C4A6E", corner_radius=6, font=ctk.CTkFont(size=11, weight="bold"), padx=10, pady=5)
        seleccion_label.pack(side="right", padx=10)

        table_container = ctk.CTkFrame(col_vacia_frame, fg_color="#FFFFFF", corner_radius=10, border_width=1, border_color="#E6E6E6")
        table_container.pack(fill="both", expand=True, padx=20, pady=10)
        
        # --- HEADER TABLA ---
        header_frame_table = ctk.CTkFrame(table_container, fg_color="#E5E7EB", corner_radius=0, height=45)
        header_frame_table.pack(fill="x")
        
        for idx, titulo, peso, min_w in COL_CONF:
            header_frame_table.grid_columnconfigure(idx, weight=peso, minsize=min_w)
            pad_config = obtener_padding_columna(idx)
            ctk.CTkLabel(header_frame_table, text=titulo, font=ctk.CTkFont(size=12, weight="bold"), text_color="#1F2937", anchor="w").grid(row=0, column=idx, padx=pad_config, pady=10, sticky="ew")

        # --- SCROLL AREA ---
        scroll_frame = ctk.CTkScrollableFrame(table_container, fg_color="#FFFFFF", corner_radius=0)
        scroll_frame.pack(fill="both", expand=True)
        
        for idx, _, peso, min_w in COL_CONF:
            scroll_frame.grid_columnconfigure(idx, weight=peso, minsize=min_w)

        def seleccionar_usuario(cedula, nombre_completo, row_frame, usuario_data, bg_original):
            global usuario_seleccionado
            nonlocal last_row_selected_widget, last_row_selected_color
            
            if last_row_selected_widget is not None and last_row_selected_widget.winfo_exists():
                try: last_row_selected_widget.configure(fg_color=last_row_selected_color)
                except: pass

            row_frame.configure(fg_color="#BFDBFE")
            last_row_selected_widget = row_frame
            last_row_selected_color = bg_original
            
            usuario_seleccionado = {'cedula': cedula, 'nombre_completo': nombre_completo, 'row_frame': row_frame, 'data': usuario_data}
            
            # ACTIVAR BOTONES
            btn_bloqueo_global.configure(state="normal")
            btn_historial_global.configure(state="normal")
            
            if usuario_data['bloqueado']:
                btn_bloqueo_global.configure(text="DESBLOQUEAR", fg_color="#16A34A")
            else:
                btn_bloqueo_global.configure(text="BLOQUEAR", fg_color="#D97706")
                
            seleccion_label.configure(text=f"SELECCIONADO: {nombre_completo.upper()}")
            cargar_datos_formulario(usuario_data)
        
        # Función para renderizar filas dinámicamente
        def renderizar_filas(df_datos):
            for widget in scroll_frame.winfo_children():
                widget.destroy()

            if df_datos.empty:
                ctk.CTkLabel(scroll_frame, text="No se encontraron resultados.", text_color="gray").pack(pady=20)
                return

            for i, row in df_datos.iterrows():
                bg_color = "#FFFFFF" if i % 2 == 0 else "#F9FAFB" 
                
                row_frame = ctk.CTkFrame(scroll_frame, fg_color=bg_color, corner_radius=0)
                row_frame.pack(fill="x")
                
                for idx, _, peso, min_w in COL_CONF:
                    row_frame.grid_columnconfigure(idx, weight=peso, minsize=min_w)

                nombre = str(row.get('nombre', '')).strip().upper()
                apellido = str(row.get('apellido', '')).strip().upper()
                cedula = str(row['cedula'])
                correo = str(row.get('correo', '')).strip()
                departamento = str(row.get('departamento', 'Sin departamento')).strip()
                rol_raw = str(row.get('rol', 'Sin rol')).strip()
                esta_bloqueado = bool(row.get('bloqueado', False))
                
                if rol_raw.lower() == 'administrador': rol_mostrar = "Admin"
                elif rol_raw.lower() in ['usuario', 'usuario estándar']: rol_mostrar = "Usuario"
                else: rol_mostrar = rol_raw.capitalize()
                
                estado_texto = "BLOQUEADO" if esta_bloqueado else "ACTIVO"
                estado_color = "#DC2626" if esta_bloqueado else "#16A34A"
                nombre_completo = f"{nombre} {apellido}".strip()
                usuario_data = {
                    'cedula': cedula, 'nombre': nombre, 'apellido': apellido, 
                    'correo': correo,
                    'departamento': departamento, 'rol': rol_raw, 'bloqueado': esta_bloqueado
                }

                callback = lambda e, c=cedula, n=nombre_completo, rf=row_frame, ud=usuario_data, bg=bg_color: seleccionar_usuario(c, n, rf, ud, bg)
                row_frame.bind("<Button-1>", callback)
                
                valores = [nombre, apellido, cedula, correo, departamento, rol_mostrar, estado_texto]
                
                for idx, val in enumerate(valores):
                    color_texto = estado_color if idx == 6 else "#374151"
                    font_w = "bold" if idx == 6 else "normal"
                    pad_config = obtener_padding_columna(idx)
                    pad_total = pad_config if isinstance(pad_config, int) else sum(pad_config)
                    ancho_wrap = COL_CONF[idx][3] - pad_total - 5

                    lbl = ctk.CTkLabel(
                        row_frame, 
                        text=val, 
                        font=ctk.CTkFont(size=12, weight=font_w), 
                        text_color=color_texto, 
                        anchor="w",
                        justify="left",
                        wraplength=ancho_wrap
                    )
                    lbl.grid(row=0, column=idx, padx=pad_config, pady=8, sticky="ew")
                    lbl.bind("<Button-1>", callback)
        
        def filtrar_tabla(event=None):
            texto = search_entry.get().lower().strip()
            
            if not texto:
                renderizar_filas(df_usuarios_completo)
                return
            
            mask = df_usuarios_completo.apply(lambda x: 
                texto in str(x['nombre']).lower() or
                texto in str(x['apellido']).lower() or
                texto in str(x['cedula']).lower() or
                texto in str(x['departamento']).lower() or
                texto in str(x['rol']).lower(),
                axis=1
            )
            
            df_filtrado = df_usuarios_completo[mask]
            renderizar_filas(df_filtrado)

        search_entry.bind("<KeyRelease>", filtrar_tabla)
        renderizar_filas(df_usuarios_completo)

    except Exception as e:
        ctk.CTkLabel(col_vacia_frame, text=f"Error: {e}", text_color="red").pack(pady=20)

    # --- FORMULARIO LATERAL (Sin cambios) ---
    form_frame = ctk.CTkFrame(content_frame, fg_color="#FFFFFF", corner_radius=10)
    form_frame.grid(row=0, column=1, pady=10, padx=20, ipadx=20, ipady=20, sticky="n")

    ctk.CTkLabel(form_frame, text="FORMULARIO DE USUARIO", font=ctk.CTkFont(size=18, weight="bold"), text_color="#1E3D8F").pack(pady=(10, 20))
    ANCHO_INPUT = 340
    
    registro_entries = {}
    
    cedula_ent = ctk.CTkEntry(form_frame, placeholder_text="Cédula", width=ANCHO_INPUT, height=40)
    cedula_ent.pack(pady=(0, 12))
    registro_entries['cedula'] = cedula_ent

    nombre_ent = ctk.CTkEntry(form_frame, placeholder_text="Nombre", width=ANCHO_INPUT, height=40)
    nombre_ent.pack(pady=(0, 12))
    registro_entries['nombre'] = nombre_ent

    apellido_ent = ctk.CTkEntry(form_frame, placeholder_text="Apellido", width=ANCHO_INPUT, height=40)
    apellido_ent.pack(pady=(0, 15))
    registro_entries['apellido'] = apellido_ent

    # --- CAMPO CORREO (Visible/Habilitado solo para Admin) ---
    correo_ent = ctk.CTkEntry(form_frame, placeholder_text="Correo (Solo Admin)", width=ANCHO_INPUT, height=40)
    correo_ent.pack(pady=(0, 15))
    correo_ent.configure(state="disabled", fg_color="#F0F0F0")
    registro_entries['correo'] = correo_ent

    def on_rol_change(choice):
        if "administrador" in str(choice).lower():
            correo_ent.configure(state="normal", fg_color=["#F9F9FA", "#343638"])
        else:
            correo_ent.delete(0, 'end')
            correo_ent.configure(state="disabled", fg_color="#F0F0F0")

    ctk.CTkLabel(form_frame, text="ROL", font=ctk.CTkFont(size=12, weight="bold"), text_color="#475569").pack(pady=(5, 2))
    rol_combo = ctk.CTkComboBox(form_frame, values=rol_names or ["--"], width=ANCHO_INPUT, height=40, state="readonly", command=on_rol_change)
    rol_combo.set(rol_names[0] if rol_names else "--")
    rol_combo.pack(pady=(0, 15))
    registro_entries['rol'] = rol_combo

    ctk.CTkLabel(form_frame, text="DEPARTAMENTO", font=ctk.CTkFont(size=12, weight="bold"), text_color="#475569").pack(pady=(5, 2))
    depto_display = ctk.CTkEntry(form_frame, placeholder_text="Seleccione...", width=ANCHO_INPUT, height=40, state="readonly")
    depto_display.pack(pady=(0, 8))
    depto_nombre_var = tk.StringVar(value=departamento_names[0] if departamento_names else "")
    depto_display.configure(state="normal"); depto_display.insert(0, depto_nombre_var.get()); depto_display.configure(state="readonly")
    registro_entries['departamento'] = depto_nombre_var

    ctk.CTkButton(form_frame, text="BUSCAR / SELECCIONAR", width=ANCHO_INPUT, height=35, fg_color="#3D89D1", command=lambda: abrir_ventana_seleccion_depto(root, depto_display, depto_nombre_var)).pack(pady=(5, 20))

    ctk.CTkButton(form_frame, text="CANCELAR", fg_color="#6B7280", width=ANCHO_INPUT, height=42, command=lambda: limpiar_formulario()).pack(pady=(0, 10))

    def guardar_usuario():
        if usuario_seleccionado and usuario_seleccionado['data']['bloqueado']:
            messagebox.showwarning("Restringido", "Usuario BLOQUEADO."); return

        c, n, a = registro_entries['cedula'].get(), registro_entries['nombre'].get().strip().upper(), registro_entries['apellido'].get().strip().upper()
        r_nom, d_nom = registro_entries['rol'].get(), registro_entries['departamento'].get()
        correo_val = registro_entries['correo'].get()

        if not c or not n or not a: _set_registro_notificacion("Faltan datos", "orange"); return
        
        if "administrador" in r_nom.lower() and not correo_val:
             _set_registro_notificacion("Correo requerido para Admin", "orange"); return

        datos_db = {
            'cedula': int(c), 
            'nombre': n, 
            'apellido': a, 
            'departamento': departamentos_map.get(d_nom), 
            'rol': roles_map.get(r_nom)
        }
        
        if "administrador" in r_nom.lower():
            datos_db['correo'] = correo_val
        else:
            datos_db['correo'] = ""

        def tarea():
            try:
                # EDICIÓN
                if usuario_seleccionado and str(usuario_seleccionado['cedula']) == str(c):
                    # --- LÓGICA DE DETECCIÓN DE CAMBIOS ---
                    cambios = []
                    old_data = usuario_seleccionado['data']
                    
                    if old_data['nombre'] != n: cambios.append(f"Nombre: {old_data['nombre']} > {n}")
                    if old_data['apellido'] != a: cambios.append(f"Apellido: {old_data['apellido']} > {a}")
                    
                    old_rol = old_data.get('rol', '')
                    if old_rol != r_nom: cambios.append(f"Rol: {old_rol} > {r_nom}")
                    
                    old_depto = old_data.get('departamento', '')
                    if old_depto != d_nom: cambios.append(f"Depto: {old_depto} > {d_nom}")
                    
                    old_correo = old_data.get('correo', '') or ""
                    if old_correo != correo_val: cambios.append(f"Correo: {old_correo} > {correo_val}")
                    
                    detalles_msg = ", ".join(cambios) if cambios else "Sin cambios detectados"
                    
                    supabase.table("Usuario").update(datos_db).eq("cedula", int(c)).execute()
                    
                    # REGISTRO HISTORIAL CON DETALLES
                    registrar_historial_bd(c, "EDICIÓN", detalles_msg)

                # CREACIÓN
                else:
                    if supabase.table("Usuario").select("cedula").eq("cedula", int(c)).execute().data:
                        _set_registro_notificacion("Cédula duplicada", "red"); return
                    supabase.table("Usuario").insert(datos_db).execute()
                    # REGISTRO HISTORIAL
                    registrar_historial_bd(c, "CREACIÓN", f"Usuario {n} {a} registrado.")

                app_root.after(0, lambda: [recargar_tabla_usuarios(), limpiar_formulario(), _set_registro_notificacion("Guardado OK", "#16A34A")])
            except Exception as e: print(e); _set_registro_notificacion("Error DB", "red")
            
        threading.Thread(target=tarea, daemon=True).start()

    ctk.CTkButton(form_frame, text="GUARDAR USUARIO", fg_color="#16A34A", width=ANCHO_INPUT, height=42, command=guardar_usuario).pack(pady=(0, 6))

    registro_notificacion = ctk.CTkLabel(form_frame, text="", text_color="red", wraplength=ANCHO_INPUT)
    registro_notificacion.pack(pady=(5, 15))
    
    def cargar_datos_formulario(u_data):
        cedula_ent.delete(0,'end'); cedula_ent.insert(0, u_data.get('cedula',''))
        nombre_ent.delete(0,'end'); nombre_ent.insert(0, u_data.get('nombre',''))
        apellido_ent.delete(0,'end'); apellido_ent.insert(0, u_data.get('apellido',''))
        
        rol_actual = u_data.get('rol', '')
        if rol_actual: 
            rol_combo.set(rol_actual)
            on_rol_change(rol_actual)
        
        if "administrador" in rol_actual.lower():
            correo_ent.delete(0, 'end')
            correo_ent.insert(0, u_data.get('correo', ''))

        if u_data.get('departamento'):
            depto_display.configure(state="normal"); depto_display.delete(0,'end'); depto_display.insert(0, u_data['departamento']); depto_display.configure(state="readonly")
            depto_nombre_var.set(u_data['departamento'])
        registro_notificacion.configure(text="Usuario Bloqueado" if u_data.get('bloqueado') else "Editando...", text_color="#DC2626" if u_data.get('bloqueado') else "#16A34A")

    def limpiar_formulario():
        global usuario_seleccionado
        nonlocal last_row_selected_widget
        if last_row_selected_widget: 
            try: last_row_selected_widget.configure(fg_color=last_row_selected_color) 
            except: pass
        last_row_selected_widget = None; usuario_seleccionado = None
        cedula_ent.delete(0,'end'); nombre_ent.delete(0,'end'); apellido_ent.delete(0,'end')
        correo_ent.delete(0, 'end'); correo_ent.configure(state="disabled", fg_color="#F0F0F0")
        
        depto_display.configure(state="normal"); depto_display.delete(0,'end'); depto_display.insert(0, departamento_names[0] if departamento_names else ""); depto_display.configure(state="readonly")
        
        if rol_names:
            rol_combo.set(rol_names[0])
            on_rol_change(rol_names[0])

        btn_bloqueo_global.configure(state="disabled", text="BLOQUEAR USUARIO", fg_color="#D97706")
        btn_historial_global.configure(state="disabled") # Bloquear btn historial
        seleccion_label.configure(text="NINGÚN USUARIO SELECCIONADO")
        registro_notificacion.configure(text="")
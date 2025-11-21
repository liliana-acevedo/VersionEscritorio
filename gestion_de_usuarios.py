import customtkinter as ctk
from cliente_supabase import supabase
import tkinter as tk
import threading
import pandas as pd
from tkinter import messagebox
import os
from PIL import Image as PILImage 

# Variables globales específicas para Gestión de Usuarios
registro_entries = {}
registro_notificacion = None
usuario_seleccionado = None
app_root = None

# --- Funciones Utilitarias Internas ---

def _clear_widgets(root):
    for widget in root.winfo_children():
        widget.destroy()

def _set_registro_notificacion(text, color):
    global registro_notificacion, app_root
    if not registro_notificacion or not app_root:
        return
    app_root.after(0, lambda: registro_notificacion.configure(text=text, text_color=color))

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

# --- Consultas a BD requeridas por este módulo ---

def obtener_departamentos():
    """Obtiene departamentos para llenar los dropdowns de usuario."""
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
            .select('nombre, apellido, cedula, Departamento(nombre_departamento), Rol(nombre_rol)')
            .execute()
        )
        datos = response.data

        if not datos:
            return pd.DataFrame(columns=['nombre', 'apellido', 'cedula', 'departamento', 'rol'])

        usuarios_procesados = []
        for usuario in datos:
            usuario_procesado = {
                'nombre': usuario.get('nombre', ''),
                'apellido': usuario.get('apellido', ''),
                'cedula': usuario.get('cedula', ''),
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
        return df_usuarios

    except Exception as e:
        print(f"Ocurrió un error al obtener datos de Supabase: {e}")
        return pd.DataFrame(columns=['nombre', 'apellido', 'cedula', 'departamento', 'rol'])

def eliminar_usuario(cedula, nombre_completo, row_frame=None):
    def _eliminar():
        try:
            cedula_int = int(cedula)
            response = supabase.table("Usuario").delete().eq("cedula", cedula_int).execute()
            if response.data:
                print(f"Usuario {nombre_completo} eliminado correctamente")
                def eliminar_fila_ui():
                    if row_frame and row_frame.winfo_exists():
                        row_frame.destroy()
                    global usuario_seleccionado, app_root
                    if usuario_seleccionado and usuario_seleccionado['cedula'] == cedula:
                        usuario_seleccionado = None
                        # Limpiar etiquetas de selección si existen
                        if app_root:
                            for widget in app_root.winfo_children():
                                if isinstance(widget, ctk.CTkFrame):
                                    for child in widget.winfo_children():
                                        if isinstance(child, ctk.CTkFrame):
                                            for subchild in child.winfo_children():
                                                if hasattr(subchild, 'cget') and "USUARIO SELECCIONADO" in subchild.cget("text", "").upper():
                                                    subchild.configure(text="NINGÚN USUARIO SELECCIONADO", text_color="white")
                if app_root:
                    app_root.after(0, eliminar_fila_ui)
            else:
                if app_root:
                    app_root.after(0, lambda: messagebox.showerror("Error", f"No se pudo eliminar al usuario {nombre_completo}"))
        except Exception as e:
            if app_root:
                app_root.after(0, lambda: messagebox.showerror("Error", f"Error al eliminar usuario: {e}"))
    
    confirmar = tk.messagebox.askyesno(
        "Confirmar Eliminación", 
        f"¿Está seguro de que desea eliminar al usuario:\n{nombre_completo}?\n\nCédula: {cedula}"
    )
    if confirmar:
        threading.Thread(target=_eliminar, daemon=True).start()

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
    global registro_entries, registro_notificacion, app_root, usuario_seleccionado
    
    # Importación diferida para evitar error circular al volver
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
    content_frame.grid_columnconfigure(0, weight=3)
    content_frame.grid_columnconfigure(1, weight=1)

    col_vacia_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
    col_vacia_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
    
    try:
        df_usuarios = obtener_usuarios_completos() 
        botones_superior_frame = ctk.CTkFrame(col_vacia_frame, fg_color="transparent")
        botones_superior_frame.pack(fill="x", padx=20, pady=(0, 10))
        
        try:
            ruta_eliminar_reg = os.path.join("imagen", "eliminar.png")
            icono_eliminar_reg = ctk.CTkImage(light_image=PILImage.open(ruta_eliminar_reg), size=(20, 20))
            texto_elim_reg = ""
            ancho_elim_reg = 40
        except Exception:
            icono_eliminar_reg = None
            texto_elim_reg = "ELIMINAR"
            ancho_elim_reg = 120

        btn_eliminar_superior = ctk.CTkButton(botones_superior_frame, text=texto_elim_reg, image=icono_eliminar_reg, fg_color="#DC2626", hover_color="#B91C1C", font=ctk.CTkFont(size=13, weight="bold"), width=ancho_elim_reg, height=35, command=lambda: _eliminar_usuario_seleccionado())
        btn_eliminar_superior.pack(side="left", padx=(0, 10))
        
        seleccion_label = ctk.CTkLabel(botones_superior_frame, text="NINGÚN USUARIO SELECCIONADO", text_color="white", fg_color="#0C4A6E", corner_radius=6, font=ctk.CTkFont(size=11, weight="bold"), padx=10, pady=5)
        seleccion_label.pack(side="right", padx=10)

        if df_usuarios.empty:
            ctk.CTkLabel(col_vacia_frame, text="No se encontraron usuarios en la base de datos.", text_color="#1E3D8F", font=ctk.CTkFont(size=14)).pack(pady=10)
        else:
            table_container = ctk.CTkFrame(col_vacia_frame, fg_color="#FFFFFF", corner_radius=10, border_width=1, border_color="#E6E6E6")
            table_container.pack(fill="both", expand=True, padx=20, pady=10)
            
            header_frame_table = ctk.CTkFrame(table_container, fg_color="#F3F4F6", corner_radius=0)
            header_frame_table.pack(fill="x")
            header_frame_table.grid_columnconfigure(0, weight=0, minsize=120)
            header_frame_table.grid_columnconfigure(1, weight=0, minsize=120)
            header_frame_table.grid_columnconfigure(2, weight=0, minsize=100)
            header_frame_table.grid_columnconfigure(3, weight=1, minsize=350)
            header_frame_table.grid_columnconfigure(4, weight=0, minsize=120)
            
            ctk.CTkLabel(header_frame_table, text="NOMBRE", font=ctk.CTkFont(size=13, weight="bold"), text_color="#374151", anchor="w").grid(row=0, column=0, padx=8, pady=10, sticky="w")
            ctk.CTkLabel(header_frame_table, text="APELLIDO", font=ctk.CTkFont(size=13, weight="bold"), text_color="#374151", anchor="w").grid(row=0, column=1, padx=8, pady=10, sticky="w")
            ctk.CTkLabel(header_frame_table, text="CÉDULA", font=ctk.CTkFont(size=13, weight="bold"), text_color="#374151", anchor="w").grid(row=0, column=2, padx=8, pady=10, sticky="w")
            ctk.CTkLabel(header_frame_table, text="DEPARTAMENTO", font=ctk.CTkFont(size=13, weight="bold"), text_color="#374151", anchor="w").grid(row=0, column=3, padx=8, pady=10, sticky="w")
            ctk.CTkLabel(header_frame_table, text="ROL", font=ctk.CTkFont(size=13, weight="bold"), text_color="#374151", anchor="w").grid(row=0, column=4, padx=8, pady=10, sticky="w")

            scroll_frame = ctk.CTkScrollableFrame(table_container, fg_color="#FFFFFF", corner_radius=0)
            scroll_frame.pack(fill="both", expand=True)
            scroll_frame.grid_columnconfigure(0, weight=0, minsize=120)
            scroll_frame.grid_columnconfigure(1, weight=0, minsize=120)
            scroll_frame.grid_columnconfigure(2, weight=0, minsize=100)
            scroll_frame.grid_columnconfigure(3, weight=1, minsize=350)
            scroll_frame.grid_columnconfigure(4, weight=0, minsize=120)
            
            def seleccionar_usuario(cedula, nombre_completo, row_frame, usuario_data):
                global usuario_seleccionado
                
                # --- PASO 1: Restauración visual ultrarrápida ---
                # En lugar de calcular pares/impares, usamos el color que guardamos en memoria.
                if usuario_seleccionado and usuario_seleccionado.get('row_frame'):
                    prev_frame = usuario_seleccionado['row_frame']
                    prev_color = usuario_seleccionado.get('original_color', '#FFFFFF')
                    try:
                        if prev_frame.winfo_exists():
                            prev_frame.configure(fg_color=prev_color)
                    except Exception:
                        pass

                # --- PASO 2: Guardar estado actual y pintar nuevo ---
                # Obtenemos el color actual de la fila (blanco o gris) antes de ponerla azul
                try:
                    current_color = row_frame.cget("fg_color")
                except:
                    current_color = "#FFFFFF"

                # Pintamos de azul INMEDIATAMENTE (Feedback visual instantáneo)
                row_frame.configure(fg_color="#E0F2FE")

                # Actualizamos la variable global
                usuario_seleccionado = {
                    'cedula': cedula, 
                    'nombre_completo': nombre_completo, 
                    'row_frame': row_frame, 
                    'data': usuario_data,
                    'original_color': current_color # Guardamos el color original aquí
                }

                # --- PASO 3: Carga de datos DIFERIDA ---
                # Aquí está el truco: usamos .after(5, ...)
                # Esto permite que la interfaz dibuje el color azul PRIMERO y 5ms después llene los datos.
                # El usuario sentirá que el clic fue instantáneo.
                def _llenar_campos_tardios():
                    try:
                        seleccion_label.configure(text=f"SELECCIONADO: {nombre_completo.upper()}", text_color="white")
                        cargar_datos_formulario(usuario_data)
                    except Exception as e:
                        print(f"Error UI diferido: {e}")

                row_frame.after(5, _llenar_campos_tardios)
                
            for i, row in df_usuarios.iterrows():
                bg_color = "#FFFFFF" if i % 2 == 0 else "#F9FAFB" 
                text_color = "#374151"
               
                row_frame = ctk.CTkFrame(scroll_frame, fg_color=bg_color, corner_radius=0, height=35)
                row_frame.pack(fill="x")
                row_frame.grid_columnconfigure(0, weight=0, minsize=120)
                row_frame.grid_columnconfigure(1, weight=0, minsize=120)
                row_frame.grid_columnconfigure(2, weight=0, minsize=100)
                row_frame.grid_columnconfigure(3, weight=1, minsize=350)
                row_frame.grid_columnconfigure(4, weight=0, minsize=120)

                nombre = str(row.get('nombre', '')).strip().upper()
                apellido = str(row.get('apellido', '')).strip().upper()
                cedula = str(row['cedula'])
                departamento = str(row.get('departamento', 'Sin departamento')).strip()
                rol = str(row.get('rol', 'Sin rol')).strip()
                
                if rol.lower() == 'administrador':
                    rol_mostrar = "administrador"
                elif rol.lower() == 'usuario' or rol.lower() == 'usuario estándar':
                    rol_mostrar = "usuario"
                elif rol.lower() == 'tecnico de soporte':
                    rol_mostrar = "tecnico de soporte"
                else:
                    rol_mostrar = rol.lower()
                
                nombre_completo = f"{nombre} {apellido}".strip()
                usuario_data = {'cedula': cedula, 'nombre': nombre, 'apellido': apellido, 'departamento': departamento, 'rol': rol}

                row_frame.bind("<Button-1>", lambda e, c=cedula, n=nombre_completo, rf=row_frame, ud=usuario_data: seleccionar_usuario(c, n, rf, ud))
                
                ctk.CTkLabel(row_frame, text=nombre, font=ctk.CTkFont(size=13), text_color=text_color, anchor="w").grid(row=0, column=0, padx=8, pady=8, sticky="w")
                ctk.CTkLabel(row_frame, text=apellido, font=ctk.CTkFont(size=13), text_color=text_color, anchor="w").grid(row=0, column=1, padx=8, pady=8, sticky="w")
                ctk.CTkLabel(row_frame, text=cedula, font=ctk.CTkFont(size=13), text_color=text_color, anchor="w").grid(row=0, column=2, padx=8, pady=8, sticky="w")
                ctk.CTkLabel(row_frame, text=departamento, font=ctk.CTkFont(size=13), text_color=text_color, anchor="w").grid(row=0, column=3, padx=8, pady=8, sticky="w")
                ctk.CTkLabel(row_frame, text=rol_mostrar, font=ctk.CTkFont(size=13), text_color=text_color, anchor="w").grid(row=0, column=4, padx=8, pady=8, sticky="w")

    except Exception as e:
        ctk.CTkLabel(col_vacia_frame, text=f"Error al cargar usuarios: {e}", text_color="red", font=ctk.CTkFont(size=14)).pack(pady=20, padx=20)

    form_frame = ctk.CTkFrame(content_frame, fg_color="#FFFFFF", corner_radius=10)
    form_frame.grid(row=0, column=1, pady=10, padx=20, ipadx=20, ipady=20, sticky="n")

    ctk.CTkLabel(form_frame, text="FORMULARIO DE USUARIO", font=ctk.CTkFont(size=18, weight="bold"), text_color="#1E3D8F").pack(pady=(10, 20))

    ANCHO_INPUT = 340
    ALTO_INPUT = 40
    COLOR_BORDE = "#94A3B8"
    COLOR_PLACEHOLDER = "#9CA3AF"

    registro_entries = {}
    
    cedula_ent = ctk.CTkEntry(form_frame, placeholder_text="Cédula", placeholder_text_color=COLOR_PLACEHOLDER, width=ANCHO_INPUT, height=ALTO_INPUT, corner_radius=8, border_width=1, fg_color="white", border_color=COLOR_BORDE, text_color="black", font=ctk.CTkFont(size=14))
    cedula_ent.pack(pady=(0, 12))
    registro_entries['cedula'] = cedula_ent

    nombre_ent = ctk.CTkEntry(form_frame, placeholder_text="Nombre", placeholder_text_color=COLOR_PLACEHOLDER, width=ANCHO_INPUT, height=ALTO_INPUT, corner_radius=8, border_width=1, fg_color="white", border_color=COLOR_BORDE, text_color="black", font=ctk.CTkFont(size=14))
    nombre_ent.pack(pady=(0, 12))
    registro_entries['nombre'] = nombre_ent

    apellido_ent = ctk.CTkEntry(form_frame, placeholder_text="Apellido", placeholder_text_color=COLOR_PLACEHOLDER, width=ANCHO_INPUT, height=ALTO_INPUT, corner_radius=8, border_width=1, fg_color="white", border_color=COLOR_BORDE, text_color="black", font=ctk.CTkFont(size=14))
    apellido_ent.pack(pady=(0, 15))
    registro_entries['apellido'] = apellido_ent

    ctk.CTkLabel(form_frame, text="ROL DE USUARIO", font=ctk.CTkFont(size=12, weight="bold"), text_color="#475569").pack(pady=(5, 2))
    
    rol_vals = rol_names if rol_names else ["-- Sin roles --"]
    rol_combo = ctk.CTkComboBox(form_frame, values=rol_vals, width=ANCHO_INPUT, height=ALTO_INPUT, corner_radius=8, border_width=1, border_color=COLOR_BORDE, fg_color="white", text_color="black", justify="center", button_color="#E2E8F0", button_hover_color="#CBD5E1", dropdown_fg_color="white", dropdown_text_color="black", dropdown_hover_color="#E0F2FE", state="readonly")
    if rol_names:
        default_rol = "usuario" if "usuario" in rol_names else rol_names[0]
        rol_combo.set(default_rol)
    else:
        rol_combo.set("-- Sin roles --")
    rol_combo.pack(pady=(0, 15))
    registro_entries['rol'] = rol_combo

    ctk.CTkLabel(form_frame, text="DEPARTAMENTO", font=ctk.CTkFont(size=12, weight="bold"), text_color="#475569").pack(pady=(5, 2))

    depto_display = ctk.CTkEntry(form_frame, placeholder_text="Seleccione un Departamento...", width=ANCHO_INPUT, height=ALTO_INPUT, corner_radius=8, border_width=1, fg_color="#F8FAFC", border_color=COLOR_BORDE, text_color="black", font=ctk.CTkFont(size=14))
    depto_display.pack(pady=(0, 8))
    
    depto_display.insert(0, departamento_names[0] if departamento_names else "-- Sin departamentos --")
    depto_display.configure(state="readonly")
    
    depto_nombre_var = tk.StringVar(value=departamento_names[0] if departamento_names else "")
    registro_entries['departamento'] = depto_nombre_var

    ctk.CTkButton(form_frame, text="BUSCAR / SELECCIONAR", width=ANCHO_INPUT, height=35, fg_color="#3D89D1", hover_color="#1E3D8F", font=ctk.CTkFont(size=12, weight="bold"), command=lambda: abrir_ventana_seleccion_depto(root, depto_display, depto_nombre_var)).pack(pady=(5, 20))

    btn_limpiar = ctk.CTkButton(form_frame, text="CANCELAR", fg_color="#6B7280", hover_color="#4B5563", font=ctk.CTkFont(size=13, weight="bold"), width=ANCHO_INPUT, height=42, command=lambda: limpiar_formulario())
    btn_limpiar.pack(pady=(0, 10))

    def guardar_usuario():
        cedula_val = (registro_entries.get('cedula').get() or "").strip()
        nombre_val = (registro_entries.get('nombre').get() or "").strip()
        apellido_val = (registro_entries.get('apellido').get() or "").strip()
        rol_nombre = (registro_entries.get('rol').get() or "").strip()
        depto_nombre = (registro_entries.get('departamento').get() or "").strip()

        if not cedula_val or not nombre_val or not apellido_val:
            _set_registro_notificacion("Faltan campos obligatorios.", "orange")
            return
        if not cedula_val.isdigit() or len(cedula_val) < 4:
            _set_registro_notificacion("Cédula inválida o muy corta.", "orange")
            return
        if rol_nombre not in roles_map or depto_nombre not in departamentos_map:
            _set_registro_notificacion("Rol/Departamento no válido.", "red")
            return

        datos_db = {'cedula': int(cedula_val), 'nombre': nombre_val, 'apellido': apellido_val, 'departamento': departamentos_map[depto_nombre], 'rol': roles_map[rol_nombre]}
        datos_visuales = {'cedula': cedula_val, 'nombre': nombre_val.upper(), 'apellido': apellido_val.upper(), 'departamento': depto_nombre, 'rol': rol_nombre}
        _set_registro_notificacion("Procesando...", "#1E3D8F")

        def actualizar_ui_inmediata(es_edicion):
            try:
                if es_edicion and usuario_seleccionado:
                    row = usuario_seleccionado['row_frame']
                    widgets = row.winfo_children()
                    if len(widgets) >= 5:
                        widgets[0].configure(text=datos_visuales['nombre'])
                        widgets[1].configure(text=datos_visuales['apellido'])
                        widgets[2].configure(text=datos_visuales['cedula'])
                        widgets[3].configure(text=datos_visuales['departamento'])
                        widgets[4].configure(text=datos_visuales['rol'])
                    
                    usuario_seleccionado['nombre_completo'] = f"{datos_visuales['nombre']} {datos_visuales['apellido']}"
                    usuario_seleccionado['data'].update(datos_visuales)
                    seleccion_label.configure(text=f"SELECCIONADO: {usuario_seleccionado['nombre_completo']}")
                    _set_registro_notificacion("✓ Usuario actualizado (Vista actualizada)", "#16A34A")
                else:
                    count = len(scroll_frame.winfo_children())
                    bg_color = "#FFFFFF" if count % 2 == 0 else "#F9FAFB"
                    new_row = ctk.CTkFrame(scroll_frame, fg_color=bg_color, corner_radius=0, height=35)
                    new_row.pack(fill="x")
                    new_row.grid_columnconfigure(0, weight=0, minsize=120)
                    new_row.grid_columnconfigure(1, weight=0, minsize=120)
                    new_row.grid_columnconfigure(2, weight=0, minsize=100)
                    new_row.grid_columnconfigure(3, weight=1, minsize=350)
                    new_row.grid_columnconfigure(4, weight=0, minsize=120)
                    
                    font_std = ctk.CTkFont(size=13)
                    color_std = "#374151"
                    lbl_nom = ctk.CTkLabel(new_row, text=datos_visuales['nombre'], font=font_std, text_color=color_std, anchor="w")
                    lbl_ape = ctk.CTkLabel(new_row, text=datos_visuales['apellido'], font=font_std, text_color=color_std, anchor="w")
                    lbl_ced = ctk.CTkLabel(new_row, text=datos_visuales['cedula'], font=font_std, text_color=color_std, anchor="w")
                    lbl_dep = ctk.CTkLabel(new_row, text=datos_visuales['departamento'], font=font_std, text_color=color_std, anchor="w")
                    lbl_rol = ctk.CTkLabel(new_row, text=datos_visuales['rol'], font=font_std, text_color=color_std, anchor="w")
                    
                    lbl_nom.grid(row=0, column=0, padx=8, pady=8, sticky="w")
                    lbl_ape.grid(row=0, column=1, padx=8, pady=8, sticky="w")
                    lbl_ced.grid(row=0, column=2, padx=8, pady=8, sticky="w")
                    lbl_dep.grid(row=0, column=3, padx=8, pady=8, sticky="w")
                    lbl_rol.grid(row=0, column=4, padx=8, pady=8, sticky="w")
                    
                    nombre_completo = f"{datos_visuales['nombre']} {datos_visuales['apellido']}"
                    def bind_click(widget):
                        widget.bind("<Button-1>", lambda e, c=datos_visuales['cedula'], n=nombre_completo, rf=new_row, ud=datos_visuales: seleccionar_usuario(c, n, rf, ud))
                    bind_click(new_row)
                    bind_click(lbl_nom)
                    bind_click(lbl_ape)
                    bind_click(lbl_ced)
                    bind_click(lbl_dep)
                    bind_click(lbl_rol)
                    _set_registro_notificacion("✓ Usuario registrado (Tabla actualizada)", "#16A34A")
                    limpiar_formulario()
            except Exception as e:
                print(f"Error actualizando UI: {e}")
                _set_registro_notificacion("Datos guardados, pero error visual (recargue)", "orange")

        def tarea_guardado():
            try:
                es_edicion = False
                if usuario_seleccionado and str(usuario_seleccionado['cedula']) == str(cedula_val):
                    es_edicion = True
                    resp = supabase.table("Usuario").update(datos_db).eq("cedula", int(cedula_val)).execute()
                else:
                    dup = supabase.table("Usuario").select("cedula").eq("cedula", int(cedula_val)).execute()
                    if dup.data:
                        _set_registro_notificacion("Error: Cédula ya existe.", "red")
                        return
                    resp = supabase.table("Usuario").insert(datos_db).execute()

                if resp.data:
                    app_root.after(0, lambda: actualizar_ui_inmediata(es_edicion))
                else:
                    _set_registro_notificacion("Error al guardar en base de datos.", "red")

            except Exception as e:
                msg = str(e)
                print("Error DB:", msg)
                _set_registro_notificacion("Error de conexión o base de datos.", "red")

        threading.Thread(target=tarea_guardado, daemon=True).start()

    ctk.CTkButton(form_frame, text="GUARDAR USUARIO", fg_color="#16A34A", hover_color="#15803D", font=ctk.CTkFont(size=14, weight="bold"), width=ANCHO_INPUT, height=42, command=guardar_usuario).pack(pady=(0, 6))

    global registro_notificacion 
    registro_notificacion = ctk.CTkLabel(form_frame, text="", font=ctk.CTkFont(size=12, weight="bold"), text_color="#DC2626", wraplength=ANCHO_INPUT)
    registro_notificacion.pack(pady=(5, 15))
    
    def cargar_datos_formulario(usuario_data):
        try:
            cedula_ent.delete(0, 'end')
            cedula_ent.insert(0, usuario_data.get('cedula', ''))
            nombre_ent.delete(0, 'end')
            nombre_ent.insert(0, usuario_data.get('nombre', ''))
            apellido_ent.delete(0, 'end')
            apellido_ent.insert(0, usuario_data.get('apellido', ''))
            
            depto_nombre = usuario_data.get('departamento', '')
            if depto_nombre:
                depto_display.configure(state="normal")
                depto_display.delete(0, 'end')
                depto_display.insert(0, depto_nombre)
                depto_display.configure(state="readonly")
                depto_nombre_var.set(depto_nombre)
            
            rol_nombre = usuario_data.get('rol', '')
            if rol_nombre:
                rol_combo.set(rol_nombre)
            
            registro_notificacion.configure(text="Datos cargados para edición", text_color="#16A34A")
        except Exception as e:
            registro_notificacion.configure(text=f"Error al cargar datos: {e}", text_color="#DC2626")

    def limpiar_formulario():
        global usuario_seleccionado
        usuario_seleccionado = None
        cedula_ent.delete(0, 'end')
        nombre_ent.delete(0, 'end')
        apellido_ent.delete(0, 'end')
        
        if rol_names:
            default_rol = "usuario" if "usuario" in rol_names else rol_names[0]
            rol_combo.set(default_rol)
        
        if departamento_names:
            depto_display.configure(state="normal")
            depto_display.delete(0, 'end')
            depto_display.insert(0, departamento_names[0])
            depto_display.configure(state="readonly")
            depto_nombre_var.set(departamento_names[0])
        
        for widget in scroll_frame.winfo_children():
            if isinstance(widget, ctk.CTkFrame):
                index = scroll_frame.winfo_children().index(widget)
                bg_color = "#FFFFFF" if index % 2 == 0 else "#F9FAFB"
                widget.configure(fg_color=bg_color)
        
        seleccion_label.configure(text="NINGÚN USUARIO SELECCIONADO", text_color="white")
        registro_notificacion.configure(text="Formulario listo para nuevo usuario", text_color="#3D89D1")

    def _eliminar_usuario_seleccionado():
        global usuario_seleccionado
        if not usuario_seleccionado:
            tk.messagebox.showwarning("Advertencia", "Por favor seleccione un usuario primero.")
            return
        row_frame_seleccionado = None
        for widget in scroll_frame.winfo_children():
            if isinstance(widget, ctk.CTkFrame) and widget.cget("fg_color") == "#E0F2FE":
                row_frame_seleccionado = widget
                break
        eliminar_usuario(usuario_seleccionado['cedula'], usuario_seleccionado['nombre_completo'], row_frame_seleccionado)
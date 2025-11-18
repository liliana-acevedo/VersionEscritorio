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

# --- NUEVAS IMPORTACIONES PARA GRÁFICOS ---
try:
    import matplotlib
    matplotlib.use('TkAgg') # Especificar el backend de Tkinter para Matplotlib
except ImportError:
    print("ADVERTENCIA: Matplotlib no está instalado. Ejecute 'pip install matplotlib' para ver los gráficos.")

# --- IMPORTACIÓN DEL NUEVO CONTROLADOR ---
try:
    from controladores_graficos import mostrar_pantalla_graficos
except ImportError as e:
    print(f"Error al importar controladores_graficos: {e}")
    # Definir una función ficticia para evitar que la app se rompa
    def mostrar_pantalla_graficos(root):
        messagebox.showerror("Error", "No se pudo cargar el módulo de gráficos (controladores_graficos.py).")
# ------------------------------------------


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

# Variable global para usuario seleccionado
usuario_seleccionado = None


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

# --- FUNCIÓN MODIFICADA PARA INCLUIR DEPARTAMENTO Y ROL ---
def obtener_usuarios_completos():
    """
    Consulta la tabla 'Usuario' en Supabase con JOIN a 'Departamento' y 'Rol'
    y devuelve un DataFrame con nombre, apellido, cedula, nombre_departamento y nombre_rol.
    """
    try:
        # Consulta con JOIN para obtener el nombre del departamento y rol
        response = (
            supabase.table('Usuario')
            .select('nombre, apellido, cedula, Departamento(nombre_departamento), Rol(nombre_rol)')
            .execute()
        )

        # Extraer los datos
        datos = response.data

        if not datos:
            print("No se encontraron usuarios.")
            return pd.DataFrame(columns=['nombre', 'apellido', 'cedula', 'departamento', 'rol'])

        # Procesar los datos para extraer el nombre del departamento y rol
        usuarios_procesados = []
        for usuario in datos:
            usuario_procesado = {
                'nombre': usuario.get('nombre', ''),
                'apellido': usuario.get('apellido', ''),
                'cedula': usuario.get('cedula', ''),
                'departamento': 'Sin departamento',
                'rol': 'Sin rol'
            }
            
            # Extraer el nombre del departamento del objeto anidado
            depto_data = usuario.get('Departamento')
            if depto_data and isinstance(depto_data, list) and len(depto_data) > 0:
                usuario_procesado['departamento'] = depto_data[0].get('nombre_departamento', 'Sin departamento')
            elif depto_data and isinstance(depto_data, dict):
                usuario_procesado['departamento'] = depto_data.get('nombre_departamento', 'Sin departamento')
            
            # Extraer el nombre del rol del objeto anidado
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
# ------------------------------------------------

# --- FUNCIONES PARA ELIMINAR Y EDITAR USUARIOS ---
def eliminar_usuario(cedula, nombre_completo, row_frame=None):
    """Elimina un usuario de la base de datos sin recargar toda la página"""
    def _eliminar():
        try:
            # CONVERTIR LA CÉDULA A ENTERO ANTES DE ELIMINAR
            cedula_int = int(cedula)
            response = supabase.table("Usuario").delete().eq("cedula", cedula_int).execute()
            if response.data:
                print(f"Usuario {nombre_completo} eliminado correctamente")
                # En lugar de recargar toda la pantalla, solo eliminamos la fila visualmente
                def eliminar_fila_ui():
                    if row_frame and row_frame.winfo_exists():
                        row_frame.destroy()
                    # También actualizamos la selección
                    global usuario_seleccionado
                    if usuario_seleccionado and usuario_seleccionado['cedula'] == cedula:
                        usuario_seleccionado = None
                        # Actualizar la etiqueta de selección
                        for widget in app_root.winfo_children():
                            if isinstance(widget, ctk.CTkFrame):
                                for child in widget.winfo_children():
                                    if isinstance(child, ctk.CTkFrame):
                                        for subchild in child.winfo_children():
                                            if hasattr(subchild, 'cget') and "Ningún usuario seleccionado" in subchild.cget("text", ""):
                                                subchild.configure(text="Ningún usuario seleccionado", text_color="#6B7280")
                app_root.after(0, eliminar_fila_ui)
            else:
                print(f"Error al eliminar usuario {nombre_completo}")
                app_root.after(0, lambda: messagebox.showerror("Error", f"No se pudo eliminar al usuario {nombre_completo}"))
        except Exception as e:
            print(f"Error al eliminar usuario: {e}")
            app_root.after(0, lambda: messagebox.showerror("Error", f"Error al eliminar usuario: {e}"))
    
    # Confirmación antes de eliminar
    confirmar = tk.messagebox.askyesno(
        "Confirmar Eliminación", 
        f"¿Está seguro de que desea eliminar al usuario:\n{nombre_completo}?\n\nCédula: {cedula}"
    )
    
    if confirmar:
        threading.Thread(target=_eliminar, daemon=True).start()

def editar_usuario(cedula, usuario_data):
    """Abre una ventana para editar los datos del usuario"""
    # Crear ventana de edición compacta
    ventana_edicion = ctk.CTkToplevel(app_root)
    ventana_edicion.title(f"Editar Usuario - {usuario_data['nombre']} {usuario_data['apellido']}")
    ventana_edicion.geometry("450x580")
    ventana_edicion.configure(fg_color="#F8F8F8")
    ventana_edicion.grab_set()
    ventana_edicion.focus_force()
    ventana_edicion.minsize(450, 580)
    ventana_edicion.resizable(False, False)
    
    # Variable para controlar si la ventana sigue abierta
    ventana_abierta = True
    
    def cerrar_ventana():
        nonlocal ventana_abierta
        ventana_abierta = False
        ventana_edicion.destroy()
    
    ventana_edicion.protocol("WM_DELETE_WINDOW", cerrar_ventana)
    
    # Marco principal compacto
    main_frame = ctk.CTkFrame(ventana_edicion, fg_color="#F7F9FB")
    main_frame.pack(expand=True, fill="both", padx=20, pady=20)
    
    # Formulario compacto
    form_frame = ctk.CTkFrame(main_frame, fg_color="#FFFFFF", corner_radius=10)
    form_frame.pack(fill="both", expand=True, padx=0, pady=0)
    
    # Contenedor interno compacto
    content_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
    content_frame.pack(fill="both", expand=True, padx=5, pady=5)
    
    # Campos del formulario - COMPACTOS
    campos = {}
    
    # Cédula (solo lectura) - compacto
    ctk.CTkLabel(content_frame, text="Cédula:", text_color="#1E3D8F", 
                 font=ctk.CTkFont(size=12, weight="bold")).pack(pady=(5, 5), anchor="w")
    cedula_entry = ctk.CTkEntry(content_frame, 
                               fg_color="#F8FAFC", border_color="#D1D5DB",
                               text_color="#64748B", font=ctk.CTkFont(size=12),
                               border_width=1, corner_radius=6,
                               height=35)
    cedula_entry.insert(0, str(cedula))
    cedula_entry.configure(state="disabled")
    cedula_entry.pack(pady=(0, 12), fill="x")
    
    # Nombre - compacto
    ctk.CTkLabel(content_frame, text="Nombre:", text_color="#1E3D8F",
                 font=ctk.CTkFont(size=12, weight="bold")).pack(pady=(3, 5), anchor="w")
    nombre_entry = ctk.CTkEntry(content_frame,
                               fg_color="white", border_color="#CBD5E1",
                               text_color="#1E293B", font=ctk.CTkFont(size=12),
                               border_width=1, corner_radius=6,
                               placeholder_text="Ingrese el nombre",
                               height=35)
    nombre_entry.insert(0, usuario_data.get('nombre', ''))
    nombre_entry.pack(pady=(0, 12), fill="x")
    campos['nombre'] = nombre_entry
    
    # Apellido - compacto
    ctk.CTkLabel(content_frame, text="Apellido:", text_color="#1E3D8F",
                 font=ctk.CTkFont(size=12, weight="bold")).pack(pady=(3, 5), anchor="w")
    apellido_entry = ctk.CTkEntry(content_frame,
                                 fg_color="white", border_color="#CBD5E1",
                                 text_color="#1E293B", font=ctk.CTkFont(size=12),
                                 border_width=1, corner_radius=6,
                                 placeholder_text="Ingrese el apellido",
                                 height=35)
    apellido_entry.insert(0, usuario_data.get('apellido', ''))
    apellido_entry.pack(pady=(0, 12), fill="x")
    campos['apellido'] = apellido_entry
    
    # Departamento - compacto
    ctk.CTkLabel(content_frame, text="Departamento:", text_color="#1E3D8F",
                 font=ctk.CTkFont(size=12, weight="bold")).pack(pady=(3, 5), anchor="w")
    departamentos_map = obtener_departamentos()
    departamento_names = list(departamentos_map.keys())
    
    depto_combo = ctk.CTkComboBox(content_frame, values=departamento_names, 
                                 dropdown_font=ctk.CTkFont(size=11),
                                 dropdown_fg_color="white",
                                 dropdown_text_color="black",
                                 dropdown_hover_color="#F1F5F9",
                                 border_color="#CBD5E1",
                                 button_color="#0C4A6E",
                                 button_hover_color="#1E3D8F",
                                 fg_color="white",
                                 text_color="#1E293B",
                                 border_width=1,
                                 corner_radius=6,
                                 height=35)
    
    if departamento_names:
        depto_actual = usuario_data.get('departamento', 'Sin departamento')
        if depto_actual in departamento_names:
            depto_combo.set(depto_actual)
        else:
            depto_combo.set(departamento_names[0])
    depto_combo.pack(pady=(0, 12), fill="x")
    campos['departamento'] = depto_combo
    
    # Rol - compacto
    ctk.CTkLabel(content_frame, text="Rol:", text_color="#1E3D8F",
                 font=ctk.CTkFont(size=12, weight="bold")).pack(pady=(3, 5), anchor="w")
    roles_map = obtener_roles()
    rol_names = list(roles_map.keys())
    
    rol_combo = ctk.CTkComboBox(content_frame, values=rol_names, 
                               dropdown_font=ctk.CTkFont(size=11),
                               dropdown_fg_color="white",
                               dropdown_text_color="black",
                               dropdown_hover_color="#F1F5F9",
                               border_color="#CBD5E1",
                               button_color="#0C4A6E",
                               button_hover_color="#1E3D8F",
                               fg_color="white",
                               text_color="#1E293B",
                               border_width=1,
                                 corner_radius=6,
                                 height=35)
    
    if rol_names:
        rol_actual = usuario_data.get('rol', 'Sin rol')
        if rol_actual in rol_names:
            rol_combo.set(rol_actual)
        else:
            rol_combo.set(rol_names[0])
    rol_combo.pack(pady=(0, 15), fill="x")
    campos['rol'] = rol_combo
    
    # Notificación compacta
    notificacion = ctk.CTkLabel(content_frame, text="", 
                               font=ctk.CTkFont(size=11, weight="bold"))
    notificacion.pack(pady=(8, 10))
    
    def _actualizar_seguro(datos_actualizados, cedula_int):
        """Función segura para actualizar en hilo separado"""
        try:
            response = supabase.table("Usuario").update(datos_actualizados).eq("cedula", cedula_int).execute()
            
            def actualizar_ui():
                if not ventana_abierta:
                    return
                    
                if response.data:
                    notificacion.configure(text="✓ Cambios guardados", text_color="#16A34A")
                    ventana_edicion.after(1500, cerrar_ventana)
                    # Recargar la pantalla de registro
                    if app_root and app_root.winfo_exists():
                        app_root.after(1600, lambda: mostrar_pantalla_registro(app_root))
                else:
                    notificacion.configure(text="✗ Error al guardar", text_color="#DC2626")
            
            if ventana_abierta:
                ventana_edicion.after(0, actualizar_ui)
                
        except Exception as e:
            def mostrar_error():
                if ventana_abierta:
                    notificacion.configure(text=f"✗ Error: {str(e)}", text_color="#DC2626")
            
            if ventana_abierta:
                ventana_edicion.after(0, mostrar_error)
    
    def guardar_cambios():
        # Validar campos
        nombre_val = campos['nombre'].get().strip()
        apellido_val = campos['apellido'].get().strip()
        depto_nombre = campos['departamento'].get().strip()
        rol_nombre = campos['rol'].get().strip()
        
        if not nombre_val or not apellido_val:
            notificacion.configure(text="⚠️ Campos obligatorios", text_color="#D97706")
            return
        
        if depto_nombre not in departamentos_map or rol_nombre not in roles_map:
            notificacion.configure(text="⚠️ Departamento o rol no válido", text_color="#D97706")
            return
        
        # Preparar datos para actualizar
        datos_actualizados = {
            'nombre': nombre_val,
            'apellido': apellido_val,
            'departamento': departamentos_map[depto_nombre],
            'rol': roles_map[rol_nombre]
        }
        
        notificacion.configure(text="⏳ Guardando...", text_color="#1E3D8F")
        
        try:
            cedula_int = int(cedula)
            # Ejecutar en hilo separado pero con manejo seguro
            threading.Thread(target=_actualizar_seguro, 
                           args=(datos_actualizados, cedula_int), 
                           daemon=True).start()
        except ValueError:
            notificacion.configure(text="⚠️ Cédula debe ser numérica", text_color="#DC2626")
    
    # BOTONES COMPACTOS
    botones_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
    botones_frame.pack(fill="x", pady=(5, 0))
    
    # Configurar columnas para los botones
    botones_frame.grid_columnconfigure(0, weight=1)
    botones_frame.grid_columnconfigure(1, weight=1)
    
    # Botones compactos
    btn_guardar = ctk.CTkButton(botones_frame, text="GUARDAR", 
                  fg_color="#16A34A", hover_color="#15803D", 
                  font=ctk.CTkFont(size=12, weight="bold"),
                  height=36,
                  corner_radius=6,
                  command=guardar_cambios)
    btn_guardar.grid(row=0, column=0, padx=(0, 8), sticky="ew")
    
    btn_cancelar = ctk.CTkButton(botones_frame, text="CANCELAR", 
                  fg_color="#6B7280", hover_color="#4B5563", 
                  font=ctk.CTkFont(size=12, weight="bold"),
                  height=36,
                  corner_radius=6,
                  command=cerrar_ventana)
    btn_cancelar.grid(row=0, column=1, padx=(8, 0), sticky="ew")
    
    # Centrar la ventana en la pantalla
    ventana_edicion.update_idletasks()
    x = (ventana_edicion.winfo_screenwidth() // 2) - (ventana_edicion.winfo_width() // 2)
    y = (ventana_edicion.winfo_screenheight() // 2) - (ventana_edicion.winfo_height() // 2)
    ventana_edicion.geometry(f"+{x}+{y}")

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









# --- INICIO: FUNCIÓN MOVIDA FUERA DE mostrar_pantalla_registro ---
# NUEVA FUNCIÓN AUXILIAR (MOVIDA FUERA DE mostrar_pantalla_registro)
def abrir_ventana_seleccion_depto(root, display_entry, nombre_var):
    """Abre una ventana emergente para seleccionar un departamento con búsqueda."""
    
    # Aseguramos el acceso a la función obtener_departamentos
    deptos_map = obtener_departamentos()
    all_deptos = sorted(list(deptos_map.keys())) # Lista de nombres de deptos

    ventana = ctk.CTkToplevel(root)
    ventana.title("Seleccionar Departamento")
    ventana.configure(fg_color="#F7F9FB")
    ventana.grab_set()
    ventana.focus_force()
    ventana.geometry("500x500") # Tamaño fijo para la búsqueda
    
    contenido = ctk.CTkFrame(ventana, fg_color="#FFFFFF")
    # EXPANDIR: Quitamos el padding vertical para que el contenido se ajuste al borde.
    contenido.pack(padx=20, pady=20, fill="both", expand=True) 
    contenido.grid_columnconfigure(0, weight=1)

    ctk.CTkLabel(contenido, text="Buscar Departamento", font=ctk.CTkFont(size=18, weight="bold"), text_color="#0C4A6E").grid(row=0, column=0, pady=(10, 15), sticky="w")
    
    search_entry = ctk.CTkEntry(contenido, placeholder_text="Escriba para buscar...", width=450, height=35)
    search_entry.grid(row=1, column=0, pady=(0, 10), sticky="ew")
    
    # --- MODIFICACIÓN CLAVE: SCROLLABLE FRAME EXPANDIDO ---
    scroll_frame = ctk.CTkScrollableFrame(contenido, fg_color="#F9FAFB", label_text_color="black")
    # Usamos sticky="nsew" y pady=(0, 0) para que ocupe el espacio restante.
    scroll_frame.grid(row=2, column=0, sticky="nsew", pady=(0, 0)) 
    scroll_frame.grid_columnconfigure(0, weight=1)
    
    # Configuramos la columna 0 del contenido principal para que la lista crezca
    contenido.grid_rowconfigure(2, weight=1) # <-- Hace que la fila 2 (scroll_frame) tome todo el espacio.
    # ----------------------------------------------------

    def seleccionar_depto(nombre):
        display_entry.configure(state="normal")
        display_entry.delete(0, 'end')
        display_entry.insert(0, nombre)
        display_entry.configure(state="readonly")
        nombre_var.set(nombre)
        ventana.destroy()
    
    # ... (El resto de las funciones render_list y filtrar_lista permanecen igual)

    def render_list(filtro=""):
        for widget in scroll_frame.winfo_children():
            widget.destroy()
        
        filtro_lower = filtro.lower()
        
        for i, nombre in enumerate(all_deptos):
            if not filtro or filtro_lower in nombre.lower():
                # Usamos un botón para que sea más claro el click
                btn = ctk.CTkButton(
                    scroll_frame, 
                    text=nombre, 
                    fg_color="transparent", 
                    hover_color="#E0F2FE", 
                    text_color="black", 
                    corner_radius=0, 
                    anchor="w",
                    command=lambda n=nombre: seleccionar_depto(n)
                )
                btn.grid(row=i, column=0, sticky="ew", pady=(1, 1))

    def filtrar_lista(e):
        render_list(search_entry.get())
        
    search_entry.bind("<KeyRelease>", filtrar_lista)
    render_list() # Cargar la lista inicial
    
    # *** ELIMINACIÓN DEL BOTÓN CANCELAR ***
    # La línea que definía el botón de Cancelar ha sido eliminada.
    # *** ELIMINACIÓN DEL BOTÓN CANCELAR ***
    

    
    # Botón de Cancelar
    ctk.CTkButton(contenido, text="CANCELAR", fg_color="#6B7280", hover_color="#4B5563", width=150, height=35, command=ventana.destroy).grid(row=3, column=0, pady=(10, 0))
# --- FIN: FUNCIÓN MOVIDA FUERA DE mostrar_pantalla_registro ---



# PANTALLA: AGREGAR NUEVO DEPARTAMENTO
# -------------------------
# PANTALLA: GESTIÓN DE DEPARTAMENTOS (Lista izquierda + Form derecha)
# -------------------------
def mostrar_pantalla_departamentos(root):
    global depto_entry, depto_notificacion

    _clear_widgets(root)
    root.title("Gestión de Departamentos")

    # ============================
    # CONTENEDOR PRINCIPAL
    # ============================
    main = ctk.CTkFrame(root, fg_color="#F2F5F9")
    main.pack(expand=True, fill="both")
    main.grid_rowconfigure(1, weight=1)
    main.grid_columnconfigure(0, weight=1)

    # ============================
    # HEADER (Estilo y posición de botón "VOLVER" corregidos)
    # ============================
    header = ctk.CTkFrame(main, fg_color="#0C4A6E", height=70)
    header.grid(row=0, column=0, sticky="ew")
    header.grid_columnconfigure(0, weight=1)  # Título
    header.grid_columnconfigure(1, weight=0)  # Botón

    # TÍTULO
    ctk.CTkLabel(
        header,
        text="Gestión de Departamentos",
        text_color="white",
        font=ctk.CTkFont(size=20, weight="bold")
    ).grid(row=0, column=0, padx=20, pady=18, sticky="w")

    # BOTÓN VOLVER
    volver_btn = ctk.CTkButton(
        header,
        text="VOLVER", 
        width=90,
        height=36,
        fg_color="#3D89D1", 
        hover_color="#1E3D8F",  
        text_color="white",
        command=lambda: mostrar_pantalla_principal(root)
    )
    volver_btn.grid(row=0, column=1, padx=20, pady=17, sticky="e")

    # ============================
    # CONTENIDO PRINCIPAL
    # ============================
    content = ctk.CTkFrame(main, fg_color="transparent")
    content.grid(row=1, column=0, sticky="nsew", padx=12, pady=12)

    content.grid_columnconfigure(0, weight=3)
    content.grid_columnconfigure(1, weight=2)
    content.grid_rowconfigure(0, weight=1)

    # ================================================================
    # PANEL IZQUIERDO
    # ================================================================
    left = ctk.CTkFrame(content, fg_color="#FFFFFF", corner_radius=10)
    left.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
    left.grid_rowconfigure(1, weight=1)
    left.grid_columnconfigure(0, weight=1)

    # Acciones
    actions = ctk.CTkFrame(left, fg_color="transparent")
    actions.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 0))
    actions.grid_columnconfigure(1, weight=1)

    eliminar_btn = ctk.CTkButton(
        actions,
        text="🗑️ ELIMINAR",
        fg_color="#DC2626",
        hover_color="#B91C1C",
        width=110,
        height=34,
        command=lambda: on_eliminar()
    )
    eliminar_btn.grid(row=0, column=0)

    selection_label = ctk.CTkLabel(
        actions, text="Ningún departamento seleccionado",
        text_color="#6B7280"
    )
    selection_label.grid(row=0, column=1, sticky="e")

    # LISTA SCROLLABLE
    rows = ctk.CTkScrollableFrame(left, fg_color="transparent")
    rows.grid(row=1, column=0, sticky="nsew", padx=12, pady=12)
    rows.grid_columnconfigure(0, weight=1)

    selected = {"id": None, "nombre": None}

    # ================================================================
    # PANEL DERECHO (FORM)
    # ================================================================
    right = ctk.CTkFrame(content, fg_color="#FFFFFF", corner_radius=10)
    right.grid(row=0, column=1, sticky="nsew")
    right.grid_columnconfigure(0, weight=1)

    ctk.CTkLabel(
        right,
        text="Agregar / Editar Departamento",
        font=ctk.CTkFont(size=16, weight="bold"),
        text_color="#1E3D8F"
    ).grid(row=0, column=0, pady=(20, 5), padx=20)

    depto_entry = ctk.CTkEntry(right, placeholder_text="Nombre del departamento", width=320)
    depto_entry.grid(row=1, column=0, pady=(5, 5), padx=20)

    depto_notificacion = ctk.CTkLabel(right, text="", text_color="#16A34A")
    depto_notificacion.grid(row=2, column=0, pady=(0, 10))

    # --------------------------
    # GUARDAR (Lógica de inserción integrada para depuración)
    # --------------------------
    def on_guardar():
        nombre = depto_entry.get().strip()
        if not nombre:
            depto_notificacion.configure(text="Ingrese un nombre válido.", text_color="orange")
            return

        if selected["id"]:
            # Es una edición
            actualizar_departamento(selected["id"], nombre)
            cargar_departamentos()
            limpiar_seleccion()
        else:
            # Es un nuevo registro: LÓGICA DE INSERCIÓN INTEGRADA AQUÍ
            try:
                # Utilizamos la variable 'supabase' que debe estar definida globalmente
                supabase.table("Departamento") \
                    .insert({"nombre_departamento": nombre}) \
                    .execute()
                
                # Éxito:
                depto_notificacion.configure(text="Departamento agregado con éxito.", text_color="#16A34A")
                cargar_departamentos()
                limpiar_seleccion()
                
            except Exception as e:
                # Error:
                print(f"ERROR DE SUPABASE AL INSERTAR: {e}")
                depto_notificacion.configure(
                    text=f"Error al guardar: {str(e)}", 
                    text_color="red"
                )

    guardar_btn = ctk.CTkButton(
        right,
        text="GUARDAR",
        fg_color="#16A34A",
        hover_color="#15803D",
        width=320,
        height=42,
        command=on_guardar
    )
    guardar_btn.grid(row=3, column=0, pady=(10, 5), padx=20)

    cancelar_btn = ctk.CTkButton(
        right,
        text="CANCELAR",
        fg_color="#6B7280",
        hover_color="#4B5563",
        width=320,
        height=36,
        command=lambda: limpiar_seleccion()
    )
    cancelar_btn.grid(row=4, column=0, pady=(0, 20))

    # ============================
    # SELECT / LIMPIAR
    # ============================
    def limpiar_seleccion():
        selected["id"] = None
        selected["nombre"] = None
        depto_entry.delete(0, "end")
        selection_label.configure(text="Ningún departamento seleccionado")
        guardar_btn.configure(text="GUARDAR")
        # Limpiar el mensaje de notificación al cancelar
        depto_notificacion.configure(text="", text_color="#16A34A")

    def seleccionar(id_dep, nombre, frame):
        for r in rows.winfo_children():
            r.configure(fg_color="transparent")

        frame.configure(fg_color="#E0F2FE")

        selected["id"] = id_dep
        selected["nombre"] = nombre

        selection_label.configure(text=f"Seleccionado: {nombre}")

        depto_entry.delete(0, "end")
        depto_entry.insert(0, nombre)
        guardar_btn.configure(text="GUARDAR CAMBIOS")
        # Borrar notificación al seleccionar un elemento
        depto_notificacion.configure(text="", text_color="#16A34A") 

    # ============================
    # CRUD
    # ============================
    def actualizar_departamento(id_dep, nombre):
        try:
            supabase.table("Departamento") \
                .update({"nombre_departamento": nombre}) \
                .eq("id_departamento", id_dep) \
                .execute()
            depto_notificacion.configure(text="Departamento actualizado.", text_color="#16A34A")
        except Exception as e:
            depto_notificacion.configure(text=f"Error: {e}", text_color="red")

    def on_eliminar():
        if not selected["id"]:
            tk.messagebox.showwarning("Advertencia", "Seleccione un departamento.")
            return

        if not tk.messagebox.askyesno("Confirmar", f"¿Eliminar {selected['nombre']}?"):
            return

        try:
            supabase.table("Departamento") \
                .delete() \
                .eq("id_departamento", selected["id"]) \
                .execute()
            depto_notificacion.configure(text="Departamento eliminado.", text_color="#16A34A")
        except Exception as e:
            depto_notificacion.configure(text=f"Error: {e}", text_color="red")

        cargar_departamentos()
        limpiar_seleccion()

    # ============================
    # CARGAR LISTA
    # ============================
    def cargar_departamentos():
        for w in rows.winfo_children():
            w.destroy()

        try:
            data = supabase.table("Departamento") \
                .select("id_departamento, nombre_departamento") \
                .order("nombre_departamento") \
                .execute().data or []
        except:
            data = []

        # ----------------------------
        # Renderizar departamentos
        # ----------------------------
        for d in data:
            f = ctk.CTkFrame(
                rows,
                fg_color="transparent",
                height=42,
                corner_radius=0
            )
            f.pack(fill="x", pady=3)

            f.grid_columnconfigure(0, weight=1, uniform="deptos")
            f.configure(width=rows.winfo_width())

            lbl = ctk.CTkLabel(
                f,
                text=d["nombre_departamento"],
                font=ctk.CTkFont(size=14),
                anchor="w"
            )
            lbl.grid(row=0, column=0, sticky="w", padx=10)

            def on_select(e=None, i=d["id_departamento"], n=d["nombre_departamento"], fr=f):
                for r in rows.winfo_children():
                    r.configure(fg_color="transparent")

                fr.configure(fg_color="#E0F2FE")
                seleccionar(i, n, fr)

            f.bind("<Button-1>", on_select)
            lbl.bind("<Button-1>", on_select)

    cargar_departamentos()








# REGISTRO DE USUARIO
def registrar_usuario(root, roles_map, departamentos_map):
  
    global registro_entries

    cedula_val = (registro_entries.get('cedula').get() or "").strip()
    nombre_val = (registro_entries.get('nombre').get() or "").strip()
    apellido_val = (registro_entries.get('apellido').get() or "").strip()
    rol_nombre = (registro_entries.get('rol').get() or "").strip()
    
    # --- CAMBIO AQUÍ: OBTENER EL VALOR DE LA VARIABLE StringVar ---
    depto_var = registro_entries.get('departamento')
    depto_nombre = (depto_var.get() or "").strip() # Usamos .get() en la variable tk.StringVar
    # -----------------------------------------------------------

    if not cedula_val or not nombre_val or not apellido_val:
    # ... (el resto de la función se mantiene igual)
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

    global registro_entries, registro_notificacion, app_root, usuario_seleccionado
    app_root = root
    usuario_seleccionado = None  # Reiniciar selección
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

    ctk.CTkLabel(header_frame, text="REGISTRO DE NUEVO USUARIO",
                 font=ctk.CTkFont(size=22, weight="bold"),
                 text_color="white").grid(row=0, column=1, padx=(30, 20), pady=15, sticky="w")

    # --- INICIO: CARGAR ICONO DE RECARGAR ---
    try:
        reload_icon = ctk.CTkImage(PILImage.open("imagen/recargar.png"), size=(25, 25))
    except Exception:
        reload_icon = None
    # --- FIN: CARGAR ICONO DE RECARGAR ---

    # Botón VOLVER
    ctk.CTkButton(header_frame, text="VOLVER", fg_color="#3D89D1",
                  hover_color="#1E3D8F",
                  font=ctk.CTkFont(size=13, weight="bold"),
                  corner_radius=8, width=120, height=40,
                  command=lambda: mostrar_pantalla_principal(root)).grid(row=0, column=2, padx=(10, 20), pady=12, sticky="e")

    # --- INICIO: BOTÓN RECARGAR EN EL HEADER ---
    # Función para recargar la pantalla de registro
    def recargar_registro():
        mostrar_pantalla_registro(root)
    
    # Botón de Recargar en el header (al lado del botón VOLVER)
    if reload_icon:
        ctk.CTkButton(
            header_frame, 
            text="", 
            image=reload_icon, 
            width=40, 
            height=40,
            fg_color="#E5E7EB", 
            hover_color="#CBD5E1", 
            corner_radius=8,
            command=recargar_registro
        ).grid(row=0, column=3, padx=(0, 10), pady=12, sticky="e")
    else:
        ctk.CTkButton(
            header_frame, 
            text="⟳", 
            width=40, 
            height=40,
            fg_color="#E5E7EB", 
            hover_color="#CBD5E1", 
            corner_radius=8,
            font=ctk.CTkFont(size=16, weight="bold"),
            command=recargar_registro
        ).grid(row=0, column=3, padx=(0, 10), pady=12, sticky="e")
    # --- FIN: BOTÓN RECARGAR EN EL HEADER ---

    # Ajustar el layout del content_frame
    content_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
    content_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
    content_frame.grid_rowconfigure(0, weight=1)
    content_frame.grid_columnconfigure(0, weight=3)  # Más peso para la tabla
    content_frame.grid_columnconfigure(1, weight=1) # Menos peso para el formulario
    
    # Columna 0 (Izquierda): Contenedor para la lista de usuarios.
    col_vacia_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
    col_vacia_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
    
    # --- BLOQUE DE CÓDIGO MEJORADO: LISTA DE USUARIOS COMO EN LA IMAGEN ---
    try:
        # Ejecutar la función para obtener el DataFrame con departamentos y roles
        df_usuarios = obtener_usuarios_completos() 
        
        # Título de la sección
        ctk.CTkLabel(col_vacia_frame, text="Usuarios Registrados", 
                     text_color="#0C4A6E", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=(15, 10))

        # Botones de acción en la parte superior
        botones_superior_frame = ctk.CTkFrame(col_vacia_frame, fg_color="transparent")
        botones_superior_frame.pack(fill="x", padx=20, pady=(0, 10))
        
        # Botón Editar
        btn_editar_superior = ctk.CTkButton(botones_superior_frame, text="✏️ EDITAR USUARIO", 
                                           fg_color="#3D89D1", hover_color="#1E3D8F",
                                           font=ctk.CTkFont(size=13, weight="bold"),
                                           width=150, height=35,
                                           command=lambda: _editar_usuario_seleccionado())
        btn_editar_superior.pack(side="left", padx=(0, 10))
        
        # Botón Eliminar
        btn_eliminar_superior = ctk.CTkButton(botones_superior_frame, text="🗑️ ELIMINAR USUARIO", 
                                             fg_color="#DC2626", hover_color="#B91C1C",
                                             font=ctk.CTkFont(size=13, weight="bold"),
                                             width=150, height=35,
                                             command=lambda: _eliminar_usuario_seleccionado())
        btn_eliminar_superior.pack(side="left")
        
        # Etiqueta para mostrar usuario seleccionado
        seleccion_label = ctk.CTkLabel(botones_superior_frame, text="Ningún usuario seleccionado", 
                                      text_color="#6B7280", font=ctk.CTkFont(size=12))
        seleccion_label.pack(side="right", padx=10)

        if df_usuarios.empty:
            ctk.CTkLabel(col_vacia_frame, text="No se encontraron usuarios en la base de datos.", 
                         text_color="#1E3D8F", font=ctk.CTkFont(size=14)).pack(pady=10)
        else:
            # Contenedor para la 'tabla' con bordes
            table_container = ctk.CTkFrame(col_vacia_frame, fg_color="#FFFFFF", corner_radius=10, 
                                           border_width=1, border_color="#E6E6E6")
            table_container.pack(fill="both", expand=True, padx=20, pady=10)
            
            # Marco para el encabezado (Header Fijo)
            header_frame = ctk.CTkFrame(table_container, fg_color="#F3F4F6", corner_radius=0)
            header_frame.pack(fill="x")
            
            # CONFIGURACIÓN DE COLUMNAS CORREGIDA - TODAS CON weight=0 EXCEPTO DEPARTAMENTO
            header_frame.grid_columnconfigure(0, weight=0, minsize=120)  # Nombre
            header_frame.grid_columnconfigure(1, weight=0, minsize=120)  # Apellido
            header_frame.grid_columnconfigure(2, weight=0, minsize=100)  # Cédula
            header_frame.grid_columnconfigure(3, weight=1, minsize=350)  # Departamento (única que se expande)
            header_frame.grid_columnconfigure(4, weight=0, minsize=120)  # Rol - CORREGIDO: weight=0 y minsize aumentado
            
            # Encabezados de la tabla ALINEADOS A LA IZQUIERDA como en la imagen
            ctk.CTkLabel(header_frame, text="NOMBRE", font=ctk.CTkFont(size=13, weight="bold"), 
                         text_color="#374151", anchor="w").grid(row=0, column=0, padx=8, pady=10, sticky="w")
            ctk.CTkLabel(header_frame, text="APELLIDO", font=ctk.CTkFont(size=13, weight="bold"), 
                         text_color="#374151", anchor="w").grid(row=0, column=1, padx=8, pady=10, sticky="w")
            ctk.CTkLabel(header_frame, text="CÉDULA", font=ctk.CTkFont(size=13, weight="bold"), 
                         text_color="#374151", anchor="w").grid(row=0, column=2, padx=8, pady=10, sticky="w")
            ctk.CTkLabel(header_frame, text="DEPARTAMENTO", font=ctk.CTkFont(size=13, weight="bold"), 
                         text_color="#374151", anchor="w").grid(row=0, column=3, padx=8, pady=10, sticky="w")
            ctk.CTkLabel(header_frame, text="ROL", font=ctk.CTkFont(size=13, weight="bold"), 
                         text_color="#374151", anchor="w").grid(row=0, column=4, padx=8, pady=10, sticky="w")

            # Creamos un marco desplazable para los datos (Scrollable body)
            scroll_frame = ctk.CTkScrollableFrame(table_container, fg_color="#FFFFFF", corner_radius=0)
            scroll_frame.pack(fill="both", expand=True)

            # CONFIGURACIÓN DE COLUMNAS DEL CUERPO CORREGIDA - MISMOS VALORES QUE EL HEADER
            scroll_frame.grid_columnconfigure(0, weight=0, minsize=120)  # Nombre
            scroll_frame.grid_columnconfigure(1, weight=0, minsize=120)  # Apellido
            scroll_frame.grid_columnconfigure(2, weight=0, minsize=100)  # Cédula
            scroll_frame.grid_columnconfigure(3, weight=1, minsize=350)  # Departamento (única que se expande)
            scroll_frame.grid_columnconfigure(4, weight=0, minsize=120)  # Rol - CORREGIDO: weight=0 y minsize aumentado
            
            # Función para manejar la selección de usuario
            def seleccionar_usuario(cedula, nombre_completo, row_frame):
                global usuario_seleccionado
                # Resetear color de todas las filas
                for widget in scroll_frame.winfo_children():
                    if isinstance(widget, ctk.CTkFrame):
                        # Restaurar colores alternos
                        index = scroll_frame.winfo_children().index(widget)
                        bg_color = "#FFFFFF" if index % 2 == 0 else "#F9FAFB"
                        widget.configure(fg_color=bg_color)
                
                # Resaltar fila seleccionada
                row_frame.configure(fg_color="#E0F2FE")
                usuario_seleccionado = {
                    'cedula': cedula,
                    'nombre_completo': nombre_completo,
                    'row_frame': row_frame  # Guardar referencia al frame
                }
                seleccion_label.configure(text=f"Seleccionado: {nombre_completo}", text_color="#0C4A6E")
            
            # Iteramos sobre el DataFrame y creamos etiquetas para cada fila (con rayas)
            for i, row in df_usuarios.iterrows():
                # Color de fondo alternante para 'rayas' (striping)
                bg_color = "#FFFFFF" if i % 2 == 0 else "#F9FAFB" 
                text_color = "#374151"
                
                # Marco de la Fila (contenedor para el striping)
                row_frame = ctk.CTkFrame(scroll_frame, fg_color=bg_color, corner_radius=0, height=35)
                row_frame.pack(fill="x")
                
                # CONFIGURACIÓN DE COLUMNAS DE LA FILA CORREGIDA - MISMOS VALORES
                row_frame.grid_columnconfigure(0, weight=0, minsize=120)  # Nombre
                row_frame.grid_columnconfigure(1, weight=0, minsize=120)  # Apellido
                row_frame.grid_columnconfigure(2, weight=0, minsize=100)  # Cédula
                row_frame.grid_columnconfigure(3, weight=1, minsize=350)  # Departamento (única que se expande)
                row_frame.grid_columnconfigure(4, weight=0, minsize=120)  # Rol - CORREGIDO: weight=0 y minsize aumentado

                nombre = str(row.get('nombre', '')).strip()
                apellido = str(row.get('apellido', '')).strip()
                cedula = str(row['cedula'])
                departamento = str(row.get('departamento', 'Sin departamento')).strip()
                rol = str(row.get('rol', 'Sin rol')).strip()
                
                # --- CORRECCIÓN: CONVERSIÓN DE ROLES AL FORMATO DE LA IMAGEN 2 ---
                if rol.lower() == 'administrador':
                    rol_mostrar = "administrador"
                elif rol.lower() == 'usuario' or rol.lower() == 'usuario estándar':
                    rol_mostrar = "usuario"
                elif rol.lower() == 'tecnico de soporte':
                    rol_mostrar = "tecnico de soporte"
                else:
                    rol_mostrar = rol.lower()  # Mantener el valor original en minúsculas
                
                nombre_completo = f"{nombre} {apellido}".strip()
                
                # Hacer que toda la fila sea clickeable
                row_frame.bind("<Button-1>", lambda e, c=cedula, n=nombre_completo, rf=row_frame: seleccionar_usuario(c, n, rf))
                
                # Etiquetas ALINEADAS A LA IZQUIERDA como en la imagen
                lbl_nombre = ctk.CTkLabel(row_frame, text=nombre, font=ctk.CTkFont(size=13), 
                                         text_color=text_color, anchor="w")
                lbl_nombre.grid(row=0, column=0, padx=8, pady=8, sticky="w")
                lbl_nombre.bind("<Button-1>", lambda e, c=cedula, n=nombre_completo, rf=row_frame: seleccionar_usuario(c, n, rf))
                
                lbl_apellido = ctk.CTkLabel(row_frame, text=apellido, font=ctk.CTkFont(size=13), 
                                           text_color=text_color, anchor="w")
                lbl_apellido.grid(row=0, column=1, padx=8, pady=8, sticky="w")
                lbl_apellido.bind("<Button-1>", lambda e, c=cedula, n=nombre_completo, rf=row_frame: seleccionar_usuario(c, n, rf))

                lbl_cedula = ctk.CTkLabel(row_frame, text=cedula, font=ctk.CTkFont(size=13), 
                                         text_color=text_color, anchor="w")
                lbl_cedula.grid(row=0, column=2, padx=8, pady=8, sticky="w")
                lbl_cedula.bind("<Button-1>", lambda e, c=cedula, n=nombre_completo, rf=row_frame: seleccionar_usuario(c, n, rf))

                lbl_depto = ctk.CTkLabel(row_frame, text=departamento, font=ctk.CTkFont(size=13), 
                                        text_color=text_color, anchor="w")
                lbl_depto.grid(row=0, column=3, padx=8, pady=8, sticky="w")
                lbl_depto.bind("<Button-1>", lambda e, c=cedula, n=nombre_completo, rf=row_frame: seleccionar_usuario(c, n, rf))

                # --- ETIQUETA DE ROL CON EL FORMATO CORREGIDO ---
                lbl_rol = ctk.CTkLabel(row_frame, text=rol_mostrar, font=ctk.CTkFont(size=13), 
                                      text_color=text_color, anchor="w")
                lbl_rol.grid(row=0, column=4, padx=8, pady=8, sticky="w")
                lbl_rol.bind("<Button-1>", lambda e, c=cedula, n=nombre_completo, rf=row_frame: seleccionar_usuario(c, n, rf))

        # Funciones para los botones de acción
        def _editar_usuario_seleccionado():
            global usuario_seleccionado
            if not usuario_seleccionado:
                tk.messagebox.showwarning("Advertencia", "Por favor seleccione un usuario primero.")
                return
            
            # Obtener datos completos del usuario seleccionado
            try:
                response = supabase.table("Usuario").select("*").eq("cedula", usuario_seleccionado['cedula']).execute()
                if response.data:
                    usuario_data = response.data[0]
                    # Obtener nombres de departamento y rol
                    deptos = obtener_departamentos()
                    roles = obtener_roles()
                    
                    # Buscar nombres correspondientes a los IDs
                    depto_nombre = next((k for k, v in deptos.items() if v == usuario_data.get('departamento')), 'Sin departamento')
                    rol_nombre = next((k for k, v in roles.items() if v == usuario_data.get('rol')), 'Sin rol')
                    
                    datos_completos = {
                        'nombre': usuario_data.get('nombre', ''),
                        'apellido': usuario_data.get('apellido', ''),
                        'departamento': depto_nombre,
                        'rol': rol_nombre
                    }
                    
                    editar_usuario(usuario_seleccionado['cedula'], datos_completos)
                else:
                    tk.messagebox.showerror("Error", "No se pudieron obtener los datos del usuario.")
            except Exception as e:
                tk.messagebox.showerror("Error", f"Error al obtener datos del usuario: {e}")

        def _eliminar_usuario_seleccionado():
            global usuario_seleccionado
            if not usuario_seleccionado:
                tk.messagebox.showwarning("Advertencia", "Por favor seleccione un usuario primero.")
                return
            
            # Buscar el frame de la fila seleccionada
            row_frame_seleccionado = None
            for widget in scroll_frame.winfo_children():
                if isinstance(widget, ctk.CTkFrame) and widget.cget("fg_color") == "#E0F2FE":
                    row_frame_seleccionado = widget
                    break
            
            eliminar_usuario(usuario_seleccionado['cedula'], usuario_seleccionado['nombre_completo'], row_frame_seleccionado)

    except NameError:
        ctk.CTkLabel(col_vacia_frame, text="Error: La función no se pudo ejecutar (posiblemente falta la importación de 'pandas').",
                     text_color="red", font=ctk.CTkFont(size=14)).pack(pady=20, padx=20)
    except Exception as e:
         ctk.CTkLabel(col_vacia_frame, text=f"Error al ejecutar la función: {e}",
                     text_color="red", font=ctk.CTkFont(size=14)).pack(pady=20, padx=20)
    # --- FIN DEL BLOQUE DE CÓDIGO MEJORADO ---

    # Resto del código del formulario permanece igual...
    # Columna 1 (Derecha): Contiene el formulario
    content_frame.grid_columnconfigure(1, weight=0) 

    # Formulario central
    form_frame = ctk.CTkFrame(content_frame, fg_color="#FFFFFF", corner_radius=10)
    form_frame.grid(row=0, column=1, pady=20, padx=20, ipadx=20, ipady=20, sticky="n")

    ctk.CTkLabel(form_frame, text="Complete los campos", font=ctk.CTkFont(size=16, weight="bold"), text_color="#1E3D8F").pack(pady=10)

    # Entradas de datos (Cédula, Nombre, Apellido)
    registro_entries = {}
    cedula_ent = ctk.CTkEntry(form_frame, placeholder_text="Cédula de Identidad", width=320, height=38, corner_radius=10, border_width=1, fg_color="white", border_color="#A1A1A1", text_color="black", font=ctk.CTkFont(size=14))
    cedula_ent.pack(pady=(10, 8))
    registro_entries['cedula'] = cedula_ent

    nombre_ent = ctk.CTkEntry(form_frame, placeholder_text="Nombre", width=320, height=38, corner_radius=10, border_width=1, fg_color="white", border_color="#A1A1A1", text_color="black", font=ctk.CTkFont(size=14))
    nombre_ent.pack(pady=8)
    registro_entries['nombre'] = nombre_ent

    apellido_ent = ctk.CTkEntry(form_frame, placeholder_text="Apellido", width=320, height=38, corner_radius=10, border_width=1, fg_color="white", border_color="#A1A1A1", text_color="black", font=ctk.CTkFont(size=14))
    apellido_ent.pack(pady=8)
    registro_entries['apellido'] = apellido_ent    
    
    # SELECTOR DE ROL CON BARRA DE DESPLAZAMIENTO MEJORADO (EL ROL NO TIENE MUCHOS ITEMS, SE MANTIENE EL COMBOBOX)
    # ... (Código anterior de Cédula, Nombre, Apellido)

# ----------------------------------------------------
# --- INICIO: SELECTOR DE ROL (MOVIDO ARRIBA) ---
# ----------------------------------------------------
    # SELECTOR DE ROL CON BARRA DE DESPLAZAMIENTO MEJORADO (EL ROL NO TIENE MUCHOS ITEMS, SE MANTIENE EL COMBOBOX)
    ctk.CTkLabel(form_frame, text="Rol:", text_color="#1E1E1E").pack(pady=(10, 0))
    
    rol_vals = rol_names if rol_names else ["-- Sin roles --"]

    # Crear el ComboBox para roles
    rol_combo = ctk.CTkComboBox(
        form_frame, 
        values=rol_vals, 
        width=320,
        height=38,
        dropdown_font=ctk.CTkFont(size=12),  # Tamaño más pequeño para más elementos
        dropdown_fg_color="white",
        dropdown_text_color="black",
        dropdown_hover_color="#E5E7EB",
        state="readonly"
    )

    if rol_names:
        default_rol = "usuario" if "usuario" in rol_names else rol_names[0]
        rol_combo.set(default_rol)
    else:
        rol_combo.set("-- Sin roles --")
    rol_combo.pack(pady=(4, 15)) # Aumento el margen inferior a 15 para separarlo de Departamento
    registro_entries['rol'] = rol_combo
# ----------------------------------------------------
# --- FIN: SELECTOR DE ROL ---
# ----------------------------------------------------


# ----------------------------------------------------
# --- INICIO: REEMPLAZO DEL COMBOBOX DE DEPARTAMENTO (MOVIDO ABAJO) ---
# ----------------------------------------------------
    ctk.CTkLabel(form_frame, text="Departamento:", text_color="#1E1E1E").pack(pady=(10, 0))

    # 1. Entrada de texto para mostrar el valor (deshabilitada)
    depto_display = ctk.CTkEntry(form_frame, 
                                 placeholder_text="Seleccione un Departamento...", 
                                 width=320, 
                                 height=38, 
                                 corner_radius=10, 
                                 border_width=1, 
                                 fg_color="white", 
                                 border_color="#A1A1A1", 
                                 text_color="black", 
                                 font=ctk.CTkFont(size=14))
    depto_display.pack(pady=(4, 0))
    depto_display.insert(0, departamento_names[0] if departamento_names else "-- Sin departamentos --")
    depto_display.configure(state="readonly")
    
    # 2. Variable oculta para almacenar el nombre real (para el registro)
    depto_nombre_var = tk.StringVar(value=departamento_names[0] if departamento_names else "")
    registro_entries['departamento'] = depto_nombre_var 

    # 3. Botón para abrir la ventana de búsqueda
    ctk.CTkButton(form_frame, text="Buscar/Seleccionar", 
                  width=320, height=30, 
                  fg_color="#3D89D1", hover_color="#1E3D8F",
                  font=ctk.CTkFont(size=12, weight="bold"),
                  command=lambda: abrir_ventana_seleccion_depto(root, depto_display, depto_nombre_var)).pack(pady=(10, 19)) # Ajustado el pady superior a 4 para separar
# ----------------------------------------------------
# --- FIN: REEMPLAZO DEL COMBOBOX DE DEPARTAMENTO ---
# ----------------------------------------------------


# ----------------------------------------------------
# --- INICIO: BOTÓN REGISTRAR ---
# ----------------------------------------------------
    # Notificación de registro
    global registro_notificacion
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
# ----------------------------------------------------
# --- FIN: BOTÓN REGISTRAR ---
# ----------------------------------------------------






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
        logo_img = ctk.CTkImage(PILImage.open("imagen/exportar.png"), size=(200, 60))
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

    # --- (INICIO) NUEVAS IMÁGENES PARA EL HEADER ---
    try:
        icon_depto = ctk.CTkImage(PILImage.open("imagen/departamento.png"), size=(25, 25))
    except Exception as e:
        print(f"Error al cargar imagen/departamento.png: {e}")
        icon_depto = None
    
    try:
        icon_usuario = ctk.CTkImage(PILImage.open("imagen/usuario.png"), size=(25, 25))
    except Exception as e:
        print(f"Error al cargar imagen/usuario.png: {e}")
        icon_usuario = None
        
    try:
        # El usuario pidió 'seccion.png' (para "cerrar sección")
        icon_sesion = ctk.CTkImage(PILImage.open("imagen/seccion.png"), size=(25, 25))
    except Exception as e:
        print(f"Error al cargar imagen/seccion.png: {e}")
        icon_sesion = None
    # --- (FIN) NUEVAS IMÁGENES PARA EL HEADER ---

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

    # --- INICIO: NUEVA IMAGEN PARA BOTÓN GRÁFICOS (ACTUALIZADO) ---
    # AHORA CARGAMOS 'grafica.png' COMO UN ICONO PEQUEÑO
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        # CAMBIO: Usar 'grafica.png' según la solicitud del usuario
        ruta_imagen_graficos_icon = os.path.join(base_dir, "imagen", "grafica.png") 
        
        icon_graficos = ctk.CTkImage(
            PILImage.open(ruta_imagen_graficos_icon), 
            size=(25, 25) # Cargar como un icono
        )
    except FileNotFoundError:
        print(f"ADVERTENCIA: No se encontró 'imagen/grafica.png'. Se usará un botón de texto.")
        icon_graficos = None
    except Exception as e:
        print(f"Error al cargar la imagen del botón de gráficos: {e}. Se usará un botón de texto.")
        icon_graficos = None
    # --- FIN: NUEVA IMAGEN PARA BOTÓN GRÁFICOS ---

    # --- FIN: CARGA DE IMÁGENES ---

    # --- (INICIO) BOTONES DE NAVEGACIÓN CON ÍCONOS Y COLOR DE FONDO ---
    
    # Botón 1: AGREGAR DEPARTAMENTO
    if icon_depto:
        ctk.CTkButton(header_frame, text="", 
                      image=icon_depto,
                      fg_color="#16A34A",       # <-- CAMBIO: Color verde original
                      hover_color="#15803D",    # <-- CAMBIO: Hover verde
                      width=40, height=40,
                      corner_radius=8,       # <-- Añadido: para que se vea bien
                      command=lambda: mostrar_pantalla_departamentos(root)
                      ).grid(row=0, column=1, padx=(10, 5), pady=12, sticky="e")
    else:
        # Fallback a botón de texto si la imagen no carga
        ctk.CTkButton(header_frame, text="AGREGAR DEPARTAMENTO", fg_color="#16A34A",
                      hover_color="#15803D",
                      font=ctk.CTkFont(size=13, weight="bold"),
                      corner_radius=8, width=180, height=40,
                      command=lambda: mostrar_pantalla_departamentos(root)
                      ).grid(row=0, column=1, padx=(10, 5), pady=12, sticky="e")

    # Botón 2: AGREGAR USUARIO
    if icon_usuario:
        ctk.CTkButton(header_frame, text="", 
                      image=icon_usuario,
                      fg_color="#3D89D1",       # <-- CAMBIO: Color azul original
                      hover_color="#1E3D8F",    # <-- CAMBIO: Hover azul
                      width=40, height=40,
                      corner_radius=8,
                      command=lambda: mostrar_pantalla_registro(root)
                      ).grid(row=0, column=2, padx=(10, 5), pady=12, sticky="e")
    else:
         # Fallback a botón de texto si la imagen no carga
        ctk.CTkButton(header_frame, text="AGREGAR USUARIO", fg_color="#3D89D1",
                      hover_color="#1E3D8F",
                      font=ctk.CTkFont(size=13, weight="bold"),
                      corner_radius=8, width=140, height=40,
                      command=lambda: mostrar_pantalla_registro(root)
                      ).grid(row=0, column=2, padx=(10, 5), pady=12, sticky="e")

    # Botón 3: CERRAR SESIÓN
    if icon_sesion:
        ctk.CTkButton(header_frame, text="", 
                      image=icon_sesion,
                      fg_color="#C82333",       # <-- CAMBIO: Color rojo original
                      hover_color="#A31616",    # <-- CAMBIO: Hover rojo
                      width=40, height=40,
                      corner_radius=8,
                      command=lambda: cerrar_sesion(root)
                      ).grid(row=0, column=3, padx=10, pady=12, sticky="e")
    else:
        # Fallback a botón de texto si la imagen no carga
        ctk.CTkButton(header_frame, text="CERRAR SESIÓN", fg_color="#C82333",
                      hover_color="#A31616", command=lambda: cerrar_sesion(root),
                      font=ctk.CTkFont(size=13, weight="bold"),
                      corner_radius=8, width=130, height=40).grid(row=0, column=3, padx=10, pady=12, sticky="e")

    # --- (FIN) BOTONES DE NAVEGACIÓN ---

    scrollable = ctk.CTkScrollableFrame(table_card, corner_radius=10)
    scrollable.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")

    # Funciones de Lógica de la Lista
   
    def obtener_servicios_filtrados():
        query = supabase.table("Servicio").select("*").order("id_servicio", desc=True)
        estado_map = {"Pendiente": 1, "Completado": 2, "Recibido": 3}
        estado_val = filtro_estado.get()
        fecha_val = filtro_fecha.get() # <-- LÍNEA NUEVA: Obtenemos el valor del filtro de fecha
        
        # --- OPTIMIZACIÓN DE CARGA INICIAL ---
        # Si AMBOS filtros están en "Todos", aplicamos el límite de 100
        # para que la carga inicial sea súper rápida.
        if estado_val == "Todos" and fecha_val == "Todos": # <-- LÍNEA NUEVA
            query = query.limit(100) # <-- LÍNEA NUEVA
        # Si se aplica CUALQUIER otro filtro, esta condición no se cumple
        # y la consulta buscará en TODOS los registros (sin límite).

        # Aplicar filtro de estado
        if estado_val in estado_map:
            query = query.eq("estado", estado_map[estado_val])
            
        
        # Aplicar filtro de técnico o departamento
        tecnico_id_val = filtros_especiales.get('tecnico_id')
        depto_id_val = filtros_especiales.get('depto_id')

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
        # (El valor de fecha_val ya lo obtuvimos arriba)
        
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

        elif fecha_val == "Semana anterior":
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
                FONT_DETAIL = ctk.CTkFont(size=15) # Con el tamaño 15 que ajustamos
                FONT_PILL = ctk.CTkFont(size=11, weight="bold")

                colores_estado = {
                    "Completado": ("#D1FAE5", "#047857", "#047857"),
                    "Pendiente":  ("#FEF3C7", "#92400E", "#92400E"),
                    "Recibido":   ("#DBEAFE", "#1E3A8A", "#1E3A8A"),
                    "Desconocido": ("#F3F4F6", "#374151", "#374151")
                }
                # --- FIN: Definiciones de Diseño ---

                # --- INICIO: Bucle de Renderizado con Nuevo Diseño ---
                
                # --- (INICIO) DEFINICIÓN DE ANCHOS ---
                col_min_width = 340 
                wrap_width = col_min_width - 15 
                # --- (FIN) DEFINICIÓN DE ANCHOS ---

                
                for index, s in enumerate(servicios):
                    estado_text = traducir_estado(s.get("estado"))
                    color_bg, color_border, color_text = colores_estado.get(estado_text, colores_estado["Desconocido"])

                    # 1. Contenedor principal
                    card_main = ctk.CTkFrame(
                        scrollable,
                        fg_color=COLOR_BODY_BG, 
                        corner_radius=CARD_CORNER_RADIUS,
                        border_color="#DCDCDC",
                        border_width=1
                    )
                    
                    card_main.grid(row=index, column=0, sticky="ew", padx=15, pady=5)

                    # --- Configuración interna de la tarjeta ---
                    card_main.grid_columnconfigure(0, weight=1) 
                    card_main.grid_rowconfigure(0, weight=0)
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
                    
                    # 3a. Frame de detalles (se coloca en la fila 0)
                    details_frame = ctk.CTkFrame(body_container, fg_color="transparent")
                    details_frame.grid(row=0, column=0, sticky="nsew")

                    # --- Título (CON TEXT-WRAPPING) ---
                    titulo_val = (s.get('descripcion') or "Sin descripción").capitalize()
                        
                    ctk.CTkLabel(
                        details_frame, 
                        text=titulo_val, 
                        font=FONT_TITLE, 
                        text_color=COLOR_TITLE_TEXT, 
                        anchor="w",
                        justify="left", # <-- Arregla la indentación
                        wraplength= (col_min_width * 3) - 50 
                    ).pack(fill="x", pady=(0, 4))

                    # Frame para las 3 columnas de abajo
                    columns_frame = ctk.CTkFrame(details_frame, fg_color="transparent")
                    columns_frame.pack(fill="x")
                    
                    # --- Forzamos un ancho mínimo para cada columna de datos ---
                    columns_frame.grid_columnconfigure(0, weight=1, minsize=col_min_width)
                    columns_frame.grid_columnconfigure(2, weight=1, minsize=col_min_width)
                    columns_frame.grid_columnconfigure(4, weight=1, minsize=col_min_width)
                    
                    columns_frame.grid_columnconfigure((1, 3), weight=0) # Separadores no crecen
                    columns_frame.grid_rowconfigure(0, weight=1) # Fila expandible

                    # --- Columna 1 (CON TEXT-WRAPPING) ---
                    col1_frame = ctk.CTkFrame(columns_frame, fg_color="transparent")
                    # --- CAMBIO IMPORTANTE: "sticky" vuelve a "nsew" ---
                    col1_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
                    
                    usuario_val = usuarios_map.get(str(s.get('usuario')), 'Desconocido')
                    depto_val = s.get('Departamento', 'Desconocido')
                    
                    ctk.CTkLabel(
                        col1_frame, 
                        text=f"Usuario: {usuario_val}", 
                        font=FONT_DETAIL, 
                        text_color=COLOR_DETAIL_TEXT, 
                        anchor="w",
                        justify="left", # <-- Arregla la indentación
                        wraplength=wrap_width 
                    ).pack(fill="x", pady=0, anchor="w") # <-- "anchor" alinea arriba
                    ctk.CTkLabel(
                        col1_frame, 
                        text=f"Departamento: {depto_val}", 
                        font=FONT_DETAIL, 
                        text_color=COLOR_DETAIL_TEXT, 
                        anchor="w",
                        justify="left", # <-- Arregla la indentación
                        wraplength=wrap_width
                    ).pack(fill="x", pady=0, anchor="w") # <-- "anchor" alinea arriba

                    # --- Separador 1 ---
                    ctk.CTkFrame(columns_frame, width=2, fg_color=COLOR_SEPARATOR).grid(row=0, column=1, sticky="ns")

                    # --- Columna 2 (CON TEXT-WRAPPING) ---
                    col2_frame = ctk.CTkFrame(columns_frame, fg_color="transparent")
                    # --- CAMBIO IMPORTANTE: "sticky" vuelve a "nsew" ---
                    col2_frame.grid(row=0, column=2, sticky="nsew", padx=5)
                    
                    tecnico_val = usuarios_map.get(str(s.get('tecnico')), 'Sin asignar')
                        
                    ctk.CTkLabel(
                        col2_frame, 
                        text=f"Técnico: {tecnico_val}", 
                        font=FONT_DETAIL, 
                        text_color=COLOR_DETAIL_TEXT, 
                        anchor="w",
                        justify="left", # <-- Arregla la indentación
                        wraplength=wrap_width 
                    ).pack(fill="x", pady=0, anchor="w") # <-- "anchor" alinea arriba
                    
                    reporte_valor = s.get("reporte")
                    if not reporte_valor or str(reporte_valor).strip().lower() in ["none", "null", ""]:
                        reporte_valor = "Sin reporte"
                        
                    ctk.CTkLabel(
                        col2_frame, 
                        text=f"Reporte: {reporte_valor}",
                        font=FONT_DETAIL, 
                        text_color=COLOR_DETAIL_TEXT, 
                        anchor="w",
                        justify="left", # <-- Arregla la indentación
                        wraplength=wrap_width 
                    ).pack(fill="x", pady=0, anchor="w") # <-- "anchor" alinea arriba

                    # --- Separador 2 ---
                    ctk.CTkFrame(columns_frame, width=2, fg_color=COLOR_SEPARATOR).grid(row=0, column=3, sticky="ns")

                    # --- Columna 3 (Las fechas no necesitan wrap) ---
                    col3_frame = ctk.CTkFrame(columns_frame, fg_color="transparent")
                    # --- CAMBIO IMPORTANTE: "sticky" vuelve a "nsew" ---
                    col3_frame.grid(row=0, column=4, sticky="nsew", padx=(5, 0))

                    ctk.CTkLabel(
                        col3_frame, 
                        text=f"Fecha creación: {formatear_fecha(s.get('fecha'))}", 
                        font=FONT_DETAIL, 
                        text_color=COLOR_DETAIL_TEXT, 
                        anchor="w",
                        justify="left"
                    ).pack(fill="x", pady=0, anchor="w") # <-- "anchor" alinea arriba
                    ctk.CTkLabel(
                        col3_frame, 
                        text=f"Fecha de culminación: {formatear_fecha(s.get('fecha_culminado'))}", 
                        font=FONT_DETAIL, 
                        text_color=COLOR_DETAIL_TEXT, 
                        anchor="w",
                        justify="left"
                    ).pack(fill="x", pady=0, anchor="w") # <-- "anchor" alinea arriba
                    
                    # 3b. Insignia (Pill)
                    pill = ctk.CTkFrame(
                        body_container, 
                        fg_color=color_bg, 
                        border_color=color_border, 
                        border_width=1, 
                        corner_radius=14 
                    )
                    pill.grid(row=0, column=1, padx=(10, 0), pady=(0,3), sticky="se") 
                    
                    ctk.CTkLabel(
                        pill, 
                        text=estado_text.upper(), 
                        text_color=color_text, 
                        font=FONT_PILL
                    ).pack(padx=12, pady=5) 

            scrollable.after(0, _render)

        threading.Thread(target=tarea, daemon=True).start()
        
        
        
        
    
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
                    depto_nombre = s.get('Departamento', 'Desconocido')
                    
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
                        ws.column_dimensions['A'].width = 10
                        ws.column_dimensions['B'].width = 20
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

    # --- INICIO: CORRECCIÓN Y ADICIÓN DE BOTONES DE FILTRO ---
    
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

    # Botón de Exportar (Columna 3)
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
    
    # --- NUEVO BOTÓN DE GRÁFICOS (Columna 4) ---
    if icon_graficos: # Si el ICONO 'grafica.png' se cargó
        ctk.CTkButton(
            title_frame,
            text="", 
            image=icon_graficos, 
            width=45,  
            height=35, 
            fg_color="#D97706",  
            hover_color="#B45309",
            corner_radius=8,
            # --- CAMBIO AQUÍ ---
            command=lambda: mostrar_pantalla_graficos(root, mostrar_pantalla_principal)
        ).grid(row=0, column=4, padx=5, sticky="e")
    else:
        # Fallback a botón de texto
        ctk.CTkButton(
            title_frame,
            text="Gráficos",
            width=100,
            height=35,
            fg_color="#D97706",
            hover_color="#B45309",
            corner_radius=8,
            # --- CAMBIO AQUÍ ---
            command=lambda: mostrar_pantalla_graficos(root, mostrar_pantalla_principal)
        ).grid(row=0, column=4, padx=5, sticky="e")

    # Botón de Recargar (Columna 5 - MOVIDO)
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
    ).grid(row=0, column=5, padx=5, sticky="e") # Cambiado de columna 4 a 5
    
    # --- FIN: CORRECCIÓN DE BOTONES DE FILTRO ---
    renderizar_servicios()

# Pantalla de Login / Configuración Inicial
def setup_login_app(root):
    
    _clear_widgets(root)
    
    ctk.set_appearance_mode("light")
    root.title("Sistema de Acceso")

    # 1. El main_frame actúa como el contenedor principal.
    main_frame = ctk.CTkFrame(root, fg_color="#FFFFFF")
    main_frame.pack(expand=True, fill="both") 
    
    image_path = "imagen/login.png"
    
    try:
        if not os.path.exists(image_path):
            print(f"Advertencia: No se encontró '{image_path}'. Creando placeholder.")
            try:
                os.makedirs("imagen", exist_ok=True)
                placeholder_img = PILImage.new('RGB', (1024, 768), color = '#3498db')
                placeholder_img.save(image_path)
                print(f"Placeholder 'login.png' creado en la carpeta 'imagen/'.")
            except Exception as e:
                raise Exception(f"No se pudo crear placeholder: {e}")

        # Cargar la imagen original (PIL)
        original_bg_image = PILImage.open(image_path)
        
        # 2. La etiqueta de fondo se coloca en el main_frame y lo llena
        bg_image_label = ctk.CTkLabel(main_frame, text="", image=None)
        bg_image_label.place(relx=0, rely=0, relwidth=1, relheight=1)

        # 3. Función anidada para redimensionar la imagen
        def resize_bg_image(event):
            new_width = event.width
            new_height = event.height
            
            if new_width <= 1 or new_height <= 1:
                return 

            resized_img = original_bg_image.resize((new_width, new_height), PILImage.Resampling.LANCZOS)
            new_bg_ctk_image = ctk.CTkImage(light_image=resized_img, size=(new_width, new_height))
            bg_image_label.configure(image=new_bg_ctk_image)
            bg_image_label.image = new_bg_ctk_image 

        # 4. Vincular el evento de redimensionado al main_frame
        main_frame.bind("<Configure>", resize_bg_image)

    except Exception as e:
        print(f"Error al cargar la imagen de fondo: {e}")
        pass 

    
    # --- POSICIONAMIENTO DE WIDGETS FLOTANTES (SIN CUADRO CENTRAL) ---
    # Todos los widgets se colocan directamente sobre el 'main_frame' usando .place(


    global cedula_entry, notificacion, app_root
    app_root = root 

    # Posicionamos el campo de cédula (rely=0.55)
    cedula_entry = ctk.CTkEntry(main_frame, placeholder_text="Cédula de Identidad", width=300, height=45, corner_radius=0, border_width=1, fg_color="white", border_color="#A1A1A1", text_color="black", font=ctk.CTkFont(size=14))
    cedula_entry.place(relx=0.5, rely=0.55, anchor="center")

    # Posicionamos el botón (rely=0.65)
    login_button = ctk.CTkButton(main_frame, text="INGRESAR", width=300, height=50, fg_color="#002D64", hover_color="#1A4E91", corner_radius=0, font=ctk.CTkFont(size=16, weight="bold"), text_color="white", command=validar_cedula)
    login_button.place(relx=0.5, rely=0.65, anchor="center")

    # Posicionamos la notificación (rely=0.73)
    notificacion = ctk.CTkLabel(main_frame, text="", text_color="yellow", font=ctk.CTkFont(size=14, weight="bold"), fg_color="transparent")
    notificacion.place(relx=0.5, rely=0.73, anchor="center")
    
# --- Código para ejecutar la aplicación ---
if __name__ == "__main__":
    root = ctk.CTk()
    root.geometry("800x600")
    setup_login_app(root)
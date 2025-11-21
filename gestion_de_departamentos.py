import customtkinter as ctk
from cliente_supabase import supabase
import tkinter as tk
from tkinter import messagebox
import os
from PIL import Image as PILImage 

# Referencias Globales del Módulo
depto_entry = None
depto_notificacion = None

def _clear_widgets(root):
    for widget in root.winfo_children():
        widget.destroy()

def mostrar_pantalla_departamentos(root):
    global depto_entry, depto_notificacion

    # Importación diferida para evitar ciclos de importación con sistema_acceso
    from sistema_acceso import mostrar_pantalla_principal

    _clear_widgets(root)
    root.title("GESTIÓN DE DEPARTAMENTOS")

    main = ctk.CTkFrame(root, fg_color="#F2F5F9")
    main.pack(expand=True, fill="both")
    main.grid_rowconfigure(1, weight=1)
    main.grid_columnconfigure(0, weight=1)

    header = ctk.CTkFrame(main, fg_color="#0C4A6E", height=70, corner_radius=0)
    header.grid(row=0, column=0, sticky="ew")
    header.grid_columnconfigure(0, weight=1) 
    header.grid_columnconfigure(1, weight=0)  

    ctk.CTkLabel(header, text="Gestión de Departamentos", text_color="white", font=ctk.CTkFont(size=20, weight="bold")).grid(row=0, column=0, padx=20, pady=18, sticky="w")

    try:
        ruta_volver = os.path.join("imagen", "volver.png")
        icono_volver = ctk.CTkImage(light_image=PILImage.open(ruta_volver), size=(20, 20))
        texto_btn = "" 
        ancho_btn = 50 
    except Exception:
        icono_volver = None
        texto_btn = "VOLVER" 
        ancho_btn = 90

    volver_btn = ctk.CTkButton(header, text=texto_btn, image=icono_volver, width=ancho_btn, height=36, fg_color="#3D89D1", hover_color="#1E3D8F", command=lambda: mostrar_pantalla_principal(root))
    volver_btn.grid(row=0, column=1, padx=20, pady=17, sticky="e")

    content = ctk.CTkFrame(main, fg_color="transparent")
    content.grid(row=1, column=0, sticky="nsew", padx=12, pady=12)
    content.grid_columnconfigure(0, weight=3)
    content.grid_columnconfigure(1, weight=2)
    content.grid_rowconfigure(0, weight=1)

    left = ctk.CTkFrame(content, fg_color="#FFFFFF", corner_radius=10)
    left.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
    left.grid_rowconfigure(1, weight=1)
    left.grid_columnconfigure(0, weight=1)

    actions = ctk.CTkFrame(left, fg_color="transparent", height=50) 
    actions.grid_propagate(False) 
    actions.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 0))
    actions.grid_columnconfigure(1, weight=1)

    try:
        ruta_eliminar = os.path.join("imagen", "eliminar.png")
        icono_eliminar = ctk.CTkImage(light_image=PILImage.open(ruta_eliminar), size=(20, 20))
        texto_eliminar = ""
        ancho_eliminar = 40 
    except Exception:
        icono_eliminar = None
        texto_eliminar = "ELIMINAR"
        ancho_eliminar = 110

    eliminar_btn = ctk.CTkButton(actions, text=texto_eliminar, image=icono_eliminar, fg_color="#DC2626", hover_color="#B91C1C", width=ancho_eliminar, height=34, command=lambda: on_eliminar())
    eliminar_btn.grid(row=0, column=0)

    selection_label = ctk.CTkLabel(actions, text="NINGÚN DEPARTAMENTO SELECCIONADO", text_color="white", fg_color="#0C4A6E", corner_radius=6, font=ctk.CTkFont(size=11, weight="bold"), padx=10, pady=5)
    selection_label.grid(row=0, column=1, sticky="e", padx=(10, 0))

    rows = ctk.CTkScrollableFrame(left, fg_color="transparent")
    rows.grid(row=1, column=0, sticky="nsew", padx=12, pady=12)
    rows.grid_columnconfigure(0, weight=1)

    selected = {"id": None, "nombre": None}

    right = ctk.CTkFrame(content, fg_color="#FFFFFF", corner_radius=10)
    right.grid(row=0, column=1, sticky="nsew")
    right.grid_columnconfigure(0, weight=1)

    ctk.CTkLabel(right, text="AGREGAR / EDITAR DEPARTAMENTO", font=ctk.CTkFont(size=18, weight="bold"), text_color="#1E3D8F").grid(row=0, column=0, pady=(30, 15), padx=20)

    depto_entry = ctk.CTkEntry(right, placeholder_text="Nombre del departamento", width=450, height=45, font=ctk.CTkFont(size=14), border_color="#CDCECF")
    depto_entry.grid(row=1, column=0, pady=(5, 5), padx=20)

    depto_notificacion = ctk.CTkLabel(right, text="", text_color="#16A34A")
    depto_notificacion.grid(row=2, column=0, pady=(0, 20))

    def on_guardar():
        nombre = depto_entry.get().strip().upper()
        if not nombre:
            depto_notificacion.configure(text="Ingrese un nombre válido.", text_color="orange")
            return

        if selected["id"]:
            actualizar_departamento(selected["id"], nombre)
            cargar_departamentos()
            limpiar_seleccion()
        else:
            try:
                supabase.table("Departamento").insert({"nombre_departamento": nombre}).execute()
                depto_notificacion.configure(text="Departamento agregado con éxito.", text_color="#16A34A")
                cargar_departamentos()
                limpiar_seleccion()
            except Exception as e:
                print(f"ERROR: {e}")
                depto_notificacion.configure(text=f"Error al guardar: {str(e)}", text_color="red")

    guardar_btn = ctk.CTkButton(right, text="GUARDAR CAMBIOS", fg_color="#16A34A", hover_color="#15803D", font=ctk.CTkFont(size=13, weight="bold"), width=450, height=45, command=on_guardar)
    guardar_btn.grid(row=3, column=0, pady=(10, 10), padx=20)

    cancelar_btn = ctk.CTkButton(right, text="CANCELAR", fg_color="#8b8a8a", hover_color="#777373", font=ctk.CTkFont(size=13, weight="bold"), width=450, height=45, command=lambda: limpiar_seleccion())
    cancelar_btn.grid(row=4, column=0, pady=(0, 20))
    
    def limpiar_seleccion():
        selected["id"] = None
        selected["nombre"] = None
        depto_entry.delete(0, "end")
        selection_label.configure(text="Ningún departamento seleccionado")
        guardar_btn.configure(text="GUARDAR")
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
        depto_notificacion.configure(text="", text_color="#16A34A") 

    def actualizar_departamento(id_dep, nombre):
        try:
            supabase.table("Departamento").update({"nombre_departamento": nombre}).eq("id_departamento", id_dep).execute()
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
            supabase.table("Departamento").delete().eq("id_departamento", selected["id"]).execute()
            depto_notificacion.configure(text="Departamento eliminado.", text_color="#16A34A")
        except Exception as e:
            depto_notificacion.configure(text=f"Error: {e}", text_color="red")
        cargar_departamentos()
        limpiar_seleccion()

    def cargar_departamentos():
        for w in rows.winfo_children():
            w.destroy()
        try:
            data = supabase.table("Departamento").select("id_departamento, nombre_departamento").order("nombre_departamento").execute().data or []
        except:
            data = []
        for d in data:
            f = ctk.CTkFrame(rows, fg_color="transparent", height=42, corner_radius=0)
            f.pack(fill="x", pady=3)
            f.grid_columnconfigure(0, weight=1, uniform="deptos")
            f.configure(width=rows.winfo_width())
            lbl = ctk.CTkLabel(f, text=d["nombre_departamento"], font=ctk.CTkFont(size=14), anchor="w")
            lbl.grid(row=0, column=0, sticky="w", padx=10)
            def on_select(e=None, i=d["id_departamento"], n=d["nombre_departamento"], fr=f):
                for r in rows.winfo_children():
                    r.configure(fg_color="transparent")
                fr.configure(fg_color="#E0F2FE")
                seleccionar(i, n, fr)
            f.bind("<Button-1>", on_select)
            lbl.bind("<Button-1>", on_select)

    cargar_departamentos()
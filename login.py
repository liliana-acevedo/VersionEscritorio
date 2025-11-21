import customtkinter as ctk
import threading
import os
from PIL import Image as PILImage
from cliente_supabase import supabase
import tkinter as tk

# Referencias Globales del Login
cedula_entry = None
notificacion = None
app_root = None

def _clear_widgets(root):
    for widget in root.winfo_children():
        widget.destroy()

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
        
        # IMPORTACIÓN DIFERIDA PARA EVITAR CICLOS
        # Importamos aquí porque sistema_acceso también importa login
        from sistema_acceso import mostrar_pantalla_principal
        
        app_root.after(1200, lambda: mostrar_pantalla_principal(app_root))

    except Exception as e:
        print("Error validando cédula:", e)
        app_root.after(0, lambda: notificacion.configure(text="Error de conexión o base de datos", text_color="purple"))

def setup_login_app(root):
    global cedula_entry, notificacion, app_root
    app_root = root 
    
    _clear_widgets(root)
    
    ctk.set_appearance_mode("light")
    root.title("Sistema de Acceso")

    main_frame = ctk.CTkFrame(root, fg_color="#FFFFFF")
    main_frame.pack(expand=True, fill="both") 
    
    image_path = os.path.join("imagen", "login.png")
    
    try:
        if not os.path.exists(image_path):
            print(f"Advertencia: No se encontró '{image_path}'.")
            # Crear carpeta imagen si no existe
            os.makedirs("imagen", exist_ok=True)
        else:
            original_bg_image = PILImage.open(image_path)
            bg_image_label = ctk.CTkLabel(main_frame, text="", image=None)
            bg_image_label.place(relx=0, rely=0, relwidth=1, relheight=1)

            def resize_bg_image(event):
                new_width = event.width
                new_height = event.height
                if new_width <= 1 or new_height <= 1:
                    return 
                try:
                    resized_img = original_bg_image.resize((new_width, new_height), PILImage.Resampling.LANCZOS)
                    new_bg_ctk_image = ctk.CTkImage(light_image=resized_img, size=(new_width, new_height))
                    bg_image_label.configure(image=new_bg_ctk_image)
                    bg_image_label.image = new_bg_ctk_image 
                except Exception:
                    pass

            main_frame.bind("<Configure>", resize_bg_image)

    except Exception as e:
        print(f"Error al cargar la imagen de fondo: {e}")
        pass 

    # Posicionamos el campo de cédula (rely=0.55)
    cedula_entry = ctk.CTkEntry(main_frame, placeholder_text="Cédula de Identidad", width=300, height=45, corner_radius=0, border_width=1, fg_color="white", border_color="#A1A1A1", text_color="black", font=ctk.CTkFont(size=14))
    cedula_entry.place(relx=0.5, rely=0.55, anchor="center")

    # Posicionamos el botón (rely=0.65)
    login_button = ctk.CTkButton(main_frame, text="INGRESAR", width=300, height=50, fg_color="#002D64", hover_color="#1A4E91", corner_radius=0, font=ctk.CTkFont(size=16, weight="bold"), text_color="white", command=validar_cedula)
    login_button.place(relx=0.5, rely=0.65, anchor="center")

    # Posicionamos la notificación (rely=0.73)
    notificacion = ctk.CTkLabel(main_frame, text="", text_color="yellow", font=ctk.CTkFont(size=14, weight="bold"), fg_color="transparent")
    notificacion.place(relx=0.5, rely=0.73, anchor="center")
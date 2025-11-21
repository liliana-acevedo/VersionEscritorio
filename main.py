import customtkinter as ctk
import tkinter as tk
from login import setup_login_app
import platform 

def main():

    # Crear la ventana principal
    root = ctk.CTk()
    root.title("Sistema de Acceso")

    try:
        root.state("zoomed")
    except tk.TclError:
        try:
            root.attributes("-zoomed", True)
        except Exception:
            pass

    root.minsize(1000, 700)
    
    # Cargar interfaz principal (el login)
    setup_login_app(root)

    # Iniciar el bucle principal
    root.mainloop()

if __name__ == "__main__":
    main()
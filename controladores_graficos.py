import customtkinter as ctk
import tkinter as tk
import threading
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from collections import Counter
import textwrap
import os
from PIL import Image

# Importar supabase
try:
    from cliente_supabase import supabase
    print("--- DEBUG: Supabase importado correctamente ---")
except ImportError:
    supabase = None
    print("--- DEBUG: Error importando cliente_supabase ---")
except Exception as e:
    supabase = None
    print(f"--- DEBUG: Error general en importacion: {e} ---")


# ------------------------------------------------------
# FUNCIONES AUXILIARES
# ------------------------------------------------------

def _clear_widgets(root):
    try:
        for widget in root.winfo_children():
            widget.destroy()
    except Exception as e:
        print(f"--- DEBUG: Error limpiando widgets: {e} ---")


def traducir_estado(valor):
    return {1: "Pendiente", 2: "Completado", 3: "Recibido"}.get(int(valor), "Desconocido") if valor else "Desconocido"


def _obtener_mapa_nombres(tabla, id_col, nombre_cols, filtro=None):
    if not supabase:
        return {}

    mapa = {}
    try:
        query = supabase.table(tabla).select(f"{id_col}, {', '.join(nombre_cols)}")
        if filtro:
            query = query.eq(filtro[0], filtro[1])
        resp = query.execute()

        for item in resp.data or []:
            idd = item.get(id_col)
            nombre_completo = " ".join(str(item.get(col) or "").strip() for col in nombre_cols).strip()
            if idd and nombre_completo:
                mapa[str(idd)] = nombre_completo

    except Exception as e:
        print(f"Error al obtener mapa para {tabla}: {e}")

    return mapa


# ------------------------------------------------------
# OBTENCIÓN DE DATOS
# ------------------------------------------------------

def _fetch_chart_data():
    print("--- DEBUG: Iniciando descarga de datos (hilo) ---")
    if not supabase:
        return {"error": "Supabase no inicializado."}

    try:
        servicios_resp = supabase.table("Servicio").select("estado, departamento, tecnico").execute()
        servicios = servicios_resp.data or []
        print(f"--- DEBUG: Se encontraron {len(servicios)} servicios ---")

        deptos_map_id = _obtener_mapa_nombres("Departamento", "id_departamento", ["nombre_departamento"])
        tech_map = _obtener_mapa_nombres("Usuario", "cedula", ["nombre", "apellido"], filtro=("rol", 1))

        conteo_estados = Counter([traducir_estado(s.get('estado')) for s in servicios])

        conteo_deptos = Counter()
        for s in servicios:
            depto_val = s.get('departamento')
            nombre_depto = deptos_map_id.get(str(depto_val), "ID Desconocido") if str(depto_val).isdigit() else (
                str(depto_val).strip() if depto_val else "Sin Depto."
            )
            conteo_deptos[nombre_depto] += 1

        conteo_tecnicos = Counter()
        for s in servicios:
            tecnico_id = str(s.get('tecnico') or "Sin asignar")
            nombre_tecnico = tech_map.get(tecnico_id, "Sin asignar")
            if nombre_tecnico.lower() != "sin asignar":
                conteo_tecnicos[nombre_tecnico] += 1

        conteo_tecnicos_filtrado = {k: v for k, v in conteo_tecnicos.items() if v > 0}

        return {
            "status": dict(conteo_estados),
            "dept": dict(conteo_deptos),
            "tech": dict(conteo_tecnicos_filtrado)
        }

    except Exception as e:
        print(f"--- DEBUG: Error CRÍTICO buscando datos: {e}")
        return {"error": str(e)}


# ------------------------------------------------------
# GRÁFICOS
# ------------------------------------------------------

def _crear_grafico_estado(tab_frame, data):
    # Verificación de seguridad: si el frame ya no existe, no intentar dibujar
    if not tab_frame.winfo_exists():
        return

    if not data:
        try:
            ctk.CTkLabel(tab_frame, text="No hay datos disponibles").pack(pady=20)
        except Exception:
            pass
        return

    labels = data.keys()
    sizes = data.values()

    color_map = {
        'Pendiente': '#FFC107',
        'Completado': '#4CAF50',
        'Recibido': '#2196F3',
        'Desconocido': '#9E9E9E'
    }
    pie_colors = [color_map.get(label, '#9E9E9E') for label in labels]

    try:
        plt.close('all')
        
        fig, ax = plt.subplots(figsize=(8, 6))

        ax.pie(
            sizes, labels=labels,
            autopct='%1.1f%%',
            startangle=90,
            colors=pie_colors,
            wedgeprops={'edgecolor': 'white'},
            textprops={'color': 'black', 'weight': 'bold'}
        )

        ax.axis('equal')
        fig.patch.set_facecolor('#FFFFFF')
        ax.set_title("Distribución de servicios por estado", color="#0C4A6E", fontsize=16, weight="bold")

        canvas = FigureCanvasTkAgg(fig, master=tab_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)
    except Exception as e:
        print(f"Error dibujando gráfico circular: {e}")


def _crear_grafico_barras(tab_frame, data, title):
    # Verificación de seguridad
    if not tab_frame.winfo_exists():
        return

    if not data:
        try:
            ctk.CTkLabel(tab_frame, text="No hay datos disponibles").pack(pady=20)
        except Exception:
            pass
        return

    sorted_data = dict(sorted(data.items(), key=lambda item: item[1], reverse=True))
    labels = list(sorted_data.keys())
    values = list(sorted_data.values())

    wrapped_labels = [textwrap.fill(label, width=30) for label in labels]
    fig_height = max(7, len(labels) * 0.8)

    try:
        plt.close('all')

        fig, ax = plt.subplots(figsize=(8, fig_height))
        bars = ax.barh(wrapped_labels, values, color='#3D89D1', edgecolor='black')

        ax.set_xlabel("Cantidad de servicios", fontsize=12, color="#333")
        ax.set_title(title, fontsize=16, color="#0C4A6E", weight="bold")
        ax.invert_yaxis()

        for bar in bars:
            ax.text(
                bar.get_width() + 0.1,
                bar.get_y() + bar.get_height() / 2,
                f"{bar.get_width()}",
                va="center",
                fontsize=10
            )

        fig.patch.set_facecolor('#FFFFFF')
        ax.set_facecolor('#FFFFFF')
        
        fig.tight_layout(rect=[0, 0, 0.85, 1]) 

        canvas = FigureCanvasTkAgg(fig, master=tab_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)
    except Exception as e:
        print(f"Error dibujando barras: {e}")


# ------------------------------------------------------
# RENDERIZADO
# ------------------------------------------------------

def _fetch_and_render(root_window, content_frame, tabview, loading_label):
    # 1. Obtenemos datos (esto tarda unos segundos)
    chart_data = _fetch_chart_data()

    # 2. Definimos la función que actualiza la GUI
    def _render():
        # --- CORRECCIÓN CLAVE ---
        # Verificamos si la ventana principal aún existe antes de hacer NADA.
        try:
            if not root_window.winfo_exists():
                print("--- DEBUG: Ventana cerrada, cancelando renderizado ---")
                return
        except Exception:
            return # Si winfo_exists falla, la ventana ya no está.

        try:
            if loading_label.winfo_exists():
                loading_label.destroy()

            if "error" in chart_data:
                if content_frame.winfo_exists():
                    ctk.CTkLabel(content_frame, text=f"Error: {chart_data['error']}", text_color="red").pack(pady=20)
                return

            if tabview.winfo_exists():
                tabview.pack(expand=True, fill="both", padx=10, pady=10)

                # Intentamos crear los gráficos solo si las pestañas existen
                try:
                    _crear_grafico_estado(tabview.tab("Por Estado"), chart_data.get('status'))
                except Exception as e:
                    print(f"Error graficando estado: {e}")

                try:
                    _crear_grafico_barras(tabview.tab("Por Departamento"), chart_data.get('dept'), "Demanda por departamento")
                except Exception as e:
                    print(f"Error graficando departamento: {e}")

                try:
                    _crear_grafico_barras(tabview.tab("Por Técnico"), chart_data.get('tech'), "Cantidad de servicios por técnico")
                except Exception as e:
                    print(f"Error graficando tecnico: {e}")
                
        except Exception as main_e:
            print(f"--- DEBUG: Error controlado en _render (posible cierre de ventana): {main_e} ---")

    # 3. Programamos la ejecución de _render en el hilo principal
    # Usamos try/except por si root_window se destruyó justo en este milisegundo
    try:
        if root_window.winfo_exists():
            root_window.after(0, _render)
    except Exception:
        print("--- DEBUG: No se pudo programar el renderizado, ventana cerrada ---")


# ------------------------------------------------------
# PANTALLA PRINCIPAL
# ------------------------------------------------------

def mostrar_pantalla_graficos(root, funcion_volver):
    print("--- DEBUG: Entrando a mostrar_pantalla_graficos ---")
    
    try:
        _clear_widgets(root)
        root.title("Dashboard de Gráficos")

        # Aseguramos limpieza de gráficos previos de Matplotlib
        plt.close('all')

        main_frame = ctk.CTkFrame(root, fg_color="#F7F9FB")
        main_frame.pack(expand=True, fill="both")
        main_frame.grid_rowconfigure(1, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)

        # HEADER
        header_frame = ctk.CTkFrame(main_frame, fg_color="#0C4A6E", corner_radius=0, height=70)
        header_frame.grid(row=0, column=0, sticky="ew")
        header_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            header_frame,
            text="ANÁLISIS DE SERVICIO",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color="white"
        ).grid(row=0, column=1, padx=20, pady=15, sticky="w")

        # Botón volver
        current_dir = os.path.dirname(os.path.abspath(__file__))
        image_path = os.path.join(current_dir, "imagen", "volver.png")
        
        icon = None
        if os.path.exists(image_path):
            try:
                img = Image.open(image_path)
                icon = ctk.CTkImage(light_image=img, dark_image=img, size=(24, 24))
            except Exception as e:
                print(f"--- DEBUG: Error cargando imagen: {e}")

        btn = ctk.CTkButton(
            header_frame,
            text="VOLVER" if not icon else "",
            image=icon,
            fg_color="#3D89D1",
            hover_color="#1E3D8F",
            corner_radius=8,
            width=50 if icon else 90,
            height=40,
            command=lambda: funcion_volver(root)
        )
        btn.grid(row=0, column=2, padx=20)

        # CONTENIDO
        content_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        content_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)

        tabview = ctk.CTkTabview(content_frame, fg_color="transparent")
        tabview.add("Por Estado")
        tabview.add("Por Departamento")
        tabview.add("Por Técnico")

        for t in ["Por Estado", "Por Departamento", "Por Técnico"]:
            tabview.tab(t).configure(fg_color="transparent")

        loading_label = ctk.CTkLabel(
            content_frame,
            text="Cargando datos y generando gráficos...",
            font=ctk.CTkFont(size=16)
        )
        loading_label.pack(pady=50)

        hilo = threading.Thread(
            target=_fetch_and_render,
            args=(root, content_frame, tabview, loading_label),
            daemon=True
        )
        hilo.start()

    except Exception as e:
        print(f"--- DEBUG: Error FATAL construyendo interfaz: {e} ---")
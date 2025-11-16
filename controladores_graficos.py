import customtkinter as ctk
import tkinter as tk
import threading
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from collections import Counter
import textwrap  # Para ajustar el texto de las etiquetas

# Importar la instancia de supabase desde tu archivo principal
try:
    from cliente_supabase import supabase
except ImportError:
    print("Error: No se pudo importar 'supabase' desde 'cliente_supabase'.")
    supabase = None

# --- Funciones Auxiliares (Copiadas/Adaptadas de sistema_acceso.py) ---

def _clear_widgets(root):
    """Limpia todos los widgets de un frame o root."""
    for widget in root.winfo_children():
        widget.destroy()

def traducir_estado(valor):
    """Traduce el ID de estado a un texto legible."""
    return {1: "Pendiente", 2: "Completado", 3: "Recibido"}.get(int(valor), "Desconocido") if valor else "Desconocido"

def _obtener_mapa_nombres(tabla, id_col, nombre_cols, filtro=None):
    """
    Función genérica para crear un mapa de ID -> Nombre desde Supabase.
    """
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
            nombre_completo = " ".join(
                str(item.get(col) or "").strip() for col in nombre_cols
            ).strip()
            
            if idd and nombre_completo:
                mapa[str(idd)] = nombre_completo
                
    except Exception as e:
        print(f"Error al obtener mapa para {tabla}: {e}")
    return mapa

# --- Lógica de Carga de Datos para Gráficos ---

def _fetch_chart_data():
    """
    Busca todos los datos necesarios para los gráficos en un hilo separado.
    """
    if not supabase:
        return {"error": "Supabase no inicializado."}

    try:
        servicios_resp = supabase.table("Servicio").select("estado, departamento, tecnico").execute()
        servicios = servicios_resp.data or []
        
        deptos_map_id = _obtener_mapa_nombres("Departamento", "id_departamento", ["nombre_departamento"])
        
        tech_map = _obtener_mapa_nombres("Usuario", "cedula", ["nombre", "apellido"], filtro=("rol", 1))

        # --- Procesar Datos ---
        conteo_estados = Counter([traducir_estado(s.get('estado')) for s in servicios])
        
        conteo_deptos = Counter()
        for s in servicios:
            depto_val = s.get('departamento')
            if str(depto_val).isdigit():
                nombre_depto = deptos_map_id.get(str(depto_val), "ID Desconocido")
            else:
                nombre_depto = str(depto_val).strip() if depto_val else "Sin Depto."
            conteo_deptos[nombre_depto] += 1
            
        conteo_tecnicos = Counter()
        for s in servicios:
            tecnico_id = str(s.get('tecnico') or "Sin asignar")
            nombre_tecnico = tech_map.get(tecnico_id, "Sin asignar")
            if nombre_tecnico != "Sin Asignar":
                conteo_tecnicos[nombre_tecnico] += 1
                
        conteo_tecnicos_filtrado = {k: v for k, v in conteo_tecnicos.items() if v > 0}

        return {
            "status": dict(conteo_estados),
            "dept": dict(conteo_deptos),
            "tech": dict(conteo_tecnicos_filtrado)
        }

    except Exception as e:
        print(f"Error al buscar datos de gráficos: {e}")
        return {"error": str(e)}

# --- Funciones de Renderizado de Gráficos ---

def _crear_grafico_estado(tab_frame, data):
    """Crea un gráfico de pastel para los estados."""
    if not data:
        ctk.CTkLabel(tab_frame, text="No hay datos de estado para mostrar.").pack(pady=20)
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

    # --- CAMBIO: Aumentado el tamaño del gráfico ---
    fig, ax = plt.subplots(figsize=(8, 6)) # Tamaño base más grande
    
    ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90, colors=pie_colors,
           wedgeprops={'edgecolor': 'white'}, textprops={'color': 'black', 'weight': 'bold'})
    ax.axis('equal')  
    
    fig.patch.set_facecolor('#F7F9FB') 
    ax.set_title("Distribución de servicios por estado", color="#0C4A6E", fontsize=16, weight="bold")
    
    ax.legend(labels, loc="best", bbox_to_anchor=(0.9, 0.9))
    
    plt.tight_layout()

    canvas = FigureCanvasTkAgg(fig, master=tab_frame)
    canvas.draw()
    
    # --- CAMBIO: Volvemos a expandir el gráfico ---
    canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=10)

def _crear_grafico_barras(tab_frame, data, title):
    """Crea un gráfico de barras horizontal."""
    if not data:
        ctk.CTkLabel(tab_frame, text=f"No hay datos para '{title}'.").pack(pady=20)
        return

    sorted_data = dict(sorted(data.items(), key=lambda item: item[1], reverse=True))
    
    labels = list(sorted_data.keys())
    values = list(sorted_data.values())

    # --- INICIO DE CAMBIOS ---
    
    # 1. Envolver (wrap) las etiquetas largas (esto sigue bien)
    wrapped_labels = [textwrap.fill(label, width=35) for label in labels] 

    # 2. Altura dinámica (esto sigue bien)
    n_items = len(labels)
    fig_height = max(7, n_items * 0.8) 
    
    fig, ax = plt.subplots(figsize=(8, fig_height)) # Usar altura dinámica
    
    bars = ax.barh(wrapped_labels, values, color='#3D89D1', edgecolor='black')
    
    ax.set_xlabel('Cantidad de servicios', fontsize=12, color="#333")
    ax.set_title(title, color="#0C4A6E", fontsize=16, weight="bold")
    ax.invert_yaxis()  
    
    for bar in bars:
        ax.text(bar.get_width() + 0.1, bar.get_y() + bar.get_height()/2, 
                f' {bar.get_width()}', 
                va='center', ha='left', color='black', fontsize=10)

    fig.patch.set_facecolor('#F7F9FB')
    ax.set_facecolor('#FFFFFF')
    
    # --- ¡ESTE ES EL ARREGLO! ---
    # ELIMINAMOS la línea 'plt.subplots_adjust(left=0.45)'
    # Ahora 'tight_layout' (abajo) ajustará el gráfico automáticamente
    # al tamaño de las etiquetas sin crear un espacio gigante.
    
    plt.tight_layout(pad=3.0)

    # 3. Volvemos a expandir el gráfico (esto sigue bien)
    canvas = FigureCanvasTkAgg(fig, master=tab_frame)
    canvas.draw()
    canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=10)
    


# --- Función Principal (Modificada) ---

def _fetch_and_render(root_window, content_frame, tabview, loading_label):
    """
    Función objetivo para el hilo: busca datos y luego renderiza.
    """
    chart_data = _fetch_chart_data()
    
    def _render():
        loading_label.destroy() 
        
        if "error" in chart_data:
            ctk.CTkLabel(content_frame, text=f"Error al cargar datos: {chart_data['error']}", text_color="red").pack(pady=20)
            return
        
        tabview.pack(expand=True, fill="both", padx=10, pady=10)

        try:
            _crear_grafico_estado(tabview.tab("Por Estado"), chart_data.get('status'))
        except Exception as e:
            ctk.CTkLabel(tabview.tab("Por estado"), text=f"Error al renderizar gráfico: {e}", text_color="red").pack(pady=10)
            
        try:
            _crear_grafico_barras(tabview.tab("Por departamento"), chart_data.get('dept'), 'Demanda por departamento')
        except Exception as e:
            ctk.CTkLabel(tabview.tab("Por departamento"), text=f"Error al renderizar gráfico: {e}", text_color="red").pack(pady=10)

        try:
            _crear_grafico_barras(tabview.tab("Por técnico"), chart_data.get('tech'), 'Cantidad de servicios por técnico')
        except Exception as e:
            ctk.CTkLabel(tabview.tab("Por Técnico"), text=f"Error al renderizar gráfico: {e}", text_color="red").pack(pady=10)

    root_window.after(0, _render)


def mostrar_pantalla_graficos(root, funcion_volver):
    """
    Muestra la pantalla de gráficos DENTRO del root.
    """
    
    _clear_widgets(root) 
    root.title("Dashboard de Gráficos")
    
    main_frame = ctk.CTkFrame(root, fg_color="#F7F9FB")
    main_frame.pack(expand=True, fill="both")
    main_frame.grid_rowconfigure(1, weight=1) 
    main_frame.grid_columnconfigure(0, weight=1)
    
    header_frame = ctk.CTkFrame(main_frame, fg_color="#0C4A6E", corner_radius=0, height=70)
    header_frame.grid(row=0, column=0, sticky="ew")
    header_frame.grid_columnconfigure(1, weight=1) 
    header_frame.grid_columnconfigure(2, weight=0) 

    ctk.CTkLabel(header_frame, text="Análisis de servicios",
                 font=ctk.CTkFont(size=22, weight="bold"),
                 text_color="white").grid(row=0, column=1, padx=(30, 20), pady=15, sticky="w")

    ctk.CTkButton(header_frame, text="VOLVER", fg_color="#3D89D1",
                  hover_color="#1E3D8F",
                  font=ctk.CTkFont(size=13, weight="bold"),
                  corner_radius=8, width=120, height=40,
                  command=lambda: funcion_volver(root)
                  ).grid(row=0, column=2, padx=(10, 20), pady=12, sticky="e")
    
    content_frame = ctk.CTkFrame(main_frame, fg_color="#F7F9FB")
    content_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)

    tabview = ctk.CTkTabview(content_frame, fg_color="#FFFFFF")
    tabview.add("Por Estado")
    tabview.add("Por Departamento")
    tabview.add("Por Técnico")
    
    loading_label = ctk.CTkLabel(
        content_frame, 
        text="Cargando datos y generando gráficos...",
        font=ctk.CTkFont(size=16)
    )
    loading_label.pack(pady=50, expand=True)

    threading.Thread(
        target=_fetch_and_render, 
        args=(root, content_frame, tabview, loading_label), 
        daemon=True
    ).start()
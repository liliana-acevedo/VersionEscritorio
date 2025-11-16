import customtkinter as ctk
import tkinter as tk
import threading
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from collections import Counter

# Importar la instancia de supabase desde tu archivo principal
# Asegúrate de que cliente_supabase.py esté accesible
try:
    from cliente_supabase import supabase
except ImportError:
    print("Error: No se pudo importar 'supabase' desde 'cliente_supabase'.")
    supabase = None

# --- Funciones Auxiliares (Copiadas/Adaptadas de sistema_acceso.py) ---

def traducir_estado(valor):
    """Traduce el ID de estado a un texto legible."""
    return {1: "Pendiente", 2: "Completado", 3: "Recibido"}.get(int(valor), "Desconocido") if valor else "Desconocido"

def _obtener_mapa_nombres(tabla, id_col, nombre_cols, filtro=None):
    """
    Función genérica para crear un mapa de ID -> Nombre desde Supabase.
    nombre_cols es una lista, ej: ["nombre", "apellido"]
    filtro es una tupla opcional, ej: ("rol", 1)
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
            
            # Construir el nombre completo
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
        # 1. Obtener todos los servicios
        servicios_resp = supabase.table("Servicio").select("estado, departamento, tecnico").execute()
        servicios = servicios_resp.data or []
        
        # 2. Obtener mapa de Departamentos (ID -> Nombre)
        # Asumiendo que 'departamento' en Servicio puede ser un ID o un nombre
        deptos_map_id = _obtener_mapa_nombres("Departamento", "id_departamento", ["nombre_departamento"])
        
        # 3. Obtener mapa de Técnicos (Cédula -> Nombre)
        # Asumiendo que Rol 1 = Técnico
        tech_map = _obtener_mapa_nombres("Usuario", "cedula", ["nombre", "apellido"], filtro=("rol", 1))

        # --- Procesar Datos ---
        
        # Gráfico 1: Conteo por Estado
        conteo_estados = Counter([traducir_estado(s.get('estado')) for s in servicios])
        
        # Gráfico 2: Conteo por Departamento
        conteo_deptos = Counter()
        for s in servicios:
            depto_val = s.get('departamento')
            if str(depto_val).isdigit():
                nombre_depto = deptos_map_id.get(str(depto_val), "ID Desconocido")
            else:
                nombre_depto = str(depto_val).strip() if depto_val else "Sin Depto."
            conteo_deptos[nombre_depto] += 1
            
        # Gráfico 3: Conteo por Técnico
        conteo_tecnicos = Counter()
        for s in servicios:
            tecnico_id = str(s.get('tecnico') or "Sin Asignar")
            nombre_tecnico = tech_map.get(tecnico_id, "Sin Asignar")
            if nombre_tecnico != "Sin Asignar":
                conteo_tecnicos[nombre_tecnico] += 1
                
        # Filtrar técnicos con 0 servicios (aunque ya se hizo con el bucle)
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
    
    # Definir colores
    colors = ['#FFC107', '#4CAF50', '#2196F3'] # Amarillo (Pendiente), Verde (Completado), Azul (Recibido)
    color_map = {
        'Pendiente': '#FFC107',
        'Completado': '#4CAF50',
        'Recibido': '#2196F3',
        'Desconocido': '#9E9E9E'
    }
    pie_colors = [color_map.get(label, '#9E9E9E') for label in labels]

    fig, ax = plt.subplots(figsize=(7, 5))
    ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90, colors=pie_colors,
           wedgeprops={'edgecolor': 'white'}, textprops={'color': 'black', 'weight': 'bold'})
    ax.axis('equal')  # Asegura que el pastel sea circular
    
    fig.patch.set_facecolor('#F7F9FB') # Fondo que coincide con la app
    ax.set_title("Distribución de Servicios por Estado", color="#0C4A6E", fontsize=16, weight="bold")
    
    # Añadir leyenda
    ax.legend(labels, loc="best", bbox_to_anchor=(0.9, 0.9))
    
    plt.tight_layout()

    # Incrustar en Tkinter
    canvas = FigureCanvasTkAgg(fig, master=tab_frame)
    canvas.draw()
    canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=10)

def _crear_grafico_barras(tab_frame, data, title):
    """Crea un gráfico de barras horizontal."""
    if not data:
        ctk.CTkLabel(tab_frame, text=f"No hay datos para '{title}'.").pack(pady=20)
        return

    # Ordenar datos para mejor visualización (de mayor a menor)
    sorted_data = dict(sorted(data.items(), key=lambda item: item[1], reverse=True))
    
    labels = list(sorted_data.keys())
    values = list(sorted_data.values())

    fig, ax = plt.subplots(figsize=(8, 6))
    
    # Gráfico de barras horizontal
    bars = ax.barh(labels, values, color='#3D89D1', edgecolor='black')
    
    ax.set_xlabel('Cantidad de Servicios', fontsize=12, color="#333")
    ax.set_title(title, color="#0C4A6E", fontsize=16, weight="bold")
    ax.invert_yaxis()  # Muestra el más alto arriba
    
    # Añadir etiquetas de valor en las barras
    for bar in bars:
        ax.text(bar.get_width() + 0.1, bar.get_y() + bar.get_height()/2, 
                f' {bar.get_width()}', 
                va='center', ha='left', color='black', fontsize=10)

    fig.patch.set_facecolor('#F7F9FB')
    ax.set_facecolor('#FFFFFF')
    
    # Ajustar márgenes
    plt.subplots_adjust(left=0.3) # Dar más espacio a las etiquetas del eje Y
    plt.tight_layout(pad=2.0)

    # Incrustar en Tkinter
    canvas = FigureCanvasTkAgg(fig, master=tab_frame)
    canvas.draw()
    canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=10)


# --- Función Principal de la Ventana de Gráficos ---

def _fetch_and_render(toplevel, tabview, loading_label):
    """Función objetivo para el hilo: busca datos y luego renderiza."""
    chart_data = _fetch_chart_data()
    
    def _render():
        loading_label.destroy() # Ocultar "Cargando..."
        
        if "error" in chart_data:
            ctk.CTkLabel(toplevel, text=f"Error al cargar datos: {chart_data['error']}", text_color="red").pack(pady=20)
            return
        
        # Mostrar el TabView
        tabview.pack(expand=True, fill="both", padx=10, pady=10)

        # Renderizar cada gráfico en su pestaña
        try:
            _crear_grafico_estado(tabview.tab("Por Estado"), chart_data.get('status'))
        except Exception as e:
            ctk.CTkLabel(tabview.tab("Por Estado"), text=f"Error al renderizar gráfico: {e}", text_color="red").pack(pady=10)
            
        try:
            _crear_grafico_barras(tabview.tab("Por Departamento"), chart_data.get('dept'), 'Demanda por Departamento')
        except Exception as e:
            ctk.CTkLabel(tabview.tab("Por Departamento"), text=f"Error al renderizar gráfico: {e}", text_color="red").pack(pady=10)

        try:
            _crear_grafico_barras(tabview.tab("Por Técnico"), chart_data.get('tech'), 'Cantidad de Servicios por Técnico')
        except Exception as e:
            ctk.CTkLabel(tabview.tab("Por Técnico"), text=f"Error al renderizar gráfico: {e}", text_color="red").pack(pady=10)

    # Programar el renderizado en el hilo principal de Tkinter
    toplevel.after(0, _render)


def mostrar_pantalla_graficos(root):
    """
    Crea y muestra la ventana emergente (Toplevel) para los gráficos.
    """
    
    ventana_graficos = ctk.CTkToplevel(root)
    ventana_graficos.title("Dashboard de Gráficos")
    ventana_graficos.geometry("900x700")
    ventana_graficos.configure(fg_color="#F7F9FB")
    ventana_graficos.grab_set() # Bloquear interacción con la ventana principal
    ventana_graficos.focus_force()
    
    # Título principal de la ventana
    ctk.CTkLabel(
        ventana_graficos, 
        text="Análisis de servicios", 
        font=ctk.CTkFont(size=24, weight="bold"), 
        text_color="#0C4A6E"
    ).pack(pady=(15, 5))
    
    # Crear el TabView (contenedor de pestañas)
    tabview = ctk.CTkTabview(ventana_graficos, fg_color="#FFFFFF")
    tabview.add("Por Estado")
    tabview.add("Por Departamento")
    tabview.add("Por Técnico")
    # Ocultar el tabview hasta que los datos estén listos
    
    # Etiqueta de "Cargando..."
    loading_label = ctk.CTkLabel(
        ventana_graficos, 
        text="Cargando datos y generando gráficos...",
        font=ctk.CTkFont(size=16)
    )
    loading_label.pack(pady=50, expand=True)

    # Iniciar la carga de datos en un hilo separado
    threading.Thread(
        target=_fetch_and_render, 
        args=(ventana_graficos, tabview, loading_label), 
        daemon=True
    ).start()
import tkinter as tk
from tkinter import messagebox, ttk
import pandas as pd
import os
from datetime import datetime, timedelta

ARCHIVO_MAESTRO = "Base_Maestra_Descansos_SZ_LOJA.csv"

# --- 1. CARGA Y LIMPIEZA DE DATOS ---
def cargar_base_final():
    if not os.path.exists(ARCHIVO_MAESTRO):
        return None
    try:
        df = pd.read_csv(ARCHIVO_MAESTRO, sep=';', encoding='latin-1', dtype=str)
        df.columns = df.columns.str.strip()
        df = df.loc[:, ~df.columns.duplicated()]
        if 'CEDULA' in df.columns:
            df['CEDULA'] = df['CEDULA'].str.replace('.0', '', regex=False).str.zfill(10)
        return df
    except Exception as e:
        print(f"Error en carga: {e}")
        return None

# --- 2. REPORTES Y CÁLCULOS ---
def obtener_alertas_reincorporacion():
    df = cargar_base_final()
    if df is None: return "Base de datos no vinculada."
    try:
        hoy = datetime.now().date()
        texto = "📋 ALERTAS DE REINCORPORACIÓN (VÁLIDO):\n"
        df_temp = df.copy()
        df_temp['FECHA_DT'] = pd.to_datetime(df_temp['FECHA_DE_PRESENTACION'], format='%d/%m/%Y', errors='coerce')
        
        for i, label in enumerate(["HOY", "MAÑANA", "PASADO MAÑANA"]):
            fecha_buscada = hoy + timedelta(days=i)
            subs = df_temp[df_temp['FECHA_DT'].dt.date == fecha_buscada]
            texto += f"📍 {label} ({fecha_buscada.strftime('%d/%m/%Y')}): {len(subs)} Servidor(es)\n"
            for _, r in subs.iterrows():
                unidad = r.get('SUBZONAO_DISTRITO', 'S/D')
                texto += f"   - {r.get('GRADO','')} {r.get('NOMBRES','')} [{unidad}]\n"
        return texto
    except: return "Esperando datos de fechas..."

def calcular_dias_restantes_auto(fecha_pres_str):
    """Calcula días faltantes desde hoy hasta la fecha de presentación"""
    try:
        hoy = datetime.now().date()
        f_pres = datetime.strptime(fecha_pres_str, '%d/%m/%Y').date()
        diff = (f_pres - hoy).days
        return str(diff) if diff > 0 else "0"
    except:
        return "0"

def auto_calcular_relacion_fechas(*args):
    try:
        f_ini_str = variables["FECHA_DE_INICIO"].get()
        dias_val = variables["TIEMPO_EN_DIAS"].get()
        if f_ini_str and dias_val:
            dias = int(float(dias_val))
            f_ini = datetime.strptime(f_ini_str, '%d/%m/%Y')
            f_pres = f_ini + timedelta(days=dias)
            
            f_pres_str = f_pres.strftime('%d/%m/%Y')
            variables["FECHA_DE_PRESENTACION"].set(f_pres_str)
            variables["TOTAL_DE_DIAS_DE_DESCANSO_MEDICO"].set(str(dias))
            
            # Condición agregada: Días restantes automáticos
            variables["DIAS_RESTANTES"].set(calcular_dias_restantes_auto(f_pres_str))
    except: pass

# --- 3. FUNCIONES DE GESTIÓN ---
def buscar_historial():
    df = cargar_base_final()
    if df is None: return
    bus = entry_busqueda.get().strip().upper()
    f = df[(df['CEDULA'] == bus.zfill(10)) | (df['NOMBRES'].str.contains(bus, na=False))]
    for i in tree.get_children(): tree.delete(i)
    if not f.empty:
        f = f.copy()
        f['DT'] = pd.to_datetime(f['FECHA_DE_INICIO'], format='%d/%m/%Y', errors='coerce')
        f = f.sort_values(by='DT', ascending=False)
        for idx, r in f.iterrows():
            tree.insert("", "end", iid=idx, values=(r.get('FECHA_DE_INICIO'), r.get('TIEMPO_EN_DIAS'), r.get('PRESENTACION', 'NO'), r.get('CAUSA')))
        lbl_status.config(text=f"✅ {f.iloc[0]['NOMBRES']}", fg="green")
    else: messagebox.showinfo("SZ-LOJA", "Búsqueda sin resultados.")

def cargar_en_ficha(event):
    sel = tree.selection()
    if not sel: return
    df = cargar_base_final()
    global cur_idx
    cur_idx = int(sel[0])
    reg = df.loc[cur_idx]
    for c, v in variables.items():
        v.set(str(reg.get(c, "")))
    
    # Recalcular días restantes al cargar por si pasó el tiempo
    f_pres = variables["FECHA_DE_PRESENTACION"].get()
    variables["DIAS_RESTANTES"].set(calcular_dias_restantes_auto(f_pres))

def guardar_cambios():
    if 'cur_idx' not in globals(): return
    try:
        df = pd.read_csv(ARCHIVO_MAESTRO, sep=';', encoding='latin-1', dtype=str)
        df.columns = df.columns.str.strip()
        df = df.loc[:, ~df.columns.duplicated()]
        
        cedula_actual = variables["CEDULA"].get()
        anio_actual = str(datetime.now().year)

        # Actualizar el registro actual
        for c, v in variables.items():
            df.at[cur_idx, c] = v.get().upper().strip()

        # CONDICIÓN AGREGADA: Sincronización de TOTAL_DIAS_ANUAL
        mask_anual = (df['CEDULA'] == cedula_actual) & (df['FECHA_DE_INICIO'].str.contains(anio_actual, na=False))
        total_anual = df.loc[mask_anual, 'TIEMPO_EN_DIAS'].astype(float).sum()
        df.loc[mask_anual, 'TOTAL_DIAS_ANUAL'] = str(int(total_anual))

        df.to_csv(ARCHIVO_MAESTRO, index=False, sep=';', encoding='latin-1')
        messagebox.showinfo("SZ-LOJA", "Cambios guardados y acumulados anuales sincronizados.")
        buscar_historial()
    except Exception as e: messagebox.showerror("Error", str(e))

# --- 4. INTERFAZ GRÁFICA ---
root = tk.Tk()
root.title("SISTEMA MÉDICO INTEGRAL - SZ LOJA v16.1")
root.geometry("1100x950")

# Alertas
f_ale = tk.LabelFrame(root, text="Panel de Alertas Próximas (Solo Válidos)", bg="#fff9c4")
f_ale.pack(fill="x", padx=20, pady=5)
txt_ale = tk.Text(f_ale, height=5, font=("Arial", 9, "bold"), bg="#feffef")
txt_ale.insert("1.0", obtener_alertas_reincorporacion())
txt_ale.config(state="disabled")
txt_ale.pack(fill="x", padx=10, pady=5)

# Buscador
f_bus = tk.Frame(root, pady=10, bg="#e3f2fd")
f_bus.pack(fill="x")
tk.Label(f_bus, text="Búsqueda Exacta (Cédula/Nombres):", font=("Arial", 9, "bold"), bg="#e3f2fd").pack(side="left", padx=15)
entry_busqueda = tk.Entry(f_bus, font=("Arial", 11), width=45)
entry_busqueda.pack(side="left", padx=5)
tk.Button(f_bus, text="🔍 CONSULTAR", command=buscar_historial, bg="#0d47a1", fg="white").pack(side="left", padx=10)

# Historial
f_tree = tk.LabelFrame(root, text="Historial Cronológico de Descansos")
f_tree.pack(fill="x", padx=20, pady=5)
tree = ttk.Treeview(f_tree, columns=("F", "D", "P", "C"), show='headings', height=4)
for c, t in zip(["F", "D", "P", "C"], ["Inicio", "Días", "¿Presentó?", "Causa"]): tree.heading(c, text=t)
tree.pack(fill="x")
tree.bind("<<TreeviewSelect>>", cargar_en_ficha)

# Ficha Técnica
f_fm = tk.LabelFrame(root, text="Ficha de Gestión Institucional")
f_fm.pack(fill="both", expand=True, padx=20, pady=5)
can = tk.Canvas(f_fm); sb = ttk.Scrollbar(f_fm, orient="vertical", command=can.yview); f_sc = tk.Frame(can)
f_sc.bind("<Configure>", lambda e: can.configure(scrollregion=can.bbox("all")))
can.create_window((0,0), window=f_sc, anchor="nw", width=1050); can.configure(yscrollcommand=sb.set)

campos = [
    "GRADO", "NOMBRES", "CEDULA", "DESIGNACION", "TIPO_DE_PERMISO", "CAUSA", 
    "FECHA_DE_INICIO", "TIEMPO_EN_DIAS", "FECHA_DE_PRESENTACION", "DIAS_RESTANTES", 
    "TOTAL_DE_DIAS_DE_DESCANSO_MEDICO", "TOTAL_DIAS_ANUAL", "TOTAL_DE_DIAS_GENERAL", 
    "DR._QUE_EMITE", "DR._QUE_VALIDA", "OBSERVACION", "REGISTRO_SIIPNE", 
    "SUBZONAO_DISTRITO", "ESTADO_ACTUAL", "PRESENTACION"
]
variables = {c: tk.StringVar() for c in campos}
variables["FECHA_DE_INICIO"].trace_add("write", auto_calcular_relacion_fechas)
variables["TIEMPO_EN_DIAS"].trace_add("write", auto_calcular_relacion_fechas)

for i, c in enumerate(campos):
    r, col = divmod(i, 2)
    tk.Label(f_sc, text=c.replace('_', ' ') + ":", font=("Arial", 8, "bold")).grid(row=r, column=col*2, sticky="w", pady=3, padx=10)
    # Bloqueo de campos calculados para evitar error manual
    st = "readonly" if c in ["FECHA_DE_PRESENTACION", "DIAS_RESTANTES", "TOTAL_DIAS_ANUAL"] else "normal"
    tk.Entry(f_sc, textvariable=variables[c], width=45, state=st).grid(row=r, column=col*2+1, pady=3)

can.pack(side="left", fill="both", expand=True); sb.pack(side="right", fill="y")
lbl_status = tk.Label(root, text="SZ-LOJA v16.1 | Cálculos Dinámicos Activos", fg="blue")
lbl_status.pack()

# Botones
f_btns = tk.Frame(root, pady=15); f_btns.pack()
tk.Button(f_btns, text="🔄 ACTUALIZAR Y SINCRONIZAR", command=guardar_cambios, bg="#1976d2", fg="white", width=30, height=2).pack(side="left", padx=10)
tk.Button(f_btns, text="➕ CREAR NUEVO", command=lambda: messagebox.showinfo("SZ-LOJA", "Use los campos de arriba y guarde"), bg="#2e7d32", fg="white", width=25, height=2).pack(side="left", padx=10)

root.mainloop()
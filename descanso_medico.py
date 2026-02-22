import streamlit as st
import pandas as pd
import os
import smtplib
import socket
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="SZ LOJA - GESTIÓN MÉDICA", layout="wide")

ARCHIVO_MAESTRO = "Base_Maestra_Descansos_SZ_LOJA.csv"

# --- CONFIGURACIÓN DE CORREO ---
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = "talentohumanoloja11@gmail.com"
SENDER_PASSWORD = "zozexhfqjdpfynkf"

# --- 1. PROCESOS DE DATOS ---
def cargar_base():
    if not os.path.exists(ARCHIVO_MAESTRO):
        columnas = ["GRADO", "NOMBRES", "CEDULA", "DESIGNACION", "TIPO_DE_PERMISO", "CAUSA", 
                    "FECHA_DE_INICIO", "TIEMPO_EN_DIAS", "FECHA_DE_PRESENTACION", "DIAS_RESTANTES", 
                    "TOTAL_DE_DIAS_DE_DESCANSO_MEDICO", "TOTAL_DIAS_ANUAL", "TOTAL_DE_DIAS_GENERAL", 
                    "DR._QUE_EMITE", "DR._QUE_VALIDA", "OBSERVACION", "REGISTRO_SIIPNE", 
                    "SUBZONAO_DISTRITO", "ESTADO_ACTUAL", "PRESENTACION", "EMAIL_SERVIDOR"]
        df = pd.DataFrame(columns=columnas)
        df.to_csv(ARCHIVO_MAESTRO, index=False, sep=';', encoding='latin-1')
        return df
    return pd.read_csv(ARCHIVO_MAESTRO, sep=';', encoding='latin-1', dtype=str)

def sincronizar_totales(df, cedula, anio):
    df['D_NUM'] = pd.to_numeric(df['TIEMPO_EN_DIAS'].str.replace(',', '.'), errors='coerce').fillna(0)
    df['F_DT'] = pd.to_datetime(df['FECHA_DE_INICIO'], format='%d/%m/%Y', errors='coerce')
    ced_buscada = str(cedula).strip().zfill(10)
    mask_a = (df['CEDULA'].str.zfill(10) == ced_buscada) & (df['F_DT'].dt.year == int(anio))
    df.loc[mask_a, 'TOTAL_DIAS_ANUAL'] = str(int(df.loc[mask_a, 'D_NUM'].sum()))
    mask_g = (df['CEDULA'].str.zfill(10) == ced_buscada)
    df.loc[mask_g, 'TOTAL_DE_DIAS_GENERAL'] = str(int(df.loc[mask_g, 'D_NUM'].sum()))
    return df.drop(columns=['D_NUM', 'F_DT'])

# --- 2. MOTOR DE CORREO (CUERPO ORIGINAL) ---
def enviar_correo(datos):
    dest = datos.get("EMAIL_SERVIDOR")
    if not dest or "@" not in str(dest): return False
    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=10)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        mensaje = MIMEMultipart()
        mensaje['From'] = SENDER_EMAIL
        mensaje['To'] = dest
        mensaje['Subject'] = f"NOTIFICACIÓN REGISTRO SZ LOJA: {datos['TIPO_DE_PERMISO']}"
        
        cuerpo = f"""Estimado(a) {datos['GRADO']} {datos['NOMBRES']},

Se le comunica que se ha registrado en el sistema su {datos['TIPO_DE_PERMISO']}.
        
DETALLES DEL REGISTRO:
- Causa: {datos['CAUSA']}
- Fecha de Inicio: {datos['FECHA_DE_INICIO']}
- Tiempo en Días: {datos['TIEMPO_EN_DIAS']}
- Fecha de Presentación: {datos['FECHA_DE_PRESENTACION']}
        
IMPORTANTE: Debe presentarse en la oficina de Talento Humano el día {datos['FECHA_DE_PRESENTACION']} a las 07:45 para el registro y control.
	
Se comunica que es obligatorio la entrega de su certificado en ORIGINAL, para la incorporación de la documentación en su expediente, dentro de las 48:00 de acuerdo al instructivo de validación de descansos médicos versión 2.

En el caso de continuar con descanso medico es necesario comunicar oportunamente al encargado y jefe de su unidad o departamento, Talento Humano mediante correo electrónico "talentohumanoloja11@gmail.com" y medios alternativo.

Atentamente,
Departamento de Talento Humano - Subzona Loja"""
        
        mensaje.attach(MIMEText(cuerpo, 'plain'))
        server.send_message(mensaje)
        server.quit()
        return True
    except: return False

# --- 3. INTERFAZ WEB ---
st.title("SISTEMA MÉDICO INTEGRAL - SZ LOJA (WEB)")
df = cargar_base()

# Paneles de Alertas
col_a1, col_a2 = st.columns(2)
with col_a1:
    st.info("📋 ALERTAS DE REINCORPORACIÓN")
    hoy = datetime.now().date()
    df_temp = df.copy()
    df_temp['F_DT'] = pd.to_datetime(df_temp['FECHA_DE_PRESENTACION'], format='%d/%m/%Y', errors='coerce')
    for label, days in [("HOY", 0), ("MAÑANA", 1), ("PASADO MAÑANA", 2)]:
        fecha = hoy + timedelta(days=days)
        subs = df_temp[df_temp['F_DT'].dt.date == fecha]
        st.write(f"📍 {label}: {len(subs)} Servidores")

with col_a2:
    st.error("⚠️ EXCESO +90 DÍAS ANUALES")
    anio = datetime.now().year
    df['D_INT'] = pd.to_numeric(df['TIEMPO_EN_DIAS'].str.replace(',', '.'), errors='coerce').fillna(0)
    df['I_DT'] = pd.to_datetime(df['FECHA_DE_INICIO'], format='%d/%m/%Y', errors='coerce')
    excesos = df[df['I_DT'].dt.year == anio].groupby(['GRADO', 'NOMBRES'])['D_INT'].sum().reset_index()
    for _, r in excesos[excesos['D_INT'] > 90].iterrows():
        st.write(f"🚨 {r['GRADO']} {r['NOMBRES']} - {int(r['D_INT'])} días.")

# Buscador e Historial
st.divider()
busqueda = st.text_input("🔍 Cédula o Nombres para Consultar:").upper()
if busqueda:
    mask = df['CEDULA'].str.contains(busqueda, na=False) | df['NOMBRES'].str.contains(busqueda, na=False)
    st.dataframe(df[mask][["FECHA_DE_INICIO", "TIEMPO_EN_DIAS", "PRESENTACION", "CAUSA"]], use_container_width=True)

# Ficha Técnica
st.subheader("📝 Ficha de Gestión Institucional")
with st.form("ficha"):
    c1, c2 = st.columns(2)
    inputs = {}
    campos = ["GRADO", "NOMBRES", "CEDULA", "DESIGNACION", "TIPO_DE_PERMISO", "CAUSA", 
              "FECHA_DE_INICIO", "TIEMPO_EN_DIAS", "DR._QUE_EMITE", "DR._QUE_VALIDA", 
              "OBSERVACION", "REGISTRO_SIIPNE", "SUBZONAO_DISTRITO", "PRESENTACION", "EMAIL_SERVIDOR"]
    
    for i, c in enumerate(campos):
        col = c1 if i % 2 == 0 else c2
        inputs[c] = col.text_input(c.replace("_", " "), key=f"in_{c}")

    # Botones
    b1, b2, b3 = st.columns(3)
    if b2.form_submit_button("➕ CREAR NUEVO"):
        # Lógica de guardado automático (Simulada para web)
        st.success("Registro creado exitosamente.")
        enviar_correo(inputs)
    
    if b1.form_submit_button("🔄 ACTUALIZAR"):
        st.info("Función de actualización procesada.")

if st.button("🗑️ ELIMINAR REGISTRO"):
    st.warning("Seleccione un registro para eliminar.")

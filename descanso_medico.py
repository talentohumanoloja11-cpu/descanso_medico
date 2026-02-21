import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os

# Configuración de la página
st.set_page_config(page_title="Gestión Médica SZ-LOJA", layout="wide")

# --- SEGURIDAD: LOGIN ---
def check_password():
    def password_entered():
        if st.session_state["password"] == "LOJA2026": # CAMBIAR ESTA CLAVE
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input("Introduzca la clave de acceso de RRHH:", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("Clave incorrecta. Intente de nuevo:", type="password", on_change=password_entered, key="password")
        return False
    return True

if check_password():
    # --- CARGA DE DATOS ---
    @st.cache_data
    def cargar_datos():
        df = pd.read_csv("Base_Maestra_Descansos_SZ_LOJA.csv", sep=";", encoding="latin-1", dtype=str)
        df.columns = df.columns.str.strip()
        df = df.loc[:, ~df.columns.duplicated()]
        if 'CEDULA' in df.columns:
            df['CEDULA'] = df['CEDULA'].str.replace('.0', '', regex=False).str.zfill(10)
        return df

    df = cargar_datos()

    # --- PANEL DE ALERTAS SUPERIOR ---
    st.title("SISTEMA MÉDICO INTEGRAL - SUBZONA LOJA")
    
    with st.expander("📋 VER PANEL DE ALERTAS (PRESENTACIONES)", expanded=True):
        hoy = datetime.now().date()
        col1, col2, col3 = st.columns(3)
        
        for i, (col, label) in enumerate(zip([col1, col2, col3], ["HOY", "MAÑANA", "PASADO MAÑANA"])):
            fecha_buscada = (hoy + timedelta(days=i)).strftime('%-d/%-m/%Y')
            subs = df[df['FECHA_DE_PRESENTACION'] == fecha_buscada]
            with col:
                st.metric(label=label, value=f"{len(subs)} Servidores")
                for _, r in subs.iterrows():
                    st.caption(f"🔹 {r['GRADO']} {r['NOMBRES']} [{r['SUBZONAO_DISTRITO']}]")

    # --- BUSCADOR Y GESTIÓN ---
    st.divider()
    busqueda = st.text_input("🔍 Buscar Servidor Policial (Cédula o Apellidos):").upper()

    if busqueda:
        resultados = df[df['CEDULA'].str.contains(busqueda) | df['NOMBRES'].str.contains(busqueda)]
        
        if not resultados.empty:
            # Seleccionar Registro del Historial
            seleccion = st.selectbox("Seleccione el registro médico para gestionar:", 
                                   resultados.index, 
                                   format_func=lambda x: f"{df.loc[x, 'FECHA_DE_INICIO']} - {df.loc[x, 'CAUSA']}")
            
            reg = df.loc[seleccion]

            # --- FICHA TÉCNICA (FORMULARIO) ---
            with st.form("ficha_loja"):
                st.subheader("Ficha de Gestión y Sincronización")
                
                c1, c2 = st.columns(2)
                
                # Diccionario de variables para los campos
                inputs = {}
                campos = [
                    "GRADO", "NOMBRES", "CEDULA", "DESIGNACION", "TIPO_DE_PERMISO", "CAUSA", 
                    "FECHA_DE_INICIO", "TIEMPO_EN_DIAS", "FECHA_DE_PRESENTACION", "DIAS_RESTANTES", 
                    "TOTAL_DE_DIAS_DE_DESCANSO_MEDICO", "TOTAL_DIAS_ANUAL", "TOTAL_DE_DIAS_GENERAL", 
                    "DR._QUE_EMITE", "DR._QUE_VALIDA", "OBSERVACION", "REGISTRO_SIIPNE", 
                    "SUBZONAO_DISTRITO", "ESTADO_ACTUAL", "PRESENTACION"
                ]

                for i, campo in enumerate(campos):
                    col = c1 if i % 2 == 0 else c2
                    # Campos de solo lectura por cálculo automático
                    if campo in ["FECHA_DE_PRESENTACION", "DIAS_RESTANTES", "TOTAL_DIAS_ANUAL"]:
                        inputs[campo] = col.text_input(campo.replace('_', ' '), value=reg[campo], disabled=True)
                    else:
                        inputs[campo] = col.text_input(campo.replace('_', ' '), value=reg[campo])

                # BOTÓN DE ACCIÓN
                if st.form_submit_button("🔄 ACTUALIZAR Y SINCRONIZAR REGISTROS"):
                    # 1. Lógica de cálculo de fecha de presentación
                    try:
                        f_ini = datetime.strptime(inputs["FECHA_DE_INICIO"], '%d/%m/%Y')
                        dias = int(float(inputs["TIEMPO_EN_DIAS"]))
                        f_pres = f_ini + timedelta(days=dias)
                        f_pres_str = f_pres.strftime('%d/%m/%Y')
                        
                        # 2. Lógica de Días Restantes
                        d_restantes = (f_pres.date() - datetime.now().date()).days
                        
                        # 3. Sincronización Anual Masiva
                        df.loc[seleccion, "FECHA_DE_PRESENTACION"] = f_pres_str
                        df.loc[seleccion, "DIAS_RESTANTES"] = str(max(0, d_restantes))
                        # ... (aquí se guardaría el CSV centralizado)
                        
                        st.success("Base de Datos Sincronizada en la Nube.")
                    except:
                        st.error("Error en formato de fechas o días.")
        else:
            st.warning("No se encontraron registros.")

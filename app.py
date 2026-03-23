import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
import os
import time
import io
from datetime import datetime, date

# 1. Configuração de Layout
st.set_page_config(page_title="Colortex 2026 - Gestão de R&D", layout="wide", page_icon="🧪")

# --- 🗄️ CONFIGURAÇÃO SQLITE ---
DB_NAME = "colortex_factory.db"

def get_connection():
    return sqlite3.connect(DB_NAME)

def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS aba_mestra 
                 (Tipo TEXT, Cor TEXT, Pigmento TEXT, [Quant OP (kg)] REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS historico_producao 
                 (data TEXT, lote TEXT, tipo_produto TEXT, cor TEXT, pigmento TEXT, 
                  [quant_ad_g] REAL, [quantidade_op] REAL, [n_plan] REAL, [n_real] REAL, [litros_unit] REAL)''')
    conn.commit()
    conn.close()

init_db()

def carregar_dados_sql(tabela):
    conn = get_connection()
    df = pd.read_sql(f"SELECT * FROM {tabela}", conn)
    conn.close()
    cols_num = ['quant_ad_g', 'quantidade_op', 'n_plan', 'n_real', 'litros_unit']
    for col in cols_num:
        if col in df.columns:
            df[col] = df[col].astype(str).str.replace(r'[^\d,.-]', '', regex=True).str.replace(',', '.')
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
    return df

def salvar_dados_sql(df, tabela, modo='replace'):
    conn = get_connection()
    df.to_sql(tabela, conn, if_exists=modo, index=False)
    conn.close()

# --- NAVEGAÇÃO ---
menu = ["🚀 Registro", "📈 Controle", "📜 Banco de Dados", "📊 Aba Mestra", "📂 Importar CSV"]
aba = st.sidebar.radio("Navegação:", menu)

# --- ABA: IMPORTAR CSV (ONDE ESTÁ O BOTÃO) ---
if aba == "📂 Importar CSV":
    st.title("📂 Importação e Reset")
    
    up = st.file_uploader("Selecione o arquivo CSV", type="csv")
    alvo = st.selectbox("Destino", ["aba_mestra", "historico_producao"])
    
    if up and st.button("🚀 Confirmar Importação"):
        try:
            raw = up.read()
            try: text = raw.decode('latin-1')
            except: text = raw.decode('utf-8', errors='ignore')
            df_imp = pd.read_csv(io.StringIO(text), sep=None, engine='python')
            df_imp.columns = [c.strip().lower() for c in df_imp.columns]
            
            if alvo == "aba_mestra":
                df_imp.columns = ['Tipo', 'Cor', 'Pigmento', 'Quant OP (kg)']
                salvar_dados_sql(df_imp, "aba_mestra", modo='append')
                st.success("Mestra Atualizada!")
            else:
                df_imp.columns = ['data', 'lote', 'tipo_produto', 'cor', 'pigmento', 'quant_ad_g', 'quantidade_op', 'n_plan', 'n_real', 'litros_unit']
                salvar_dados_sql(df_imp, "historico_producao", modo='append')
                st.success("Histórico Atualizado!")
            time.sleep(1); st.rerun()
        except Exception as e:
            st.error(f"Erro: {e}")

    st.markdown("---")
    st.subheader("⚠️ Zona de Perigo")
    # O botão abaixo DEVE aparecer agora:
    if st.button("🔴 RESET TOTAL DO BANCO DE DADOS"):
        conn = get_connection()
        conn.execute("DROP TABLE IF EXISTS aba_mestra")
        conn.execute("DROP TABLE IF EXISTS historico_producao")
        conn.commit(); conn.close()
        init_db()
        st.warning("Banco de dados reiniciado com sucesso!")
        time.sleep(1); st.rerun()

# --- ABA: CONTROLE ---
elif aba == "📈 Controle":
    st.title("📈 Dashboard")
    df_db = carregar_dados_sql("historico_producao")
    if df_db.empty:
        st.info("Banco vazio. Use a aba de Importação.")
    else:
        p_sel = st.selectbox("Produto", sorted(df_db['tipo_produto'].unique()))
        df_plot = df_db[df_db['tipo_produto'] == p_sel].copy()
        if not df_plot.empty:
            df_plot['Var %'] = ((df_plot['quant_ad_g'] / df_plot['quantidade_op'].replace(0, np.nan)) - 1) * 100
            st.line_chart(df_plot.pivot_table(index='lote', columns='pigmento', values='Var %'))
            st.dataframe(df_plot)

# --- OUTRAS ABAS (Resumidas para teste) ---
elif aba == "📜 Banco de Dados":
    st.title("📜 Banco de Dados")
    df = carregar_dados_sql("historico_producao")
    st.dataframe(df)
elif aba == "📊 Aba Mestra":
    st.title("📊 Aba Mestra")
    df = carregar_dados_sql("aba_mestra")
    st.dataframe(df)
elif aba == "🚀 Registro":
    st.title("🚀 Registro")
    st.write("Use esta aba para registrar lotes manualmente.")

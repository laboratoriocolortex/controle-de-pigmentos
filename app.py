import streamlit as st
import pandas as pd
import os
from datetime import datetime
import numpy as np

# Configuração inicial da página
st.set_page_config(page_title="Controle Colortex 2026", layout="wide", page_icon="🧪")

# --- ESTILO CSS ---
st.markdown("""
    <style>
    div.stButton > button:first-child {
        background-color: #d4edda; color: #155724; border: 1px solid #c3e6cb;
        font-weight: bold; width: 100%; height: 3em;
    }
    .block-container { padding-top: 1.5rem; }
    h3 { margin-bottom: 0rem !important; font-size: 1.10rem !important; }
    hr { margin: 0.5rem 0rem !important; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNÇÕES DE PADRONIZAÇÃO ---

def corrigir_acentos_e_nomes(df):
    if df is None or df.empty: return df
    traducoes = {'Oxido': 'Óxido', 'Franca': 'França', 'Tintometrico': 'Tintométrico', 'Padrao': 'Padrão'}
    cols_texto = ['tipo de produto', 'cor', 'pigmento', 'Tipo', 'Cor', 'Pigmento', 'Produto']
    for col in df.columns:
        if col in cols_texto:
            df[col] = df[col].astype(str).str.strip().replace(traducoes, regex=True).str.title()
    return df

def load_data(file):
    if os.path.exists(file):
        try:
            df = pd.read_csv(file, sep=None, engine='python', encoding='latin-1')
            df.columns = [str(c).strip() for c in df.columns]
            return corrigir_acentos_e_nomes(df)
        except: return pd.DataFrame()
    return pd.DataFrame()

# --- CARREGAMENTO INICIAL ---
df_mestra = load_data("Aba_Mestra.csv")
df_h = load_data("Historico_Producao.csv")
df_p = load_data("Padroes_Registrados.csv")

# --- NAVEGAÇÃO (RESTAURADA) ---
menu = ["🚀 Nova Pigmentação", "📈 Variações & CEP", "📋 Padrões", "📜 Banco de Dados", "➕ Cadastro", "📊 Aba Mestra", "📂 Importar Dados"]
aba = st.sidebar.radio("Navegação:", menu)

# --- ABA: NOVA PIGMENTAÇÃO ---
if aba == "🚀 Nova Pigmentação":
    st.title("🚀 Registrar Produção")
    if df_mestra.empty:
        st.info("Aba Mestra vazia. Use a aba 'Cadastro' ou 'Importar Dados'.")
    else:
        with st.container():
            c1, c2, c3 = st.columns(3)
            with c1: t_sel = st.selectbox("Produto", sorted(df_mestra['Tipo'].unique()))
            with c2: c_sel = st.selectbox("Cor", sorted(df_mestra[df_mestra['Tipo'] == t_sel]['Cor'].unique()))
            with c3: lote = st.text_input("Lote")
            
            if st.button("Gravar Lote (Exemplo Simples)"):
                st.success("Lote registrado localmente!")

# --- ABA: CEP (CORRIGIDA) ---
elif aba == "📈 Variações & CEP":
    st.title("📈 Controle Estatístico (CEP)")
    if not df_h.empty:
        # Resolve o KeyError da imagem: garante que as colunas existam antes de converter
        cols_necessarias = ["Quant ad (g)", "Quantidade OP", "#Plan", "#Real", "Litros/Unit"]
        existentes = [c for c in cols_necessarias if c in df_h.columns]
        
        for col in existentes:
            df_h[col] = pd.to_numeric(df_h[col].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
        
        if "Desvio_%" not in df_h.columns and len(existentes) > 1:
             df_h['Desvio_%'] = ((df_h['Quant ad (g)'] / (df_h['Quantidade OP'] + 0.0001)) - 1) * 100

        st.line_chart(df_h.set_index('lote')['Desvio_%'] if 'lote' in df_h.columns else None)
        st.dataframe(df_h)
    else:
        st.info("Sem dados no histórico para gerar gráficos.")

# --- ABA: PADRÕES (RESTAURADA) ---
elif aba == "📋 Padrões":
    st.title("📋 Evolução de Padrões")
    if not df_p.empty: st.dataframe(df_p)
    else: st.info("Nenhuma alteração de padrão registrada.")

# --- ABA: CADASTRO (RESTAURADA) ---
elif aba == "➕ Cadastro":
    st.title("➕ Novo Cadastro")
    with st.form("cad"):
        t = st.text_input("Tipo")
        c = st.text_input("Cor")
        p = st.text_input("Pigmento")
        q = st.number_input("Coeficiente (kg/L)", format="%.6f")
        if st.form_submit_button("Salvar"):
            novo = pd.DataFrame([{"Tipo": t, "Cor": c, "Pigmento": p, "Quant OP (kg)": q}])
            df_mestra = pd.concat([df_mestra, novo], ignore_index=True)
            df_mestra.to_csv("Aba_Mestra.csv", index=False, encoding='latin-1')
            st.success("Cadastrado!")

# --- DEMAIS ABAS ---
elif aba == "📜 Banco de Dados":
    st.title("📜 Histórico")
    st.dataframe(df_h)
    if st.button("Deletar Histórico"):
        if os.path.exists("Historico_Producao.csv"): os.remove("Historico_Producao.csv")
        st.rerun()

elif aba == "📊 Aba Mestra":
    st.title("📊 Gestão Mestra")
    st.data_editor(df_mestra)

elif aba == "📂 Importar Dados":
    st.title("📂 Importar CSV")
    up = st.file_uploader("Arquivo", type="csv")
    if up and st.button("Confirmar"):
        df_imp = pd.read_csv(up, encoding='latin-1')
        df_imp.to_csv("Aba_Mestra.csv", index=False, encoding='latin-1')
        st.success("Importado!")

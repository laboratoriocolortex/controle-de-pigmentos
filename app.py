import streamlit as st
import pandas as pd
import os
import numpy as np
from datetime import datetime

st.set_page_config(page_title="Controle 2026", layout="wide")

# --- FUNÇÃO DE CARGA SEGURA ---
def load_csv(file, sep=';'):
    if os.path.exists(file):
        try:
            return pd.read_csv(file, sep=sep, encoding='latin-1')
        except:
            return pd.DataFrame()
    return pd.DataFrame()

# --- ABA DE VARIABILIDADE (VERSÃO ULTRA-LEVE) ---
def aba_variabilidade():
    st.title("📈 Variabilidade de Produção")
    
    df = load_csv("Historico_Producao.csv")
    
    if df.empty:
        st.info("Nenhum dado encontrado no Histórico.")
        return

    try:
        # Limpeza rápida
        for c in ["Quant ad (g)", "Quantidade OP", "#Plan", "#Real", "Litros/Unit"]:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
        
        # Preenchimento de Lote
        df['#Real'] = df['#Real'].replace(0, np.nan).ffill()
        df['#Plan'] = df['#Plan'].replace(0, np.nan).ffill()
        df['Litros/Unit'] = df['Litros/Unit'].replace(0, np.nan).ffill()
        
        # Cálculo de Desvio
        df['Vol_Real'] = df['#Real'] * df['Litros/Unit']
        df['Vol_Plan'] = df['#Plan'] * df['Litros/Unit']
        
        df = df[df['Vol_Real'] > 0].copy()
        df['Desvio_%'] = (( (df['Quant ad (g)']/df['Vol_Real']) / (df['Quantidade OP']/(df['Vol_Plan']+0.0001)) ) - 1) * 100

        # Filtros
        prod = st.selectbox("Produto", df['tipo de produto'].unique())
        df_f = df[df['tipo de produto'] == prod]

        # Gráfico Nativo (Mais estável que Plotly para testes)
        st.subheader("Gráfico de Desvios (%)")
        chart_data = df_f.pivot_table(index='data', columns='pigmento', values='Desvio_%')
        st.line_chart(chart_data)
        
        st.dataframe(df_f[['data', 'lote', 'pigmento', 'Desvio_%']])
    except Exception as e:
        st.error(f"Erro no processamento: {e}")

# --- MENU ---
aba = st.sidebar.radio("Menu", ["Nova Pigmentação", "Variações"])

if aba == "Nova Pigmentação":
    st.title("🚀 Registro")
    st.write("O sistema de registro está pronto. Preencha os campos abaixo.")
    # (Seu código de registro aqui)
    
elif aba == "Variações":
    aba_variabilidade()

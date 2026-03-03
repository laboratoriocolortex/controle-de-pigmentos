import streamlit as st
import pandas as pd
import os
from datetime import datetime
import plotly.express as px
import numpy as np

st.set_page_config(page_title="Controle 2026", layout="wide", page_icon="🧪")

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

# --- FUNÇÕES DE CARGA ---
def load_data(file):
    if os.path.exists(file):
        try:
            df = pd.read_csv(file, sep=None, engine='python', encoding='latin-1')
            df.columns = [str(c).strip() for c in df.columns]
            return df
        except:
            return pd.DataFrame()
    return pd.DataFrame()

# --- ABA DE VARIAÇÕES (REVISADA) ---
def renderizar_aba_variacoes():
    st.title("📈 Análise de Variabilidade e CEP")
    
    if not os.path.exists("Historico_Producao.csv"):
        st.info("Aguardando o primeiro registro de produção para gerar análises.")
        return

    try:
        df_hist = pd.read_csv("Historico_Producao.csv", sep=';', encoding='latin-1')
        
        if df_hist.empty:
            st.warning("O arquivo de histórico está vazio.")
            return

        # Limpeza e Conversão de dados
        cols_num = ["Quant ad (g)", "Quantidade OP", "#Plan", "#Real", "Litros/Unit"]
        for col in cols_num:
            if col in df_hist.columns:
                df_hist[col] = df_hist[col].astype(str).str.replace(',', '.')
                df_hist[col] = pd.to_numeric(df_hist[col], errors='coerce').fillna(0)

        # Técnica para preencher os dados do lote (Unidades e Volume) em todas as linhas
        # Substituímos zeros por NaN para o ffill (forward fill) funcionar
        df_hist['#Real'] = df_hist['#Real'].replace(0, np.nan).ffill()
        df_hist['#Plan'] = df_hist['#Plan'].replace(0, np.nan).ffill()
        df_hist['Litros/Unit'] = df_hist['Litros/Unit'].replace(0, np.nan).ffill()

        # Cálculos Base
        df_hist['Vol_Real_L'] = df_hist['#Real'] * df_hist['Litros/Unit']
        df_hist['Vol_Plan_L'] = df_hist['#Plan'] * df_hist['Litros/Unit']
        
        # Filtro para evitar divisão por zero
        df_hist = df_hist[(df_hist['Vol_Real_L'] > 0) & (df_hist['Vol_Plan_L'] > 0)].copy()

        if df_hist.empty:
            st.error("Dados de volume (#Plan ou #Real) estão zerados no histórico.")
            return

        df_hist['g_L_Esperado'] = df_hist['Quantidade OP'] / df_hist['Vol_Plan_L']
        df_hist['g_L_Real'] = df_hist['Quant ad (g)'] / df_hist['Vol_Real_L']
        df_hist['Variacao_%'] = ((df_hist['g_L_Real'] / df_hist['g_L_Esperado']) - 1) * 100

        # Seleção de Filtros
        st.subheader("🔍 Filtro de Produto")
        c1, c2 = st.columns(2)
        with c1:
            prod_list = sorted(df_hist['tipo de produto'].unique())
            prod_sel = st.selectbox("Produto", prod_list)
        with c2:
            cor_list = sorted(df_hist[df_hist['tipo de produto'] == prod_sel]['cor'].unique())
            cor_sel = st.selectbox("Cor", cor_list)

        df_f = df_hist[(df_hist['tipo de produto'] == prod_sel) & (df_hist['cor'] == cor_sel)].copy()

        if not df_f.empty:
            # Estatísticas
            avg_dev = df_f['Variacao_%'].mean()
            std_dev = df_f['Variacao_%'].std()
            
            m1, m2, m3 = st.columns(3)
            m1.metric("Desvio Médio", f"{avg_dev:.2f}%")
            m2.metric("Estabilidade (DP)", f"{std_dev:.2f}%")
            m3.metric("Lotes Analisados", len(df_f['lote'].unique()))

            # Gráfico Plotly
            fig = px.line(df_f, x="data", y="Variacao_%", color="pigmento", markers=True,
                          title=f"Tendência de Desvios: {prod_sel} - {cor_sel}")
            fig.add_hline(y=0, line_dash="dash", line_color="green")
            st.plotly_chart(fig, use_container_width=True)

            st.write("📋 Detalhes dos Lotes")
            st.dataframe(df_f[["data", "lote", "pigmento", "Quant ad (g)", "Variacao_%"]], use_container_width=True)
            
    except Exception as e:
        st.error(f"Erro ao processar a aba de variações: {e}")

# --- NAVEGAÇÃO ---
df_mestra = load_data("Aba_Mestra.csv")
menu = ["🚀 Nova Pigmentação", "📈 Variações & CEP", "📋 Padrões", "📜 Banco de Dados", "➕ Cadastro", "📊 Aba Mestra"]
aba = st.sidebar.radio("Navegação:", menu)

if aba == "🚀 Nova Pigmentação":
    st.title("🚀 Registrar Produção")
    # ... código de registro (mantenha o que você já tem funcionando) ...
    st.write("Funcionalidade de registro ativa.")

elif aba == "📈 Variações & CEP":
    renderizar_aba_variacoes()

elif aba == "📋 Padrões":
    st.title("📋 Evolução de Padrões Técnicos")
    if os.path.exists("Padroes_Registrados.csv"):
        df_p = pd.read_csv("Padroes_Registrados.csv", sep=';', encoding='latin-1')
        st.dataframe(df_p.style.format({"Novo Coef (kg/L)": "{:.6f}"}), use_container_width=True)

elif aba == "📜 Banco de Dados":
    st.title("📜 Histórico Geral")
    if os.path.exists("Historico_Producao.csv"):
        df_hist_view = pd.read_csv("Historico_Producao.csv", sep=';', encoding='latin-1')
        st.dataframe(df_hist_view, use_container_width=True)

# ... demais abas ...

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
    .metric-card { background-color: #f8f9fa; padding: 15px; border-radius: 10px; border-left: 5px solid #28a745; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNÇÕES AUXILIARES ---
def format_num_padrao(valor, casas=2):
    if valor is None or valor == "": return ""
    try:
        val_float = float(valor)
        return f"{val_float:.{casas}f}"
    except:
        return str(valor)

def load_data(file):
    if os.path.exists(file):
        try:
            df = pd.read_csv(file, sep=None, engine='python', encoding='latin-1')
            df.columns = [str(c).strip() for c in df.columns]
            return df
        except:
            return pd.DataFrame()
    return pd.DataFrame()

# --- LÓGICA DA ABA DE VARIAÇÕES ---
def renderizar_aba_variacoes():
    st.title("⚠️ Análise de Variabilidade e Confiabilidade")
    
    if not os.path.exists("Historico_Producao.csv"):
        st.info("Aguardando dados de produção para análise.")
        return

    # Carregar e preparar dados
    df_hist = pd.read_csv("Historico_Producao.csv", sep=';', encoding='latin-1')
    
    for col in ["Quant ad (g)", "Quantidade OP", "#Plan", "#Real", "Litros/Unit"]:
        df_hist[col] = df_hist[col].astype(str).str.replace(',', '.')
        df_hist[col] = pd.to_numeric(df_hist[col], errors='coerce').fillna(0)

    # Preencher dados do cabeçalho do lote
    df_hist['#Real'] = df_hist['#Real'].replace(0, method='ffill')
    df_hist['#Plan'] = df_hist['#Plan'].replace(0, method='ffill')
    df_hist['Litros/Unit'] = df_hist['Litros/Unit'].replace(0, method='ffill')

    # Cálculos de Volume e Concentração
    df_hist['Vol_Real_L'] = df_hist['#Real'] * df_hist['Litros/Unit']
    df_hist['Vol_Plan_L'] = df_hist['#Plan'] * df_hist['Litros/Unit']
    
    # Evitar divisões por zero
    df_hist = df_hist[(df_hist['Vol_Real_L'] > 0) & (df_hist['Vol_Plan_L'] > 0)].copy()
    
    df_hist['g_L_Esperado'] = df_hist['Quantidade OP'] / df_hist['Vol_Plan_L']
    df_hist['g_L_Real'] = df_hist['Quant ad (g)'] / df_hist['Vol_Real_L']
    df_hist['Variacao_%'] = ((df_hist['g_L_Real'] / df_hist['g_L_Esperado']) - 1) * 100

    # --- FILTROS ---
    st.subheader("🔍 Filtro por Produto/Cor")
    c1, c2 = st.columns(2)
    with c1: prod_sel = st.selectbox("Produto", df_hist['tipo de produto'].unique())
    with c2: cor_sel = st.selectbox("Cor", df_hist[df_hist['tipo de produto'] == prod_sel]['cor'].unique())

    df_f = df_hist[(df_hist['tipo de produto'] == prod_sel) & (df_hist['cor'] == cor_sel)].copy()

    if not df_f.empty:
        # --- RESUMO ESTATÍSTICO ---
        st.markdown("---")
        avg_dev = df_f['Variacao_%'].mean()
        std_dev = df_f['Variacao_%'].std()
        confiabilidade = 100 - abs(avg_dev) # Métrica simples de precisão da fórmula

        m1, m2, m3 = st.columns(3)
        with m1:
            st.metric("Desvio Médio", f"{avg_dev:.2f}%", help="Se positivo, o padrão está baixo. Se negativo, o padrão está alto.")
        with m2:
            status = "Fórmula Estável" if std_dev < 5 else "Fórmula Instável"
            st.metric("Estabilidade (DP)", f"{std_dev:.2f}%", delta=status, delta_color="inverse")
        with m3:
            st.metric("Índice de Confiabilidade", f"{confiabilidade:.1f}%")

        # --- GRÁFICO DE LINHA DO TEMPO (VARIABILIDADE) ---
        fig = px.line(df_f, x="data", y="Variacao_%", color="pigmento", 
                      markers=True, title=f"Histórico de Desvios: {prod_sel} - {cor_sel}")
        fig.add_hline(y=0, line_dash="dash", line_color="green", annotation_text="Padrão")
        fig.add_hline(y=5, line_dash="dot", line_color="orange")
        fig.add_hline(y=-5, line_dash="dot", line_color="orange")
        st.plotly_chart(fig, use_container_width=True)

        # --- TABELA DE HISTÓRICO ---
        st.write("📋 Detalhes dos Lotes")
        st.dataframe(
            df_f[["data", "lote", "pigmento", "Quant ad (g)", "Variacao_%"]]
            .style.format({"Variacao_%": "{:.2f}%"})
            .applymap(lambda x: 'background-color: #ffcccc' if abs(x) > 10 else '', subset=['Variacao_%']),
            use_container_width=True
        )
    else:
        st.warning("Sem dados históricos suficientes para este filtro.")

# --- NAVEGAÇÃO PRINCIPAL ---
aba = st.sidebar.radio("Navegação:", ["🚀 Nova Pigmentação", "📈 Variações & CEP", "📋 Padrões", "📜 Banco de Dados", "➕ Cadastro", "📊 Aba Mestra"])

if aba == "🚀 Nova Pigmentação":
    # (O código aqui permanece o mesmo da versão anterior, com registro de lote)
    st.title("🚀 Registrar Produção")
    # ... código de registro ...
    
elif aba == "📈 Variações & CEP":
    renderizar_aba_variacoes()

elif aba == "📋 Padrões":
    st.title("📋 Evolução de Padrões Técnicos")
    if os.path.exists("Padroes_Registrados.csv"):
        df_p = pd.read_csv("Padroes_Registrados.csv", sep=';', encoding='latin-1')
        st.dataframe(df_p.style.format({"Novo Coef (kg/L)": "{:.6f}"}), use_container_width=True)
    else: st.info("Sem padrões registrados.")

# (Demais abas permanecem como antes)

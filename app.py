import streamlit as st
import pandas as pd
import os
import numpy as np
from datetime import datetime

# Configuração inicial (DEVE ser a primeira linha de código)
st.set_page_config(page_title="Controle 2026", layout="wide", page_icon="🧪")

# --- ESTILO CSS ---
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    div.stButton > button:first-child {
        background-color: #d4edda; color: #155724; border: 1px solid #c3e6cb;
        font-weight: bold; width: 100%; height: 3em;
    }
    </style>
    """, unsafe_allow_html=True)

# --- FUNÇÃO DE CARGA COM TRATAMENTO DE ERRO ---
def carregar_dados(caminho, sep=';'):
    if not os.path.exists(caminho):
        return pd.DataFrame()
    try:
        df = pd.read_csv(caminho, sep=sep, encoding='latin-1', on_bad_lines='skip')
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"Erro ao ler {caminho}: {e}")
        return pd.DataFrame()

# --- ABA DE VARIABILIDADE ---
def aba_variabilidade():
    st.title("📈 Análise de Variabilidade (CEP)")
    
    df = carregar_dados("Historico_Producao.csv")
    
    if df.empty:
        st.info("ℹ️ Nenhum dado de produção registrado no histórico ainda.")
        return

    try:
        # 1. Converter colunas para números (Padrão 2026)
        cols_calc = ["Quant ad (g)", "Quantidade OP", "#Plan", "#Real", "Litros/Unit"]
        for col in cols_calc:
            if col in df.columns:
                df[col] = df[col].astype(str).str.replace(',', '.')
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        # 2. Preenchimento de Lote (Sintaxe compatível com Python 3.13 / Pandas 2.x)
        # Substituímos 0 por NaN para o ffill funcionar corretamente
        df[['#Real', '#Plan', 'Litros/Unit']] = df[['#Real', '#Plan', 'Litros/Unit']].replace(0, np.nan).ffill()
        
        # 3. Cálculos de Volume e Desvio
        df['Vol_Real_Total'] = df['#Real'] * df['Litros/Unit']
        df['Vol_Plan_Total'] = df['#Plan'] * df['Litros/Unit']
        
        # Filtrar apenas linhas com volume válido para evitar erro de divisão
        df = df[df['Vol_Real_Total'] > 0].copy()
        
        if df.empty:
            st.warning("⚠️ Os registros existem, mas os volumes (#Plan/#Real) estão zerados.")
            return

        # Cálculo do Desvio Percentual
        # Comparando: (Grama por Litro Real) / (Grama por Litro Planejado)
        df['G_L_Real'] = df['Quant ad (g)'] / df['Vol_Real_Total']
        df['G_L_Plan'] = df['Quantidade OP'] / (df['Vol_Plan_Total'] + 0.000001)
        df['Desvio_%'] = ((df['G_L_Real'] / df['G_L_Plan']) - 1) * 100

        # 4. Interface de Filtros
        st.subheader("🔍 Filtros de Análise")
        prod_lista = sorted(df['tipo de produto'].unique())
        prod_sel = st.selectbox("Selecione o Produto", prod_lista)
        
        df_f = df[df['tipo de produto'] == prod_sel].copy()

        # 5. Visualização
        st.subheader(f"Variabilidade: {prod_sel}")
        
        # Gráfico de Linhas Nativo do Streamlit (Sem Plotly para garantir que carregue)
        chart_data = df_f.pivot_table(index='data', columns='pigmento', values='Desvio_%', aggfunc='mean')
        st.line_chart(chart_data)
        
        # Estatísticas Rápidas
        c1, c2 = st.columns(2)
        c1.metric("Desvio Médio Total", f"{df_f['Desvio_%'].mean():.2f}%")
        c2.metric("Estabilidade (Desvio Padrão)", f"{df_f['Desvio_%'].std():.2f}%")

        st.write("📋 Tabela de Dados Analisados")
        st.dataframe(df_f[['data', 'lote', 'pigmento', 'Desvio_%']].style.format({"Desvio_%": "{:.2f}%"}))

    except Exception as e:
        st.error(f"Erro no processamento dos cálculos: {e}")

# --- ESTRUTURA DO MENU (Lado de fora para garantir que apareça) ---
st.sidebar.header("Menu de Controle")
aba = st.sidebar.radio("Navegação:", ["🚀 Nova Pigmentação", "📈 Variações & CEP", "📋 Padrões"])

if aba == "🚀 Nova Pigmentação":
    st.title("🚀 Registrar Nova Pigmentação")
    st.write("O sistema está pronto para receber novos dados.")
    # Aqui você pode manter seu código de formulário que já funcionava.

elif aba == "📈 Variações & CEP":
    aba_variabilidade()

elif aba == "📋 Padrões":
    st.title("📋 Padrões Registrados")
    df_p = carregar_dados("Padroes_Registrados.csv")
    if not df_p.empty:
        st.dataframe(df_p)
    else:
        st.info("Nenhum padrão encontrado.")

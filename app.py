import streamlit as st
import pandas as pd
import os
from datetime import datetime

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
            # Tenta ler com diferentes encodings e separadores
            df = pd.read_csv(file, sep=None, engine='python', encoding='latin-1')
            df.columns = [str(c).strip() for c in df.columns]
            return df
        except:
            return pd.DataFrame()
    return pd.DataFrame()

# --- ABA DE VARIAÇÕES CRÍTICAS (LÓGICA) ---
def renderizar_aba_variacoes():
    st.title("⚠️ Acompanhamento de Variações Críticas")
    
    if not os.path.exists("Historico_Producao.csv"):
        st.info("Ainda não há dados de produção para analisar variações.")
        return

    df_hist = pd.read_csv("Historico_Producao.csv", sep=';', encoding='latin-1')
    
    # Converter colunas para numérico para cálculo (removendo a vírgula se existir)
    cols_para_fix = ["Quant ad (g)", "Quantidade OP", "#Plan", "#Real", "Litros/Unit"]
    for col in cols_para_fix:
        if col in df_hist.columns:
            df_hist[col] = df_hist[col].astype(str).str.replace(',', '.').replace('', '0')
            df_hist[col] = pd.to_numeric(df_hist[col], errors='coerce').fillna(0)

    # Lógica de análise: Comparar a concentração Real vs Sugerida
    # Precisamos preencher os dados de Unidades que ficam apenas na primeira linha do lote
    df_hist['#Real'] = df_hist['#Real'].replace(0, method='ffill')
    df_hist['Litros/Unit'] = df_hist['Litros/Unit'].replace(0, method='ffill')

    # Cálculo da Variação
    # (Gramas por Litro Real) vs (Gramas por Litro Planejado)
    df_hist['Vol_Real_L'] = df_hist['#Real'] * df_hist['Litros/Unit']
    
    # Evitar divisão por zero
    df_hist = df_hist[df_hist['Vol_Real_L'] > 0].copy()
    
    # Concentração esperada pela OP vs O que foi realmente adicionado por litro envasado
    df_hist['g_L_Esperado'] = df_hist['Quantidade OP'] / (df_hist['#Plan'] * df_hist['Litros/Unit'])
    df_hist['g_L_Real'] = df_hist['Quant ad (g)'] / df_hist['Vol_Real_L']
    
    df_hist['Variação %'] = ((df_hist['g_L_Real'] / df_hist['g_L_Esperado']) - 1) * 100
    
    # Filtros de interface
    limite = st.slider("Filtrar variações acima de (%)", 0, 50, 5)
    
    criticos = df_hist[(df_hist['Variação %'].abs() >= limite)].copy()
    
    if criticos.empty:
        st.success(f"Nenhuma variação acima de {limite}% encontrada!")
    else:
        # Formatação para exibição
        display_cols = ["data", "lote", "tipo de produto", "cor", "pigmento", "Variação %"]
        
        def color_variacao(val):
            color = 'red' if abs(val) > 10 else 'orange'
            return f'color: {color}; font-weight: bold'

        st.dataframe(
            criticos[display_cols].style.format({"Variação %": "{:.2f}%"}).applymap(color_variacao, subset=['Variação %']),
            use_container_width=True
        )
        
        st.subheader("Análise de Tendência por Pigmento")
        st.bar_chart(criticos.groupby("pigmento")["Variação %"].mean())

# --- RESTANTE DO CÓDIGO (Nova Navegação) ---
df_mestra = load_data("Aba_Mestra.csv")
aba = st.sidebar.radio("Navegação:", ["🚀 Nova Pigmentação", "⚠️ Variações Críticas", "📋 Padrões", "📜 Banco de Dados", "➕ Cadastro", "📊 Aba Mestra"])

if aba == "🚀 Nova Pigmentação":
    # ... (mesmo código anterior da Nova Pigmentação)
    st.title("🚀 Registrar Produção")
    # [Omitido para brevidade, mas permanece idêntico ao último fornecido]
    pass 

elif aba == "⚠️ Variações Críticas":
    renderizar_aba_variacoes()

elif aba == "📋 Padrões":
    st.title("📋 Evolução de Padrões Técnicos")
    if os.path.exists("Padroes_Registrados.csv"):
        df_p = pd.read_csv("Padroes_Registrados.csv", sep=';', encoding='latin-1')
        st.dataframe(df_p.style.format({"Novo Coef (kg/L)": "{:.6f}"}), use_container_width=True)
    else: st.info("Sem atualizações.")

# ... (outras abas seguem o padrão anterior)

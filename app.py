import streamlit as st
import pandas as pd
import os
from datetime import datetime
import numpy as np

# Configuração inicial da página
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

# --- FUNÇÕES DE CÁLCULO E DADOS ---

def load_data(file="Aba_Mestra.csv"):
    if os.path.exists(file):
        try:
            # Carrega a mestra. Garante que os nomes das colunas batam com a lógica
            df = pd.read_csv(file, sep=None, engine='python', encoding='latin-1')
            df.columns = [str(c).strip() for c in df.columns]
            return df
        except:
            return pd.DataFrame()
    return pd.DataFrame()

def calcular_colunas_final(lista_lote, df_mestra):
    """Gera o DataFrame com as colunas de A a Q calculadas"""
    df = pd.DataFrame(lista_lote)
    
    # L e M: Volumes Totais
    df['Volume Planejado'] = df['n_plan'] * df['Litros/Unit']
    df['volume produzido'] = df['n_real'] * df['Litros/Unit']

    # N: Formulação (Busca na Aba Mestra)
    # Ajustando nomes da mestra para o merge: 'Tipo' vira 'Tipo de Produto'
    mestra_aux = df_mestra.rename(columns={'Tipo': 'Tipo de Produto', 'Quant OP (kg)': 'Formulação'})
    df = pd.merge(df, mestra_aux[['Tipo de Produto', 'Cor', 'Pigmento', 'Formulação']], 
                  left_on=['Tipo de Produto', 'Cor', 'pigmento'], 
                  right_on=['Tipo de Produto', 'Cor', 'Pigmento'], how='left')

    # O: consumo real de pigmento (utilizado kg/L) -> (F / 1000) / M
    df['consumo real de pigmento (utilizado kg/L)'] = (df['Quant ad (g)'] / 1000) / df['volume produzido'].replace(0, 1)

    # P: variação percentual -> (O / N) - 1
    df['variação percentual'] = (df['consumo real de pigmento (utilizado kg/L)'] / df['Formulação'].replace(0, np.nan)) - 1

    # Q: variação absoluta -> (F / 1000) - (M * N)
    df['variação absoluta'] = (df['Quant ad (g)'] / 1000) - (df['volume produzido'] * df['Formulação'])

    # Reordenar para o padrão A-Q solicitado
    ordem_final = [
        'lote', 'Tipo de Produto', 'Cor', 'pigmento', 'Toques', 
        'Quant ad (g)', 'Quant OP (kg)', 'n_plan', 'n_real', 
        'Litros/Unit', 'Encomenda?', 'Volume Planejado', 
        'volume produzido', 'Formulação', 
        'consumo real de pigmento (utilizado kg/L)', 
        'variação percentual', 'variação absoluta'
    ]
    return df[ordem_final]

def salvar_no_historico(df_calculado):
    hist_path = "Historico_Producao.csv"
    if os.path.exists(hist_path):
        hist_ex = pd.read_csv(hist_path, encoding='latin-1', sep=';')
        final = pd.concat([hist_ex, df_calculado], ignore_index=True)
    else:
        final = df_calculado
    final.to_csv(hist_path, index=False, sep=';', encoding='latin-1', decimal=',')

# --- NAVEGAÇÃO ---
df_mestra = load_data()
aba = st.sidebar.radio("Navegação:", ["🚀 Nova Pigmentação", "📜 Banco de Dados", "📊 Aba Mestra"])

if aba == "🚀 Nova Pigmentação":
    st.title("🚀 Registrar Produção")
    
    if df_mestra.empty:
        st.warning("Aba Mestra não encontrada ou vazia.")
    else:
        # 1. Cabeçalho do Registro
        c1, c2, c3, c4 = st.columns([1.5, 1.5, 1, 1])
        with c1: tipo_sel = st.selectbox("Produto", sorted(df_mestra['Tipo'].unique()))
        with c2: cor_sel = st.selectbox("Cor", sorted(df_mestra[df_mestra['Tipo'] == tipo_sel]['Cor'].unique()))
        with c3: lote_id = st.text_input("Lote", placeholder="Nº Lote")
        with c4: encomenda = st.selectbox("📦 Encomenda?", ["Não", "Sim"])
        
        u1, u2, u3 = st.columns([1, 1, 2])
        with u1: num_plan = st.number_input("#Unid Plan", min_value=1, value=1)
        with u2: num_real = st.number_input("#Unid Real", min_value=1, value=1)
        with u3:
            opcoes_vol = ["0,9", "3,6", "15", "18"]
            litros_unit = st.selectbox("Litros/Unit", opcoes_vol)
            litros_unit = float(litros_unit.replace(',', '.'))

        # 2. Área de Pigmentos
        st.subheader("🎨 Pigmentos")
        formulas = df_mestra[(df_mestra['Tipo'] == tipo_sel) & (df_mestra['Cor'] == cor_sel)]
        lista_para_calculo = []

        if not formulas.empty:
            for index, row in formulas.iterrows():
                pigm = row['Pigmento']
                # Cálculo da sugestão da OP (G) para exibir na tela
                sugestao_op_g = round(row["Quant OP (kg)"] * (num_plan * litros_unit) * 1000, 2)
                
                with st.container():
                    col_info, col_pes = st.columns([1.5, 3.5])
                    with col_info:
                        st.markdown(f"### {pigm}")
                        st.caption(f"Sugestão OP: {sugestao_op_g}g")
                        n_toques = st.number_input("Toques", min_value=1, value=1, key=f"t_{index}")
                    with col_pes:
                        soma_ad = 0.0
                        cols_t = st.columns(5)
                        for t in range(1, n_toques + 1):
                            with cols_t[(t-1)%5]:
                                val = st.number_input(f"T{t}", min_value=0.0, key=f"v_{index}_{t}")
                                if val: soma_ad += val
                        st.markdown(f"*Total: {soma_ad:.2f}g*")
                    
                    # Alimenta a lista para o processamento final
                    lista_para_calculo.append({
                        "lote": lote_id, "Tipo de Produto": tipo_sel, "Cor": cor_sel,
                        "pigmento": pigm, "Toques": n_toques, "Quant ad (g)": soma_ad,
                        "Quant OP (kg)": sugestao_op_g / 1000, "n_plan": num_plan,
                        "n_real": num_real, "Litros/Unit": litros_unit, "Encomenda?": encomenda
                    })
            
            if st.button("✅ FINALIZAR E GERAR CSV"):
                if not lote_id:
                    st.error("Por favor, insira o número do Lote.")
                else:
                    df_final = calcular_colunas_final(lista_para_calculo, df_mestra)
                    salvar_no_historico(df_final)
                    st.success("Registro concluído com sucesso!")
                    st.balloons()

elif aba == "📜 Banco de Dados":
    st.title("📜 Histórico de Produção (A-Q)")
    if os.path.exists("Historico_Producao.csv"):
        df_hist = pd.read_csv("Historico_Producao.csv", sep=';', encoding='latin-1', decimal=',')
        st.dataframe(df_hist, use_container_width=True)
        
        # Botão de Download do CSV pronto
        csv = df_hist.to_csv(index=False, sep=';', decimal=',', encoding='latin-1').encode('latin-1')
        st.download_button("📥 Baixar CSV Completo", csv, "historico_calculado.csv", "text/csv")

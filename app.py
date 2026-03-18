import streamlit as st
import pandas as pd
import numpy as np
import os
from datetime import datetime

# 1. Configuração de Layout
st.set_page_config(page_title="Colortex 2026 - Gestão de R&D", layout="wide", page_icon="🧪")

# --- ESTILO CSS ---
st.markdown("""
    <style>
    .stNumberInput { margin-bottom: -1rem; }
    .stButton > button { width: 100%; background-color: #d4edda; color: #155724; font-weight: bold; height: 3em; }
    hr { margin: 0.8rem 0rem !important; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNÇÕES DE TRATAMENTO DE DADOS ---
def carregar_dados(arquivo):
    if not os.path.exists(arquivo): return pd.DataFrame()
    try:
        try:
            df = pd.read_csv(arquivo, sep=None, engine='python', encoding='latin-1')
        except:
            df = pd.read_csv(arquivo, sep=None, engine='python', encoding='utf-8')
        
        df.columns = [str(c).strip() for c in df.columns]
        traducoes = {'Oxido': 'Óxido', 'Franca': 'França', 'oxido': 'óxido', 'franca': 'frança'}
        for col in df.select_dtypes(include=['object']).columns:
            df[col] = df[col].astype(str).str.strip().replace(traducoes, regex=True).str.title()
        return df
    except: return pd.DataFrame()

def salvar_csv(df, arquivo):
    df.to_csv(arquivo, index=False, encoding='latin-1')

# --- CARREGAMENTO INICIAL ---
df_mestra = carregar_dados("Aba_Mestra.csv")
df_hist = carregar_dados("Historico_Producao.csv")
df_padr = carregar_dados("Padroes_Registrados.csv")

# --- NAVEGAÇÃO ---
menu = ["🚀 Produção (Toques)", "📈 Gráficos CEP", "📋 Padrões Registrados", "📜 Banco de Dados", "➕ Cadastro de Produtos", "📊 Editor Aba Mestra", "📂 Importar CSV"]
aba = st.sidebar.radio("Navegação:", menu)

# --- 🚀 ABA: PRODUÇÃO ---
if aba == "🚀 Produção (Toques)":
    st.title("🚀 Registro de Pesagem")
    if df_mestra.empty:
        st.warning("⚠️ Aba Mestra vazia. Importe a planilha para começar.")
    else:
        c1, c2, c3, c4 = st.columns([1.5, 1.5, 1, 1])
        with c1: t_sel = st.selectbox("Produto", sorted(df_mestra['Tipo'].unique()))
        with c2: cor_sel = st.selectbox("Cor", sorted(df_mestra[df_mestra['Tipo'] == t_sel]['Cor'].unique()))
        with c3: lote_id = st.text_input("Lote")
        with c4: data_f = st.date_input("Data", datetime.now())

        v1, v2, v3, v4 = st.columns([1, 1, 2, 1.5])
        with v1: n_p = st.number_input("# Unid Plan", min_value=1, value=1)
        with v2: n_r = st.number_input("# Unid Real", min_value=1, value=1)
        with v3:
            opcoes_v = ["0,9L", "3,6L", "15L", "18L", "25kg", "Outro"]
            sel_v = st.select_slider("Embalagem:", options=opcoes_v, value="15L")
            litros_u = float(sel_v.replace('L','').replace('kg','').replace(',','.')) if sel_v != "Outro" else st.number_input("Valor Unit:", value=15.0)
        with v4:
            st.write("") 
            salvar_como_padrao = st.checkbox("🌟 Salvar como novo padrão")

        vol_p_tot = n_p * litros_u
        formula = df_mestra[(df_mestra['Tipo'] == t_sel) & (df_mestra['Cor'] == cor_sel)]
        st.divider()

        registros_lote = []
        for i, row in formula.iterrows():
            pigm = row['Pigmento']
            coef = pd.to_numeric(str(row['Quant OP (kg)']).replace(',', '.'), errors='coerce')
            sugestao_g = round(coef * vol_p_tot * 1000, 2)
            
            with st.container():
                col_i, col_p = st.columns([1.5, 3.5])
                with col_i:
                    st.subheader(pigm)
                    st.write(f"Sugestão: {sugestao_g}g")
                    n_t = st.number_input(f"Toques", min_value=1, value=1, key=f"nt_{i}")
                with col_p:
                    s_ad = 0.0
                    cols = st.columns(5)
                    for t in range(1, int(n_t) + 1):
                        with cols[(t-1)%5]:
                            v = st.number_input(f"T{t}", min_value=0.0, format="%.2f", key=f"v_{i}_{t}")
                            s_ad += v
                    st.markdown(f"**Total: {s_ad:.2f} g**")
            registros_lote.append({
                "data": data_f.strftime("%d/%m/%Y"), "lote": lote_id, "tipo de produto": t_sel,
                "cor": cor_sel, "pigmento": pigm, "Quant ad (g)": s_ad,
                "Quantidade OP": coef, "#Plan": n_p, "#Real": n_r, "Litros/Unit": litros_u
            })
            st.divider()

        if st.button("💾 SALVAR LOTE"):
            if not lote_id:
                st.error("Preencha o Lote.")
            else:
                df_hist = pd.concat([df_hist, pd.DataFrame(registros_lote)], ignore_index=True)
                salvar_csv(df_hist, "Historico_Producao.csv")
                if salvar_como_padrao:
                    novo_padr = pd.DataFrame([{"Data": data_f, "Produto": t_sel, "Cor": cor_sel, "Lote": lote_id, "Status": "Padrão"}])
                    df_padr = pd.concat([df_padr, novo_padr], ignore_index=True)
                    salvar_csv(df_padr, "Padroes_Registrados.csv")
                st.success("Salvo!"); st.rerun()

# --- 📈 ABA: CEP (STATUS APENAS EMOJI 🚨 PARA EXCESSO) ---
elif aba == "📈 Gráficos CEP":
    st.title("📈 Análise de Precisão")
    if df_hist.empty:
        st.info("Sem dados.")
    else:
        df_cep = df_hist.copy()
        for col in ['Quant ad (g)', 'Quantidade OP']:
            df_cep[col] = pd.to_numeric(df_cep[col].astype(str).str.replace(',', '.'), errors='coerce').fillna(0.0)

        df_cep['OP_g'] = df_cep['Quantidade OP'] * 1000
        df_cep['Desvio_%'] = ((df_cep['Quant ad (g)'] / (df_cep['OP_g'].replace(0, np.nan))) - 1) * 100
        
        # STATUS: APENAS EMOJI 🚨 SE > 10%
        df_cep['Status'] = df_cep['Desvio_%'].apply(lambda d: "🚨" if d > 10.0 else "✅")

        p_sel = st.selectbox("Selecione o Produto", sorted(df_cep['tipo de produto'].unique()))
        c_sel = st.selectbox("Selecione a Cor", sorted(df_cep[df_cep['tipo de produto'] == p_sel]['cor'].unique()))

        df_plot = df_cep[(df_cep['tipo de produto'] == p_sel) & (df_cep['cor'] == c_sel)].copy()
        
        if not df_plot.empty:
            df_plot['lote'] = df_plot['lote'].astype(str)
            st.line_chart(df_plot.pivot_table(index='lote', columns='pigmento', values='Desvio_%', aggfunc='mean'))
            st.subheader("📋 Relatório de Pesagem")
            st.dataframe(
                df_plot[['data', 'lote', 'pigmento', 'Quant ad (g)', 'OP_g', 'Desvio_%', 'Status']].style.format({'Desvio_%': '{:.2f}%'})
            )

# --- 📋 ABA: PADRÕES ---
elif aba == "📋 Padrões Registrados":
    st.title("📋 Padrões")
    st.dataframe(df_padr, use_container_width=True)

# --- 📂 ABA: IMPORTAR ---
elif aba == "📂 Importar CSV":
    st.title("📂 Importar")
    up = st.file_uploader("Arquivo", type="csv")
    alvo = st.selectbox("Destino", ["Aba_Mestra.csv", "Historico_Producao.csv", "Padroes_Registrados.csv"])
    if up and st.button("Confirmar"):
        df_imp = pd.read_csv(up, encoding='latin-1', sep=None, engine='python')
        salvar_csv(df_imp, alvo); st.success("Ok!"); st.rerun()

# --- ➕ ABA: CADASTRO DE PRODUTOS (RESTAURADA) ---
elif aba == "➕ Cadastro de Produtos":
    st.title("➕ Cadastrar Novo Pigmento na Mestra")
    with st.form("form_cadastro"):
        col1, col2 = st.columns(2)
        with col1:
            novo_tipo = st.text_input("Tipo de Produto (Ex: Colormax)")
            novo_pigmento = st.text_input("Nome do Pigmento")
        with col2:
            nova_cor = st.text_input("Cor do Produto (Ex: Branco Gelo)")
            novo_coef = st.number_input("Coeficiente de Dosagem (kg/L)", format="%.6f")
        
        if st.form_submit_button("Adicionar à Aba Mestra"):
            if novo_tipo and nova_cor and novo_pigmento:
                novo_item = pd.DataFrame([{
                    "Tipo": novo_tipo.strip().title(),
                    "Cor": nova_cor.strip().title(),
                    "Pigmento": novo_pigmento.strip().title(),
                    "Quant OP (kg)": novo_coef
                }])
                df_mestra = pd.concat([df_mestra, novo_item], ignore_index=True)
                salvar_csv(df_mestra, "Aba_Mestra.csv")
                st.success(f"Item {novo_pigmento} adicionado com sucesso!")
            else:
                st.error("Preencha todos os campos obrigatórios.")

# --- 📊 ABA: EDITOR ---
elif aba == "📊 Editor Aba Mestra":
    ed = st.data_editor(df_mestra, num_rows="dynamic")
    if st.button("Salvar Tudo"): salvar_csv(ed, "Aba_Mestra.csv"); st.success("Salvo!")

# --- 📜 ABA: BANCO ---
elif aba == "📜 Banco de Dados":
    st.dataframe(df_hist)

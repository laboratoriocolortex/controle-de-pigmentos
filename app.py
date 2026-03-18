import streamlit as st
import pandas as pd
import numpy as np
import os
from datetime import datetime

# 1. Configuração de Layout
st.set_page_config(page_title="Colortex 2026 - Gestão de R&D", layout="wide", page_icon="🧪")

# --- ESTILO CSS PARA ALERTAS ---
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

        v1, v2, v3 = st.columns([1, 1, 2])
        with v1: n_p = st.number_input("# Unid Plan", min_value=1, value=1)
        with v2: n_r = st.number_input("# Unid Real", min_value=1, value=1)
        with v3:
            opcoes_v = ["0,9L", "3,6L", "15L", "18L", "25kg", "Outro"]
            sel_v = st.select_slider("Embalagem:", options=opcoes_v, value="15L")
            litros_u = float(sel_v.replace('L','').replace('kg','').replace(',','.')) if sel_v != "Outro" else st.number_input("Valor Unit:", value=15.0)

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
            df_hist = pd.concat([df_hist, pd.DataFrame(registros_lote)], ignore_index=True)
            salvar_csv(df_hist, "Historico_Producao.csv")
            st.success("Gravado com sucesso!")

# --- 📈 ABA: CEP (ALERTA COM TOLERÂNCIA DE 10%) ---
elif aba == "📈 Gráficos CEP":
    st.title("📈 Análise de Precisão (Tolerância 10%)")
    if df_hist.empty:
        st.info("Sem dados registrados no histórico.")
    else:
        df_cep = df_hist.copy()
        for col in ['Quant ad (g)', 'Quantidade OP']:
            df_cep[col] = pd.to_numeric(df_cep[col].astype(str).str.replace(',', '.'), errors='coerce').fillna(0.0)

        df_cep['OP_g'] = df_cep['Quantidade OP'] * 1000
        df_cep['Desvio_%'] = ((df_cep['Quant ad (g)'] / (df_cep['OP_g'].replace(0, np.nan))) - 1) * 100
        
        # --- LÓGICA DE STATUS COM TOLERÂNCIA AJUSTADA ---
        tolerancia_ajustada = 10.0 
        
        def definir_status_10(row):
            d = row['Desvio_%']
            if pd.isna(d): return "⚪ Sem Base"
            if row['Quant ad (g)'] == 0: return "⚠️ NÃO UTILIZADO"
            if abs(d) > tolerancia_ajustada:
                direcao = "EXCESSO" if d > 0 else "FALTA"
                return f"🚨 DESVIO ALTO ({direcao})"
            return "✅ OK"

        df_cep['Status'] = df_cep.apply(definir_status_10, axis=1)

        p_sel = st.selectbox("Selecione o Produto", sorted(df_cep['tipo de produto'].unique()))
        c_sel = st.selectbox("Selecione a Cor", sorted(df_cep[df_cep['tipo de produto'] == p_sel]['cor'].unique()))

        df_plot = df_cep[(df_cep['tipo de produto'] == p_sel) & (df_cep['cor'] == c_sel)].copy()
        
        if not df_plot.empty:
            df_plot['lote'] = df_plot['lote'].astype(str)
            chart_data = df_plot.pivot_table(index='lote', columns='pigmento', values='Desvio_%', aggfunc='mean')
            st.line_chart(chart_data)
            
            st.subheader("📋 Relatório de Conformidade Técnica")
            
            def style_status_10(val):
                if "🚨" in str(val): return 'background-color: #f8d7da; color: #721c24; font-weight: bold'
                if "⚠️" in str(val): return 'color: #856404; font-weight: bold'
                return 'color: #155724'

            st.dataframe(
                df_plot[['data', 'lote', 'pigmento', 'Quant ad (g)', 'OP_g', 'Desvio_%', 'Status']].style.format({'Desvio_%': '{:.2f}%'})
                .applymap(style_status_10, subset=['Status'])
            )
        else:
            st.warning("Selecione um produto e cor válidos.")

# --- 📋 ABA: PADRÕES ---
elif aba == "📋 Padrões Registrados":
    st.title("📋 Padrões Técnicos de Cor")
    if df_padr.empty: st.info("Importe o arquivo 'Padroes_Registrados.csv' para visualizar.")
    else: st.dataframe(df_padr, use_container_width=True)

# --- 📂 ABA: IMPORTAR ---
elif aba == "📂 Importar CSV":
    st.title("📂 Upload de Dados")
    up = st.file_uploader("Arraste seu CSV aqui", type="csv")
    alvo = st.selectbox("Destino do arquivo", ["Aba_Mestra.csv", "Historico_Producao.csv", "Padroes_Registrados.csv"])
    if up and st.button("Processar Arquivo"):
        df_imp = pd.read_csv(up, encoding='latin-1', sep=None, engine='python')
        salvar_csv(df_imp, alvo)
        st.success(f"Dados integrados ao sistema ({alvo})!"); st.rerun()

# --- EDITOR E CADASTRO ---
elif aba == "➕ Cadastro de Produtos":
    st.title("➕ Novo Item na Mestra")
    with st.form("cad"):
        t = st.text_input("Tipo"); c = st.text_input("Cor"); p = st.text_input("Pigmento"); coef = st.number_input("Coef (kg/L)", format="%.6f")
        if st.form_submit_button("Adicionar"):
            n = pd.DataFrame([{"Tipo":t,"Cor":c,"Pigmento":p,"Quant OP (kg)":coef}])
            df_mestra = pd.concat([df_mestra, n], ignore_index=True)
            salvar_csv(df_mestra, "Aba_Mestra.csv"); st.success("Adicionado!"); st.rerun()

elif aba == "📊 Editor Aba Mestra":
    ed = st.data_editor(df_mestra, num_rows="dynamic")
    if st.button("Salvar Tudo"): salvar_csv(ed, "Aba_Mestra.csv"); st.success("Salvo!")

elif aba == "📜 Banco de Dados":
    st.title("📜 Histórico Geral")
    st.dataframe(df_hist)

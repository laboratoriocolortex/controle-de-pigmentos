import streamlit as st
import pandas as pd
import numpy as np
import os
from datetime import datetime

# 1. Configuração de Layout e Estilo
st.set_page_config(page_title="Colortex 2026 - Gestão de R&D", layout="wide", page_icon="🧪")

st.markdown("""
    <style>
    .stNumberInput { margin-bottom: -1rem; }
    .stButton > button { width: 100%; background-color: #d4edda; color: #155724; font-weight: bold; height: 3em; }
    .status-alerta { color: #d9534f; font-weight: bold; }
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
        # Padronização de nomes técnicos e acentos
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

# --- NAVEGAÇÃO LATERAL ---
menu = ["🚀 Produção (Toques)", "📈 Gráficos CEP", "📋 Padrões Registrados", "📜 Banco de Dados", "➕ Cadastro de Produtos", "📊 Editor Aba Mestra", "📂 Importar CSV"]
aba = st.sidebar.radio("Navegação Principal:", menu)

# --- 🚀 ABA: PRODUÇÃO (COM SLIDERS E SISTEMA DE TOQUES) ---
if aba == "🚀 Produção (Toques)":
    st.title("🚀 Registro de Pesagem e Toques")
    
    if df_mestra.empty:
        st.warning("⚠️ Aba Mestra não encontrada. Por favor, realize o upload ou cadastro.")
    else:
        # Filtros Superiores
        c1, c2, c3, c4 = st.columns([1.5, 1.5, 1, 1])
        with c1: t_sel = st.selectbox("Produto", sorted(df_mestra['Tipo'].unique()))
        with c2: cor_sel = st.selectbox("Cor", sorted(df_mestra[df_mestra['Tipo'] == t_sel]['Cor'].unique()))
        with c3: lote_id = st.text_input("Lote", placeholder="Ex: 2026-101")
        with c4: data_f = st.date_input("Data de Fabricação", datetime.now())

        # Configuração de Volumes (Sliders Restaurados)
        v1, v2, v3 = st.columns([1, 1, 2])
        with v1: n_p = st.number_input("# Unid Planejadas", min_value=1, value=1)
        with v2: n_r = st.number_input("# Unid Reais", min_value=1, value=1)
        with v3:
            opcoes_v = ["0,9L", "3,6L", "15L", "18L", "25kg", "Outro"]
            sel_v = st.select_slider("Tipo de Embalagem:", options=opcoes_v, value="15L")
            litros_u = float(sel_v.replace('L','').replace('kg','').replace(',','.')) if sel_v != "Outro" else st.number_input("Valor Unitário (L/kg):", value=15.0)

        vol_p_tot = n_p * litros_u
        st.info(f"Volume de Cálculo Planejado: **{vol_p_tot:.2f} L/kg**")
        
        formula = df_mestra[(df_mestra['Tipo'] == t_sel) & (df_mestra['Cor'] == cor_sel)]
        st.divider()

        registros_lote = []
        if not formula.empty:
            for i, row in formula.iterrows():
                pigm = row['Pigmento']
                # Coeficiente da Mestra (kg/L)
                coef = pd.to_numeric(str(row['Quant OP (kg)']).replace(',', '.'), errors='coerce')
                sugestao_g = round(coef * vol_p_tot * 1000, 2)
                
                with st.container():
                    col_info, col_pesos = st.columns([1.5, 3.5])
                    with col_info:
                        st.subheader(pigm)
                        st.write(f"Sugestão OP: **{sugestao_g} g**")
                        n_toques = st.number_input(f"Qtd Toques ({pigm})", min_value=1, max_value=10, value=1, key=f"nt_{i}")
                    
                    with col_pesos:
                        soma_ad = 0.0
                        cols_t = st.columns(5)
                        for t in range(1, int(n_toques) + 1):
                            with cols_t[(t-1)%5]:
                                val_t = st.number_input(f"T{t} (g)", min_value=0.0, format="%.2f", key=f"val_{i}_{t}")
                                soma_ad += val_t
                        st.markdown(f"**Total Adicionado: {soma_ad:.2f} g**")
                
                registros_lote.append({
                    "data": data_f.strftime("%d/%m/%Y"), "lote": lote_id, "tipo de produto": t_sel,
                    "cor": cor_sel, "pigmento": pigm, "Quant ad (g)": soma_ad,
                    "Quantidade OP": coef, "#Plan": n_p, "#Real": n_r, "Litros/Unit": litros_u, "toque": n_toques
                })
                st.divider()

            if st.button("💾 FINALIZAR E GRAVAR NO BANCO DE DADOS"):
                if not lote_id: 
                    st.error("ERRO: O campo 'Lote' é obrigatório!")
                else:
                    df_novo = pd.DataFrame(registros_lote)
                    df_hist = pd.concat([df_hist, df_novo], ignore_index=True)
                    salvar_csv(df_hist, "Historico_Producao.csv")
                    st.success(f"Sucesso! Lote {lote_id} registrado."); st.balloons()

# --- 📈 ABA: CEP (AUDITORIA E CÁLCULO G vs KG) ---
elif aba == "📈 Gráficos CEP":
    st.title("📈 CEP - Controle Estatístico de Processo")
    
    if df_hist.empty:
        st.info("O histórico está vazio. Realize registros para gerar os gráficos.")
    else:
        df_cep = df_hist.copy()

        # 1. CONVERSÃO E CÁLCULO TÉCNICO
        for col in ['Quant ad (g)', 'Quantidade OP']:
            df_cep[col] = pd.to_numeric(df_cep[col].astype(str).str.replace(',', '.'), errors='coerce').fillna(0.0)

        # Cálculo de Desvios (OP kg -> g)
        df_cep['OP_g'] = df_cep['Quantidade OP'] * 1000
        df_cep['Desvio_Absoluto_g'] = df_cep['Quant ad (g)'] - df_cep['OP_g']
        df_cep['Desvio_%'] = ((df_cep['Quant ad (g)'] / (df_cep['OP_g'].replace(0, np.nan))) - 1) * 100

        # Status de Auditoria
        df_cep['Status'] = df_cep['Quant ad (g)'].apply(lambda x: "⚠️ NÃO UTILIZADO" if x <= 0 else "✅ OK")

        # 2. FILTROS
        f1, f2 = st.columns(2)
        with f1: p_sel = st.selectbox("Produto", sorted(df_cep['tipo de produto'].unique()))
        with f2: c_sel = st.selectbox("Cor", sorted(df_cep[df_cep['tipo de produto'] == p_sel]['cor'].unique()))

        df_plot = df_cep[(df_cep['tipo de produto'] == p_sel) & (df_cep['cor'] == c_sel)].copy()

        if not df_plot.empty:
            # 3. GRÁFICO (Pivot Table por Pigmento)
            df_plot['lote'] = df_plot['lote'].astype(str)
            chart_data = df_plot.pivot_table(index='lote', columns='pigmento', values='Desvio_%', aggfunc='mean')
            chart_data = chart_data.replace([np.inf, -np.inf], np.nan).dropna(how='all')

            if not chart_data.empty:
                st.subheader(f"Variação Percentual (%) - {c_sel}")
                st.line_chart(chart_data)
            
            # 4. TABELA DE AUDITORIA
            st.divider()
            st.subheader("📋 Auditoria Técnica de Pigmentação")
            
            def colorir_status(val):
                color = 'red' if val == "⚠️ NÃO UTILIZADO" else 'black'
                return f'color: {color}; font-weight: bold'

            st.dataframe(df_plot[[
                'data', 'lote', 'pigmento', 'Quant ad (g)', 'OP_g', 'Desvio_Absoluto_g', 'Desvio_%', 'Status'
            ]].style.format({
                'Quant ad (g)': '{:.2f}g', 'OP_g': '{:.2f}g', 
                'Desvio_Absoluto_g': '{:.2f}g', 'Desvio_%': '{:.2f}%'
            }).applymap(colorir_status, subset=['Status']))

            # Alerta de pigmentos ociosos
            ociosos = df_plot[df_plot['Quant ad (g)'] <= 0]['pigmento'].unique()
            if len(ociosos) > 0:
                st.error(f"🚨 Itens na fórmula mas não pesados: {', '.join(ociosos)}")
        else:
            st.warning("Nenhum registro encontrado para este filtro.")

# --- DEMAIS ABAS (SIMPLIFICADAS) ---
elif aba == "➕ Cadastro de Produtos":
    st.title("➕ Cadastrar Novo Item")
    with st.form("cad_form"):
        t, c = st.columns(2)
        with t: tipo = st.text_input("Tipo")
        with c: cor = st.text_input("Cor")
        pig = st.text_input("Pigmento")
        coef = st.number_input("Coeficiente (kg/L)", format="%.6f")
        if st.form_submit_button("Salvar Cadastro"):
            novo = pd.DataFrame([{"Tipo": tipo, "Cor": cor, "Pigmento": pig, "Quant OP (kg)": coef}])
            df_mestra = pd.concat([df_mestra, novo], ignore_index=True)
            salvar_csv(df_mestra, "Aba_Mestra.csv")
            st.success("Cadastrado!"); st.rerun()

elif aba == "📂 Importar CSV":
    st.title("📂 Importar Planilhas")
    up = st.file_uploader("Selecione o arquivo CSV", type="csv")
    alvo = st.selectbox("Destino", ["Aba_Mestra.csv", "Historico_Producao.csv"])
    if up and st.button("Confirmar Importação"):
        df_imp = pd.read_csv(up, encoding='latin-1', sep=None, engine='python')
        salvar_csv(df_imp, alvo)
        st.success("Importado com sucesso!"); st.rerun()

elif aba == "📊 Editor Aba Mestra":
    st.title("📊 Gestão da Aba Mestra")
    ed = st.data_editor(df_mestra, num_rows="dynamic")
    if st.button("Salvar Alterações"):
        salvar_csv(ed, "Aba_Mestra.csv")
        st.success("Aba Mestra atualizada!")

elif aba == "📜 Banco de Dados":
    st.title("📜 Histórico de Produção")
    st.dataframe(df_hist)
    if st.button("🗑️ Limpar Banco de Dados"):
        if os.path.exists("Historico_Producao.csv"): os.remove("Historico_Producao.csv")
        st.rerun()

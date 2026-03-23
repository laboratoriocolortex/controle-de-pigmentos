import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
import re
import time
import io
from datetime import datetime, date

# 1. Configuração de Layout
st.set_page_config(page_title="Colortex 2026 - Gestão de R&D", layout="wide", page_icon="🧪")

# --- 🗄️ CONFIGURAÇÃO SQLITE ---
DB_NAME = "colortex_factory.db"

def get_connection():
    return sqlite3.connect(DB_NAME)

def init_db():
    conn = get_connection()
    c = conn.cursor()
    # Tabela Aba Mestra
    c.execute('''CREATE TABLE IF NOT EXISTS aba_mestra 
                 (Tipo TEXT, Cor TEXT, Pigmento TEXT, [Quant OP (kg)] REAL)''')
    # Tabela Histórico de Produção
    c.execute('''CREATE TABLE IF NOT EXISTS historico_producao 
                 (data TEXT, lote TEXT, [tipo de produto] TEXT, cor TEXT, pigmento TEXT, 
                  [Quant ad (g)] REAL, [Quantidade OP] REAL, [#Plan] REAL, [#Real] REAL, [Litros/Unit] REAL)''')
    # Tabela de Padrões
    c.execute('''CREATE TABLE IF NOT EXISTS padroes_registrados 
                 (Data TEXT, Produto TEXT, Cor TEXT, Lote TEXT, Status TEXT)''')
    conn.commit()
    conn.close()

init_db()

def carregar_sql(tabela):
    conn = get_connection()
    df = pd.read_sql(f"SELECT * FROM {tabela}", conn)
    conn.close()
    # Tratamento numérico para garantir cálculos
    cols_num = ['Quant ad (g)', 'Quantidade OP', '#Plan', '#Real', 'Litros/Unit', 'Quant OP (kg)']
    for col in cols_num:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce').fillna(0.0)
    return df

def salvar_sql(df, tabela, modo='replace'):
    conn = get_connection()
    # Remove colunas virtuais de cálculo antes de salvar
    cols_ignore = ['Desvio (g)', 'Var %', 'Situação', 'Especificado (g)']
    df_save = df.drop(columns=[c for c in cols_ignore if c in df.columns], errors='ignore')
    df_save.to_sql(tabela, conn, if_exists=modo, index=False)
    conn.close()

# --- ESTILO CSS ---
st.markdown("""
    <style>
    .stNumberInput { margin-bottom: -1rem; }
    .stButton > button { width: 100%; background-color: #d4edda; color: #155724; font-weight: bold; height: 3em; }
    hr { margin: 0.8rem 0rem !important; }
    </style>
    """, unsafe_allow_html=True)

# --- NAVEGAÇÃO ---
menu = ["🚀 Registro", "📈 Controle", "📜 Banco de Dados", "📋 Padrões", "📊 Aba Mestra", "📂 Importar CSV"]
aba = st.sidebar.radio("Navegação:", menu)

# --- 🚀 ABA: REGISTRO ---
if aba == "🚀 Registro":
    st.title("🚀 Registro de Pigmentação")
    df_mestra = carregar_sql("aba_mestra")
    
    if df_mestra.empty:
        st.warning("Aba Mestra vazia. Importe os dados em 'Importar CSV'.")
    else:
        c1, c2, c3, c4 = st.columns([1.5, 1.5, 1, 1])
        t_sel = c1.selectbox("Produto", sorted(df_mestra['Tipo'].unique()))
        cor_sel = c2.selectbox("Cor", sorted(df_mestra[df_mestra['Tipo'] == t_sel]['Cor'].unique()))
        lote_id = c3.text_input("Lote")
        data_f = c4.date_input("Data", date.today())

        v1, v2, v3, v4 = st.columns([1, 1, 2, 1.5])
        n_p = v1.number_input("# Unid Plan", min_value=0.1, value=1.0)
        n_r = v2.number_input("# Unid Real", min_value=0.1, value=1.0)
        sel_v = v3.select_slider("Embalagem:", options=["0,9L", "3,6L", "15L", "18L", "25kg", "Outro"], value="15L")
        litros_u = float(re.sub(r'[^\d.]', '', sel_v.replace(',','.'))) if sel_v != "Outro" else v3.number_input("Valor Unit:", value=15.0)
        check_padrao = v4.checkbox("🌟 Definir como Novo Padrão")

        formula = df_mestra[(df_mestra['Tipo'] == t_sel) & (df_mestra['Cor'] == cor_sel)]
        st.divider()

        regs = []
        for i, row in formula.iterrows():
            espec_final_g = round((row['Quant OP (kg)'] * 1000) * (n_p * litros_u), 2)
            
            with st.container():
                col_i, col_p = st.columns([1.5, 3.5])
                col_i.subheader(row['Pigmento']); col_i.write(f"Espec: {espec_final_g}g")
                n_t = col_i.number_input(f"Toques", min_value=1, value=1, key=f"nt_{i}")
                
                s_ad = 0.0
                cols = col_p.columns(5)
                for t in range(1, int(n_t) + 1):
                    v = cols[(t-1)%5].number_input(f"T{t} (g)", min_value=0.0, format="%.2f", key=f"v_{i}_{t}")
                    s_ad += v
                col_p.info(f"Total: {s_ad:.2f} g")
            
            regs.append({
                "data": data_f.strftime("%d/%m/%Y"), "lote": lote_id, "tipo de produto": t_sel,
                "cor": cor_sel, "pigmento": row['Pigmento'], "Quant ad (g)": s_ad,
                "Quantidade OP": espec_final_g, "#Plan": n_p, "#Real": n_r, "Litros/Unit": litros_u
            })
            st.divider()

        if st.button("💾 SALVAR LOTE"):
            if not lote_id: st.error("Lote obrigatório.")
            else:
                df_novo = pd.DataFrame(regs)
                salvar_sql(df_novo, "historico_producao", modo='append')

                if check_padrao:
                    # Atualiza Tabela de Padrões
                    df_p = pd.DataFrame([{"Data": data_f.strftime("%d/%m/%Y"), "Produto": t_sel, "Cor": cor_sel, "Lote": lote_id, "Status": "Padrão"}])
                    salvar_sql(df_p, "padroes_registrados", modo='append')

                    # Sincroniza Aba Mestra (Recalcula kg/L baseado no real)
                    vol_real_total = n_r * litros_u
                    df_m_atual = carregar_sql("aba_mestra")
                    for _, r in df_novo.iterrows():
                        novo_coef = (r['Quant ad (g)'] / 1000) / vol_real_total if vol_real_total > 0 else 0
                        mask = (df_m_atual['Tipo'] == t_sel) & (df_m_atual['Cor'] == cor_sel) & (df_m_atual['Pigmento'] == r['pigmento'])
                        if mask.any(): df_m_atual.loc[mask, 'Quant OP (kg)'] = novo_coef
                    salvar_sql(df_m_atual, "aba_mestra")

                st.success("Lote registrado no Banco!"); st.balloons(); time.sleep(1); st.rerun()

# --- 📈 ABA: GRÁFICOS CEP ---
elif aba == "📈 Controle":
    st.title("📈 Dashboard de Qualidade (CEP)")
    df_hist = carregar_sql("historico_producao")
    if df_hist.empty: st.info("Sem dados no banco.")
    else:
        c1, c2 = st.columns(2)
        p_sel = c1.selectbox("Produto", sorted(df_hist['tipo de produto'].unique()))
        c_sel = c2.selectbox("Cor", sorted(df_hist[df_hist['tipo de produto'] == p_sel]['cor'].unique()))
        df_plot = df_hist[(df_hist['tipo de produto'] == p_sel) & (df_hist['cor'] == c_sel)].copy()
        
        if not df_plot.empty:
            df_plot['Var %'] = ((df_plot['Quant ad (g)'] / df_plot['Quantidade OP'].replace(0, np.nan)) - 1) * 100
            st.line_chart(df_plot.pivot_table(index='lote', columns='pigmento', values='Var %'))
            df_plot['Situação'] = df_plot.apply(lambda r: "⚠️ Fora" if abs(r['Var %']) > 10 else "✅ Ok", axis=1)
            st.dataframe(df_plot, use_container_width=True)

# --- 📜 BANCO DE DADOS ---
elif aba == "📜 Banco de Dados":
    st.title("📜 Gestão de Dados (SQLite)")
    df_h = carregar_sql("historico_producao")
    
    with st.expander("🌟 Homologar Lote Antigo como Padrão"):
        l_busca = st.text_input("Número do Lote:")
        if st.button("Confirmar Homologação") and l_busca:
            l_data = df_h[df_h['lote'].astype(str) == l_busca]
            if not l_data.empty:
                # Lógica de atualização de padrão e mestra idêntica ao Registro
                df_p = pd.DataFrame([{"Data": l_data.iloc[0]['data'], "Produto": l_data.iloc[0]['tipo de produto'], "Cor": l_data.iloc[0]['cor'], "Lote": l_busca, "Status": "Padrão"}])
                salvar_sql(df_p, "padroes_registrados", modo='append')
                st.success("Padrão atualizado!"); time.sleep(1); st.rerun()
    
    ed_h = st.data_editor(df_h, num_rows="dynamic", use_container_width=True)
    if st.button("💾 Salvar Alterações"):
        salvar_sql(ed_h, "historico_producao")
        st.success("Banco de Dados Atualizado!")

# --- DEMAIS ABAS ---
elif aba == "📋 Padrões":
    st.title("📋 Histórico de Padrões")
    df_p = carregar_sql("padroes_registrados")
    ed_p = st.data_editor(df_p, num_rows="dynamic", use_container_width=True)
    if st.button("Salvar Padrões"):
        salvar_sql(ed_p, "padroes_registrados"); st.success("Salvo!")

elif aba == "📊 Aba Mestra":
    st.title("📊 Editor Aba Mestra (kg/L)")
    df_m = carregar_sql("aba_mestra")
    ed_m = st.data_editor(df_m, num_rows="dynamic", use_container_width=True)
    if st.button("💾 Salvar Mestra"):
        salvar_sql(ed_m, "aba_mestra"); st.success("Fórmulas Atualizadas!")

elif aba == "📂 Importar CSV":
    st.title("📂 Manutenção do Banco")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Importar Dados")
        up = st.file_uploader("Selecione o arquivo CSV", type="csv")
        alvo = st.selectbox("Tabela Destino", ["aba_mestra", "historico_producao", "padroes_registrados"])
        if up and st.button("🚀 Injetar no SQLite"):
            df_imp = pd.read_csv(up, sep=None, engine='python', encoding='utf-8-sig')
            salvar_sql(df_imp, alvo, modo='append')
            st.success("Dados injetados!"); time.sleep(1); st.rerun()
    with c2:
        st.subheader("Zona de Perigo")
        if st.button("🔴 RESET TOTAL DO BANCO"):
            conn = get_connection()
            conn.execute("DROP TABLE IF EXISTS aba_mestra")
            conn.execute("DROP TABLE IF EXISTS historico_producao")
            conn.execute("DROP TABLE IF EXISTS padroes_registrados")
            conn.commit(); conn.close(); init_db()
            st.warning("Banco de dados reiniciado!"); st.rerun()

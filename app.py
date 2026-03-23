import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
import os
import time
import io
import re
from datetime import datetime, date

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

# --- 🗄️ CONFIGURAÇÃO SQLITE ---
DB_NAME = "colortex_factory.db"

def get_connection():
    return sqlite3.connect(DB_NAME)

def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS aba_mestra 
                 (Tipo TEXT, Cor TEXT, Pigmento TEXT, [Quant OP (kg)] REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS historico_producao 
                 (data TEXT, lote TEXT, tipo_produto TEXT, cor TEXT, pigmento TEXT, 
                  [quant_ad_g] REAL, [quantidade_op] REAL, [n_plan] REAL, [n_real] REAL, [litros_unit] REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS padroes_registrados 
                 (Data TEXT, Produto TEXT, Cor TEXT, Lote TEXT, Status TEXT)''')
    conn.commit()
    conn.close()

init_db()

def carregar_dados_sql(tabela):
    conn = get_connection()
    df = pd.read_sql(f"SELECT * FROM {tabela}", conn)
    conn.close()
    # Força conversão numérica ao carregar para o Dashboard não dar erro de 'str'
    cols_num = ['quant_ad_g', 'quantidade_op', 'n_plan', 'n_real', 'litros_unit']
    for col in cols_num:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
    return df

def salvar_dados_sql(df, tabela, modo='replace'):
    conn = get_connection()
    df.to_sql(tabela, conn, if_exists=modo, index=False)
    conn.close()

# --- NAVEGAÇÃO ---
menu = ["🚀 Registro", "📈 Controle", "📜 Banco de Dados", "📋 Padrões", "📊 Aba Mestra", "📂 Importar CSV"]
aba = st.sidebar.radio("Navegação:", menu)

# --- 🚀 ABA: PRODUÇÃO ---
if aba == "🚀 Registro":
    st.title("🚀 Registro de Pigmentação")
    df_mestra = carregar_dados_sql("aba_mestra")
    if df_mestra.empty:
        st.warning("Aba Mestra vazia. Importe os dados primeiro.")
    else:
        c1, c2, c3, c4 = st.columns([1.5, 1.5, 1, 1])
        t_sel = c1.selectbox("Produto", sorted(df_mestra['Tipo'].unique()))
        cor_sel = c2.selectbox("Cor", sorted(df_mestra[df_mestra['Tipo'] == t_sel]['Cor'].unique()))
        lote_id = c3.text_input("Lote")
        data_f = c4.date_input("Data", date.today())

        v1, v2, v3, v4 = st.columns([1, 1, 2, 1.5])
        n_p = v1.number_input("# Unid Plan", min_value=1.0, value=1.0)
        n_r = v2.number_input("# Unid Real", min_value=1.0, value=1.0)
        sel_v = v3.select_slider("Embalagem:", options=["0,9L", "3,6L", "15L", "18L", "25kg", "Outro"], value="15L")
        litros_u = float(sel_v.replace('L','').replace('kg','').replace(',','.')) if sel_v != "Outro" else v3.number_input("Valor Unit:", value=15.0)
        check_padrão = v4.checkbox("🌟 Novo Padrão")

        formula = df_mestra[(df_mestra['Tipo'] == t_sel) & (df_mestra['Cor'] == cor_sel)]
        st.divider()

        regs = []
        for i, row in formula.iterrows():
            espec_final_g = round((float(row['Quant OP (kg)']) * 1000) * (n_p * litros_u), 2)
            with st.container():
                col_i, col_p = st.columns([1.5, 3.5])
                col_i.subheader(row['Pigmento']); col_i.write(f"Espec: {espec_final_g}g")
                n_t = col_i.number_input(f"Toques", min_value=1, value=1, key=f"nt_{i}")
                s_ad = sum([col_p.columns(5)[(t-1)%5].number_input(f"T{t}", min_value=0.0, format="%.2f", key=f"v_{i}_{t}") for t in range(1, int(n_t) + 1)])
                col_p.info(f"Total: {s_ad:.2f} g")
            
            regs.append({"data": data_f.strftime("%d/%m/%Y"), "lote": lote_id, "tipo_produto": t_sel, "cor": cor_sel, "pigmento": row['Pigmento'], "quant_ad_g": s_ad, "quantidade_op": espec_final_g, "n_plan": n_p, "n_real": n_r, "litros_unit": litros_u})
            st.divider()

        if st.button("💾 SALVAR LOTE"):
            if not lote_id: st.error("Lote obrigatório.")
            else:
                salvar_dados_sql(pd.DataFrame(regs), "historico_producao", modo='append')
                st.success("Lote salvo!"); time.sleep(1); st.rerun()

# --- 📈 ABA: CONTROLE ---
elif aba == "📈 Controle":
    st.title("📈 Dashboard de Qualidade")
    df_hist = carregar_dados_sql("historico_producao")
    if df_hist.empty: st.info("Sem dados registrados.")
    else:
        c1, c2 = st.columns(2)
        p_sel = c1.selectbox("Produto", sorted(df_hist['tipo_produto'].unique()))
        c_sel = c2.selectbox("Cor", sorted(df_hist[df_hist['tipo_produto'] == p_sel]['cor'].unique()))
        df_plot = df_hist[(df_hist['tipo_produto'] == p_sel) & (df_hist['cor'] == c_sel)].copy()
        
        if not df_plot.empty:
            # Garante que as colunas são números para evitar o erro 'str' - 'str'
            df_plot['quant_ad_g'] = pd.to_numeric(df_plot['quant_ad_g'], errors='coerce')
            df_plot['quantidade_op'] = pd.to_numeric(df_plot['quantidade_op'], errors='coerce')
            
            df_plot['Var %'] = ((df_plot['quant_ad_g'] / df_plot['quantidade_op'].replace(0, np.nan)) - 1) * 100
            st.line_chart(df_plot.pivot_table(index='lote', columns='pigmento', values='Var %'))
            st.dataframe(df_plot, use_container_width=True)

# --- 📜 BANCO DE DADOS ---
elif aba == "📜 Banco de Dados":
    st.title("📜 Gestão de Dados")
    df_hist = carregar_dados_sql("historico_producao")
    ed_h = st.data_editor(df_hist, num_rows="dynamic", use_container_width=True)
    if st.button("💾 Salvar Alterações"):
        salvar_dados_sql(ed_h, "historico_producao"); st.success("Atualizado!")

# --- 📊 ABA MESTRA ---
elif aba == "📊 Aba Mestra":
    st.title("📊 Editor Aba Mestra (kg/L)")
    df_m = carregar_dados_sql("aba_mestra")
    ed_m = st.data_editor(df_m, num_rows="dynamic", use_container_width=True)
    if st.button("💾 Salvar Mestra"):
        salvar_dados_sql(ed_m, "aba_mestra"); st.success("Salvo!")

# --- 📂 ABA: IMPORTAR CSV (RECALCULO BLINDADO) ---
elif aba == "📂 Importar CSV":
    st.title("📂 Importação Inteligente")
    st.info("💡 A 'quantidade_op' será recalculada com base nos coeficientes da Aba Mestra atual.")
    
    up = st.file_uploader("Selecione o arquivo CSV", type="csv")
    alvo = st.selectbox("Destino", ["aba_mestra", "historico_producao"])
    
    if up and st.button("🚀 Confirmar Importação"):
        try:
            raw = up.read()
            try: text = raw.decode('latin-1')
            except: text = raw.decode('utf-8', errors='ignore')
            
            df_imp = pd.read_csv(io.StringIO(text), sep=None, engine='python')
            df_imp.columns = [c.strip().lower() for c in df_imp.columns] # Padroniza para minúsculas

            if alvo == "aba_mestra":
                df_imp = df_imp.iloc[:, :4]
                df_imp.columns = ['Tipo', 'Cor', 'Pigmento', 'Quant OP (kg)']
                df_imp['Quant OP (kg)'] = pd.to_numeric(df_imp['Quant OP (kg)'].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
                salvar_dados_sql(df_imp, "aba_mestra", modo='append')
                st.success("Mestra importada!")

            elif alvo == "historico_producao":
                df_mestra = carregar_dados_sql("aba_mestra")
                if df_mestra.empty:
                    st.error("⚠️ Importe a Aba Mestra PRIMEIRO.")
                    st.stop()
                
                # Mapeia colunas baseadas na foto do seu Excel
                df_imp = df_imp[['data', 'lote', 'tipo_produto', 'cor', 'pigmento', 'quant_ad_g', 'quantidade_op', 'n_plan', 'n_real', 'litros_unit']]
                
                # LIMPEZA NUMÉRICA ANTES DO CÁLCULO
                for col in ['quant_ad_g', 'quantidade_op', 'n_plan', 'n_real', 'litros_unit']:
                    df_imp[col] = df_imp[col].astype(str).str.replace(r'[^\d,.-]', '', regex=True).str.replace(',', '.')
                    df_imp[col] = pd.to_numeric(df_imp[col], errors='coerce').fillna(0.0)

                def rec_op(row):
                    match = df_mestra[(df_mestra['Tipo'] == str(row['tipo_produto'])) & 
                                    (df_mestra['Cor'] == str(row['cor'])) & 
                                    (df_mestra['Pigmento'] == str(row['pigmento']))]
                    if not match.empty:
                        coef = float(match.iloc[0]['Quant OP (kg)'])
                        return round((coef * 1000) * (float(row['n_plan']) * float(row['litros_unit'])), 2)
                    return float(row['quantidade_op'])

                df_imp['quantidade_op'] = df_imp.apply(rec_op, axis=1)
                salvar_dados_sql(df_imp, "historico_producao", modo='append')
                st.success("Histórico recalculado e importado!")
            
            time.sleep(1); st.rerun()
        except Exception as e:
            st.error(f"Erro no processamento: {e}")

    st.divider()
    with st.expander("⚠️ Reiniciar Sistema (Reboot)"):
        confirma = st.text_input("Digite APAGAR para resetar:")
        if st.button("🔴 RESET TOTAL") and confirma == "APAGAR":
            conn = get_connection()
            for t in ["aba_mestra", "historico_producao", "padroes_registrados"]: conn.execute(f"DROP TABLE IF EXISTS {t}")
            conn.commit(); conn.close()
            init_db(); st.rerun()

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

# --- 🗄️ CONFIGURAÇÃO SQLITE ---
DB_NAME = "colortex_factory.db"

def get_connection():
    return sqlite3.connect(DB_NAME)

def init_db():
    conn = get_connection()
    c = conn.cursor()
    # Criando tabelas com nomes de colunas fixos e seguros
    c.execute('''CREATE TABLE IF NOT EXISTS aba_mestra 
                 (Tipo TEXT, Cor TEXT, Pigmento TEXT, [Quant OP (kg)] REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS historico_producao 
                 (data TEXT, lote TEXT, tipo_produto TEXT, cor TEXT, pigmento TEXT, 
                  [quant_ad_g] REAL, [quantidade_op] REAL, [n_plan] REAL, [n_real] REAL, [litros_unit] REAL)''')
    conn.commit()
    conn.close()

init_db()

def carregar_dados_sql(tabela):
    conn = get_connection()
    df = pd.read_sql(f"SELECT * FROM {tabela}", conn)
    conn.close()
    
    # CONVERSÃO FORÇADA PARA NÚMEROS (Resolve o erro TypeError: str - str)
    cols_num = ['quant_ad_g', 'quantidade_op', 'n_plan', 'n_real', 'litros_unit', 'Quant OP (kg)']
    for col in cols_num:
        if col in df.columns:
            # Limpa vírgulas, espaços e letras (como 'L' ou 'g') e converte para float
            df[col] = df[col].astype(str).str.replace(r'[^\d,.-]', '', regex=True).str.replace(',', '.')
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
    return df

def salvar_dados_sql(df, tabela, modo='replace'):
    conn = get_connection()
    df.to_sql(tabela, conn, if_exists=modo, index=False)
    conn.close()

# --- NAVEGAÇÃO ---
menu = ["🚀 Registro", "📈 Controle", "📜 Banco de Dados", "📊 Aba Mestra", "📂 Importar CSV"]
aba = st.sidebar.radio("Navegação:", menu)

# --- 🚀 ABA: REGISTRO ---
if aba == "🚀 Registro":
    st.title("🚀 Registro de Produção")
    df_mestra = carregar_dados_sql("aba_mestra")
    if df_mestra.empty:
        st.warning("Aba Mestra vazia. Importe os dados primeiro.")
    else:
        c1, c2, c3 = st.columns([1.5, 1.5, 1])
        t_sel = c1.selectbox("Produto", sorted(df_mestra['Tipo'].unique()))
        cor_sel = c2.selectbox("Cor", sorted(df_mestra[df_mestra['Tipo'] == t_sel]['Cor'].unique()))
        lote_id = c3.text_input("Lote")
        
        v1, v2, v3 = st.columns([1, 1, 2])
        n_p = v1.number_input("# Plan", min_value=0.1, value=1.0)
        sel_v = v3.select_slider("Embalagem:", options=["0,9L", "3,6L", "15L", "18L", "25kg"], value="15L")
        litros_u = float(sel_v.replace('L','').replace('kg','').replace(',','.'))
        
        formula = df_mestra[(df_mestra['Tipo'] == t_sel) & (df_mestra['Cor'] == cor_sel)]
        st.divider()
        
        regs = []
        for i, row in formula.iterrows():
            espec_g = round((float(row['Quant OP (kg)']) * 1000) * (n_p * litros_u), 2)
            st.subheader(f"🧪 {row['Pigmento']}")
            st.caption(f"Especificado para este lote: {espec_g}g")
            s_ad = st.number_input(f"Quantidade Real Adicionada (g)", key=f"reg_{i}", format="%.2f")
            
            regs.append({
                "data": date.today().strftime("%d/%m/%Y"), "lote": lote_id, "tipo_produto": t_sel, 
                "cor": cor_sel, "pigmento": row['Pigmento'], "quant_ad_g": s_ad, 
                "quantidade_op": espec_g, "n_plan": n_p, "n_real": n_p, "litros_unit": litros_u
            })
            st.markdown("---")

        if st.button("💾 SALVAR NO BANCO DE DADOS"):
            if not lote_id: st.error("Por favor, informe o Lote.")
            else:
                salvar_dados_sql(pd.DataFrame(regs), "historico_producao", modo='append')
                st.success("Lote salvo com sucesso no Banco!"); time.sleep(1); st.rerun()

# --- 📈 ABA: CONTROLE (DASHBOARD CEP) ---
elif aba == "📈 Controle":
    st.title("📈 Dashboard de Qualidade")
    df_db = carregar_dados_sql("historico_producao")
    
    if df_db.empty:
        st.info("Banco de dados vazio. Importe o histórico na última aba.")
    else:
        c1, c2 = st.columns(2)
        p_sel = c1.selectbox("Filtrar Produto", sorted(df_db['tipo_produto'].unique()))
        c_sel = c2.selectbox("Filtrar Cor", sorted(df_db[df_db['tipo_produto'] == p_sel]['cor'].unique()))
        
        df_plot = df_db[(df_db['tipo_produto'] == p_sel) & (df_db['cor'] == c_sel)].copy()
        
        if not df_plot.empty:
            # Cálculo de Var % (Seguro contra divisões por zero)
            df_plot['Var %'] = ((df_plot['quant_ad_g'] / df_plot['quantidade_op'].replace(0, np.nan)) - 1) * 100
            
            st.subheader(f"Desvio de Pigmentação (%) - {p_sel} {c_sel}")
            st.line_chart(df_plot.pivot_table(index='lote', columns='pigmento', values='Var %'))
            st.write("**Dados Extraídos do SQLite:**")
            st.dataframe(df_plot, use_container_width=True)

# --- 📜 ABA: BANCO DE DADOS ---
elif aba == "📜 Banco de Dados":
    st.title("📜 Editor do Histórico (SQLite)")
    df_hist = carregar_dados_sql("historico_producao")
    st.info("💡 As alterações feitas aqui corrigem os gráficos instantaneamente.")
    ed_h = st.data_editor(df_hist, num_rows="dynamic", use_container_width=True)
    if st.button("💾 Aplicar Correções"):
        salvar_dados_sql(ed_h, "historico_producao")
        st.success("Banco de Dados atualizado!"); st.rerun()

# --- 📊 ABA MESTRA ---
elif aba == "📊 Aba Mestra":
    st.title("📊 Gestão de Fórmulas (Aba Mestra)")
    df_m = carregar_dados_sql("aba_mestra")
    ed_m = st.data_editor(df_m, num_rows="dynamic", use_container_width=True)
    if st.button("💾 Salvar Alterações na Mestra"):
        salvar_dados_sql(ed_m, "aba_mestra")
        st.success("Aba Mestra salva!"); st.rerun()

# --- 📂 ABA: IMPORTAR CSV (BOTÃO DE RESET) ---
elif aba == "📂 Importar CSV":
    st.title("📂 Importação e Manutenção")
    
    up = st.file_uploader("Selecione o arquivo CSV", type="csv")
    alvo = st.selectbox("Onde salvar?", ["aba_mestra", "historico_producao"])
    
    if up and st.button("🚀 Injetar no Banco"):
        try:
            raw = up.read()
            try: text = raw.decode('latin-1')
            except: text = raw.decode('utf-8', errors='ignore')
            df_imp = pd.read_csv(io.StringIO(text), sep=None, engine='python')

            if alvo == "aba_mestra":
                # PEGA PELA POSIÇÃO (Resolve o erro de nome da coluna)
                df_imp = df_imp.iloc[:, :4] 
                df_imp.columns = ['Tipo', 'Cor', 'Pigmento', 'Quant OP (kg)']
                salvar_dados_sql(df_imp, "aba_mestra", modo='append')
                st.success("Aba Mestra alimentada com sucesso!")
            else:
                # Padroniza as 10 colunas do histórico
                df_imp = df_imp.iloc[:, :10]
                df_imp.columns = ['data', 'lote', 'tipo_produto', 'cor', 'pigmento', 'quant_ad_g', 'quantidade_op', 'n_plan', 'n_real', 'litros_unit']
                salvar_dados_sql(df_imp, "historico_producao", modo='append')
                st.success("Histórico adicionado ao banco!")
            time.sleep(1); st.rerun()
        except Exception as e:
            st.error(f"Erro na importação: {e}")

    st.markdown("---")
    st.subheader("⚠️ Zona de Perigo")
    st.write("Se os gráficos estiverem dando erro, use o botão abaixo para limpar o banco e reimportar os arquivos.")
    
    if st.button("🔴 RESET TOTAL DO BANCO DE DADOS"):
        conn = get_connection()
        conn.execute("DROP TABLE IF EXISTS aba_mestra")
        conn.execute("DROP TABLE IF EXISTS historico_producao")
        conn.commit(); conn.close()
        init_db()
        st.warning("Banco de dados apagado! Reimporte os arquivos agora.")
        time.sleep(1); st.rerun()

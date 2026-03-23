import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
import os
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
    
    # Limpeza profunda para garantir que o Dashboard receba NÚMEROS
    cols_num = ['quant_ad_g', 'quantidade_op', 'n_plan', 'n_real', 'litros_unit']
    for col in cols_num:
        if col in df.columns:
            # Remove qualquer caractere que não seja número ou ponto/vírgula
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
        
        formula = df_mestra[(df_mestra['Tipo'] == t_sel) & (df_mestra['Cor'] == cor_sel)]
        regs = []
        for i, row in formula.iterrows():
            st.write(f"**{row['Pigmento']}**")
            s_ad = st.number_input(f"Qtd Adicionada (g) - {row['Pigmento']}", key=f"reg_{i}", format="%.2f")
            regs.append({
                "data": date.today().strftime("%d/%m/%Y"), "lote": lote_id, "tipo_produto": t_sel, 
                "cor": cor_sel, "pigmento": row['Pigmento'], "quant_ad_g": s_ad, 
                "quantidade_op": 0.0, "n_plan": 1.0, "n_real": 1.0, "litros_unit": 15.0
            })

        if st.button("💾 SALVAR NO BANCO"):
            salvar_dados_sql(pd.DataFrame(regs), "historico_producao", modo='append')
            st.success("Salvo com sucesso!"); time.sleep(1); st.rerun()

# --- 📈 ABA: CONTROLE (PUXA DO BANCO) ---
elif aba == "📈 Controle":
    st.title("📈 Dashboard de Qualidade (Banco de Dados)")
    df_db = carregar_dados_sql("historico_producao")
    
    if df_db.empty:
        st.info("Banco de dados vazio. Importe o histórico.")
    else:
        c1, c2 = st.columns(2)
        p_sel = c1.selectbox("Produto", sorted(df_db['tipo_produto'].unique()))
        c_sel = c2.selectbox("Cor", sorted(df_db[df_db['tipo_produto'] == p_sel]['cor'].unique()))
        
        df_plot = df_db[(df_db['tipo_produto'] == p_sel) & (df_db['cor'] == c_sel)].copy()
        
        if not df_plot.empty:
            # Cálculos seguros (Tudo já foi convertido no carregar_dados_sql)
            df_plot['Var %'] = ((df_plot['quant_ad_g'] / df_plot['quantidade_op'].replace(0, np.nan)) - 1) * 100
            st.line_chart(df_plot.pivot_table(index='lote', columns='pigmento', values='Var %'))
            st.dataframe(df_plot, use_container_width=True)

# --- 📜 BANCO DE DADOS ---
elif aba == "📜 Banco de Dados":
    st.title("📜 Editor do Banco de Dados")
    df_hist = carregar_dados_sql("historico_producao")
    ed_h = st.data_editor(df_hist, num_rows="dynamic", use_container_width=True)
    if st.button("💾 Atualizar Banco"):
        salvar_dados_sql(ed_h, "historico_producao"); st.success("Banco Atualizado!")

# --- 📊 ABA MESTRA ---
elif aba == "📊 Aba Mestra":
    st.title("📊 Aba Mestra")
    df_m = carregar_dados_sql("aba_mestra")
    ed_m = st.data_editor(df_m, num_rows="dynamic", use_container_width=True)
    if st.button("💾 Salvar Mestra"):
        salvar_dados_sql(ed_m, "aba_mestra"); st.success("Salvo!")

# --- 📂 ABA: IMPORTAR CSV (BOTÃO VERMELHO AQUI) ---
elif aba == "📂 Importar CSV":
    st.title("📂 Importar para o Banco de Dados")
    
    up = st.file_uploader("Selecione o arquivo CSV", type="csv")
    alvo = st.selectbox("Onde salvar?", ["aba_mestra", "historico_producao"])
    
    if up and st.button("🚀 Confirmar Injeção"):
        try:
            raw = up.read()
            try: text = raw.decode('latin-1')
            except: text = raw.decode('utf-8', errors='ignore')
            
            df_imp = pd.read_csv(io.StringIO(text), sep=None, engine='python')
            df_imp.columns = [c.strip().lower() for c in df_imp.columns]

            if alvo == "aba_mestra":
                df_imp.columns = ['Tipo', 'Cor', 'Pigmento', 'Quant OP (kg)']
                salvar_dados_sql(df_imp, "aba_mestra", modo='append')
                st.success("Mestra Atualizada!")
            else:
                df_imp.columns = ['data', 'lote', 'tipo_produto', 'cor', 'pigmento', 'quant_ad_g', 'quantidade_op', 'n_plan', 'n_real', 'litros_unit']
                salvar_dados_sql(df_imp, "historico_producao", modo='append')
                st.success("Histórico Atualizado!")
            time.sleep(1); st.rerun()
        except Exception as e:
            st.error(f"Erro: {e}")

    st.markdown("---")
    st.subheader("⚠️ Zona de Perigo")
    
    # Botão de reset agora fora de qualquer condicional de texto para garantir visibilidade
    if st.button("🔴 APAGAR TODO O BANCO DE DADOS (RESET)"):
        conn = get_connection()
        conn.execute("DROP TABLE IF EXISTS aba_mestra")
        conn.execute("DROP TABLE IF EXISTS historico_producao")
        conn.commit()
        conn.close()
        init_db()
        st.warning("O Banco de Dados foi reiniciado!")
        time.sleep(1)
        st.rerun()

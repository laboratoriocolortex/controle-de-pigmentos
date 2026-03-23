import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
import io
import time
from datetime import date

# 1. Configuração de Layout
st.set_page_config(page_title="Colortex 2026 - Gestão de R&D", layout="wide", page_icon="🧪")

# --- 🗄️ CONFIGURAÇÃO SQLITE ---
DB_NAME = "colortex_factory.db"

def get_connection():
    return sqlite3.connect(DB_NAME)

def init_db():
    conn = get_connection()
    c = conn.cursor()
    # Criando tabelas com a estrutura exata do seu "Banco de Dados"
    c.execute('''CREATE TABLE IF NOT EXISTS aba_mestra 
                 (Tipo TEXT, Cor TEXT, Pigmento TEXT, [Quant OP (kg)] REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS historico_producao 
                 (data TEXT, lote TEXT, tipo_produto TEXT, cor TEXT, pigmento TEXT, 
                  quant_ad_g REAL, quantidade_op REAL, n_plan REAL, n_real REAL, litros_unit REAL)''')
    conn.commit()
    conn.close()

init_db()

def carregar_dados_sql(tabela):
    conn = get_connection()
    df = pd.read_sql(f"SELECT * FROM {tabela}", conn)
    conn.close()
    
    # ESPELHAMENTO E PADRONIZAÇÃO DE COLUNAS (O SEGREDO DO RECONHECIMENTO)
    if tabela == "historico_producao":
        # Forçamos os nomes para garantir que o gráfico reconheça
        df.columns = ['data', 'lote', 'tipo_produto', 'cor', 'pigmento', 
                      'quant_ad_g', 'quantidade_op', 'n_plan', 'n_real', 'litros_unit']
        
        # Limpeza de números (Troca vírgula por ponto e remove textos)
        cols_calc = ['quant_ad_g', 'quantidade_op']
        for col in cols_calc:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.').str.replace(r'[^\d.-]', '', regex=True), errors='coerce').fillna(0.0)
    
    elif tabela == "aba_mestra":
        df.columns = ['Tipo', 'Cor', 'Pigmento', 'Quant OP (kg)']
        df['Quant OP (kg)'] = pd.to_numeric(df['Quant OP (kg)'].astype(str).str.replace(',', '.'), errors='coerce').fillna(0.0)
        
    return df

def salvar_dados_sql(df, tabela, modo='replace'):
    conn = get_connection()
    df.to_sql(tabela, conn, if_exists=modo, index=False)
    conn.close()

# --- NAVEGAÇÃO ---
menu = ["🚀 Registro", "📈 Controle (CEP)", "📜 Banco de Dados", "📊 Aba Mestra", "📂 Importar CSV"]
aba = st.sidebar.radio("Navegação:", menu)

# --- 🚀 ABA: REGISTRO (Salva no Banco) ---
if aba == "🚀 Registro":
    st.title("🚀 Novo Registro de Lote")
    df_mestra = carregar_dados_sql("aba_mestra")
    if df_mestra.empty:
        st.warning("Aba Mestra vazia. Importe os dados primeiro.")
    else:
        c1, c2, l = st.columns([2,2,1])
        t_sel = c1.selectbox("Produto", sorted(df_mestra['Tipo'].unique()))
        cor_sel = c2.selectbox("Cor", sorted(df_mestra[df_mestra['Tipo'] == t_sel]['Cor'].unique()))
        lote_id = l.text_input("Lote")
        
        formula = df_mestra[(df_mestra['Tipo'] == t_sel) & (df_mestra['Cor'] == cor_sel)]
        regs = []
        for i, row in formula.iterrows():
            st.write(f"**{row['Pigmento']}**")
            val = st.number_input(f"Gramos adicionados ({row['Pigmento']})", key=f"r_{i}", format="%.2f")
            regs.append({
                "data": date.today().strftime("%d/%m/%Y"), "lote": lote_id, "tipo_produto": t_sel, 
                "cor": cor_sel, "pigmento": row['Pigmento'], "quant_ad_g": val, 
                "quantidade_op": 1.0, "n_plan": 1.0, "n_real": 1.0, "litros_unit": 15.0
            })
        if st.button("💾 Gravar no Banco de Dados"):
            salvar_dados_sql(pd.DataFrame(regs), "historico_producao", modo='append')
            st.success("Gravado com sucesso!"); time.sleep(1); st.rerun()

# --- 📈 ABA: CONTROLE (CEP) - PUXA DIRETO DO BANCO ---
elif aba == "📈 Controle (CEP)":
    st.title("📈 Gráfico CEP (Fonte: Banco de Dados)")
    # O gráfico agora ignora o CSV e lê o Banco que você editou
    df_cep = carregar_dados_sql("historico_producao")
    
    if df_cep.empty:
        st.info("O Banco de Dados está vazio.")
    else:
        prod = st.selectbox("Escolha o Produto para Análise", sorted(df_cep['tipo_produto'].unique()))
        # Filtra apenas o que está no banco
        df_view = df_cep[df_cep['tipo_produto'] == prod].copy()
        
        # Cálculo de Variância % baseado nas colunas espelhadas
        df_view['Var %'] = ((df_view['quant_ad_g'] / df_view['quantidade_op'].replace(0, np.nan)) - 1) * 100
        
        st.subheader(f"Variabilidade por Lote - {prod}")
        # Pivot para o gráfico reconhecer os pigmentos como linhas diferentes
        chart_data = df_view.pivot_table(index='lote', columns='pigmento', values='Var %')
        st.line_chart(chart_data)
        
        st.write("**Visualização do Banco de Dados Filtrado:**")
        st.dataframe(df_view, use_container_width=True)

# --- 📜 ABA: BANCO DE DADOS (EDITOR) ---
elif aba == "📜 Banco de Dados":
    st.title("📜 Editor do Banco de Dados")
    st.caption("Qualquer alteração feita aqui altera o gráfico CEP automaticamente.")
    df_h = carregar_dados_sql("historico_producao")
    ed_h = st.data_editor(df_h, num_rows="dynamic", use_container_width=True)
    if st.button("💾 Salvar Alterações no Banco"):
        salvar_dados_sql(ed_h, "historico_producao")
        st.success("Banco de Dados Atualizado!"); st.rerun()

# --- 📂 ABA: IMPORTAR CSV (ALIMENTA O BANCO) ---
elif aba == "📂 Importar CSV":
    st.title("📂 Alimentar Banco de Dados")
    up = st.file_uploader("Selecione o arquivo CSV", type="csv")
    alvo = st.selectbox("Destino", ["aba_mestra", "historico_producao"])
    
    if up and st.button("🚀 Injetar Dados"):
        try:
            raw = up.read()
            text = raw.decode('latin-1')
            df_imp = pd.read_csv(io.StringIO(text), sep=None, engine='python')
            
            if alvo == "aba_mestra":
                df_imp = df_imp.iloc[:, :4] # Pega as 4 colunas pela posição
                df_imp.columns = ['Tipo', 'Cor', 'Pigmento', 'Quant OP (kg)']
                salvar_dados_sql(df_imp, "aba_mestra", modo='append')
            else:
                df_imp = df_imp.iloc[:, :10] # Pega as 10 colunas pela posição
                df_imp.columns = ['data', 'lote', 'tipo_produto', 'cor', 'pigmento', 
                                  'quant_ad_g', 'quantidade_op', 'n_plan', 'n_real', 'litros_unit']
                salvar_dados_sql(df_imp, "historico_producao", modo='append')
            
            st.success("Dados injetados com sucesso no Banco!"); time.sleep(1); st.rerun()
        except Exception as e:
            st.error(f"Erro na importação: {e}")

    st.divider()
    if st.button("🔴 RESET TOTAL (LIMPAR TUDO)"):
        conn = get_connection()
        conn.execute("DROP TABLE IF EXISTS aba_mestra")
        conn.execute("DROP TABLE IF EXISTS historico_producao")
        conn.commit(); conn.close(); init_db(); st.rerun()

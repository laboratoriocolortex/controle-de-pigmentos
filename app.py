import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
import io
import time
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
    c.execute('''CREATE TABLE IF NOT EXISTS aba_mestra 
                 (Tipo TEXT, Cor TEXT, Pigmento TEXT, [Quant OP (kg)] REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS historico_producao 
                 (data TEXT, lote TEXT, tipo_produto TEXT, cor TEXT, pigmento TEXT, 
                  quant_ad_g REAL, quantidade_op REAL, n_plan REAL, n_real REAL, litros_unit REAL, padrao INTEGER DEFAULT 0)''')
    conn.commit()
    conn.close()

init_db()

def carregar_dados_sql(tabela):
    conn = get_connection()
    df = pd.read_sql(f"SELECT * FROM {tabela}", conn)
    conn.close()
    
    # Padronização de Colunas e Limpeza Numérica
    if tabela == "historico_producao":
        cols_num = ['quant_ad_g', 'quantidade_op', 'n_plan', 'n_real', 'litros_unit']
        for col in cols_num:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.').str.replace(r'[^\d.-]', '', regex=True), errors='coerce').fillna(0.0)
    return df

def salvar_dados_sql(df, tabela, modo='replace'):
    conn = get_connection()
    df.to_sql(tabela, conn, if_exists=modo, index=False)
    conn.close()

# --- NAVEGAÇÃO ---
menu = ["🚀 Registro", "📈 Controle (CEP)", "📜 Banco de Dados", "📊 Aba Mestra", "📂 Importar CSV"]
aba = st.sidebar.radio("Navegação:", menu)

# --- 🚀 ABA: REGISTRO ---
if aba == "🚀 Registro":
    st.title("🚀 Registro de Pigmentação")
    df_mestra = carregar_dados_sql("aba_mestra")
    
    if df_mestra.empty:
        st.warning("Aba Mestra vazia.")
    else:
        c1, c2, c3, c4 = st.columns([1.5, 1.5, 1, 1])
        t_sel = c1.selectbox("Produto", sorted(df_mestra['Tipo'].unique()))
        cor_sel = c2.selectbox("Cor", sorted(df_mestra[df_mestra['Tipo'] == t_sel]['Cor'].unique()))
        lote_id = c3.text_input("Lote")
        data_f = c4.date_input("Data", date.today())

        v1, v2, v3, v4 = st.columns([1, 1, 2, 1])
        n_p = v1.number_input("# Unid Plan", min_value=0.1, value=1.0)
        n_r = v2.number_input("# Unid Real", min_value=0.1, value=1.0)
        sel_v = v3.select_slider("Embalagem:", options=["0,9L", "3,6L", "15L", "18L", "25kg", "Outro"], value="15L")
        litros_u = float(re.sub(r'[^\d.]', '', sel_v.replace(',','.'))) if sel_v != "Outro" else v3.number_input("Valor Unit:", value=15.0)
        is_padrao = v4.checkbox("Lote Padrão?")

        formula = df_mestra[(df_mestra['Tipo'] == t_sel) & (df_mestra['Cor'] == cor_sel)]
        st.divider()

        regs = []
        for i, row in formula.iterrows():
            espec_final_g = round((float(row['Quant OP (kg)']) * 1000) * (n_p * litros_u), 2)
            with st.container():
                col_info, col_toques = st.columns([1.5, 3.5])
                col_info.subheader(row['Pigmento'])
                col_info.write(f"Espec: **{espec_final_g}g**")
                
                qtd_toques = col_info.number_input(f"Toques", min_value=1, value=1, key=f"nt_{i}")
                
                # Gerador de campos para toques
                s_ad = 0.0
                cols_t = col_toques.columns(5)
                for t in range(int(qtd_toques)):
                    val_t = cols_t[t % 5].number_input(f"T{t+1} (g)", min_value=0.0, key=f"v_{i}_{t}", format="%.2f")
                    s_ad += val_t
                
                col_info.info(f"Total: {s_ad:.2f} g")
            
            regs.append({
                "data": data_f.strftime("%d/%m/%Y"), "lote": lote_id, "tipo_produto": t_sel, 
                "cor": cor_sel, "pigmento": row['Pigmento'], "quant_ad_g": s_ad, 
                "quantidade_op": espec_final_g, "n_plan": n_p, "n_real": n_r, 
                "litros_unit": litros_u, "padrao": 1 if is_padrao else 0
            })
            st.divider()

        if st.button("💾 SALVAR LOTE NO BANCO"):
            if not lote_id: st.error("Lote é obrigatório.")
            else:
                salvar_dados_sql(pd.DataFrame(regs), "historico_producao", modo='append')
                st.success("Lote registrado!"); time.sleep(1); st.rerun()

# --- 📈 ABA: CONTROLE (CEP) ---
elif aba == "📈 Controle (CEP)":
    st.title("📈 Controle Estatístico de Processo")
    df_cep = carregar_dados_sql("historico_producao")
    
    if df_cep.empty:
        st.info("Sem dados no banco.")
    else:
        c1, c2 = st.columns(2)
        p_sel = c1.selectbox("Produto", sorted(df_cep['tipo_produto'].unique()))
        # Filtro de cor agora funcional:
        cores_disp = sorted(df_cep[df_cep['tipo_produto'] == p_sel]['cor'].unique())
        cor_sel = c2.selectbox("Cor", cores_disp)
        
        df_view = df_cep[(df_cep['tipo_produto'] == p_sel) & (df_cep['cor'] == cor_sel)].copy()
        
        if not df_view.empty:
            df_view['Var %'] = ((df_view['quant_ad_g'] / df_view['quantidade_op'].replace(0, np.nan)) - 1) * 100
            
            st.subheader(f"Variância % - {p_sel} ({cor_sel})")
            chart_data = df_view.pivot_table(index='lote', columns='pigmento', values='Var %')
            st.line_chart(chart_data)
            st.dataframe(df_view, use_container_width=True)

# --- 📜 ABA: BANCO DE DADOS ---
elif aba == "📜 Banco de Dados":
    st.title("📜 Gestão do Banco de Dados")
    df_db = carregar_dados_sql("historico_producao")
    
    # Adicionando coluna para exclusão manual se necessário
    st.write("Edite os valores abaixo ou marque para exclusão:")
    ed_db = st.data_editor(df_db, num_rows="dynamic", use_container_width=True, key="editor_db")
    
    if st.button("💾 Salvar Alterações"):
        salvar_dados_sql(ed_db, "historico_producao")
        st.success("Banco atualizado!"); st.rerun()

# --- 📊 ABA MESTRA ---
elif aba == "📊 Aba Mestra":
    st.title("📊 Aba Mestra (Fórmulas)")
    df_m = carregar_dados_sql("aba_mestra")
    ed_m = st.data_editor(df_m, num_rows="dynamic", use_container_width=True)
    if st.button("💾 Salvar Aba Mestra"):
        salvar_dados_sql(ed_m, "aba_mestra")
        st.success("Mestra atualizada!"); st.rerun()

# --- 📂 ABA: IMPORTAR CSV ---
elif aba == "📂 Importar CSV":
    st.title("📂 Importação")
    up = st.file_uploader("Selecione o CSV", type="csv")
    alvo = st.selectbox("Destino", ["aba_mestra", "historico_producao"])
    
    if up and st.button("🚀 Confirmar"):
        try:
            raw = up.read()
            try: text = raw.decode('latin-1')
            except: text = raw.decode('utf-8', errors='ignore')
            df_imp = pd.read_csv(io.StringIO(text), sep=None, engine='python')
            
            if alvo == "aba_mestra":
                df_imp = df_imp.iloc[:, :4]
                df_imp.columns = ['Tipo', 'Cor', 'Pigmento', 'Quant OP (kg)']
                salvar_dados_sql(df_imp, "aba_mestra", modo='append')
            else:
                # Garante que as 11 colunas (incluindo 'padrao') existam
                if df_imp.shape[1] < 11: df_imp['padrao'] = 0
                df_imp = df_imp.iloc[:, :11]
                df_imp.columns = ['data', 'lote', 'tipo_produto', 'cor', 'pigmento', 'quant_ad_g', 'quantidade_op', 'n_plan', 'n_real', 'litros_unit', 'padrao']
                salvar_dados_sql(df_imp, "historico_producao", modo='append')
            
            st.success("Importado com sucesso!"); time.sleep(1); st.rerun()
        except Exception as e:
            st.error(f"Erro: {e}")

    st.divider()
    if st.button("🔴 RESET TOTAL"):
        conn = get_connection()
        conn.execute("DROP TABLE IF EXISTS aba_mestra")
        conn.execute("DROP TABLE IF EXISTS historico_producao")
        conn.commit(); conn.close(); init_db(); st.rerun()

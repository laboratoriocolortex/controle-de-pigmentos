import streamlit as st
import pandas as pd
import sqlite3
import os
import time
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
    # Criação das tabelas com os nomes de colunas do seu código original
    c.execute('''CREATE TABLE IF NOT EXISTS aba_mestra 
                 (Tipo TEXT, Cor TEXT, Pigmento TEXT, [Quant OP (kg)] REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS historico_producao 
                 (data TEXT, lote TEXT, [tipo de produto] TEXT, cor TEXT, pigmento TEXT, 
                  [Quant ad (g)] REAL, [Quantidade OP] REAL, [#Plan] REAL, [#Real] REAL, [Litros/Unit] REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS padroes_registrados 
                 (Data TEXT, Produto TEXT, Cor TEXT, Lote TEXT, Status TEXT)''')
    conn.commit()
    conn.close()

init_db()

# --- 🛡️ FUNÇÕES DE MANIPULAÇÃO SQL ---
def carregar_dados_sql(tabela):
    conn = get_connection()
    df = pd.read_sql(f"SELECT * FROM {tabela}", conn)
    conn.close()
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
        st.warning("Aba Mestra vazia no Banco de Dados. Use a aba 'Importar CSV'.")
    else:
        c1, c2, c3, c4 = st.columns([1.5, 1.5, 1, 1])
        t_sel = c1.selectbox("Produto", sorted(df_mestra['Tipo'].unique()))
        cor_sel = c2.selectbox("Cor", sorted(df_mestra[df_mestra['Tipo'] == t_sel]['Cor'].unique()))
        lote_id = c3.text_input("Lote")
        data_f = c4.date_input("Data", date.today())

        v1, v2, v3, v4 = st.columns([1, 1, 2, 1.5])
        n_p = v1.number_input("# Unid Plan", min_value=1, value=1)
        n_r = v2.number_input("# Unid Real", min_value=1, value=1)
        sel_v = v3.select_slider("Embalagem:", options=["0,9L", "3,6L", "15L", "18L", "25kg", "Outro"], value="15L")
        litros_u = float(sel_v.replace('L','').replace('kg','').replace(',','.')) if sel_v != "Outro" else v3.number_input("Valor Unit:", value=15.0)
        check_padrão = v4.checkbox("🌟 Definir como Novo Padrão")

        formula = df_mestra[(df_mestra['Tipo'] == t_sel) & (df_mestra['Cor'] == cor_sel)]
        st.divider()

        regs = []
        for i, row in formula.iterrows():
            pigm = row['Pigmento']
            coef_kg_l = float(row['Quant OP (kg)'])
            espec_final_g = round((coef_kg_l * 1000) * (n_p * litros_u), 2)
            
            with st.container():
                col_i, col_p = st.columns([1.5, 3.5])
                col_i.subheader(pigm); col_i.write(f"Espec: {espec_final_g}g")
                n_t = col_i.number_input(f"Toques", min_value=1, value=1, key=f"nt_{i}")
                
                s_ad = 0.0
                cols = col_p.columns(5)
                for t in range(1, int(n_t) + 1):
                    v = cols[(t-1)%5].number_input(f"T{t}", min_value=0.0, format="%.2f", key=f"v_{i}_{t}")
                    s_ad += v
                col_p.info(f"Total: {s_ad:.2f} g")
            
            regs.append({
                "data": data_f.strftime("%d/%m/%Y"), "lote": lote_id, "tipo de produto": t_sel,
                "cor": cor_sel, "pigmento": pigm, "Quant ad (g)": s_ad,
                "Quantidade OP": espec_final_g, "#Plan": n_p, "#Real": n_r, "Litros/Unit": litros_u
            })
            st.divider()

        if st.button("💾 SALVAR LOTE"):
            if not lote_id: st.error("Lote obrigatório.")
            else:
                df_atual = pd.DataFrame(regs)
                salvar_dados_sql(df_atual, "historico_producao", modo='append')

                if check_padrão:
                    n_p_reg = pd.DataFrame([{"Data": data_f.strftime("%d/%m/%Y"), "Produto": t_sel, "Cor": cor_sel, "Lote": lote_id, "Status": "Padrão"}])
                    salvar_dados_sql(n_p_reg, "padroes_registrados", modo='append')

                    vol_real_total = n_r * litros_u
                    conn = get_connection()
                    for _, r in df_atual.iterrows():
                        novo_coef = (r['Quant ad (g)'] / 1000) / vol_real_total if vol_real_total > 0 else 0
                        conn.execute("UPDATE aba_mestra SET [Quant OP (kg)] = ? WHERE Tipo = ? AND Cor = ? AND Pigmento = ?", 
                                     (novo_coef, t_sel, cor_sel, r['pigmento']))
                    conn.commit()
                    conn.close()

                st.success("Lote registrado!"); st.balloons(); time.sleep(1); st.rerun()

# --- 📈 ABA: GRÁFICOS CEP ---
elif aba == "📈 Controle":
    st.title("📈 Dashboard de Qualidade")
    df_hist = carregar_dados_sql("historico_producao")
    if df_hist.empty: st.info("Sem dados registrados.")
    else:
        c1, c2 = st.columns(2)
        p_sel = c1.selectbox("Produto", sorted(df_hist['tipo de produto'].unique()))
        c_sel = c2.selectbox("Cor", sorted(df_hist[df_hist['tipo de produto'] == p_sel]['cor'].unique()))
        df_plot = df_hist[(df_hist['tipo de produto'] == p_sel) & (df_hist['cor'] == c_sel)].copy()
        
        if not df_plot.empty:
            df_plot['Desvio (g)'] = df_plot['Quant ad (g)'] - df_plot['Quantidade OP']
            df_plot['Var %'] = ((df_plot['Quant ad (g)'] / df_plot['Quantidade OP'].replace(0, 1)) - 1) * 100
            st.line_chart(df_plot.pivot_table(index='lote', columns='pigmento', values='Var %'))
            df_plot['Situação'] = df_plot.apply(lambda r: "⚠️ Fora" if abs(r['Var %']) > 10 else "✅ Ok", axis=1)
            st.dataframe(df_plot[['data', 'lote', 'pigmento', 'Quantidade OP', 'Quant ad (g)', 'Desvio (g)', 'Situação']], use_container_width=True)

# --- 📜 BANCO DE DADOS ---
elif aba == "📜 Banco de Dados":
    st.title("📜 Gestão de Dados")
    df_hist = carregar_dados_sql("historico_producao")
    
    with st.expander("🌟 Registrar Lote Existente como Padrão"):
        l_busca = st.text_input("Número do Lote para Homologar:")
        if st.button("Confirmar e Atualizar Mestra") and l_busca:
            l_data = df_hist[df_hist['lote'].astype(str) == l_busca]
            if not l_data.empty:
                t_prod = l_data.iloc[0]['tipo de produto']
                cor_prod = l_data.iloc[0]['cor']
                # Atualiza Padrões
                n_p = pd.DataFrame([{"Data": l_data.iloc[0]['data'], "Produto": t_prod, "Cor": cor_prod, "Lote": l_busca, "Status": "Padrão"}])
                salvar_dados_sql(n_p, "padroes_registrados", modo='append')
                
                # Sincroniza com Aba Mestra
                conn = get_connection()
                for _, r in l_data.iterrows():
                    vol_real = r['#Real'] * r['Litros/Unit']
                    novo_coef = (r['Quant ad (g)'] / 1000) / vol_real if vol_real > 0 else 0
                    conn.execute("UPDATE aba_mestra SET [Quant OP (kg)] = ? WHERE Tipo = ? AND Cor = ? AND Pigmento = ?", 
                                 (novo_coef, t_prod, cor_prod, r['pigmento']))
                conn.commit()
                conn.close()
                st.success(f"Lote {l_busca} homologado!"); time.sleep(1); st.rerun()

    ed_h = st.data_editor(df_hist, num_rows="dynamic", key="editor_hist", use_container_width=True)
    c1, c2 = st.columns(2)
    if c1.button("💾 Salvar Alterações"):
        salvar_dados_sql(ed_h, "historico_producao")
        st.success("Histórico atualizado!")
    with c2:
        l_del = st.text_input("Lote para EXCLUIR:")
        if st.button("❌ EXCLUIR LOTE"):
            conn = get_connection()
            conn.execute("DELETE FROM historico_producao WHERE lote = ?", (l_del,))
            conn.commit()
            conn.close()
            st.rerun()

# --- DEMAIS ABAS ---
elif aba == "📋 Padrões":
    st.title("📋 Histórico de Padrões")
    df_padr = carregar_dados_sql("padroes_registrados")
    ed_p = st.data_editor(df_padr, num_rows="dynamic", use_container_width=True)
    if st.button("Salvar Padrões"):
        salvar_dados_sql(ed_p, "padroes_registrados")
        st.success("Salvo!")

elif aba == "📊 Aba Mestra":
    st.title("📊 Editor Aba Mestra (kg/L)")
    df_mestra = carregar_dados_sql("aba_mestra")
    ed_m = st.data_editor(df_mestra, num_rows="dynamic", use_container_width=True)
    if st.button("💾 Salvar Mestra"):
        salvar_dados_sql(ed_m, "aba_mestra")
        st.success("Mestra Atualizada!")

elif aba == "📂 Importar CSV":
    st.title("📂 Importação / Exportação")
    df_hist = carregar_dados_sql("historico_producao")
    st.download_button("📥 Baixar Backup CSV", df_hist.to_csv(index=False, sep=';', encoding='utf-8-sig'), "Backup_Producao.csv")
    
    up = st.file_uploader("Subir CSV", type="csv")
    alvo = st.selectbox("Destino", ["aba_mestra", "historico_producao", "padroes_registrados"])
    
    if up and st.button("🚀 Confirmar Importação"):
        # Leitura ultra-resistente para o seu caso
        try:
            up.seek(0)
            df_imp = pd.read_csv(up, sep=None, engine='python', encoding='latin-1', on_bad_lines='skip')
            
            # Ajuste automático de nomes de colunas para bater com o banco
            if alvo == "aba_mestra":
                df_imp.columns = ['Tipo', 'Cor', 'Pigmento', 'Quant OP (kg)']
            elif alvo == "historico_producao":
                df_imp.columns = ['data', 'lote', 'tipo de produto', 'cor', 'pigmento', 
                                 'Quant ad (g)', 'Quantidade OP', '#Plan', '#Real', 'Litros/Unit']
            
            salvar_dados_sql(df_imp, alvo, modo='append')
            st.success("Dados importados para o SQLite com sucesso!")
            time.sleep(1); st.rerun()
        except Exception as e:
            st.error(f"Erro na importação: {e}")

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
    # Tabela Aba Mestra (Fórmulas Oficiais)
    c.execute('''CREATE TABLE IF NOT EXISTS aba_mestra 
                 (Tipo TEXT, Cor TEXT, Pigmento TEXT, Quant_OP_kg REAL)''')
    # Tabela Histórico de Produção (Registros Diários)
    c.execute('''CREATE TABLE IF NOT EXISTS historico_producao 
                 (data TEXT, lote TEXT, tipo_produto TEXT, cor TEXT, pigmento TEXT, 
                  quant_ad_g REAL, quantidade_op REAL, n_plan REAL, n_real REAL, litros_unit REAL)''')
    # Tabela Padrões Registrados (Rastreabilidade de Homologação)
    c.execute('''CREATE TABLE IF NOT EXISTS padroes_registrados 
                 (Data TEXT, Produto TEXT, Cor TEXT, Lote TEXT, Status TEXT)''')
    conn.commit()
    conn.close()

# Inicializa o banco de dados
init_db()

# --- 🛡️ FUNÇÕES DE MANIPULAÇÃO DE DADOS ---
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
menu = ["🚀 Produção", "📈 Gráficos CEP", "📜 Banco de Dados", "📋 Padrões Registrados", "📊 Editor Aba Mestra", "📂 Importar/Exportar"]
aba = st.sidebar.radio("Navegação:", menu)

# --- 🚀 ABA: PRODUÇÃO ---
if aba == "🚀 Produção":
    st.title("🚀 Registro de Pesagem")
    df_mestra = carregar_dados_sql("aba_mestra")
    
    if df_mestra.empty:
        st.warning("Aba Mestra vazia. Importe seus dados na aba 'Importar/Exportar'.")
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
        check_padrão = v4.checkbox("🌟 Definir como Novo Padrão")

        formula = df_mestra[(df_mestra['Tipo'] == t_sel) & (df_mestra['Cor'] == cor_sel)]
        st.divider()

        regs = []
        for i, row in formula.iterrows():
            coef_kg_l = float(row['Quant_OP_kg'])
            # Cálculo do Especificado em Gramas (Lógica original preservada)
            espec_final_g = round((coef_kg_l * 1000) * (n_p * litros_u), 2)
            
            with st.container():
                col_i, col_p = st.columns([1.5, 3.5])
                col_i.subheader(row['Pigmento']); col_i.write(f"Espec: {espec_final_g}g")
                n_t = col_i.number_input(f"Toques", min_value=1, value=1, key=f"nt_{i}")
                
                s_ad = 0.0
                cols = col_p.columns(5)
                for t in range(1, int(n_t) + 1):
                    v = cols[(t-1)%5].number_input(f"T{t}", min_value=0.0, format="%.2f", key=f"v_{i}_{t}")
                    s_ad += v
                col_p.info(f"Total: {s_ad:.2f} g")
            
            regs.append({
                "data": data_f.strftime("%d/%m/%Y"), "lote": lote_id, "tipo_produto": t_sel,
                "cor": cor_sel, "pigmento": row['Pigmento'], "quant_ad_g": s_ad,
                "quantidade_op": espec_final_g, "n_plan": n_p, "n_real": n_r, "litros_unit": litros_u
            })
            st.divider()

        if st.button("💾 SALVAR LOTE"):
            if not lote_id: st.error("Lote obrigatório.")
            else:
                df_atual = pd.DataFrame(regs)
                save_conn = get_connection()
                # Salva no histórico
                df_atual.to_sql("historico_producao", save_conn, if_exists='append', index=False)
                
                if check_padrão:
                    # 1. Registro de Padrão
                    n_p_reg = pd.DataFrame([{"Data": data_f.strftime("%d/%m/%Y"), "Produto": t_sel, "Cor": cor_sel, "Lote": lote_id, "Status": "Padrão"}])
                    n_p_reg.to_sql("padroes_registrados", save_conn, if_exists='append', index=False)

                    # 2. Atualização Automática da Aba Mestra (kg/L)
                    vol_real_total = n_r * litros_u
                    for _, r in df_atual.iterrows():
                        novo_coef = (r['quant_ad_g'] / 1000) / vol_real_total if vol_real_total > 0 else 0
                        save_conn.execute("UPDATE aba_mestra SET Quant_OP_kg = ? WHERE Tipo = ? AND Cor = ? AND Pigmento = ?", 
                                              (novo_coef, t_sel, cor_sel, r['pigmento']))
                
                save_conn.commit()
                save_conn.close()
                st.success("Lote salvo com sucesso!"); st.balloons(); time.sleep(1); st.rerun()

# --- 📈 ABA: GRÁFICOS CEP ---
elif aba == "📈 Gráficos CEP":
    st.title("📈 Dashboard de Qualidade")
    df_hist = carregar_dados_sql("historico_producao")
    if df_hist.empty: st.info("Sem dados registrados.")
    else:
        c1, c2 = st.columns(2)
        p_sel = c1.selectbox("Produto", sorted(df_hist['tipo_produto'].unique()))
        c_sel = c2.selectbox("Cor", sorted(df_hist[df_hist['tipo_produto'] == p_sel]['cor'].unique()))
        df_plot = df_hist[(df_hist['tipo_produto'] == p_sel) & (df_hist['cor'] == c_sel)].copy()
        
        if not df_plot.empty:
            # Réplica fiel da coluna Quantidade OP para o gráfico
            df_plot['Especificado (g)'] = df_plot['quantidade_op']
            df_plot['Desvio (g)'] = df_plot['quant_ad_g'] - df_plot['Especificado (g)']
            df_plot['Var %'] = ((df_plot['quant_ad_g'] / df_plot['Especificado (g)'].replace(0, np.nan)) - 1) * 100
            st.line_chart(df_plot.pivot_table(index='lote', columns='pigmento', values='Var %'))
            df_plot['Situação'] = df_plot.apply(lambda r: "⚠️ Fora" if abs(r['Var %']) > 10 else "✅ Ok", axis=1)
            st.dataframe(df_plot[['data', 'lote', 'pigmento', 'Especificado (g)', 'quant_ad_g', 'Desvio (g)', 'Situação']], use_container_width=True)

# --- 📜 BANCO DE DADOS (SQLite) ---
elif aba == "📜 Banco de Dados":
    st.title("📜 Gestão de Registros")
    df_hist = carregar_dados_sql("historico_producao")
    
    with st.expander("🌟 Homologar Lote Antigo como Padrão"):
        l_busca = st.text_input("Número do Lote:")
        if st.button("Confirmar Padrão Retroativo") and l_busca:
            l_data = df_hist[df_hist['lote'].astype(str) == l_busca]
            if not l_data.empty:
                conn = get_connection()
                for _, r in l_data.iterrows():
                    vol_real = r['n_real'] * r['litros_unit']
                    novo_coef = (r['quant_ad_g'] / 1000) / vol_real if vol_real > 0 else 0
                    conn.execute("UPDATE aba_mestra SET Quant_OP_kg = ? WHERE Tipo = ? AND Cor = ? AND Pigmento = ?", 
                                 (novo_coef, r['tipo_produto'], r['cor'], r['pigmento']))
                conn.commit()
                conn.close()
                st.success(f"Lote {l_busca} validado como nova referência!"); time.sleep(1); st.rerun()

    ed_h = st.data_editor(df_hist, num_rows="dynamic", use_container_width=True)
    c1, c2 = st.columns(2)
    if c1.button("💾 Salvar Alterações"):
        salvar_dados_sql(ed_h, "historico_producao")
        st.success("Banco de Dados Atualizado!")
    with c2:
        l_del = st.text_input("Excluir Lote (ID):")
        if st.button("❌ EXCLUIR"):
            conn = get_connection()
            conn.execute("DELETE FROM historico_producao WHERE lote = ?", (l_del,))
            conn.commit()
            conn.close()
            st.rerun()

# --- 📋 PADRÕES ---
elif aba == "📋 Padrões Registrados":
    st.title("📋 Histórico de Padrões")
    df_padr = carregar_dados_sql("padroes_registrados")
    ed_p = st.data_editor(df_padr, num_rows="dynamic", use_container_width=True)
    if st.button("Salvar Tabela de Padrões"):
        salvar_dados_sql(ed_p, "padroes_registrados")
        st.success("Salvo!")

# --- 📊 EDITOR ABA MESTRA ---
elif aba == "📊 Editor Aba Mestra":
    st.title("📊 Gestão de Fórmulas (kg/L)")
    df_mestra = carregar_dados_sql("aba_mestra")
    ed_m = st.data_editor(df_mestra, num_rows="dynamic", use_container_width=True)
    if st.button("💾 Salvar Fórmulas na Mestra"):
        salvar_dados_sql(ed_m, "aba_mestra")
        st.success("Aba Mestra atualizada!")

# --- 📂 IMPORTAR/EXPORTAR ---
elif aba == "📂 Importar/Exportar":
    st.title("📂 Migração e Exportação Offline")
    
    # EXPORTAÇÃO
    st.subheader("📤 Exportar para Excel/Uso Offline")
    tabela_sel = st.selectbox("Selecione os dados:", ["historico_producao", "aba_mestra", "padroes_registrados"])
    df_exp = carregar_dados_sql(tabela_sel)
    if not df_exp.empty:
        csv = df_exp.to_csv(index=False, sep=';', encoding='utf-8-sig')
        st.download_button(f"📥 Baixar {tabela_sel}.csv", csv, f"{tabela_sel}.csv", "text/csv")

    st.divider()

    # IMPORTAÇÃO
    st.subheader("📥 Importar CSV para o Sistema")
    up = st.file_uploader("Subir arquivo CSV", type="csv")
    alvo = st.selectbox("Destino da Importação", ["aba_mestra", "historico_producao", "padroes_registrados"])
    if up and st.button("🚀 Confirmar Importação"):
        try:
            df_imp = pd.read_csv(up, sep=None, engine='python', encoding='utf-8-sig')
            # Garante que os nomes das colunas batam com o SQL (case sensitive)
            if alvo == "aba_mestra":
                df_imp.columns = ["Tipo", "Cor", "Pigmento", "Quant_OP_kg"]
            salvar_dados_sql(df_imp, alvo, modo='append')
            st.success("Importação concluída!")
            time.sleep(1); st.rerun()
        except Exception as e:
            st.error(f"Erro ao processar arquivo: {e}")

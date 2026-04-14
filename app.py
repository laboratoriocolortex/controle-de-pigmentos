import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
import os
import time
import re
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
    # Adicionado Versao e Status para Versionamento (Rastreabilidade)
    c.execute('''CREATE TABLE IF NOT EXISTS aba_mestra 
                 (Tipo TEXT, Cor TEXT, Pigmento TEXT, [Quant OP (kg)] REAL, Versao INTEGER DEFAULT 1, Status TEXT DEFAULT 'Ativo')''')
    
    # Bloco de migração simples caso a tabela antiga já exista sem as novas colunas
    try:
        c.execute("ALTER TABLE aba_mestra ADD COLUMN Versao INTEGER DEFAULT 1")
        c.execute("ALTER TABLE aba_mestra ADD COLUMN Status TEXT DEFAULT 'Ativo'")
    except sqlite3.OperationalError:
        pass # Colunas já existem

    c.execute('''CREATE TABLE IF NOT EXISTS historico_producao 
                 (data TEXT, lote TEXT, [tipo de produto] TEXT, cor TEXT, pigmento TEXT, 
                  [Quant ad (g)] REAL, [Quantidade OP] REAL, [#Plan] REAL, [#Real] REAL, [Litros/Unit] REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS padroes_registrados 
                 (Data TEXT, Produto TEXT, Cor TEXT, Lote TEXT, Status TEXT)''')
    conn.commit()
    conn.close()

init_db()

def carregar_sql(tabela, apenas_ativos=False):
    conn = get_connection()
    query = f"SELECT * FROM {tabela}"
    if tabela == "aba_mestra" and apenas_ativos:
        query += " WHERE Status = 'Ativo'"
        
    df = pd.read_sql(query, conn)
    conn.close()
    cols_num = ['Quant ad (g)', 'Quantidade OP', '#Plan', '#Real', 'Litros/Unit', 'Quant OP (kg)']
    for col in cols_num:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce').fillna(0.0)
    return df

def salvar_sql(df, tabela, modo='replace'):
    conn = get_connection()
    cols_db = {
        "aba_mestra": ['Tipo', 'Cor', 'Pigmento', 'Quant OP (kg)', 'Versao', 'Status'],
        "historico_producao": ['data', 'lote', 'tipo de produto', 'cor', 'pigmento', 'Quant ad (g)', 'Quantidade OP', '#Plan', '#Real', 'Litros/Unit'],
        "padroes_registrados": ['Data', 'Produto', 'Cor', 'Lote', 'Status']
    }
    colunas_validas = cols_db.get(tabela, df.columns)
    df_save = df[[c for c in colunas_validas if c in df.columns]].copy()
    df_save.to_sql(tabela, conn, if_exists=modo, index=False)
    conn.commit()
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
menu = ["🚀 Registro", "📈 Controle (CEP)", "📜 Banco de Dados", "📋 Padrões", "📊 Aba Mestra", "📂 Importar CSV"]
aba = st.sidebar.radio("Navegação:", menu)

# --- 🚀 ABA: REGISTRO ---
if aba == "🚀 Registro":
    st.title("🚀 Registro de Pigmentação")
    # Carrega apenas as fórmulas ativas
    df_mestra = carregar_sql("aba_mestra", apenas_ativos=True)
    
    if df_mestra.empty:
        st.warning("Aba Mestra vazia ou sem fórmulas ativas.")
    else:
        # Controles fora do form para atualização dinâmica de dropdowns
        c1, c2, c3, c4 = st.columns([1.5, 1.5, 1, 1])
        t_sel = c1.selectbox("Produto", sorted(df_mestra['Tipo'].unique()))
        cor_sel = c2.selectbox("Cor", sorted(df_mestra[df_mestra['Tipo'] == t_sel]['Cor'].unique()))
        lote_id = c3.text_input("Lote")
        data_f = c4.date_input("Data", date.today())

        formula = df_mestra[(df_mestra['Tipo'] == t_sel) & (df_mestra['Cor'] == cor_sel)]
        
        # OTIMIZAÇÃO: Uso de st.form para evitar reloads a cada digitação de peso
        with st.form("form_registro"):
            v1, v2, v3, v4 = st.columns([1, 1, 2, 1.5])
            n_p = v1.number_input("# Unid Plan", min_value=0.1, value=1.0)
            n_r = v2.number_input("# Unid Real", min_value=0.1, value=1.0)
            opcoes_emb = ["0,9L", "1,5kg", "3L", "3,6L", "5kg", "14L", "15L", "18kg", "20kg", "22kg", "25kg", "Outro"]
            sel_v = v3.select_slider("Embalagem:", options=opcoes_emb, value="15L")
            litros_u = v3.number_input("Valor Unitário:", min_value=0.1, value=1.0) if sel_v == "Outro" else float(re.sub(r'[^\d.]', '', sel_v.replace(',','.')))

            check_padrao = v4.checkbox("🌟 Definir como Novo Padrão")
            st.divider()

            regs = []
            # Como estamos em um form, usamos 5 colunas fixas para toques (Poka-Yoke de layout)
            for i, row in formula.iterrows():
                coef = float(row['Quant OP (kg)'])
                espec_g = round((coef * 1000) * (n_p * litros_u), 2)
                
                col_i, col_p = st.columns([1.5, 3.5])
                col_i.subheader(row['Pigmento'])
                col_i.write(f"Espec: {espec_g}g")
                
                cols = col_p.columns(5)
                t1 = cols[0].number_input("T1 (g)", min_value=0.0, format="%.2f", key=f"v_{i}_1")
                t2 = cols[1].number_input("T2 (g)", min_value=0.0, format="%.2f", key=f"v_{i}_2")
                t3 = cols[2].number_input("T3 (g)", min_value=0.0, format="%.2f", key=f"v_{i}_3")
                t4 = cols[3].number_input("T4 (g)", min_value=0.0, format="%.2f", key=f"v_{i}_4")
                t5 = cols[4].number_input("T5 (g)", min_value=0.0, format="%.2f", key=f"v_{i}_5")
                
                s_ad = t1 + t2 + t3 + t4 + t5
                
                regs.append({
                    "data": data_f.strftime("%d/%m/%Y"), "lote": lote_id, "tipo de produto": t_sel,
                    "cor": cor_sel, "pigmento": row['Pigmento'], "Quant ad (g)": s_ad,
                    "Quantidade OP": espec_g, "#Plan": n_p, "#Real": n_r, "Litros/Unit": litros_u
                })

            submit_btn = st.form_submit_button("💾 SALVAR LOTE")

        if submit_btn:
            if not lote_id: 
                st.error("Lote obrigatório.")
            else:
                salvar_sql(pd.DataFrame(regs), "historico_producao", modo='append')
                
                if check_padrao:
                    df_p = pd.DataFrame([{"Data": data_f.strftime("%d/%m/%Y"), "Produto": t_sel, "Cor": cor_sel, "Lote": lote_id, "Status": "Padrão"}])
                    salvar_sql(df_p, "padroes_registrados", modo='append')
                    
                    # VERSIONAMENTO DA ABA MESTRA
                    conn = get_connection()
                    for r in regs:
                        novo_coef = (r['Quant ad (g)'] / 1000) / (n_r * litros_u)
                        
                        # 1. Pega a versão atual
                        curr_v = pd.read_sql(f"SELECT Versao FROM aba_mestra WHERE Tipo='{t_sel}' AND Cor='{cor_sel}' AND Pigmento='{r['pigmento']}' AND Status='Ativo'", conn)
                        v_num = int(curr_v.iloc[0]['Versao']) + 1 if not curr_v.empty else 1
                        
                        # 2. Inativa a versão antiga
                        conn.execute("UPDATE aba_mestra SET Status = 'Inativo' WHERE Tipo = ? AND Cor = ? AND Pigmento = ?", (t_sel, cor_sel, r['pigmento']))
                        
                        # 3. Insere a nova versão
                        conn.execute("INSERT INTO aba_mestra (Tipo, Cor, Pigmento, [Quant OP (kg)], Versao, Status) VALUES (?, ?, ?, ?, ?, 'Ativo')", 
                                     (t_sel, cor_sel, r['pigmento'], novo_coef, v_num))
                    
                    conn.commit()
                    conn.close()
                
                st.success("Lote salvo com sucesso!")
                time.sleep(1)
                st.rerun()

# --- 📋 ABA: PADRÕES ---
elif aba == "📋 Padrões":
    st.title("📋 Padrões Aprovados")
    df_p = carregar_sql("padroes_registrados")
    if not df_p.empty:
        c1, c2 = st.columns([3, 1])
        csv = df_p.to_csv(index=False).encode('utf-8-sig')
        c1.download_button("📥 Baixar CSV", data=csv, file_name="padroes.csv")
        
        lote_del = c2.selectbox("Excluir Padrão do Lote:", ["Selecionar"] + list(df_p['Lote'].unique()))
        if c2.button("🗑️ Confirmar Exclusão") and lote_del != "Selecionar":
            conn = get_connection()
            conn.execute("DELETE FROM padroes_registrados WHERE Lote = ?", (lote_del,))
            conn.commit(); conn.close()
            st.rerun()
        st.dataframe(df_p, use_container_width=True)
    else: st.info("Nenhum padrão registrado.")

# --- 📜 BANCO DE DADOS ---
elif aba == "📜 Banco de Dados":
    st.title("📜 Histórico e Promoção a Padrão")
    df_h = carregar_sql("historico_producao")
    
    col1, col2 = st.columns([2, 1])
    lote_busca = col1.selectbox("Selecione um Lote para promover a Padrão:", [""] + list(df_h['lote'].unique()))
    
    if col2.button("🌟 Definir Lote como Padrão") and lote_busca != "":
        lote_data = df_h[df_h['lote'] == lote_busca]
        df_p_new = pd.DataFrame([{"Data": lote_data.iloc[0]['data'], "Produto": lote_data.iloc[0]['tipo de produto'], "Cor": lote_data.iloc[0]['cor'], "Lote": lote_busca, "Status": "Padrão"}])
        salvar_sql(df_p_new, "padroes_registrados", modo='append')
        
        # VERSIONAMENTO DA ABA MESTRA
        conn = get_connection()
        for _, r in lote_data.iterrows():
            novo_c = (r['Quant ad (g)'] / 1000) / (r['#Real'] * r['Litros/Unit'])
            
            curr_v = pd.read_sql(f"SELECT Versao FROM aba_mestra WHERE Tipo='{r['tipo de produto']}' AND Cor='{r['cor']}' AND Pigmento='{r['pigmento']}' AND Status='Ativo'", conn)
            v_num = int(curr_v.iloc[0]['Versao']) + 1 if not curr_v.empty else 1
            
            conn.execute("UPDATE aba_mestra SET Status = 'Inativo' WHERE Tipo = ? AND Cor = ? AND Pigmento = ?", (r['tipo de produto'], r['cor'], r['pigmento']))
            conn.execute("INSERT INTO aba_mestra (Tipo, Cor, Pigmento, [Quant OP (kg)], Versao, Status) VALUES (?, ?, ?, ?, ?, 'Ativo')", 
                         (r['tipo de produto'], r['cor'], r['pigmento'], novo_c, v_num))
        conn.commit(); conn.close()
        st.success(f"Lote {lote_busca} agora é o padrão!"); time.sleep(1); st.rerun()

    ed_h = st.data_editor(df_h, num_rows="dynamic", use_container_width=True)
    if st.button("💾 Salvar Edições"): salvar_sql(ed_h, "historico_producao"); st.success("Salvo!")

# --- 📈 CONTROLE (CEP) ---
elif aba == "📈 Controle (CEP)":
    st.title("📈 Controle Estatístico de Processo (CEP)")
    df_hist = carregar_sql("historico_producao")
    
    if not df_hist.empty:
        c1, c2 = st.columns(2)
        p_sel = c1.selectbox("Produto", sorted(df_hist['tipo de produto'].unique()))
        c_sel = c2.selectbox("Cor", sorted(df_hist[df_hist['tipo de produto'] == p_sel]['cor'].unique()))
        
        df_plot = df_hist[(df_hist['tipo de produto'] == p_sel) & (df_hist['cor'] == c_sel)].copy()
        
        if not df_plot.empty:
            df_plot['Var %'] = ((df_plot['Quant ad (g)'] / df_plot['Quantidade OP'].replace(0, np.nan)) - 1) * 100
            
            st.markdown("### Cartas de Controle por Pigmento")
            pigmentos = df_plot['pigmento'].unique()
            
            # Limites de Especificação (Tolerância industrial padrão de 10%)
            USL = 10.0 
            LSL = -10.0
            
            for pig in pigmentos:
                st.markdown(f"**Pigmento: {pig}**")
                df_pig = df_plot[df_plot['pigmento'] == pig].copy()
                
                # Cálculos Estatísticos
                media = df_pig['Var %'].mean()
                desvio = df_pig['Var %'].std()
                if pd.isna(desvio) or desvio == 0: desvio = 0.0001 # Evita divisão por zero
                
                # Limites de Controle (3 Sigma)
                LSC = media + (3 * desvio)
                LIC = media - (3 * desvio)
                
                # Capacidade do Processo
                cp = (USL - LSL) / (6 * desvio)
                cpk = min((USL - media) / (3 * desvio), (media - LSL) / (3 * desvio))
                
                # Preparando dados para o gráfico
                df_pig['Média'] = media
                df_pig['LSC (+3σ)'] = LSC
                df_pig['LIC (-3σ)'] = LIC
                
                col_chart, col_metrics = st.columns([4, 1])
                
                with col_chart:
                    st.line_chart(df_pig.set_index('lote')[['Var %', 'Média', 'LSC (+3σ)', 'LIC (-3σ)']])
                
                with col_metrics:
                    st.metric("Média de Variação", f"{media:.2f}%")
                    st.metric("Desvio Padrão (σ)", f"{desvio:.2f}%")
                    
                    # Alerta visual de Cpk
                    if cpk >= 1.33:
                        st.success(f"Cpk: {cpk:.2f} (Capaz)")
                    elif cpk >= 1.0:
                        st.warning(f"Cpk: {cpk:.2f} (Aceitável)")
                    else:
                        st.error(f"Cpk: {cpk:.2f} (Incapaz)")

            st.divider()
            st.markdown("### Dados Brutos")
            df_plot['Situação'] = df_plot.apply(lambda r: "⚠️ Fora" if abs(r['Var %']) > 10 else "✅ Ok", axis=1)
            st.dataframe(df_plot[['data', 'lote', 'pigmento', 'Quantidade OP', 'Quant ad (g)', 'Var %', 'Situação']], use_container_width=True)

# --- 📊 ABA MESTRA ---
elif aba == "📊 Aba Mestra":
    st.title("📊 Aba Mestra (kg/L)")
    st.info("Mostrando apenas versões ATIVAS. Edições diretas aqui sobrescrevem a versão atual.")
    df_m = carregar_sql("aba_mestra", apenas_ativos=True)
    
    ed_m = st.data_editor(df_m, num_rows="dynamic", use_container_width=True)
    if st.button("💾 Salvar Mestra"): 
        # Como é uma edição em massa, garantimos que os novos inseridos tenham status Ativo e Versão 1
        if 'Status' not in ed_m.columns: ed_m['Status'] = 'Ativo'
        if 'Versao' not in ed_m.columns: ed_m['Versao'] = 1
        ed_m['Status'] = ed_m['Status'].fillna('Ativo')
        ed_m['Versao'] = ed_m['Versao'].fillna(1)
        
        # Salva substituindo tudo (para simplificar a edição em massa)
        salvar_sql(ed_m, "aba_mestra")
        st.success("Atualizado!")

# --- 📂 IMPORTAR CSV ---
elif aba == "📂 Importar CSV":
    st.title("📂 Importação Blindada")
    up = st.file_uploader("Arquivo CSV", type="csv")
    alvo = st.selectbox("Destino", ["aba_mestra", "historico_producao"])
    if up and st.button("🚀 Importar"):
        df_imp = pd.read_csv(up, sep=None, engine='python', encoding='utf-8-sig')
        
        if alvo == "aba_mestra":
            if 'Versao' not in df_imp.columns: df_imp['Versao'] = 1
            if 'Status' not in df_imp.columns: df_imp['Status'] = 'Ativo'

        if alvo == "historico_producao":
            df_m_ref = carregar_sql("aba_mestra", apenas_ativos=True)
            df_imp = df_imp.drop(columns=['Quantidade OP'], errors='ignore')
            df_imp = pd.merge(df_imp, df_m_ref[['Tipo', 'Cor', 'Pigmento', 'Quant OP (kg)']], left_on=['tipo de produto', 'cor', 'pigmento'], right_on=['Tipo', 'Cor', 'Pigmento'], how='left')
            df_imp['Quantidade OP'] = (df_imp['Quant OP (kg)'] * 1000) * (df_imp['#Plan'] * df_imp['Litros/Unit'])
        
        salvar_sql(df_imp, alvo, modo='append'); st.success("Importado!")

    if st.button("🔴 RESET TOTAL"):
        conn = get_connection()
        conn.execute("DROP TABLE IF EXISTS aba_mestra")
        conn.execute("DROP TABLE IF EXISTS historico_producao")
        conn.execute("DROP TABLE IF EXISTS padroes_registrados")
        conn.commit()
        conn.close()
        init_db()
        st.rerun()

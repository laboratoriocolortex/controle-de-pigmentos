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

# --- 🛡️ FUNÇÕES DE TRATAMENTO ---
def carregar_dados_blindado(arquivo_ou_buffer):
    if isinstance(arquivo_ou_buffer, str) and not os.path.exists(arquivo_ou_buffer):
        if "Mestra" in arquivo_ou_buffer:
            return pd.DataFrame(columns=['Tipo', 'Cor', 'Pigmento', 'Quant OP (kg)'])
        return pd.DataFrame()
    try:
        df = pd.read_csv(arquivo_ou_buffer, sep=None, engine='python', encoding='utf-8-sig')
        df.columns = [str(c).replace('\ufeff', '').strip() for c in df.columns]
        for col in df.columns:
            if df[col].dtype == 'object':
                df[col] = df[col].astype(str).str.strip()
        cols_num = ['Quantidade OP', 'Quant ad (g)', '#Plan', '#Real', 'Litros/Unit', 'Quant OP (kg)']
        for col in cols_num:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce').fillna(0.0)
        return df.dropna(how='all')
    except:
        return pd.DataFrame()

def salvar_csv(df, arquivo):
    cols_calc = ['Desvio (g)', 'Var %', 'Situação', 'Especificado (g)']
    df_save = df.drop(columns=[c for c in cols_calc if c in df.columns], errors='ignore').copy()
    df_save.to_csv(arquivo, index=False, sep=';', encoding='utf-8-sig')

# --- CARREGAMENTO INICIAL ---
if 'df_mestra' not in st.session_state:
    st.session_state.df_mestra = carregar_dados_blindado("Aba_Mestra.csv")
if 'df_hist' not in st.session_state:
    st.session_state.df_hist = carregar_dados_blindado("Historico_Producao.csv")
if 'df_padr' not in st.session_state:
    st.session_state.df_padr = carregar_dados_blindado("Padroes_Registrados.csv")

# --- NAVEGAÇÃO ---
menu = ["🚀 Registro", "📈 Controle", "📜 Banco de Dados", "📋 Padrões", "📊 Aba Mestra", "📂 Importar CSV"]
aba = st.sidebar.radio("Navegação:", menu)

# --- 🚀 ABA: PRODUÇÃO ---
if aba == "🚀 Registro":
    st.title("🚀 Registro de Pigmentação")
    if st.session_state.df_mestra.empty:
        st.warning("Aba Mestra vazia.")
    else:
        c1, c2, c3, c4 = st.columns([1.5, 1.5, 1, 1])
        t_sel = c1.selectbox("Produto", sorted(st.session_state.df_mestra['Tipo'].unique()))
        cor_sel = c2.selectbox("Cor", sorted(st.session_state.df_mestra[st.session_state.df_mestra['Tipo'] == t_sel]['Cor'].unique()))
        lote_id = c3.text_input("Lote")
        data_f = c4.date_input("Data", date.today())

        v1, v2, v3, v4 = st.columns([1, 1, 2, 1.5])
        n_p = v1.number_input("# Unid Plan", min_value=1, value=1)
        n_r = v2.number_input("# Unid Real", min_value=1, value=1)
        sel_v = v3.select_slider("Embalagem:", options=["0,9L", "3,6L", "15L", "18L", "25kg", "Outro"], value="15L")
        litros_u = float(sel_v.replace('L','').replace('kg','').replace(',','.')) if sel_v != "Outro" else v3.number_input("Valor Unit:", value=15.0)
        check_padrão = v4.checkbox("🌟 Definir como Novo Padrão")

        formula = st.session_state.df_mestra[(st.session_state.df_mestra['Tipo'] == t_sel) & (st.session_state.df_mestra['Cor'] == cor_sel)]
        st.divider()

        regs = []
        for i, row in formula.iterrows():
            pigm = row['Pigmento']
            coef_kg_l = float(row.get('Quant OP (kg)', row.get('Quantidade OP', 0)))
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
                novo_h = pd.concat([st.session_state.df_hist, df_atual], ignore_index=True)
                salvar_csv(novo_h, "Historico_Producao.csv")
                st.session_state.df_hist = novo_h

                if check_padrão:
                    # Registro na Tabela de Padrões
                    n_p_reg = pd.DataFrame([{"Data": data_f.strftime("%d/%m/%Y"), "Produto": t_sel, "Cor": cor_sel, "Lote": lote_id, "Status": "Padrão"}])
                    st.session_state.df_padr = pd.concat([st.session_state.df_padr, n_p_reg], ignore_index=True)
                    salvar_csv(st.session_state.df_padr, "Padroes_Registrados.csv")

                    # Atualiza Aba Mestra
                    vol_real_total = n_r * litros_u
                    for _, r in df_atual.iterrows():
                        novo_coef = (r['Quant ad (g)'] / 1000) / vol_real_total if vol_real_total > 0 else 0
                        mask = (st.session_state.df_mestra['Tipo'] == t_sel) & \
                               (st.session_state.df_mestra['Cor'] == cor_sel) & \
                               (st.session_state.df_mestra['Pigmento'] == r['pigmento'])
                        if mask.any(): st.session_state.df_mestra.loc[mask, 'Quant OP (kg)'] = novo_coef
                        else:
                            nova_lin = pd.DataFrame([{'Tipo': t_sel, 'Cor': cor_sel, 'Pigmento': r['pigmento'], 'Quant OP (kg)': novo_coef}])
                            st.session_state.df_mestra = pd.concat([st.session_state.df_mestra, nova_lin], ignore_index=True)
                    salvar_csv(st.session_state.df_mestra, "Aba_Mestra.csv")

                st.success("Lote registrado!"); st.balloons(); time.sleep(1); st.rerun()

# --- 📈 ABA: GRÁFICOS CEP ---
elif aba == "📈 Controle":
    st.title("📈 Dashboard de Qualidade")
    if st.session_state.df_hist.empty: st.info("Sem dados.")
    else:
        c1, c2 = st.columns(2)
        p_sel = c1.selectbox("Produto", sorted(st.session_state.df_hist['tipo de produto'].unique()))
        c_sel = c2.selectbox("Cor", sorted(st.session_state.df_hist[st.session_state.df_hist['tipo de produto'] == p_sel]['cor'].unique()))
        df_plot = st.session_state.df_hist[(st.session_state.df_hist['tipo de produto'] == p_sel) & (st.session_state.df_hist['cor'] == c_sel)].copy()
        
        if not df_plot.empty:
            df_plot['Especificado (g)'] = df_plot['Quantidade OP']
            df_plot['Desvio (g)'] = df_plot['Quant ad (g)'] - df_plot['Especificado (g)']
            df_plot['Var %'] = ((df_plot['Quant ad (g)'] / df_plot['Especificado (g)'].replace(0, np.nan)) - 1) * 100
            st.line_chart(df_plot.pivot_table(index='lote', columns='pigmento', values='Var %'))
            df_plot['Situação'] = df_plot.apply(lambda r: "⚠️ Fora" if abs(r['Var %']) > 10 else "✅ Ok", axis=1)
            st.dataframe(df_plot[['data', 'lote', 'pigmento', 'Especificado (g)', 'Quant ad (g)', 'Desvio (g)', 'Situação']], use_container_width=True)

# --- 📜 BANCO DE DADOS (RESTAURADO) ---
elif aba == "📜 Banco de Dados":
    st.title("📜 Gestão de Dados")
    
    # BLOCO RESTAURADO: Registrar Lote como Padrão
    with st.expander("🌟 Registrar Lote Existente como Padrão"):
        l_busca = st.text_input("Número do Lote para Homologar:")
        if st.button("Confirmar e Atualizar Mestra") and l_busca:
            l_data = st.session_state.df_hist[st.session_state.df_hist['lote'].astype(str) == l_busca]
            if not l_data.empty:
                t_prod = l_data.iloc[0]['tipo de produto']
                cor_prod = l_data.iloc[0]['cor']
                # Atualiza Padrões
                n_p = pd.DataFrame([{"Data": l_data.iloc[0]['data'], "Produto": t_prod, "Cor": cor_prod, "Lote": l_busca, "Status": "Padrão"}])
                st.session_state.df_padr = pd.concat([st.session_state.df_padr, n_p], ignore_index=True)
                salvar_csv(st.session_state.df_padr, "Padroes_Registrados.csv")
                
                # Sincroniza com Aba Mestra (Lógica kg/L)
                for _, r in l_data.iterrows():
                    vol_real = r['#Real'] * r['Litros/Unit']
                    novo_coef = (r['Quant ad (g)'] / 1000) / vol_real if vol_real > 0 else 0
                    mask = (st.session_state.df_mestra['Tipo'] == t_prod) & \
                           (st.session_state.df_mestra['Cor'] == cor_prod) & \
                           (st.session_state.df_mestra['Pigmento'] == r['pigmento'])
                    if mask.any(): st.session_state.df_mestra.loc[mask, 'Quant OP (kg)'] = novo_coef
                salvar_csv(st.session_state.df_mestra, "Aba_Mestra.csv")
                st.success(f"Lote {l_busca} homologado como novo padrão na Aba Mestra!"); time.sleep(1); st.rerun()
            else: st.error("Lote não encontrado no histórico.")

    ed_h = st.data_editor(st.session_state.df_hist, num_rows="dynamic", use_container_width=True)
    c1, c2 = st.columns(2)
    if c1.button("💾 Salvar Alterações"):
        salvar_csv(ed_h, "Historico_Producao.csv"); st.session_state.df_hist = ed_h; st.success("Salvo!")
    with c2:
        l_del = st.text_input("Lote para EXCLUIR:")
        if st.button("❌ EXCLUIR LOTE"):
            st.session_state.df_hist = st.session_state.df_hist[st.session_state.df_hist['lote'].astype(str) != l_del]
            salvar_csv(st.session_state.df_hist, "Historico_Producao.csv"); st.rerun()

# --- DEMAIS ABAS ---
elif aba == "📋 Padrões":
    st.title("📋 Histórico de Padrões")
    ed_p = st.data_editor(st.session_state.df_padr, num_rows="dynamic", use_container_width=True)
    if st.button("Salvar Padrões"):
        salvar_csv(ed_p, "Padroes_Registrados.csv"); st.session_state.df_padr = ed_p; st.success("Salvo!")

elif aba == "📊 Aba Mestra":
    st.title("📊 Editor Aba Mestra (kg/L)")
    ed_m = st.data_editor(st.session_state.df_mestra, num_rows="dynamic", use_container_width=True)
    if st.button("💾 Salvar Mestra"):
        salvar_csv(ed_m, "Aba_Mestra.csv"); st.session_state.df_mestra = ed_m; st.success("Salvo!")

elif aba == "📂 Importar CSV":
    st.title("📂 Importação / Exportação")
    st.download_button("Baixar Backup", st.session_state.df_hist.to_csv(index=False, sep=';', encoding='utf-8-sig'), "Producao_Colortex.csv")
    up = st.file_uploader("Subir CSV", type="csv")
    alvo = st.selectbox("Destino", ["Aba_Mestra.csv", "Historico_Producao.csv", "Padroes_Registrados.csv"])
    if up and st.button("🚀 Confirmar"):
        df_imp = carregar_dados_blindado(up)
        salvar_csv(df_imp, alvo); st.success("Importado!"); time.sleep(1); st.rerun()

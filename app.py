import streamlit as st
import pandas as pd
import numpy as np
import os
import time
from datetime import datetime, date

# 1. Configuração de Layout
st.set_page_config(page_title="Colortex 2026 - Gestão de R&D", layout="wide", page_icon="🧪")

# --- 🛡️ FUNÇÕES DE TRATAMENTO ---
def carregar_dados_blindado(arquivo_ou_buffer):
    if isinstance(arquivo_ou_buffer, str) and not os.path.exists(arquivo_ou_buffer):
        return pd.DataFrame()
    try:
        df = pd.read_csv(arquivo_ou_buffer, sep=None, engine='python', encoding='utf-8-sig')
        df.columns = [str(c).replace('\ufeff', '').strip() for c in df.columns]
        for col in df.columns:
            if df[col].dtype == 'object':
                df[col] = df[col].astype(str).str.strip()
        cols_num = ['Quantidade OP', 'Quant ad (g)', '#Plan', 'Litros/Unit']
        for col in cols_num:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce').fillna(0.0)
        return df.dropna(how='all')
    except:
        return pd.DataFrame()

def salvar_csv(df, arquivo):
    # Colunas de visualização que não devem ir para o arquivo físico
    cols_calc = ['Desvio (g)', 'Var %', 'Situação', 'Especificado (g)']
    df_save = df.drop(columns=[c for c in cols_calc if c in df.columns], errors='ignore').copy()
    df_save.to_csv(arquivo, index=False, sep=';', encoding='utf-8-sig')

# --- CARREGAMENTO INICIAL ---
if 'df_mestra' not in st.session_state:
    st.session_state.df_mestra = carregar_dados_blindado("Aba_Mestra.csv")
if 'df_hist' not in st.session_state:
    st.session_state.df_hist = carregar_dados_blindado("Historico_Producao.csv")

# --- NAVEGAÇÃO ---
menu = ["🚀 Produção", "📈 Gráficos CEP", "📜 Banco de Dados", "📊 Editor Aba Mestra", "📂 Importar CSV"]
aba = st.sidebar.radio("Navegação:", menu)

# --- 🚀 ABA: PRODUÇÃO ---
if aba == "🚀 Produção":
    st.title("🚀 Registro de Pesagem")
    if st.session_state.df_mestra.empty:
        st.warning("Aba Mestra vazia.")
    else:
        c1, c2, c3, c4 = st.columns([1.5, 1.5, 1, 1])
        t_sel = c1.selectbox("Produto", sorted(st.session_state.df_mestra['Tipo'].unique()))
        cor_sel = c2.selectbox("Cor", sorted(st.session_state.df_mestra[st.session_state.df_mestra['Tipo'] == t_sel]['Cor'].unique()))
        lote_id = c3.text_input("Lote")
        data_f = c4.date_input("Data", date.today())

        v1, v2, v3 = st.columns([1, 1, 2])
        n_p = v1.number_input("# Unid Plan", min_value=1, value=1)
        sel_v = v3.select_slider("Embalagem:", options=["0,9L", "3,6L", "15L", "18L", "25kg", "Outro"], value="15L")
        litros_u = float(sel_v.replace('L','').replace('kg','').replace(',','.')) if sel_v != "Outro" else v3.number_input("Valor Unit:", value=15.0)
        
        formula = st.session_state.df_mestra[(st.session_state.df_mestra['Tipo'] == t_sel) & (st.session_state.df_mestra['Cor'] == cor_sel)]
        st.divider()

        regs = []
        for i, row in formula.iterrows():
            pigm = row['Pigmento']
            # Busca o coeficiente (kg/L) da Aba Mestra
            coef_mestra = float(row.get('Quant OP (kg)', row.get('Quantidade OP', 0)))
            # CALCULA A ESPECIFICAÇÃO FINAL EM GRAMAS PARA SALVAR NO BANCO
            espec_final_g = round((coef_mestra * 1000) * (n_p * litros_u), 2)
            
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
            
            # ATENÇÃO: Aqui salvamos o valor já convertido em 'Quantidade OP'
            regs.append({
                "data": data_f.strftime("%d/%m/%Y"), "lote": lote_id, "tipo de produto": t_sel,
                "cor": cor_sel, "pigmento": pigm, "Quant ad (g)": s_ad,
                "Quantidade OP": espec_final_g, "#Plan": n_p, "Litros/Unit": litros_u
            })
            st.divider()

        if st.button("💾 SALVAR LOTE"):
            if not lote_id: st.error("Lote obrigatório.")
            else:
                novo_h = pd.concat([st.session_state.df_hist, pd.DataFrame(regs)], ignore_index=True)
                salvar_csv(novo_h, "Historico_Producao.csv")
                st.session_state.df_hist = novo_h
                st.success("Lote salvo com as especificações convertidas!"); time.sleep(1); st.rerun()

# --- 📈 ABA: GRÁFICOS CEP (APENAS REPLICA O QUE ESTÁ NO BANCO) ---
elif aba == "📈 Gráficos CEP":
    st.title("📈 Dashboard de Qualidade")
    if st.session_state.df_hist.empty: st.info("Sem dados no histórico.")
    else:
        c1, c2 = st.columns(2)
        p_sel = c1.selectbox("Produto", sorted(st.session_state.df_hist['tipo de produto'].unique()))
        c_sel = c2.selectbox("Cor", sorted(st.session_state.df_hist[st.session_state.df_hist['tipo de produto'] == p_sel]['cor'].unique()))
        df_plot = st.session_state.df_hist[(st.session_state.df_hist['tipo de produto'] == p_sel) & (st.session_state.df_hist['cor'] == c_sel)].copy()
        
        if not df_plot.empty:
            # CONFORME PEDIDO: Apenas replicar a coluna 'Quantidade OP' que já está convertida
            df_plot['Especificado (g)'] = df_plot['Quantidade OP']
            
            df_plot['Desvio (g)'] = df_plot['Quant ad (g)'] - df_plot['Especificado (g)']
            df_plot['Var %'] = ((df_plot['Quant ad (g)'] / df_plot['Especificado (g)'].replace(0, np.nan)) - 1) * 100
            
            st.subheader(f"Variação de Pigmentos (%)")
            st.line_chart(df_plot.pivot_table(index='lote', columns='pigmento', values='Var %'))
            
            df_plot['Situação'] = df_plot.apply(lambda r: "⚠️ Fora" if abs(r['Var %']) > 10 else "✅ Ok", axis=1)
            st.dataframe(df_plot[['data', 'lote', 'pigmento', 'Especificado (g)', 'Quant ad (g)', 'Desvio (g)', 'Situação']], use_container_width=True)

# --- 📊 DEMAIS ABAS (EDITOR MESTRA, BANCO, IMPORTAR) ---
elif aba == "📜 Banco de Dados":
    st.title("📜 Gestão de Dados")
    ed_h = st.data_editor(st.session_state.df_hist, num_rows="dynamic", use_container_width=True)
    if st.button("💾 Salvar Alterações"):
        salvar_csv(ed_h, "Historico_Producao.csv"); st.session_state.df_hist = ed_h; st.success("Banco Atualizado!")

elif aba == "📊 Editor Aba Mestra":
    st.title("📊 Editor Aba Mestra (kg/L)")
    ed_m = st.data_editor(st.session_state.df_mestra, num_rows="dynamic", use_container_width=True)
    if st.button("💾 Salvar Mestra"):
        salvar_csv(ed_m, "Aba_Mestra.csv"); st.session_state.df_mestra = ed_m; st.success("Salvo!")

elif aba == "📂 Importar CSV":
    st.title("📂 Importação / Exportação")
    st.download_button("Baixar Backup", st.session_state.df_hist.to_csv(index=False, sep=';', encoding='utf-8-sig'), "Backup_Colortex.csv")
    up = st.file_uploader("Subir CSV", type="csv")
    if up and st.button("🚀 Confirmar"):
        df_imp = carregar_dados_blindado(up)
        salvar_csv(df_imp, "Historico_Producao.csv"); st.success("Importado!"); st.rerun()

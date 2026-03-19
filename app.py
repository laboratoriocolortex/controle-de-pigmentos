import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import numpy as np
from datetime import date
import time

# 1. Configuração de Layout
st.set_page_config(page_title="Colortex 2026 - R&D Cloud", layout="wide", page_icon="🧪")

# --- CONEXÃO COM GOOGLE SHEETS ---
# Ele busca automaticamente as credenciais que você colou no Secrets
conn = st.connection("gsheets", type=GSheetsConnection)

# --- FUNÇÕES DE PERSISTÊNCIA ---
def carregar_aba(nome_aba):
    try:
        # ttl="0s" força o app a ler o dado mais recente da planilha sem cache
        df = conn.read(worksheet=nome_aba, ttl="0s")
        return df.dropna(how='all') # Remove linhas vazias acidentais
    except:
        return pd.DataFrame()

def salvar_na_nuvem(df, nome_aba):
    try:
        # Remove colunas que são apenas cálculos visuais
        cols_calc = ['Desvio (g)', 'Var %', 'Situação', 'Meta_Calculada_g']
        df_save = df.drop(columns=[c for c in cols_calc if c in df.columns], errors='ignore')
        
        # Atualiza a planilha online
        conn.update(worksheet=nome_aba, data=df_save)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Erro ao salvar na nuvem ({nome_aba}): {e}")
        return False

# --- ESTADO DA SESSÃO ---
if 'df_mestra' not in st.session_state:
    st.session_state.df_mestra = carregar_aba("Aba_Mestra")
if 'df_hist' not in st.session_state:
    st.session_state.df_hist = carregar_aba("Controle")
if 'df_padr' not in st.session_state:
    st.session_state.df_padr = carregar_aba("Padroes")

# --- 🔄 SINCRONIZAÇÃO MATEMÁTICA (4,8g de precisão) ---
def aplicar_calculos(df_h, df_m):
    if df_h.empty or df_m.empty: return df_h
    # Mapeia: (Tipo, Cor, Pigmento) -> Coeficiente kg/L
    mapa = df_m.set_index(['Tipo', 'Cor', 'Pigmento'])['Quant OP (kg)'].to_dict()
    
    def calc_g(row):
        chave = (str(row['tipo de produto']), str(row['cor']), str(row['pigmento']))
        coef = float(mapa.get(chave, 0.0))
        vol_total = float(row.get('#Plan', 1)) * float(row.get('Litros/Unit', 1))
        # Ex: 0.0048 kg/L * 1L * 1000 = 4.8g
        return round(coef * vol_total * 1000, 2)
    
    df_h['Quantidade OP'] = df_h.apply(calc_g, axis=1)
    return df_h

st.session_state.df_hist = aplicar_calculos(st.session_state.df_hist, st.session_state.df_mestra)

# --- NAVEGAÇÃO ---
menu = ["🚀 Produção", "📈 Dashboard CEP", "📜 Banco de Dados", "📊 Editor Aba Mestra", "📋 Padrões"]
aba = st.sidebar.radio("Ir para:", menu)

# --- 🚀 ABA: PRODUÇÃO ---
if aba == "🚀 Produção":
    st.title("🚀 Registro de Pesagem (Fábrica)")
    if st.session_state.df_mestra.empty:
        st.warning("⚠️ Aba Mestra não carregada ou sem dados.")
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
        check_p = v4.checkbox("🌟 Salvar como Padrão")

        formula = st.session_state.df_mestra[(st.session_state.df_mestra['Tipo'] == t_sel) & (st.session_state.df_mestra['Cor'] == cor_sel)]
        st.divider()

        regs = []
        for i, row in formula.iterrows():
            pigm = row['Pigmento']
            coef = float(row['Quant OP (kg)'])
            meta_g = round(coef * n_p * litros_u * 1000, 2)
            
            with st.container():
                ci, cp = st.columns([1.5, 3.5])
                ci.subheader(pigm)
                ci.write(f"Meta: **{meta_g} g**")
                n_t = ci.number_input(f"Toques", min_value=1, value=1, key=f"t_{i}")
                
                total_pigm = 0.0
                cols = cp.columns(5)
                for t in range(1, int(n_t) + 1):
                    val = cols[(t-1)%5].number_input(f"T{t}", min_value=0.0, format="%.2f", key=f"v_{i}_{t}")
                    total_pigm += val
                cp.info(f"Total Pesado: {total_pigm:.2f}g")
            
            regs.append({
                "data": data_f.strftime("%d/%m/%Y"), "lote": lote_id, "tipo de produto": t_sel,
                "cor": cor_sel, "pigmento": pigm, "Quant ad (g)": total_pigm,
                "Quantidade OP": coef, "#Plan": n_p, "#Real": n_r, "Litros/Unit": litros_u
            })
            st.divider()

        if st.button("💾 FINALIZAR E SINCRONIZAR LOTE"):
            if not lote_id: st.error("Por favor, informe o número do Lote.")
            else:
                novo_h = pd.concat([st.session_state.df_hist, pd.DataFrame(regs)], ignore_index=True)
                if salvar_na_nuvem(novo_h, "Controle"):
                    st.session_state.df_hist = novo_h
                    if check_p:
                        npadr = pd.DataFrame([{"Data": data_f.strftime("%d/%m/%Y"), "Produto": t_sel, "Cor": cor_sel, "Lote": lote_id, "Status": "Padrão"}])
                        st.session_state.df_padr = pd.concat([st.session_state.df_padr, npadr], ignore_index=True)
                        salvar_na_nuvem(st.session_state.df_padr, "Padroes")
                    st.success("Lote salvo no Google Sheets!"); st.balloons(); time.sleep(1); st.rerun()

# --- 📜 ABA: BANCO DE DADOS (Controle) ---
elif aba == "📜 Banco de Dados":
    st.title("📜 Histórico (Aba Controle)")
    df_v = st.session_state.df_hist.copy()
    df_v['Desvio (g)'] = pd.to_numeric(df_v['Quant ad (g)'], errors='coerce') - df_v['Quantidade OP']
    
    ed_h = st.data_editor(df_v, num_rows="dynamic", use_container_width=True)
    if st.button("☁️ ATUALIZAR NUVEM"):
        if salvar_na_nuvem(ed_h, "Controle"):
            st.success("Planilha atualizada!"); st.rerun()

# --- 📊 ABA: EDITOR ABA MESTRA ---
elif aba == "📊 Editor Aba Mestra":
    st.title("📊 Gestão de Fórmulas (Aba Mestra)")
    ed_m = st.data_editor(st.session_state.df_mestra, num_rows="dynamic", use_container_width=True)
    if st.button("☁️ SINCRONIZAR MESTRA"):
        if salvar_na_nuvem(ed_m, "Aba_Mestra"):
            st.success("Fórmulas atualizadas!"); st.rerun()

# --- 📋 ABA: PADRÕES ---
elif aba == "📋 Padrões":
    st.title("📋 Lotes Padrão")
    ed_p = st.data_editor(st.session_state.df_padr, num_rows="dynamic", use_container_width=True)
    if st.button("Salvar Padrões"):
        salvar_na_nuvem(ed_p, "Padroes")

# --- 📈 ABA: DASHBOARD CEP ---
elif aba == "📈 Dashboard CEP":
    st.title("📈 Controle Estatístico")
    if not st.session_state.df_hist.empty:
        p_sel = st.selectbox("Produto", sorted(st.session_state.df_hist['tipo de produto'].unique()))
        df_plot = st.session_state.df_hist[st.session_state.df_hist['tipo de produto'] == p_sel].copy()
        df_plot['Var %'] = ((df_plot['Quant ad (g)'] / df_plot['Quantidade OP'].replace(0, np.nan)) - 1) * 100
        st.line_chart(df_plot.pivot_table(index='lote', columns='pigmento', values='Var %'))
        st.dataframe(df_plot)

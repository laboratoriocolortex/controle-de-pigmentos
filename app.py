import streamlit as st
import pandas as pd
import numpy as np
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

# --- FUNÇÕES DE TRATAMENTO DE DADOS (BLINDAGEM) ---
def carregar_dados(arquivo):
    if not os.path.exists(arquivo): 
        if "Mestra" in arquivo:
            return pd.DataFrame(columns=['Tipo', 'Cor', 'Pigmento', 'Quant OP (kg)'])
        return pd.DataFrame()
    
    try:
        # Tenta vários encodings para evitar erro de caracteres (Massa Acrílica, etc)
        df = pd.DataFrame()
        for enc in ['latin-1', 'utf-8-sig', 'utf-8', 'cp1252']:
            try:
                df = pd.read_csv(arquivo, sep=None, engine='python', encoding=enc)
                if not df.empty: break
            except: continue
        
        if df.empty: return df

        # Limpeza de colunas: remove espaços invisíveis ("Tipo " -> "Tipo")
        df.columns = [str(c).strip() for c in df.columns]
        
        # Remove colunas e linhas totalmente vazias (comum ao exportar do Excel)
        df = df.dropna(how='all', axis=1).dropna(how='all', axis=0)
        
        # Padronização de Texto e Números
        for col in df.columns:
            if df[col].dtype == 'object':
                df[col] = df[col].astype(str).str.strip()
        
        # Conversão numérica segura (troca vírgula por ponto)
        cols_num = ['Quantidade OP', 'Quant ad (g)', '#Plan', 'Litros/Unit', 'Quant OP (kg)']
        for col in cols_num:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce').fillna(0.0)
        
        return df
    except Exception as e:
        st.error(f"Erro ao carregar {arquivo}: {e}")
        return pd.DataFrame()

def salvar_csv(df, arquivo):
    # Remove colunas de cálculo dinâmico para o CSV ficar limpo
    cols_calc = ['Desvio (g)', 'Var %', 'Situação', 'data_dt_temp', 'Esperado (g)']
    df_save = df.drop(columns=[c for c in cols_calc if c in df.columns], errors='ignore').copy()
    # Salva em latin-1 para compatibilidade total com Excel local
    df_save.to_csv(arquivo, index=False, encoding='latin-1', sep=',')

# --- CARREGAMENTO DOS DADOS ---
if 'df_mestra' not in st.session_state:
    st.session_state.df_mestra = carregar_dados("Aba_Mestra.csv")
if 'df_hist' not in st.session_state:
    st.session_state.df_hist = carregar_dados("Historico_Producao.csv")
if 'df_padr' not in st.session_state:
    st.session_state.df_padr = carregar_dados("Padroes_Registrados.csv")

# --- 🔄 SINCRONIZAÇÃO MATEMÁTICA (4,8g) ---
def sincronizar_formulas(df_h, df_m):
    if df_h.empty or df_m.empty: return df_h
    
    col_m = 'Quant OP (kg)' if 'Quant OP (kg)' in df_m.columns else 'Quantidade OP'
    if not all(c in df_m.columns for c in ['Tipo', 'Cor', 'Pigmento']):
        return df_h
        
    mapa = df_m.set_index(['Tipo', 'Cor', 'Pigmento'])[col_m].to_dict()
    
    def calc_meta(row):
        # Busca flexível por nomes de colunas (maiúsculas/minúsculas)
        t = str(row.get('tipo de produto', row.get('Tipo', '')))
        c = str(row.get('cor', row.get('Cor', '')))
        p = str(row.get('pigmento', row.get('Pigmento', '')))
        
        coef = float(mapa.get((t, c, p), 0.0))
        n_p = float(row.get('#Plan', 1))
        l_u = float(row.get('Litros/Unit', 1))
        
        return round(coef * n_p * l_u * 1000, 2)

    df_h['Quantidade OP'] = df_h.apply(calc_meta, axis=1)
    return df_h

st.session_state.df_hist = sincronizar_formulas(st.session_state.df_hist, st.session_state.df_mestra)

# --- NAVEGAÇÃO ---
menu = ["🚀 Produção", "📈 Gráficos CEP", "📜 Banco de Dados", "📊 Editor Aba Mestra", "📋 Padrões", "📂 Importar CSV"]
aba = st.sidebar.radio("Navegação:", menu)

# --- 🚀 PRODUÇÃO ---
if aba == "🚀 Produção":
    st.title("🚀 Registro de Pesagem")
    if st.session_state.df_mestra.empty:
        st.warning("⚠️ Adicione produtos na Aba Mestra primeiro.")
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
            coef = float(row.get('Quant OP (kg)', 0))
            meta_g = round(coef * n_p * litros_u * 1000, 2)
            
            with st.container():
                col_info, col_pesos = st.columns([1.5, 3.5])
                col_info.subheader(pigm)
                col_info.write(f"Meta: **{meta_g} g**")
                n_t = col_info.number_input(f"Toques", min_value=1, value=1, key=f"t_{i}")
                
                s_ad = 0.0
                cols = col_pesos.columns(5)
                for t in range(1, int(n_t) + 1):
                    val = cols[(t-1)%5].number_input(f"T{t}", min_value=0.0, format="%.2f", key=f"v_{i}_{t}")
                    s_ad += val
                col_pesos.info(f"Total Pesado: {s_ad:.2f}g")
            
            regs.append({
                "data": data_f.strftime("%d/%m/%Y"), "lote": lote_id, "tipo de produto": t_sel,
                "cor": cor_sel, "pigmento": pigm, "Quant ad (g)": s_ad,
                "Quantidade OP": coef, "#Plan": n_p, "#Real": n_r, "Litros/Unit": litros_u
            })
            st.divider()

        if st.button("💾 SALVAR LOTE"):
            if not lote_id: st.error("Lote obrigatório!")
            else:
                novo_h = pd.concat([st.session_state.df_hist, pd.DataFrame(regs)], ignore_index=True)
                salvar_csv(novo_h, "Historico_Producao.csv")
                st.session_state.df_hist = novo_h
                if check_p:
                    npadr = pd.DataFrame([{"Data": data_f.strftime("%d/%m/%Y"), "Produto": t_sel, "Cor": cor_sel, "Lote": lote_id, "Status": "Padrão"}])
                    st.session_state.df_padr = pd.concat([st.session_state.df_padr, npadr], ignore_index=True)
                    salvar_csv(st.session_state.df_padr, "Padroes_Registrados.csv")
                st.success("Lote registrado com sucesso!"); st.balloons(); time.sleep(1); st.rerun()

# --- 📜 BANCO DE DADOS ---
elif aba == "📜 Banco de Dados":
    st.title("📜 Gestão de Histórico")
    df_view = st.session_state.df_hist.copy()
    if not df_view.empty:
        df_view['Desvio (g)'] = df_view['Quant ad (g)'] - df_view['Quantidade OP']
        ed_h = st.data_editor(df_view, num_rows="dynamic", use_container_width=True)
        if st.button("💾 Salvar Alterações"):
            salvar_csv(ed_h, "Historico_Producao.csv")
            st.session_state.df_hist = ed_h
            st.success("Arquivo CSV atualizado!"); st.rerun()

# --- 📊 EDITOR ABA MESTRA ---
elif aba == "📊 Editor Aba Mestra":
    st.title("📊 Editor de Fórmulas")
    ed_m = st.data_editor(st.session_state.df_mestra, num_rows="dynamic", use_container_width=True)
    if st.button("💾 Salvar Fórmulas"):
        salvar_csv(ed_m, "Aba_Mestra.csv")
        st.session_state.df_mestra = ed_m
        st.success("Aba Mestra salva!"); st.rerun()

# --- 📈 GRÁFICOS CEP ---
elif aba == "📈 Gráficos CEP":
    st.title("📈 Análise CEP")
    if st.session_state.df_hist.empty: st.info("Sem dados.")
    else:
        p_sel = st.selectbox("Produto", sorted(st.session_state.df_hist['tipo de produto'].unique()))
        df_p = st.session_state.df_hist[st.session_state.df_hist['tipo de produto'] == p_sel].copy()
        df_p['Var %'] = ((df_p['Quant ad (g)'] / df_p['Quantidade OP'].replace(0, np.nan)) - 1) * 100
        st.line_chart(df_p.pivot_table(index='lote', columns='pigmento', values='Var %'))
        st.dataframe(df_p)

# --- 📂 IMPORTAR CSV ---
elif aba == "📂 Importar CSV":
    st.title("📂 Importar Novos Dados")
    up = st.file_uploader("Selecione o arquivo CSV", type="csv")
    alvo = st.selectbox("Onde salvar esses dados?", ["Aba_Mestra.csv", "Historico_Producao.csv", "Padroes_Registrados.csv"])
    if up and st.button("Confirmar Importação"):
        df_imp = pd.read_csv(up, sep=None, engine='python', encoding='latin-1')
        salvar_csv(df_imp, alvo)
        st.success(f"Arquivo {alvo} sobrescrevido com sucesso!"); time.sleep(1); st.rerun()

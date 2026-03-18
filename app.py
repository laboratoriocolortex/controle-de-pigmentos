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
    .btn-delete > div > button { background-color: #f8d7da !important; color: #721c24 !important; border: 1px solid #f5c6cb !important; }
    hr { margin: 0.8rem 0rem !important; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNÇÕES DE TRATAMENTO DE DADOS ---
def carregar_dados(arquivo):
    if not os.path.exists(arquivo): return pd.DataFrame()
    try:
        try:
            df = pd.read_csv(arquivo, sep=None, engine='python', encoding='latin-1')
        except:
            df = pd.read_csv(arquivo, sep=None, engine='python', encoding='utf-8')
        
        # Limpeza de colunas indesejadas e Unnamed
        cols_drop = [c for c in df.columns if "Unnamed" in str(c)] + ['data_dt_temp', 'toque', 'sugestão OP', 'sugestao OP']
        df = df.drop(columns=[c for c in cols_drop if c in df.columns], errors='ignore')
        
        df.columns = [str(c).strip() for c in df.columns]
        
        # Padronização de strings e conversão numérica
        for col in df.columns:
            if df[col].dtype == 'object':
                df[col] = df[col].astype(str).str.strip()
        
        cols_num = ['Quantidade OP', 'Quant ad (g)', '#Plan', 'Litros/Unit', 'Quant OP (kg)']
        for col in cols_num:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce').fillna(0.0)
        
        if 'data' in df.columns:
            df['data_dt_temp'] = pd.to_datetime(df['data'], format='%d/%m/%Y', errors='coerce')
        return df
    except: return pd.DataFrame()

def salvar_csv(df, arquivo):
    cols_drop = [c for c in df.columns if "Unnamed" in str(c)] + ['data_dt_temp', 'toque', 'sugestão OP', 'Desvio (g)', 'Var %', 'Situação']
    # Mantemos o histórico limpo, os cálculos são feitos em tempo real ao carregar/visualizar
    df_save = df.drop(columns=[c for c in cols_drop if c in df.columns], errors='ignore').copy()
    
    if 'Quantidade OP' in df_save.columns:
        df_save['Quantidade OP'] = pd.to_numeric(df_save['Quantidade OP'], errors='coerce').fillna(0.0).map('{:.5f}'.format)
    df_save.to_csv(arquivo, index=False, encoding='latin-1')

# --- CARREGAMENTO ---
df_mestra = carregar_dados("Aba_Mestra.csv")
df_hist = carregar_dados("Historico_Producao.csv")
df_padr = carregar_dados("Padroes_Registrados.csv")

# --- SINCRONIZAÇÃO COM ABA MESTRA (Prioridade Técnica) ---
if not df_hist.empty and not df_mestra.empty:
    mapeamento = df_mestra.set_index(['Tipo', 'Cor', 'Pigmento'])['Quant OP (kg)'].to_dict()
    def sincronizar(row):
        chave = (str(row['tipo de produto']), str(row['cor']), str(row['pigmento']))
        return float(mapeamento.get(chave, row.get('Quantidade OP', 0.0)))
    df_hist['Quantidade OP'] = df_hist.apply(sincronizar, axis=1)

# --- NAVEGAÇÃO ---
menu = ["🚀 Produção", "📈 Gráficos CEP", "📋 Padrões Registrados", "📜 Banco de Dados", "➕ Cadastro de Produtos", "📊 Editor Aba Mestra", "📂 Importar CSV"]
aba = st.sidebar.radio("Navegação:", menu)

# --- 🚀 ABA: PRODUÇÃO ---
if aba == "🚀 Produção":
    st.title("🚀 Registro de Pesagem")
    if df_mestra.empty:
        st.warning("⚠️ Aba Mestra vazia.")
    else:
        c1, c2, c3, c4 = st.columns([1.5, 1.5, 1, 1])
        with c1: t_sel = st.selectbox("Produto", sorted(df_mestra['Tipo'].unique()))
        with c2: cor_sel = st.selectbox("Cor", sorted(df_mestra[df_mestra['Tipo'] == t_sel]['Cor'].unique()))
        with c3: lote_id = st.text_input("Lote")
        with c4: data_f = st.date_input("Data", datetime.now(), format="DD/MM/YYYY")

        v1, v2, v3, v4 = st.columns([1, 1, 2, 1.5])
        with v1: n_p = st.number_input("# Unid Plan", min_value=1, value=1)
        with v2: n_r = st.number_input("# Unid Real", min_value=1, value=1)
        with v3:
            opcoes_v = ["0,9L", "3L", "3,6L", "14L", "15L", "18L", "5kg", "18kg", "25kg", "Outro"]
            sel_v = st.select_slider("Embalagem:", options=opcoes_v, value="15L")
            litros_u = float(sel_v.replace('L','').replace('kg','').replace(',','.')) if sel_v != "Outro" else st.number_input("Valor Unit:", value=15.0)
        with v4:
            st.write("") 
            salvar_como_padrao = st.checkbox("🌟 Salvar como novo padrão")

        vol_p_tot = n_p * litros_u
        formula = df_mestra[(df_mestra['Tipo'] == t_sel) & (df_mestra['Cor'] == cor_sel)]
        st.divider()

        registros_lote = []
        for i, row in formula.iterrows():
            pigm = row['Pigmento']
            coef = float(row['Quant OP (kg)'])
            sugestao_g = round(coef * vol_p_tot * 1000, 2)
            
            with st.container():
                col_i, col_p = st.columns([1.5, 3.5])
                with col_i:
                    st.subheader(pigm)
                    st.write(f"Sugestão: {sugestao_g}g")
                    n_t = st.number_input(f"Toques", min_value=1, value=1, key=f"nt_{i}")
                with col_p:
                    s_ad = 0.0
                    cols = st.columns(5)
                    for t in range(1, int(n_t) + 1):
                        with cols[(t-1)%5]:
                            v = st.number_input(f"T{t}", min_value=0.0, format="%.2f", key=f"v_{i}_{t}")
                            s_ad += v
                    st.markdown(f"**Total: {s_ad:.2f} g**")
            registros_lote.append({
                "data": data_f.strftime("%d/%m/%Y"), "lote": lote_id, "tipo de produto": t_sel,
                "cor": cor_sel, "pigmento": pigm, "Quant ad (g)": s_ad,
                "Quantidade OP": coef, "#Plan": n_p, "#Real": n_r, "Litros/Unit": litros_u
            })
            st.divider()

        if st.button("💾 SALVAR LOTE"):
            if not lote_id: st.error("Preencha o Lote.")
            else:
                df_hist = pd.concat([df_hist, pd.DataFrame(registros_lote)], ignore_index=True)
                salvar_csv(df_hist, "Historico_Producao.csv")
                if salvar_como_padrao:
                    n_padr = pd.DataFrame([{"Data": data_f.strftime("%d/%m/%Y"), "Produto": t_sel, "Cor": cor_sel, "Lote": lote_id, "Status": "Padrão"}])
                    df_padr = pd.concat([df_padr, n_padr], ignore_index=True)
                    salvar_csv(df_padr, "Padroes_Registrados.csv")
                st.balloons(); st.success("Lote salvo!"); time.sleep(1); st.rerun()

# --- 📈 ABA: GRÁFICOS CEP ---
elif aba == "📈 Gráficos CEP":
    st.title("📈 Dashboard de Qualidade")
    if df_hist.empty: st.info("Sem dados.")
    else:
        p_sel = st.selectbox("Produto", sorted(df_hist['tipo de produto'].unique()))
        c_sel = st.selectbox("Cor", sorted(df_hist[df_hist['tipo de produto'] == p_sel]['cor'].unique()))
        df_plot = df_hist[(df_hist['tipo de produto'] == p_sel) & (df_hist['cor'] == c_sel)].copy()

        if not df_plot.empty:
            # Cálculo do Desvio conforme regra solicitada
            df_plot['Esperado (g)'] = df_plot['Quantidade OP'] * (df_plot['#Plan'] * df_plot['Litros/Unit']) * 1000
            df_plot['Desvio (g)'] = df_plot['Quant ad (g)'] - df_plot['Esperado (g)']
            df_plot['Var %'] = ((df_plot['Quant ad (g)'] / df_plot['Esperado (g)'].replace(0, np.nan)) - 1) * 100
            
            st.line_chart(df_plot.pivot_table(index='lote', columns='pigmento', values='Var %'))
            
            df_table = df_plot.copy()
            df_table['Situação'] = df_table.apply(lambda r: "✅ Ok" if abs(r['Var %']) <= 10 else "⚠️ Fora", axis=1)
            st.dataframe(df_table[['data', 'lote', 'pigmento', 'Quant ad (g)', 'Esperado (g)', 'Desvio (g)', 'Situação']], use_container_width=True)

# --- 📜 ABA: BANCO DE DADOS (Cálculo Dinâmico) ---
elif aba == "📜 Banco de Dados":
    st.title("📜 Histórico e Auditoria")
    if not df_hist.empty:
        df_view = df_hist.copy()
        # Cálculo do Desvio baseado na Aba Mestra x Planejado
        esperado = df_view['Quantidade OP'] * (df_view['#Plan'] * df_view['Litros/Unit']) * 1000
        df_view['Desvio (g)'] = df_view['Quant ad (g)'] - esperado
        
        # Exibe apenas colunas relevantes, removendo lixo
        cols_final = [c for c in df_view.columns if c not in ['data_dt_temp', 'toque', 'sugestão OP']]
        st.dataframe(df_view[cols_final], use_container_width=True)
        
        csv_full = df_view[cols_final].to_csv(index=False).encode('utf-8-sig')
        st.download_button(label="📥 Exportar Banco de Dados", data=csv_full, file_name=f"Backup_R&D_{date.today()}.csv")

    st.divider()
    lote_d = st.text_input("Excluir Lote:")
    if lote_d and st.button("🚨 Confirmar Exclusão"):
        df_hist = df_hist[df_hist['lote'].astype(str) != lote_d]
        salvar_csv(df_hist, "Historico_Producao.csv"); st.rerun()

# --- DEMAIS ABAS ---
elif aba == "📋 Padrões Registrados":
    st.title("📋 Padrões")
    st.dataframe(df_padr, use_container_width=True)

elif aba == "➕ Cadastro de Produtos":
    st.title("➕ Novo Cadastro Técnico")
    with st.form("cad_f"):
        c1, c2 = st.columns(2)
        t = c1.text_input("Tipo")
        p = c1.text_input("Pigmento")
        cor = c2.text_input("Cor")
        coef = c2.number_input("Coef (kg/L)", format="%.6f")
        if st.form_submit_button("Cadastrar"):
            if t and cor and p:
                n = pd.DataFrame([{"Tipo": t.strip(), "Cor": cor.strip(), "Pigmento": p.strip(), "Quant OP (kg)": coef}])
                df_mestra = pd.concat([df_mestra, n], ignore_index=True)
                salvar_csv(df_mestra, "Aba_Mestra.csv"); st.success("Salvo!")

elif aba == "📊 Editor Aba Mestra":
    ed = st.data_editor(df_mestra, num_rows="dynamic")
    if st.button("Salvar Mestra"): salvar_csv(ed, "Aba_Mestra.csv"); st.success("Atualizada!")

elif aba == "📂 Importar CSV":
    up = st.file_uploader("CSV", type="csv")
    alvo = st.selectbox("Destino", ["Aba_Mestra.csv", "Historico_Producao.csv"])
    if up and st.button("Importar"):
        df_imp = pd.read_csv(up, encoding='latin-1', sep=None, engine='python')
        salvar_csv(df_imp, alvo); st.success("Importado!"); st.rerun()

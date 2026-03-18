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
        
        df.columns = [str(c).strip() for c in df.columns]
        if 'toque' in df.columns: df = df.drop(columns=['toque'])
        
        if 'data' in df.columns:
            df['data_dt'] = pd.to_datetime(df['data'], format='%d/%m/%Y', errors='coerce')
        return df
    except: return pd.DataFrame()

def salvar_csv(df, arquivo):
    df_save = df.drop(columns=['data_dt', 'toque'], errors='ignore').copy()
    if 'Quantidade OP' in df_save.columns:
        df_save['Quantidade OP'] = pd.to_numeric(df_save['Quantidade OP'], errors='coerce').map('{:.5f}'.format)
    df_save.to_csv(arquivo, index=False, encoding='latin-1')

# --- CARREGAMENTO INICIAL ---
df_mestra = carregar_dados("Aba_Mestra.csv")
df_hist = carregar_dados("Historico_Producao.csv")
df_padr = carregar_dados("Padroes_Registrados.csv")

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
            coef = pd.to_numeric(str(row['Quant OP (kg)']).replace(',', '.'), errors='coerce')
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
            if not lote_id:
                st.error("Preencha o Lote.")
            else:
                df_hist = pd.concat([df_hist, pd.DataFrame(registros_lote)], ignore_index=True)
                salvar_csv(df_hist, "Historico_Producao.csv")
                if salvar_como_padrao:
                    novo_padr = pd.DataFrame([{"Data": data_f.strftime("%d/%m/%Y"), "Produto": t_sel, "Cor": cor_sel, "Lote": lote_id, "Status": "Padrão"}])
                    df_padr = pd.concat([df_padr, novo_padr], ignore_index=True)
                    salvar_csv(df_padr, "Padroes_Registrados.csv")
                st.balloons(); st.success("Lote salvo!"); time.sleep(1.2); st.rerun()

# --- 📈 ABA: GRÁFICOS CEP ---
elif aba == "📈 Gráficos CEP":
    st.title("📈 Dashboard de Qualidade")
    if df_hist.empty:
        st.info("Sem dados no histórico.")
    else:
        with st.expander("🔍 Filtros", expanded=True):
            f1, f2, f3, f4, f5 = st.columns([1.2, 1, 1, 1.5, 1.5])
            with f1: usar_filtro = st.checkbox("Filtrar Data?", value=False)
            with f2: d_ini = st.date_input("Início", date(datetime.now().year, datetime.now().month, 1), format="DD/MM/YYYY", disabled=not usar_filtro)
            with f3: d_fim = st.date_input("Fim", datetime.now(), format="DD/MM/YYYY", disabled=not usar_filtro)
            with f4: p_sel = st.selectbox("Produto", sorted(df_hist['tipo de produto'].unique()))
            with f5: c_sel = st.selectbox("Cor", sorted(df_hist[df_hist['tipo de produto'] == p_sel]['cor'].unique()))

        df_plot = df_hist[(df_hist['tipo de produto'] == p_sel) & (df_hist['cor'] == c_sel)].copy()
        if usar_filtro:
            df_plot = df_plot[(df_plot['data_dt'].dt.date >= d_ini) & (df_plot['data_dt'].dt.date <= d_fim)]

        if not df_plot.empty:
            for col in ['Quant ad (g)', 'Quantidade OP']:
                df_plot[col] = pd.to_numeric(df_plot[col].astype(str).str.replace(',', '.'), errors='coerce').fillna(0.0)
            
            df_plot['OP_g'] = df_plot['Quantidade OP'] * 1000
            df_plot['Desvio (g)'] = df_plot['Quant ad (g)'] - df_plot['OP_g']
            df_plot['Var %'] = ((df_plot['Quant ad (g)'] / df_plot['OP_g'].replace(0, np.nan)) - 1) * 100
            
            st.subheader("Tendência de Desvios (%)")
            st.line_chart(df_plot.pivot_table(index='lote', columns='pigmento', values='Var %'))
            
            # --- TABELA DE VISUALIZAÇÃO COM EMOJIS ---
            st.subheader("📋 Dados Brutos Filtrados")
            df_table = df_plot.drop(columns=['data_dt', 'OP_g', 'Var %'], errors='ignore').copy()
            
            # Lógica dos Emojis: OK se <= 10% de excesso. ALERTA se > 10% excesso.
            def situacao_emoji(row):
                op_g = float(row['Quantidade OP']) * 1000
                ad_g = float(row['Quant ad (g)'])
                # Se ad_g for menor ou igual à OP + 10% de tolerância, está OK
                return "✅ Ok" if ad_g <= (op_g * 1.10) else "⚠️ Alerta"

            df_table['Situação'] = df_table.apply(situacao_emoji, axis=1)
            
            # Formatação numérica
            df_table['Quantidade OP'] = df_table['Quantidade OP'].map('{:.5f}'.format)
            df_table['Desvio (g)'] = df_table['Desvio (g)'].map('{:.1f}'.format)
                
            st.dataframe(df_table, use_container_width=True)
            
            csv_data = df_plot.to_csv(index=False).encode('utf-8-sig')
            st.download_button(label="📥 Baixar Relatório (CSV)", data=csv_data, file_name=f"CEP_{p_sel}_{c_sel}.csv", mime="text/csv")
        else:
            st.warning("Sem registros.")

# --- 📜 ABA: BANCO DE DADOS (COM BUSCA E EXCLUSÃO) ---
elif aba == "📜 Banco de Dados":
    st.title("📜 Histórico e Manutenção")
    if not df_hist.empty:
        df_display = df_hist.drop(columns=['data_dt'], errors='ignore').copy()
        if 'Quantidade OP' in df_display.columns:
            df_display['Quantidade OP'] = pd.to_numeric(df_display['Quantidade OP'], errors='coerce').map('{:.5f}'.format)
        st.dataframe(df_display, use_container_width=True)
    
    st.divider()
    c_padr, c_del = st.columns(2)
    
    with c_padr:
        st.subheader("🌟 Definir Novo Padrão")
        lote_padr = st.text_input("Lote para Padrão:", key="padr_in")
        if lote_padr:
            res = df_hist[df_hist['lote'].astype(str) == lote_padr].drop_duplicates(subset=['lote'])
            if not res.empty:
                row = res.iloc[0]
                st.success(f"Lote: {row['tipo de produto']} - {row['cor']}")
                if st.button(f"⭐ Confirmar Padrão {lote_padr}"):
                    n = pd.DataFrame([{"Data": row['data'], "Produto": row['tipo de produto'], "Cor": row['cor'], "Lote": row['lote'], "Status": "Padrão"}])
                    df_padr = pd.concat([df_padr, n], ignore_index=True).drop_duplicates()
                    salvar_csv(df_padr, "Padroes_Registrados.csv"); st.toast("Padrão salvo!"); time.sleep(1); st.rerun()

    with c_del:
        st.subheader("🗑️ Apagar Lote Incorreto")
        lote_del = st.text_input("Lote para EXCLUIR:", key="del_in")
        if lote_del:
            res_del = df_hist[df_hist['lote'].astype(str) == lote_del]
            if not res_del.empty:
                st.warning(f"Atenção: {len(res_del)} linhas serão apagadas.")
                st.markdown('<div class="btn-delete">', unsafe_allow_html=True)
                if st.button(f"🚨 EXCLUIR LOTE {lote_del}"):
                    df_hist = df_hist[df_hist['lote'].astype(str) != lote_del]
                    salvar_csv(df_hist, "Historico_Producao.csv")
                    st.error("Lote excluído."); time.sleep(1.2); st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

# --- DEMAIS ABAS (MANTIDAS) ---
elif aba == "📋 Padrões Registrados":
    st.title("📋 Padrões Registrados")
    st.dataframe(df_padr, use_container_width=True)
    if not df_padr.empty and st.button("Limpar Lista"):
        salvar_csv(pd.DataFrame(columns=["Data", "Produto", "Cor", "Lote", "Status"]), "Padroes_Registrados.csv"); st.rerun()

elif aba == "➕ Cadastro de Produtos":
    st.title("➕ Novo Pigmento")
    with st.form("f_cad"):
        c1, c2 = st.columns(2)
        t = c1.text_input("Tipo"); p = c1.text_input("Pigmento"); cor = c2.text_input("Cor"); coef = c2.number_input("Coef (kg/L)", format="%.6f")
        if st.form_submit_button("Cadastrar"):
            if t and cor and p:
                n = pd.DataFrame([{"Tipo": t.title(), "Cor": cor.title(), "Pigmento": p.title(), "Quant OP (kg)": coef}])
                df_mestra = pd.concat([df_mestra, n], ignore_index=True); salvar_csv(df_mestra, "Aba_Mestra.csv"); st.success("Salvo!"); time.sleep(1); st.rerun()

elif aba == "📊 Editor Aba Mestra":
    ed = st.data_editor(df_mestra, num_rows="dynamic")
    if st.button("Salvar Alterações"): salvar_csv(ed, "Aba_Mestra.csv"); st.success("Atualizado!")

elif aba == "📂 Importar CSV":
    up = st.file_uploader("CSV", type="csv")
    alvo = st.selectbox("Destino", ["Aba_Mestra.csv", "Historico_Producao.csv", "Padroes_Registrados.csv"])
    if up and st.button("Importar"): salvar_csv(pd.read_csv(up, encoding='latin-1', sep=None, engine='python'), alvo); st.rerun()

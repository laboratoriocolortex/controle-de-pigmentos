import streamlit as st
import pandas as pd
import numpy as np
import os
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

# --- FUNÇÕES DE TRATAMENTO DE DADOS ---
def carregar_dados(arquivo):
    if not os.path.exists(arquivo): return pd.DataFrame()
    try:
        try:
            df = pd.read_csv(arquivo, sep=None, engine='python', encoding='latin-1')
        except:
            df = pd.read_csv(arquivo, sep=None, engine='python', encoding='utf-8')
        
        df.columns = [str(c).strip() for c in df.columns]
        if 'data' in df.columns:
            # Converte a coluna de texto para data real para podermos filtrar
            df['data_dt'] = pd.to_datetime(df['data'], format='%d/%m/%Y', errors='coerce')
        return df
    except: return pd.DataFrame()

def salvar_csv(df, arquivo):
    # Remove a coluna auxiliar de data antes de salvar no arquivo físico
    df_save = df.drop(columns=['data_dt'], errors='ignore')
    df_save.to_csv(arquivo, index=False, encoding='latin-1')

# --- CARREGAMENTO INICIAL ---
df_mestra = carregar_dados("Aba_Mestra.csv")
df_hist = carregar_dados("Historico_Producao.csv")
df_padr = carregar_dados("Padroes_Registrados.csv")

# --- NAVEGAÇÃO ---
menu = ["🚀 Produção (Toques)", "📈 Gráficos CEP", "📋 Padrões Registrados", "📜 Banco de Dados", "➕ Cadastro de Produtos", "📊 Editor Aba Mestra", "📂 Importar CSV"]
aba = st.sidebar.radio("Navegação:", menu)

# --- 🚀 ABA: PRODUÇÃO ---
if aba == "🚀 Produção (Toques)":
    st.title("🚀 Registro de Pesagem")
    if df_mestra.empty:
        st.warning("⚠️ Aba Mestra vazia. Importe a planilha para começar.")
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
            opcoes_v = ["0,9L", "3,6L", "15L", "18L", "25kg", "Outro"]
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
                "data": data_f.strftime("%d/%m/%Y"), 
                "lote": lote_id, "tipo de produto": t_sel,
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
                st.success("Salvo com sucesso!"); st.rerun()

# --- 📈 ABA: CEP (FILTRO OPCIONAL E EXPORTAÇÃO CORRIGIDA) ---
elif aba == "📈 Gráficos CEP":
    st.title("📈 Dashboard de Qualidade e Consumo")
    
    if df_hist.empty:
        st.info("Ainda não há dados registrados no histórico.")
    else:
        with st.expander("🔍 Filtros de Busca", expanded=True):
            f1, f2, f3, f4, f5 = st.columns([1.2, 1, 1, 1.5, 1.5])
            with f1: 
                usar_filtro_data = st.checkbox("Filtrar por Data?", value=False)
            with f2: 
                d_ini = st.date_input("Início", date(datetime.now().year, datetime.now().month, 1), format="DD/MM/YYYY", disabled=not usar_filtro_data)
            with f3: 
                d_fim = st.date_input("Fim", datetime.now(), format="DD/MM/YYYY", disabled=not usar_filtro_data)
            with f4: 
                # Garantir que as variáveis de seleção existam antes de qualquer erro
                opcoes_prod = sorted(df_hist['tipo de produto'].unique())
                p_sel = st.selectbox("Produto", opcoes_prod)
            with f5: 
                opcoes_cor = sorted(df_hist[df_hist['tipo de produto'] == p_sel]['cor'].unique())
                c_sel = st.selectbox("Cor", opcoes_cor)

        # Filtragem Principal
        df_plot = df_hist[(df_hist['tipo de produto'] == p_sel) & (df_hist['cor'] == c_sel)].copy()
        
        # Filtragem Opcional por Data
        if usar_filtro_data:
            df_plot = df_plot[(df_plot['data_dt'].dt.date >= d_ini) & (df_plot['data_dt'].dt.date <= d_fim)]

        if not df_plot.empty:
            # Tratamento numérico para evitar erros de cálculo
            for col in ['Quant ad (g)', 'Quantidade OP']:
                df_plot[col] = pd.to_numeric(df_plot[col].astype(str).str.replace(',', '.'), errors='coerce').fillna(0.0)
            
            df_plot['OP_g'] = df_plot['Quantidade OP'] * 1000
            df_plot['Desvio (g)'] = df_plot['Quant ad (g)'] - df_plot['OP_g']
            df_plot['Status'] = df_plot.apply(lambda r: "🚨" if (r['OP_g'] > 0 and (r['Desvio (g)'] / r['OP_g']) * 100 > 10.0) else "✅", axis=1)

            # Gráfico
            df_plot['lote'] = df_plot['lote'].astype(str)
            st.line_chart(df_plot.assign(Var_Perc=((df_plot['Quant ad (g)']/df_plot['OP_g'].replace(0,np.nan))-1)*100).pivot_table(index='lote', columns='pigmento', values='Var_Perc'))
            
            st.subheader("📋 Relatório Filtrado")
            st.dataframe(df_plot[['data', 'lote', 'pigmento', 'Quant ad (g)', 'OP_g', 'Desvio (g)', 'Status']].style.format({
                'Desvio (g)': '{:.2f}g', 
                'Quant ad (g)': '{:.2f}g', 
                'OP_g': '{:.2f}g'
            }))
            
            # --- CORREÇÃO DO ERRO DE EXPORTAÇÃO ---
            # Geramos o CSV com utf-8-sig para suportar acentos e ser lido pelo Excel
            csv_export = df_plot.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label="📥 Baixar Relatório (CSV)", 
                data=csv_export, 
                file_name=f"Relatorio_{p_sel}_{cor_sel}.csv", 
                mime="text/csv"
            )

            st.divider()
            st.subheader("📊 Consumo Acumulado")
            res_est = df_plot.groupby('pigmento')['Desvio (g)'].sum().reset_index()
            c1, c2 = st.columns([2, 1])
            with c1:
                st.dataframe(res_est.style.format({'Desvio (g)': '{:.2f}g'}).applymap(lambda x: 'color: red;' if x > 0 else 'color: green;', subset=['Desvio (g)']))
            with c2:
                total_acumulado = res_est['Desvio (g)'].sum()
                st.metric("Saldo Geral", f"{total_acumulado:.2f} g", delta=f"{total_acumulado:.2f} g", delta_color="inverse")
        else:
            st.warning("Sem dados para exibir com os filtros atuais.")

# --- OUTRAS ABAS ---
elif aba == "➕ Cadastro de Produtos":
    st.title("➕ Novo Pigmento na Mestra")
    with st.form("f_cad"):
        c1, c2 = st.columns(2)
        with c1: t = st.text_input("Tipo"); p = st.text_input("Pigmento")
        with c2: cor = st.text_input("Cor"); coef = st.number_input("Coef (kg/L)", format="%.6f")
        if st.form_submit_button("Cadastrar"):
            if t and cor and p:
                n = pd.DataFrame([{"Tipo": t.title(), "Cor": cor.title(), "Pigmento": p.title(), "Quant OP (kg)": coef}])
                df_mestra = pd.concat([df_mestra, n], ignore_index=True)
                salvar_csv(df_mestra, "Aba_Mestra.csv"); st.success("Cadastrado!"); st.rerun()

elif aba == "📋 Padrões Registrados":
    st.dataframe(df_padr)

elif aba == "📂 Importar CSV":
    up = st.file_uploader("Arquivo CSV", type="csv")
    alvo = st.selectbox("Destino", ["Aba_Mestra.csv", "Historico_Producao.csv", "Padroes_Registrados.csv"])
    if up and st.button("Confirmar"):
        salvar_csv(pd.read_csv(up, encoding='latin-1', sep=None, engine='python'), alvo); st.success("Ok!"); st.rerun()

elif aba == "📊 Editor Aba Mestra":
    ed = st.data_editor(df_mestra, num_rows="dynamic")
    if st.button("Salvar Tudo"): salvar_csv(ed, "Aba_Mestra.csv"); st.success("Salvo!")

elif aba == "📜 Banco de Dados":
    st.dataframe(df_hist)

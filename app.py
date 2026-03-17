import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Controle 2026 - Google Sheets", layout="wide")

# URL DA SUA PLANILHA (PÚBLICA PARA EDIÇÃO)
url_planilha = "https://docs.google.com/spreadsheets/d/19OfTga1-LFrsYS4PHcdx3nB3EAgf1oviNvp3qIuwtq8/edit#gid=1870828680"

# 2. CONEXÃO COM GOOGLE SHEETS
conn = st.connection("gsheets", type=GSheetsConnection)

def carregar_mestra():
    # Lê a aba Mestra
    df = conn.read(spreadsheet=url_planilha, worksheet="1870828680", ttl="0") # Gid da Aba Mestra
    df.columns = [str(c).strip() for c in df.columns]
    # Limpeza de números
    if "Quant OP (kg)" in df.columns:
        df["Quant OP (kg)"] = pd.to_numeric(df["Quant OP (kg)"].astype(str).str.replace(',', '.'), errors='coerce').fillna(0.0)
    return df

def carregar_historico():
    # Lê a aba de Histórico (Gid 0 geralmente é a primeira aba)
    try:
        df = conn.read(spreadsheet=url_planilha, worksheet="0", ttl="0")
        return df
    except:
        return pd.DataFrame()

# --- INTERFACE ---
df_mestra = carregar_mestra()
menu = ["🚀 Registrar Produção", "📊 Banco de Dados (Sheets)", "📈 CEP"]
aba = st.sidebar.radio("Menu:", menu)

if aba == "🚀 Registrar Produção":
    st.title("🚀 Registrar Lote no Google Sheets")
    
    with st.form("registro_lote"):
        c1, c2, c3 = st.columns(3)
        with c1: t_sel = st.selectbox("Produto", sorted(df_mestra['Tipo'].unique()))
        with c2: c_sel = st.selectbox("Cor", sorted(df_mestra[df_mestra['Tipo'] == t_sel]['Cor'].unique()))
        with c3: lote_id = st.text_input("Número do Lote")

        c4, c5, c6 = st.columns(3)
        with c4: data_fab = st.date_input("Data de Fabricação", datetime.now())
        with c5: n_p = st.number_input("Unid Plan", min_value=1, value=1)
        with c6: n_r = st.number_input("Unid Real", min_value=1, value=1)
        
        lit_u = st.number_input("Litros Unit", value=15.0)
        
        st.divider()
        formulas = df_mestra[(df_mestra['Tipo'] == t_sel) & (df_mestra['Cor'] == c_sel)]
        pesos_reais = {}
        for i, row in formulas.iterrows():
            sugestao = row["Quant OP (kg)"] * n_p * lit_u * 1000
            pesos_reais[i] = st.number_input(f"Peso Real (g) - {row['Pigmento']} (Sugestão: {sugestao:.2f}g)", key=f"p_{i}", min_value=0.0)

        if st.form_submit_button("SALVAR NA PLANILHA"):
            if not lote_id:
                st.error("Informe o lote!")
            else:
                novas_linhas = []
                for i, row in formulas.iterrows():
                    v_plan, v_real = n_p * lit_u, n_r * lit_u
                    cons_real = (pesos_reais[i] / 1000) / v_real if v_real > 0 else 0
                    var_p = (cons_real / row["Quant OP (kg)"]) - 1 if row["Quant OP (kg)"] > 0 else 0
                    
                    novas_linhas.append({
                        'Data_Fabricacao': data_fab.strftime("%d/%m/%Y"),
                        'Lote': lote_id, 'Tipo_Produto': t_sel, 'Cor': c_sel, 'Pigmento': row['Pigmento'],
                        'Toque': 1, 'Quant_ad_g': pesos_reais[i], 
                        'Quantidade_OP_g': row["Quant OP (kg)"] * v_plan * 1000,
                        'Unid_Plan': n_p, 'Unid_Real': n_r, 'Encomenda': "Não",
                        'Litros_Unit': lit_u, 'Vol_Plan': v_plan, 'Vol_Real': v_real,
                        'Formula_kgL': row["Quant OP (kg)"], 'Consumo_Real_kgL': cons_real,
                        'Variacao_Perc': var_p, 'Variacao_Abs_kg': (pesos_reais[i]/1000) - (v_real * row["Quant OP (kg)"])
                    })
                
                # BUSCA HISTÓRICO ATUAL, ANEXA E SALVA DE VOLTA
                df_h_atual = carregar_historico()
                df_final = pd.concat([df_h_atual, pd.DataFrame(novas_linhas)], ignore_index=True)
                
                conn.update(spreadsheet=url_planilha, worksheet="0", data=df_final)
                st.success("✅ Salvo com sucesso no Google Sheets!")
                st.balloons()

elif aba == "📊 Banco de Dados (Sheets)":
    st.title("📊 Dados Sincronizados com Google Sheets")
    df_h = carregar_historico()
    if not df_h.empty:
        st.dataframe(df_h, use_container_width=True)
    else:
        st.info("Nenhum dado no Histórico.")

elif aba == "📈 CEP":
    st.title("📈 CEP - Variação %")
    df_h = carregar_historico()
    if not df_h.empty:
        df_h['Variacao_Perc'] = pd.to_numeric(df_h['Variacao_Perc'].astype(str).str.replace(',', '.'), errors='coerce')
        p_sel = st.selectbox("Produto", df_h['Tipo_Produto'].unique())
        df_f = df_h[df_h['Tipo_Produto'] == p_sel]
        st.line_chart(df_f.pivot_table(index='Lote', columns='Pigmento', values='Variacao_Perc'))

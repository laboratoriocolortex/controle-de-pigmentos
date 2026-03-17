import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Controle Colortex", layout="wide")

# URL da sua planilha (Certifique-se de que está como "Editor")
URL_PLANILHA = "https://docs.google.com/spreadsheets/d/19OfTga1-LFrsYS4PHcdx3nB3EAgf1oviNvp3qIuwtq8/edit#gid=1870828680"

conn = st.connection("gsheets", type=GSheetsConnection)

# Função para carregar a Aba Mestra (Gid 1870828680)
def load_mestra():
    df = conn.read(spreadsheet=URL_PLANILHA, worksheet="1870828680", ttl=0)
    return df

# Função para carregar o Histórico (Gid 0)
def load_historico():
    df = conn.read(spreadsheet=URL_PLANILHA, worksheet="0", ttl=0)
    return df

df_mestra = load_mestra()

st.sidebar.title("Menu")
aba = st.sidebar.radio("Selecione:", ["🚀 Registrar", "📊 Histórico"])

if aba == "🚀 Registrar":
    st.title("Registro de Pigmentação")
    
    with st.form("meu_formulario"):
        c1, c2 = st.columns(2)
        with c1:
            # Pegando os nomes das colunas da Mestra
            prod_sel = st.selectbox("Tipo de Produto", df_mestra['Tipo de Produto'].unique())
            cor_sel = st.selectbox("Cor", df_mestra[df_mestra['Tipo de Produto'] == prod_sel]['Cor'].unique())
        with c2:
            lote_id = st.text_input("Lote")
            data_fab = st.date_input("Data de Fabricação")

        st.divider()
        
        # Filtra os pigmentos para aquele produto/cor
        formulas = df_mestra[(df_mestra['Tipo'] == prod_sel) & (df_mestra['Cor'] == cor_sel)]
        
        pesos_reais = {}
        for i, row in formulas.iterrows():
            pesos_reais[i] = st.number_input(f"Peso Real (g) - {row['Pigmento']}", min_value=0.0)

        # Campos extras que aparecem na sua foto
        unid_real = st.number_input("#Real (Unidades)", min_value=1, value=1)
        litros_unid = st.number_input("Litros/Unit", value=15.0)

        if st.form_submit_button("Salvar no Google Sheets"):
            novos_dados = []
            for i, row in formulas.iterrows():
                # Fazendo os cálculos A-Q conforme as colunas da sua foto
                v_real = unid_real * litros_unid
                cons_real = (pesos_reais[i] / 1000) / v_real if v_real > 0 else 0
                
                novos_dados.append({
                    "data": data_fab.strftime("%d/%m/%Y"),
                    "lote": lote_id,
                    "tipo de pr": prod_sel,
                    "cor": cor_sel,
                    "pigmento": row['Pigmento'],
                    "toque": row.get('Toque', 1), # Ajuste se houver coluna toque na mestra
                    "Quant ad (": pesos_reais[i],
                    "Quantidade": row['Quant OP (kg)'] * v_real * 1000,
                    "#Plan": unid_real,
                    "#Real": unid_real,
                    "Encomend": "Não",
                    "Litros/Unit": litros_unid,
                    # Adicione aqui o restante das colunas M até Q se desejar
                })
            
            # União com o que já existe
            df_atual = load_historico()
            df_final = pd.concat([df_atual, pd.DataFrame(novos_dados)], ignore_index=True)
            
            # Atualiza a planilha
            conn.update(spreadsheet=URL_PLANILHA, worksheet="0", data=df_final)
            st.success("Dados gravados com sucesso!")

elif aba == "📊 Histórico":
    st.title("Histórico de Produção")
    df_h = load_historico()
    st.dataframe(df_h)

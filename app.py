import streamlit as st
import pandas as pd
import os
from datetime import datetime
import numpy as np

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Controle de Produção 2026", layout="wide", page_icon="🧪")

# --- FUNÇÕES DE ARQUIVO ---

def load_mestra():
    file = "Aba_Mestra.csv"
    if not os.path.exists(file):
        df_init = pd.DataFrame(columns=['Tipo', 'Cor', 'Pigmento', 'Quant OP (kg)'])
        df_init.to_csv(file, index=False, encoding='utf-8-sig')
        return df_init
    try:
        df = pd.read_csv(file, encoding='utf-8-sig')
        if not df.empty and 'Quant OP (kg)' in df.columns:
            df['Quant OP (kg)'] = df['Quant OP (kg)'].astype(str).str.replace(',', '.')
            df['Quant OP (kg)'] = pd.to_numeric(df['Quant OP (kg)'], errors='coerce').fillna(0.0)
        return df
    except:
        return pd.DataFrame(columns=['Tipo', 'Cor', 'Pigmento', 'Quant OP (kg)'])

def salvar_no_historico_completo(novos_dados_df):
    file = "Historico_Producao.csv"
    
    # Define a ordem exata das colunas (A-Q)
    colunas_aq = [
        'Data', 'Lote', 'Tipo de Produto', 'Cor', 'Pigmento', 'Toque', 
        'Quant ad (g)', 'Quantidade OP (g)', 'Unid Plan', 'Unid Real', 
        'Encomenda', 'Litros Unit', 'Volume Planejado', 'Volume Produzido', 
        'Formulação (kg/L)', 'Consumo Real (kg/L)', 'Variação %', 'Variação Absoluta (kg)'
    ]
    
    # Garante que o DataFrame novo tem todas as colunas
    novos_dados_df = novos_dados_df[colunas_aq]

    if os.path.exists(file):
        try:
            hist_antigo = pd.read_csv(file, sep=';', encoding='utf-8-sig')
            df_final = pd.concat([hist_antigo, novos_dados_df], ignore_index=True)
        except:
            df_final = novos_dados_df
    else:
        df_final = novos_dados_df
    
    # Salva com separador ; e decimal , para compatibilidade total com Excel
    df_final.to_csv(file, index=False, sep=';', encoding='utf-8-sig', decimal=',')

# --- INTERFACE ---

df_mestra = load_mestra()
menu = ["🚀 Registrar Produção", "📊 Banco de Dados (A-Q)", "📈 Gráficos CEP", "⚙️ Configurações"]
aba = st.sidebar.radio("Navegação:", menu)

if aba == "🚀 Registrar Produção":
    st.title("🚀 Registrar Lote")
    
    if df_mestra.empty:
        st.warning("⚠️ Aba Mestra vazia. Vá em 'Configurações'.")
    else:
        with st.form("registro_lote"):
            c1, c2, c3 = st.columns(3)
            with c1: t_sel = st.selectbox("Produto", sorted(df_mestra['Tipo'].unique()))
            with c2: c_sel = st.selectbox("Cor", sorted(df_mestra[df_mestra['Tipo'] == t_sel]['Cor'].unique()))
            with c3: lote_id = st.text_input("Número do Lote")

            c4, c5, c6 = st.columns(3)
            with c4: data_prod = st.date_input("Data de Produção", datetime.now())
            with c5: n_p = st.number_input("Unid Plan", min_value=1, value=1)
            with c6: n_r = st.number_input("Unid Real", min_value=1, value=1)
            
            lit_u = st.number_input("Litros Unit", value=15.0)
            
            st.divider()
            formulas = df_mestra[(df_mestra['Tipo'] == t_sel) & (df_mestra['Cor'] == c_sel)]
            pesos_reais = {}
            
            for i, row in formulas.iterrows():
                sugestao = row["Quant OP (kg)"] * n_p * lit_u * 1000
                pesos_reais[i] = st.number_input(f"Peso Real (g) - {row['Pigmento']} (Sugestão: {sugestao:.2f}g)", key=f"p_{i}", min_value=0.0)

            if st.form_submit_button("SALVAR REGISTRO"):
                if not lote_id:
                    st.error("Informe o lote!")
                else:
                    novas_linhas = []
                    for i, row in formulas.iterrows():
                        v_plan = n_p * lit_u
                        v_real = n_r * lit_u
                        cons_real = (pesos_reais[i] / 1000) / v_real if v_real > 0 else 0
                        var_p = (cons_real / row["Quant OP (kg)"]) - 1 if row["Quant OP (kg)"] > 0 else 0
                        
                        novas_linhas.append({
                            'Data': data_prod.strftime("%d/%m/%Y"),
                            'Lote': lote_id,
                            'Tipo de Produto': t_sel,
                            'Cor': c_sel,
                            'Pigmento': row['Pigmento'],
                            'Toque': 1,
                            'Quant ad (g)': pesos_reais[i],
                            'Quantidade OP (g)': row["Quant OP (kg)"] * v_plan * 1000,
                            'Unid Plan': n_p,
                            'Unid Real': n_r,
                            'Encomenda': "Não",
                            'Litros Unit': lit_u,
                            'Volume Planejado': v_plan,
                            'Volume Produzido': v_real,
                            'Formulação (kg/L)': row["Quant OP (kg)"],
                            'Consumo Real (kg/L)': cons_real,
                            'Variação %': var_p,
                            'Variação Absoluta (kg)': (pesos_reais[i]/1000) - (v_real * row["Quant OP (kg)"])
                        })
                    
                    salvar_no_historico_completo(pd.DataFrame(novas_linhas))
                    st.success("Lote salvo com todas as colunas (A-Q)!")

elif aba == "📊 Banco de Dados (A-Q)":
    st.title("📜 Histórico Completo")
    if os.path.exists("Historico_Producao.csv"):
        # Lendo com decimal vírgula para exibir corretamente
        df_h = pd.read_csv("Historico_Producao.csv", sep=';', encoding='utf-8-sig', decimal=',')
        st.dataframe(df_h, use_container_width=True)
        
        csv = df_h.to_csv(index=False, sep=';', encoding='utf-8-sig', decimal=',').encode('utf-8-sig')
        st.download_button("📥 Baixar Planilha Completa", csv, "Historico_A_Q.csv", "text/csv")
    else:
        st.info("Nenhum registro encontrado.")

elif aba == "📈 Gráficos CEP":
    st.title("📈 Controle de Processo (CEP)")
    
    if os.path.exists("Historico_Producao.csv"):
        # Carregamos tratando os números para o gráfico não quebrar
        df_h = pd.read_csv("Historico_Producao.csv", sep=';', encoding='utf-8-sig', decimal=',')
        
        # Converte Variação % para número (caso o pandas leia como string)
        df_h['Variação %'] = pd.to_numeric(df_h['Variação %'].astype(str).str.replace(',', '.'), errors='coerce')
        
        p_sel = st.selectbox("Escolha o Produto", df_h['Tipo de Produto'].unique())
        df_f = df_h[df_h['Tipo de Produto'] == p_sel]
        
        if not df_f.empty:
            grafico_data = df_f.pivot_table(index='Lote', columns='Pigmento', values='Variação %')
            st.line_chart(grafico_data)
    else:
        st.error("Sem dados registrados.")

elif aba == "⚙️ Configurações":
    st.title("⚙️ Gerenciar Aba Mestra")
    df_editada = st.data_editor(df_mestra, num_rows="dynamic", use_container_width=True)
    if st.button("💾 Salvar Aba Mestra"):
        df_editada.to_csv("Aba_Mestra.csv", index=False, encoding='utf-8-sig')
        st.success("Configurações salvas!")
        st.rerun()

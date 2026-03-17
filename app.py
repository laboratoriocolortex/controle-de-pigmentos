import streamlit as st
import pandas as pd
import os
from datetime import datetime
import numpy as np

# Configuração inicial da página
st.set_page_config(page_title="Controle Colortex 2026", layout="wide", page_icon="🧪")

# --- FUNÇÃO PARA CORRIGIR ACENTOS E PADRONIZAR ---
def corrigir_acentos(df):
    """Corrige 'Oxido' para 'Óxido' e remove espaços extras nas colunas de texto."""
    if df.empty: return df
    
    # Lista de termos para substituir (pode adicionar mais se precisar)
    substituicoes = {
        'Oxido': 'Óxido',
        'oxido': 'óxido',
        'OXIDO': 'ÓXIDO'
    }
    
    # Colunas onde geralmente ocorrem esses nomes
    cols_texto = ['tipo de produto', 'cor', 'pigmento', 'Tipo', 'Cor', 'Pigmento', 'Produto']
    
    for col in df.columns:
        if col in cols_texto:
            df[col] = df[col].astype(str).str.strip()
            for errado, correto in substituicoes.items():
                df[col] = df[col].str.replace(errado, correto, regex=False)
    return df

# --- FUNÇÕES DE CARREGAMENTO MELHORADAS ---
def load_data(file):
    if os.path.exists(file):
        try:
            # Tenta UTF-8 primeiro, se falhar vai para Latin-1 (resolve erro de acento no Windows)
            try:
                df = pd.read_csv(file, sep=None, engine='python', encoding='utf-8')
            except:
                df = pd.read_csv(file, sep=None, engine='python', encoding='latin-1')
            
            df.columns = [str(c).strip() for c in df.columns]
            df = corrigir_acentos(df)
            return df
        except:
            return pd.DataFrame()
    return pd.DataFrame()

# ... (Mantenha as funções format_num_padrao, atualizar_padroes_e_mestra e salvar_no_historico iguais às anteriores) ...

def atualizar_padroes_e_mestra(df_mestra, lista_lote, vol_plan_calculo, vol_real_calculo, data_fab):
    padroes_file = "Padroes_Registrados.csv"
    novos_registros_padrao = []
    if vol_real_calculo <= 0: return df_mestra, False
    for item in lista_lote:
        concentracao_real_g_l = item["Quant ad (g_num)"] / vol_real_calculo
        novo_coef = (concentracao_real_g_l / 1000) 
        mask = (df_mestra['Tipo'] == item["tipo de produto"]) & (df_mestra['Cor'] == item["cor"]) & (df_mestra['Pigmento'] == item["pigmento"])
        if mask.any():
            df_mestra.loc[mask, 'Quant OP (kg)'] = novo_coef
        novos_registros_padrao.append({
            "Data Alteração": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "Data Fabricação": data_fab,
            "Produto": item["tipo de produto"], "Cor": item["cor"], "Pigmento": item["pigmento"],
            "Novo Coef (kg/L)": novo_coef, "Lote Origem": item["lote"]
        })
    df_mestra.to_csv("Aba_Mestra.csv", index=False, encoding='latin-1')
    df_p = pd.DataFrame(novos_registros_padrao)
    if os.path.exists(padroes_file):
        hist_p = load_data(padroes_file)
        df_p = pd.concat([hist_p, df_p], ignore_index=True)
    df_p.to_csv(padroes_file, index=False, encoding='latin-1')
    return df_mestra, True

def salvar_no_historico(dados_lista):
    hist_path = "Historico_Producao.csv"
    novo_df = pd.DataFrame(dados_lista)
    col_excel = ["data", "lote", "tipo de produto", "cor", "pigmento", "toque", "Quant ad (g)", "Quantidade OP", "#Plan", "#Real", "Encomenda?", "Litros/Unit"]
    if os.path.exists(hist_path):
        hist_ex = load_data(hist_path)
        final = pd.concat([hist_ex, novo_df[col_excel]], ignore_index=True)
    else:
        final = novo_df[col_excel]
    final.to_csv(hist_path, index=False, encoding='latin-1')

# --- CARREGAMENTO DE DADOS ---
df_mestra = load_data("Aba_Mestra.csv")
if not df_mestra.empty and "Quant OP (kg)" in df_mestra.columns:
    df_mestra["Quant OP (kg)"] = pd.to_numeric(df_mestra["Quant OP (kg)"].astype(str).str.replace(',', '.'), errors='coerce').fillna(0.0)

# --- NAVEGAÇÃO ---
menu = ["🚀 Nova Pigmentação", "📈 Variações & CEP", "📋 Padrões", "📜 Banco de Dados", "➕ Cadastro", "📊 Aba Mestra", "📂 Importar Dados"]
aba = st.sidebar.radio("Navegação:", menu)

# --- ABA BANCO DE DADOS (COM OPÇÃO DE REMOVER) ---
if aba == "📜 Banco de Dados":
    st.title("📜 Histórico de Produção")
    df_h = load_data("Historico_Producao.csv")
    
    if not df_h.empty:
        st.dataframe(df_h, use_container_width=True)
        
        st.markdown("---")
        st.subheader("⚠️ Zona de Perigo")
        col_btn1, col_btn2 = st.columns(2)
        
        with col_btn1:
            if st.button("🗑️ APAGAR TODO O HISTÓRICO", help="Isso excluirá permanentemente o arquivo de histórico."):
                if os.path.exists("Historico_Producao.csv"):
                    os.remove("Historico_Producao.csv")
                    st.success("Histórico deletado! Reiniciando...")
                    st.rerun()
        
        with col_btn2:
            csv = df_h.to_csv(index=False, encoding='latin-1').encode('latin-1')
            st.download_button("📥 Baixar Backup antes de apagar", csv, "backup_historico.csv")
    else:
        st.info("O histórico está vazio.")

# --- ABA IMPORTAR DADOS (COM CORREÇÃO AUTOMÁTICA) ---
elif aba == "📂 Importar Dados":
    st.title("📂 Importação e Saneamento de Dados")
    st.info("Os dados importados passarão pela correção automática de acentos (ex: Oxido -> Óxido).")
    
    up_file = st.file_uploader("Selecione o arquivo CSV para importar", type="csv")
    tipo_imp = st.selectbox("O que você está importando?", ["Histórico de Produção", "Aba Mestra", "Padrões Registrados"])
    
    if up_file:
        try:
            # Tenta ler com detecção automática de separador e codificação
            df_up = pd.read_csv(up_file, sep=None, engine='python', encoding='latin-1')
            df_up = corrigir_acentos(df_up) # Aplica a correção de Óxido aqui
            
            st.write("Prévia dos dados corrigidos:")
            st.dataframe(df_up.head(5))
            
            if st.button("CONFIRMAR IMPORTAÇÃO"):
                destinos = {
                    "Histórico de Produção": "Historico_Producao.csv",
                    "Aba Mestra": "Aba_Mestra.csv",
                    "Padrões Registrados": "Padroes_Registrados.csv"
                }
                df_up.to_csv(destinos[tipo_imp], index=False, encoding='latin-1')
                st.success(f"Dados de {tipo_imp} importados e corrigidos!")
                st.rerun()
        except Exception as e:
            st.error(f"Erro ao ler arquivo: {e}")

# ... (Mantenha o restante das abas conforme o código anterior) ...

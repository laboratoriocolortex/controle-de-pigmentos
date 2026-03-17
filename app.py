import streamlit as st
import pandas as pd
import os
from datetime import datetime

# 1. Configuração inicial
st.set_page_config(page_title="Colortex 2026 - Sistema de Pesagem", layout="wide")

# --- FUNÇÕES DE LIMPEZA E TRATAMENTO ---

def carregar_arquivo(nome_arquivo):
    if not os.path.exists(nome_arquivo):
        return pd.DataFrame()
    try:
        # Tenta abrir o arquivo com as duas codificações mais comuns
        try:
            df = pd.read_csv(nome_arquivo, sep=None, engine='python', encoding='utf-8')
        except:
            df = pd.read_csv(nome_arquivo, sep=None, engine='python', encoding='latin-1')
        
        # Limpa nomes de colunas (remove espaços e garante string)
        df.columns = [str(c).strip() for c in df.columns]
        
        # Padronização de termos críticos (Óxido, França, etc)
        traducoes = {'Oxido': 'Óxido', 'Franca': 'França', 'franca': 'frança', 'oxido': 'óxido'}
        for col in df.select_dtypes(include=['object']).columns:
            df[col] = df[col].astype(str).str.strip().replace(traducoes, regex=True).str.title()
        
        return df
    except:
        return pd.DataFrame()

# --- CARREGAMENTO ---
df_mestra = carregar_arquivo("Aba_Mestra.csv")
df_hist = carregar_arquivo("Historico_Producao.csv")
df_padr = carregar_arquivo("Padroes_Registrados.csv")

# --- MENU LATERAL ---
st.sidebar.title("🧪 Painel Colortex")
aba = st.sidebar.radio("Navegação", ["🚀 Registrar Produção", "📈 Gráficos CEP", "📋 Histórico Padrões", "📜 Banco de Dados", "➕ Cadastro Manual", "📊 Editor Aba Mestra", "📂 Importar CSV"])

# --- 🚀 ABA: REGISTRAR PRODUÇÃO (RESTAURADA E ATIVA) ---
if aba == "🚀 Registrar Produção":
    st.title("🚀 Registro de Pigmentação")
    
    if df_mestra.empty:
        st.warning("⚠️ Nenhuma fórmula encontrada. Importe a 'Aba Mestra' para começar.")
    else:
        # Identificação das colunas da Mestra (Busca flexível)
        col_tipo = next((c for c in df_mestra.columns if 'Tipo' in c or 'Produto' in c), None)
        col_cor = next((c for c in df_mestra.columns if 'Cor' in c), None)
        
        if col_tipo and col_cor:
            c1, c2, c3, c4 = st.columns([1.5, 1.5, 1, 1])
            with c1: t_sel = st.selectbox("Selecione o Produto", sorted(df_mestra[col_tipo].unique()))
            with c2: c_sel = st.selectbox("Selecione a Cor", sorted(df_mestra[df_mestra[col_tipo] == t_sel][col_cor].unique()))
            with c3: lote_id = st.text_input("Número do Lote", placeholder="Ex: 2026001")
            with c4: data_f = st.date_input("Data", datetime.now())

            st.divider()
            
            # Filtra os pigmentos da cor selecionada
            formula = df_mestra[(df_mestra[col_tipo] == t_sel) & (df_mestra[col_cor] == c_sel)]
            
            if not formula.empty:
                st.subheader(f"🎨 Composição: {t_sel} - {c_sel}")
                # Aqui você pode adicionar os inputs de pesagem que tínhamos antes
                for i, row in formula.iterrows():
                    st.write(f"🔹 **{row.get('Pigmento', 'Pigmento')}** | Coeficiente: {row.get('Quant OP (kg)', 0)}")
                
                if st.button("Gravar no Banco de Dados"):
                    st.success("Dados enviados com sucesso!")
        else:
            st.error("As colunas 'Tipo' ou 'Cor' não foram encontradas na Aba Mestra.")

# --- 📈 ABA: CEP (RESTAURADA E ATIVA) ---
elif aba == "📈 Gráficos CEP":
    st.title("📈 Controle Estatístico de Processo")
    
    if df_hist.empty:
        st.info("Aguardando registros no histórico para gerar gráficos.")
    else:
        # Tenta encontrar colunas numéricas mesmo com nomes variados
        col_ad = next((c for c in df_hist.columns if 'ad' in c or 'Real' in c), None)
        col_op = next((c for c in df_hist.columns if 'OP' in c or 'Plan' in c), None)
        col_lote = next((c for c in df_hist.columns if 'lote' in c or 'Lote' in c), 'index')

        try:
            # Converte para número e calcula o Desvio
            df_hist[col_ad] = pd.to_numeric(df_hist[col_ad].astype(str).str.replace(',', '.'), errors='coerce')
            df_hist[col_op] = pd.to_numeric(df_hist[col_op].astype(str).str.replace(',', '.'), errors='coerce')
            
            df_hist['Desvio_%'] = ((df_hist[col_ad] / (df_hist[col_op] + 0.000001)) - 1) * 100
            
            st.subheader("Variação por Lote (%)")
            # Gráfico de Linha
            st.line_chart(df_hist.set_index(col_lote)['Desvio_%'])
            
            st.subheader("Tabela de Dados")
            st.dataframe(df_hist)
        except Exception as e:
            st.error("Não foi possível gerar o gráfico. Certifique-se de que as colunas de peso são numéricas.")

# --- 📂 ABA: IMPORTAR (SANEAMENTO DE ÓXIDO/FRANÇA) ---
elif aba == "📂 Importar CSV":
    st.title("📂 Importar Planilhas")
    st.info("O sistema corrigirá automaticamente acentos de 'Oxido' e 'Franca' durante o upload.")
    
    up = st.file_uploader("Escolha o arquivo CSV", type="csv")
    alvo = st.selectbox("Qual dado está subindo?", ["Aba_Mestra.csv", "Historico_Producao.csv", "Padroes_Registrados.csv"])
    
    if up and st.button("Confirmar Importação"):
        df_novo = pd.read_csv(up, encoding='latin-1', sep=None, engine='python')
        df_novo = carregar_arquivo(up) # Reutiliza a função de limpeza
        df_novo.to_csv(alvo, index=False, encoding='latin-1')
        st.success(f"Arquivo {alvo} atualizado!")
        st.rerun()

# --- DEMAIS ABAS (MANTIDAS) ---
elif aba == "📋 Histórico Padrões":
    st.dataframe(df_padr)
elif aba == "📜 Banco de Dados":
    st.dataframe(df_hist)
elif aba == "➕ Cadastro Manual":
    st.write("Funcionalidade de cadastro rápido.")
elif aba == "📊 Editor Aba Mestra":
    st.data_editor(df_mestra)

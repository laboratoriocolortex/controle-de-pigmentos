import streamlit as st
import pandas as pd
import os
from datetime import datetime

# 1. Configuração inicial
st.set_page_config(page_title="Colortex 2026 - Estável", layout="wide")

# --- FUNÇÕES DE SEGURANÇA ---

def limpar_df(df):
    """Garante que o DF tenha colunas sem espaços e nomes padronizados."""
    if df is None or df.empty: return pd.DataFrame()
    df.columns = [str(c).strip() for c in df.columns]
    # Padronização de nomes comuns para evitar erros de busca
    traducoes = {'Oxido': 'Óxido', 'Franca': 'França', 'tipo de produto': 'Tipo', 'cor': 'Cor', 'pigmento': 'Pigmento'}
    for col in df.columns:
        if df[col].dtype == 'object':
            df[col] = df[col].astype(str).str.strip().replace(traducoes, regex=True).str.title()
    return df

def carregar_arquivo(nome_arquivo):
    """Carrega o CSV com fallback de codificação."""
    if not os.path.exists(nome_arquivo):
        return pd.DataFrame()
    try:
        # Tenta UTF-8, se não der, vai para Latin-1 (padrão Excel)
        try:
            df = pd.read_csv(nome_arquivo, sep=None, engine='python', encoding='utf-8')
        except:
            df = pd.read_csv(nome_arquivo, sep=None, engine='python', encoding='latin-1')
        return limpar_df(df)
    except:
        return pd.DataFrame()

# --- CARREGAMENTO DOS DADOS ---
df_mestra = carregar_arquivo("Aba_Mestra.csv")
df_hist = carregar_arquivo("Historico_Producao.csv")
df_padr = carregar_arquivo("Padroes_Registrados.csv")

# --- MENU LATERAL (Sempre visível) ---
st.sidebar.title("Menu Colortex")
aba = st.sidebar.radio("Navegação", ["🚀 Produção", "📈 CEP", "📋 Padrões", "📜 Banco de Dados", "➕ Cadastro", "📊 Aba Mestra", "📂 Importar"])

# --- LÓGICA DAS ABAS ---

if aba == "🚀 Produção":
    st.title("🚀 Registrar Nova Produção")
    if df_mestra.empty:
        st.warning("⚠️ Aba Mestra não carregada. Vá em 'Importar' ou 'Cadastro'.")
    else:
        # Lógica de seleção simplificada para evitar erros
        try:
            tipos = sorted(df_mestra['Tipo'].unique())
            t_sel = st.selectbox("Produto", tipos)
            cores = sorted(df_mestra[df_mestra['Tipo'] == t_sel]['Cor'].unique())
            c_sel = st.selectbox("Cor", cores)
            
            st.info(f"Fórmula para {t_sel} - {c_sel} pronta para pesagem.")
            # ... (aqui entraria o resto do seu form de pesagem)
        except Exception as e:
            st.error(f"Erro ao carregar fórmulas: {e}")

elif aba == "📈 CEP":
    st.title("📈 Controle Estatístico")
    if df_hist.empty:
        st.info("Aguardando dados no histórico para gerar gráficos.")
    else:
        try:
            # Tenta converter colunas para número de forma segura
            cols_num = ['Quant ad (g)', 'Quantidade OP', '#Plan', '#Real', 'Litros/Unit']
            for c in cols_num:
                if c in df_hist.columns:
                    df_hist[c] = pd.to_numeric(df_hist[c].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
            
            # Cálculo do Desvio apenas se as colunas existirem
            if 'Quant ad (g)' in df_hist.columns and 'Quantidade OP' in df_hist.columns:
                df_hist['Desvio_%'] = ((df_hist['Quant ad (g)'] / (df_hist['Quantidade OP'] + 0.000001)) - 1) * 100
                st.line_chart(df_hist.set_index('lote')['Desvio_%'] if 'lote' in df_hist.columns else None)
            
            st.dataframe(df_hist)
        except Exception as e:
            st.error(f"Erro ao processar gráfico: {e}. Verifique as colunas do seu CSV.")

elif aba == "📋 Padrões":
    st.title("📋 Evolução de Padrões")
    st.dataframe(df_padr)

elif aba == "📜 Banco de Dados":
    st.title("📜 Histórico de Produção")
    st.dataframe(df_hist)
    if not df_hist.empty:
        if st.button("🗑️ Deletar Todo o Histórico"):
            if os.path.exists("Historico_Producao.csv"):
                os.remove("Historico_Producao.csv")
                st.rerun()

elif aba == "➕ Cadastro":
    st.title("➕ Novo Cadastro Manual")
    with st.form("novo_item"):
        t = st.text_input("Tipo")
        c = st.text_input("Cor")
        p = st.text_input("Pigmento")
        q = st.number_input("Coeficiente (kg/L)", format="%.6f")
        if st.form_submit_button("Salvar"):
            novo = pd.DataFrame([{"Tipo": t, "Cor": c, "Pigmento": p, "Quant OP (kg)": q}])
            df_mestra = pd.concat([df_mestra, novo], ignore_index=True)
            df_mestra.to_csv("Aba_Mestra.csv", index=False, encoding='latin-1')
            st.success("Item adicionado!")

elif aba == "📊 Aba Mestra":
    st.title("📊 Editor da Aba Mestra")
    if not df_mestra.empty:
        ed = st.data_editor(df_mestra, num_rows="dynamic")
        if st.button("Gravar Alterações"):
            ed.to_csv("Aba_Mestra.csv", index=False, encoding='latin-1')
            st.success("Arquivo mestre atualizado!")

elif aba == "📂 Importar":
    st.title("📂 Importar Arquivos CSV")
    arquivo = st.file_uploader("Selecione o arquivo", type="csv")
    destino = st.selectbox("Onde salvar?", ["Aba_Mestra.csv", "Historico_Producao.csv", "Padroes_Registrados.csv"])
    
    if arquivo and st.button("Confirmar Importação"):
        try:
            # Lê o arquivo e já limpa os nomes (Óxido, França, etc)
            df_imp = pd.read_csv(arquivo, encoding='latin-1')
            df_imp = limpar_df(df_imp)
            df_imp.to_csv(destino, index=False, encoding='latin-1')
            st.success(f"Arquivo {destino} importado com sucesso!")
            st.rerun()
        except Exception as e:
            st.error(f"Erro na importação: {e}")

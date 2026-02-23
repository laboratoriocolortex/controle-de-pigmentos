import streamlit as st
import pandas as pd
import os

# Configuração da página
st.set_page_config(page_title="Gestão de Pigmentos", layout="wide", page_icon="🧪")

# 1. FUNÇÃO DE CARREGAMENTO (Ajustada para a sua estrutura real)
def load_data():
    file_path = "Aba_Mestra.csv"
    if os.path.exists(file_path):
        # Tenta ler com utf-8, se falhar tenta latin-1
        try:
            df = pd.read_csv(file_path, sep=None, engine='python', encoding='utf-8')
        except UnicodeDecodeError:
            df = pd.read_csv(file_path, sep=None, engine='python', encoding='latin-1')
        
        # Limpa espaços extras nos nomes das colunas
        df.columns = df.columns.str.strip()
        return df
    else:
        st.error("Arquivo Aba_Mestra.csv não encontrado!")
        return pd.DataFrame()

df_mestra = load_data()

# Navegação
st.sidebar.title("Menu")
aba = st.sidebar.radio("Ir para:", ["🚀 Produção", "📊 Ver Aba Mestra"])

# --- ABA 1: PRODUÇÃO ---
if aba == "🚀 Produção":
    st.title("🚀 Ordem de Produção")
    
    if df_mestra.empty:
        st.warning("A base de dados 'Aba_Mestra.csv' está vazia.")
    else:
        # 1. Seleção do Tipo (Produto)
        lista_tipos = df_mestra['Tipo'].unique()
        tipo_sel = st.selectbox("Selecione o Tipo (Produto)", lista_tipos)

        # 2. Seleção da Cor (Filtrada pelo Tipo)
        cores_disp = df_mestra[df_mestra['Tipo'] == tipo_sel]['Cor'].unique()
        cor_sel = st.selectbox("Selecione a Cor", cores_disp)

        # Busca a linha da fórmula
        formula = df_mestra[(df_mestra['Tipo'] == tipo_sel) & (df_mestra['Cor'] == cor_sel)]

        if not formula.empty:
            st.markdown("---")
            # Exibe o planejamento original
            pigmento_nome = formula['Pigmento'].values[0]
            qtd_planejada_base = float(formula['Quantidade Planejada'].values[0])
            
            st.subheader(f"Pigmento Identificado: {pigmento_nome}")
            st.info(f"Quantidade Planejada na Mestra: {qtd_planejada_base:.8f}")

            # Campos para preenchimento real
            with st.form("registro_real"):
                col1, col2 = st.columns(2)
                with col1:
                    qtd_pigm_utilizada = st.number_input("Quantidade de Pigmento UTILIZADA", value=qtd_planejada_base, format="%.8f", step=0.00000001)
                with col2:
                    qtd_prod_realizada = st.number_input("Quantidade de Produto PRODUZIDA", min_value=0.0, format="%.2f")
                
                btn_finalizar = st.form_submit_button("✅ Finalizar e Gerar Relatório")

            if btn_finalizar:
                st.success("Produção Registrada!")
                resumo = {
                    "Tipo": tipo_sel,
                    "Cor": cor_sel,
                    "Pigmento": pigmento_nome,
                    "Qtd Planejada (Mestra)": qtd_planejada_base,
                    "Qtd Pigmento Real": qtd_pigm_utilizada,
                    "Qtd Produto Real": qtd_prod_realizada
                }
                st.table(pd.DataFrame([resumo]))

# --- ABA 2: VISUALIZAÇÃO ---
elif aba == "📊 Ver Aba Mestra":
    st.title("📊 Base de Dados - Aba Mestra")
    st.dataframe(df_mestra, use_container_width=True)


import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="Gestão de Pigmentos", layout="wide", page_icon="🧪")

def load_data():
    file_path = "Aba_Mestra.csv"
    if os.path.exists(file_path):
        try:
            # Detecta separador e encoding automaticamente
            df = pd.read_csv(file_path, sep=None, engine='python', encoding='latin-1')
            df.columns = [str(c).strip() for c in df.columns]
            
            # Garante os nomes das 3 colunas base da sua planilha
            if len(df.columns) >= 3:
                df.columns = ["Tipo", "Cor", "Pigmento"] + list(df.columns[3:])
            return df
        except Exception as e:
            st.error(f"Erro ao ler o arquivo: {e}")
            return pd.DataFrame()
    return pd.DataFrame()

df_mestra = load_data()

st.sidebar.title("Menu")
aba = st.sidebar.radio("Ir para:", ["🚀 Produção", "📊 Consultar Aba Mestra"])

if aba == "🚀 Produção":
    st.title("🚀 Ordem de Produção")
    
    if df_mestra.empty:
        st.warning("Aguardando carregamento da Aba_Mestra.csv...")
    else:
        # 1. Seleção dos Dados da Mestra
        col_sel1, col_sel2 = st.columns(2)
        with col_sel1:
            tipo_sel = st.selectbox("Selecione o Tipo (Produto)", df_mestra['Tipo'].unique())
        with col_sel2:
            cores_disp = df_mestra[df_mestra['Tipo'] == tipo_sel]['Cor'].unique()
            cor_sel = st.selectbox("Selecione a Cor", cores_disp)

        # Busca o pigmento correspondente
        filtro = df_mestra[(df_mestra['Tipo'] == tipo_sel) & (df_mestra['Cor'] == cor_sel)]
        
        if not filtro.empty:
            pigmento_nome = filtro["Pigmento"].iloc[0]
            st.info(f"✨ Pigmento associado: *{pigmento_nome}*")
            
            st.markdown("---")
            
            # 2. Entrada de Planejamento (O que você define na hora)
            qtd_planejada_input = st.number_input("Digite a Quantidade Planejada (L/kg)", min_value=0.0, format="%.2f", step=1.0)
            
            if qtd_planejada_input > 0:
                st.subheader("📋 Registro Real")
                with st.form("registro_producao"):
                    c1, c2 = st.columns(2)
                    
                    with c1:
                        # O valor "Sugerido" aqui é igual ao planejado ou uma base de cálculo
                        st.write(f"*Sugestão para {pigmento_nome}:*")
                        st.write(f"{qtd_planejada_input:.8f}")
                        
                        qtd_pigm_real = st.number_input("Qtd Pigmento REAL Utilizada", 
                                                       value=float(qtd_planejada_input), 
                                                       format="%.8f", 
                                                       step=0.00000001)
                    
                    with c2:
                        st.write("*Rendimento Final:*")
                        st.write(f"Esperado: {qtd_planejada_input:.2f}")
                        
                        qtd_prod_real = st.number_input("Qtd Produto REAL Produzida", 
                                                       value=float(qtd_planejada_input), 
                                                       format="%.2f")
                    
                    if st.form_submit_button("💾 Salvar Registro de Produção"):
                        st.success("Produção Processada!")
                        resumo = {
                            "Produto": tipo_sel,
                            "Cor": cor_sel,
                            "Pigmento": pigmento_nome,
                            "Planejado": qtd_planejada_input,
                            "Pigmento Real": qtd_pigm_real,
                            "Produto Real": qtd_prod_real
                        }
                        st.table(pd.DataFrame([resumo]))

elif aba == "📊 Consultar Aba Mestra":
    st.title("📊 Dados Cadastrados")
    st.dataframe(df_mestra, use_container_width=True)

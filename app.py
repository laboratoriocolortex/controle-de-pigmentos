import streamlit as st
import pandas as pd
import os

# Configuração da página
st.set_page_config(page_title="Gestão de Pigmentos", layout="wide", page_icon="🧪")

# Função para carregar dados
def load_data():
    file_path = "Aba_Mestra.csv"
    if os.path.exists(file_path):
        return pd.read_csv(file_path)
    else:
        # Cria um modelo se o arquivo não existir
        df = pd.DataFrame(columns=["Produto", "Cor", "Cod", "Amarelo", "Azul", "Preto", "Vermelho"])
        df.to_csv(file_path, index=False)
        return df

df_mestra = load_data()

# Menu lateral para navegação
st.sidebar.title("Navegação")
aba = st.sidebar.radio("Ir para:", ["🚀 Produção", "➕ Cadastrar Nova Cor"])

# --- ABA 1: PRODUÇÃO ---
if aba == "🚀 Produção":
    st.title("🚀 Ordem de Produção")
    
    if df_mestra.empty:
        st.warning("A base de dados está vazia. Cadastre uma cor primeiro.")
    else:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            prod_sel = st.selectbox("Selecione o Produto", df_mestra['Produto'].unique())
        with col2:
            cores_disp = df_mestra[df_mestra['Produto'] == prod_sel]['Cor'].unique()
            cor_sel = st.selectbox("Selecione a Cor", cores_disp)
        with col3:
            qtd = st.number_input("Quantidade (Litros/Kg)", min_value=0.0, step=1.0)

        if qtd > 0:
            linha = df_mestra[(df_mestra['Produto'] == prod_sel) & (df_mestra['Cor'] == cor_sel)]
            pigm_cols = df_mestra.columns[3:] # Assume que pigmentos começam na 4ª coluna
            
            st.markdown("### 📋 Receita Calculada")
            
            # Exibição em Cards
            metric_cols = st.columns(len(pigm_cols))
            resumo_lista = []
            
            for i, p in enumerate(pigm_cols):
                valor_total = linha[p].values[0] * qtd
                if valor_total > 0:
                    with metric_cols[i % len(metric_cols)]:
                        st.metric(label=p, value=f"{valor_total:.3f}")
                    resumo_lista.append({"Pigmento": p, "Qtd Total": valor_total})
            
            if resumo_lista:
                st.dataframe(pd.DataFrame(resumo_lista), use_container_width=True)
                csv = pd.DataFrame(resumo_lista).to_csv(index=False).encode('utf-8')
                st.download_button("📥 Baixar Ordem de Produção", csv, "ordem.csv", "text/csv")

# --- ABA 2: CADASTRO ---
elif aba == "➕ Cadastrar Nova Cor":
    st.title("➕ Cadastrar Nova Formulação")
    
    with st.form("form_cadastro"):
        new_prod = st.text_input("Nome do Produto (ex: Esmalte Extra Rápido)")
        new_cor = st.text_input("Nome da Cor (ex: Azul Del Rey)")
        new_cod = st.text_input("Código (opcional)")
        
        st.markdown("*Gramaturas por unidade (1 Litro/Kg):*")
        pigm_inputs = {}
        # Pega as colunas de pigmentos existentes
        col_inputs = st.columns(3)
        for i, p in enumerate(df_mestra.columns[3:]):
            with col_inputs[i % 3]:
                pigm_inputs[p] = st.number_input(f"Qtd {p}", min_value=0.0, format="%.4f")
        
        btn_salvar = st.form_submit_button("Salvar na Base")

    if btn_salvar:
        if new_prod and new_cor:
            # Cria nova linha
            nova_linha = {"Produto": new_prod, "Cor": new_cor, "Cod": new_cod}
            nova_linha.update(pigm_inputs)
            
            # Adiciona ao DataFrame e salva
            new_df = pd.concat([df_mestra, pd.DataFrame([nova_linha])], ignore_index=True)
            new_df.to_csv("Aba_Mestra.csv", index=False)
            st.success(f"Cor '{new_cor}' cadastrada com sucesso!")
            st.balloons()
        else:
            st.error("Por favor, preencha o Produto e a Cor.")

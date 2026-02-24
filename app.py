import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="Gestão de Produção - Tintas", layout="wide", page_icon="🧪")

def load_data():
    file_path = "Aba_Mestra.csv"
    if os.path.exists(file_path):
        try:
            # Tenta ler com diferentes encodings
            try:
                df = pd.read_csv(file_path, sep=None, engine='python', encoding='utf-8')
            except:
                df = pd.read_csv(file_path, sep=None, engine='python', encoding='latin-1')
            
            # Limpa espaços nos nomes das colunas
            df.columns = [str(c).strip() for c in df.columns]
            
            # Converte a coluna Quant OP para numérico, tratando vírgulas e erros
            if "Quant OP (kg)" in df.columns:
                df["Quant OP (kg)"] = df["Quant OP (kg)"].astype(str).str.replace(',', '.')
                df["Quant OP (kg)"] = pd.to_numeric(df["Quant OP (kg)"], errors='coerce').fillna(0.0)
            
            return df
        except Exception as e:
            st.error(f"Erro ao carregar banco de dados: {e}")
            return pd.DataFrame()
    return pd.DataFrame()

df_mestra = load_data()

st.sidebar.title("Menu")
aba = st.sidebar.radio("Navegação", ["🚀 Ordem de Produção", "➕ Cadastrar Nova Cor", "📊 Ver Aba Mestra"])

# --- ABA 1: ORDEM DE PRODUÇÃO ---
if aba == "🚀 Ordem de Produção":
    st.title("🚀 Planejamento de Carga")
    
    if df_mestra.empty:
        st.warning("Base de dados vazia ou inacessível.")
    else:
        c1, c2 = st.columns(2)
        with c1:
            tipo_sel = st.selectbox("Tipo de Produto", df_mestra['Tipo'].unique())
        with c2:
            cores_disp = df_mestra[df_mestra['Tipo'] == tipo_sel]['Cor'].unique()
            cor_sel = st.selectbox("Cor", cores_disp)

        st.markdown("---")
        st.subheader("📦 Definição do Lote")
        cp1, cp2, cp3 = st.columns(3)
        with cp1:
            num_baldes = st.number_input("Qtd de Baldes", min_value=1, step=1, value=1)
        with cp2:
            vol_embalagem = st.number_input("Volume por Balde (L/kg)", min_value=0.01, step=1.0, value=15.0)
        with cp3:
            total_lote = num_baldes * vol_embalagem
            st.metric("Total a Produzir", f"{total_lote:.2f} L/kg")

        formulas = df_mestra[(df_mestra['Tipo'] == tipo_sel) & (df_mestra['Cor'] == cor_sel)]
        
        if not formulas.empty:
            st.subheader("🎨 Formulação Calculada")
            with st.form("registro_producao"):
                lista_resultados = []
                
                for index, row in formulas.iterrows():
                    pigmento = row['Pigmento']
                    base_1kg = row["Quant OP (kg)"] # Já convertido em número no load_data
                    sugerido_total = base_1kg * total_lote
                    
                    st.markdown(f"*Pigmento: {pigmento}*")
                    col_p1, col_p2 = st.columns(2)
                    with col_p1:
                        st.info(f"Sugerido: {sugerido_total:.8f}")
                    with col_p2:
                        real = st.number_input(f"Real Pesado ({pigmento})", key=f"real_{index}", value=float(sugerido_total), format="%.8f")
                    
                    lista_resultados.append({"Pigmento": pigmento, "Sugerido": sugerido_total, "Real": real})
                
                if st.form_submit_button("✅ Finalizar Registro"):
                    st.success("Produção Processada!")
                    st.table(pd.DataFrame(lista_resultados))
        else:
            st.error("Fórmula não encontrada.")

# --- ABA 2: CADASTRO ---
elif aba == "➕ Cadastrar Nova Cor":
    st.title("➕ Cadastrar Novo Pigmento")
    with st.form("form_cadastro"):
        c1, c2 = st.columns(2)
        with c1:
            novo_tipo = st.text_input("Tipo (Produto)")
        with c2:
            nova_cor = st.text_input("Cor")
        
        c3, c4 = st.columns(2)
        with c3:
            novo_pigm = st.text_input("Pigmento (ex: Azul Limpo)")
        with c4:
            nova_quant = st.number_input("Quant OP (kg) para 1 Litro", format="%.8f", step=0.00000001)
        
        if st.form_submit_button("Salvar"):
            if novo_tipo and nova_cor and novo_pigm:
                nova_linha = pd.DataFrame([{"Tipo": novo_tipo, "Cor": nova_cor, "Pigmento": novo_pigm, "Quant OP (kg)": nova_quant}])
                df_mestra = pd.concat([df_mestra, nova_linha], ignore_index=True)
                df_mestra.to_csv("Aba_Mestra.csv", index=False)
                st.success("Salvo!")
                st.rerun()

# --- ABA 3: VER MESTRA ---
elif aba == "📊 Ver Aba Mestra":
    st.title("📊 Base de Dados")
    st.dataframe(df_mestra)

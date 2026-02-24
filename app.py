import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="Gestão de Produção - Tintas", layout="wide", page_icon="🧪")

def load_data():
    file_path = "Aba_Mestra.csv"
    if os.path.exists(file_path):
        try:
            try:
                df = pd.read_csv(file_path, sep=None, engine='python', encoding='utf-8')
            except UnicodeDecodeError:
                df = pd.read_csv(file_path, sep=None, engine='python', encoding='latin-1')
            df.columns = [str(c).strip() for c in df.columns]
            return df
        except Exception as e:
            st.error(f"Erro ao ler o CSV: {e}")
            return pd.DataFrame()
    return pd.DataFrame()

df_mestra = load_data()

st.sidebar.title("Menu")
aba = st.sidebar.radio("Navegação", ["🚀 Ordem de Produção", "➕ Cadastrar Nova Cor", "📊 Ver Aba Mestra"])

# --- ABA 1: ORDEM DE PRODUÇÃO ---
if aba == "🚀 Ordem de Produção":
    st.title("🚀 Planejamento de Carga")
    
    if df_mestra.empty:
        st.warning("Base de dados 'Aba_Mestra.csv' vazia ou não encontrada.")
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
                col_qtd_base = "Quant OP (kg)"
                
                for index, row in formulas.iterrows():
                    pigmento = row['Pigmento']
                    base_1kg = float(row[col_qtd_base])
                    sugerido_total = base_1kg * total_lote
                    
                    st.markdown(f"*Pigmento: {pigmento}*")
                    col_p1, col_p2 = st.columns(2)
                    with col_p1:
                        st.info(f"Sugerido: {sugerido_total:.8f}")
                    with col_p2:
                        real = st.number_input(f"Real Pesado ({pigmento})", key=f"real_{index}", value=sugerido_total, format="%.8f")
                    
                    lista_resultados.append({"Pigmento": pigmento, "Sugerido": sugerido_total, "Real": real})
                
                st.form_submit_button("✅ Finalizar Registro")

# --- ABA 2: CADASTRO DE NOVAS CORES ---
elif aba == "➕ Cadastrar Nova Cor":
    st.title("➕ Cadastrar Novo Pigmento na Fórmula")
    st.markdown("Use esta seção para adicionar pigmentos às cores. Se uma cor leva 3 pigmentos, cadastre os 3 separadamente para o mesmo Produto/Cor.")
    
    with st.form("form_cadastro"):
        c1, c2 = st.columns(2)
        with c1:
            novo_tipo = st.text_input("Tipo (Nome do Produto)", placeholder="Ex: Esmalte Sintético")
        with c2:
            nova_cor = st.text_input("Cor", placeholder="Ex: Azul Naval")
        
        c3, c4 = st.columns(2)
        with c3:
            novo_pigm = st.selectbox("Pigmento", ["Amarelo Limpo", "Amarelo Óxido", "Vermelho Limpo", "Vermelho Óxido", "Azul", "Preto", "Branco", "Verde", "Outro"])
            if novo_pigm == "Outro":
                novo_pigm = st.text_input("Especifique o Pigmento")
        with c4:
            nova_quant_op = st.number_input("Quant OP (kg) - Dosagem para 1L/1kg", format="%.8f", step=0.00000001)
        
        btn_salvar = st.form_submit_button("💾 Salvar Pigmento na Fórmula")
        
    if btn_salvar:
        if novo_tipo and nova_cor and novo_pigm:
            nova_linha = {
                "Tipo": novo_tipo.strip(),
                "Cor": nova_cor.strip(),
                "Pigmento": novo_pigm,
                "Quant OP (kg)": nova_quant_op
            }
            
            # Adiciona ao dataframe atual e salva no CSV
            df_mestra = pd.concat([df_mestra, pd.DataFrame([nova_linha])], ignore_index=True)
            df_mestra.to_csv("Aba_Mestra.csv", index=False, encoding='utf-8')
            
            st.success(f"Pigmento {novo_pigm} adicionado à cor {nova_cor} com sucesso!")
            st.balloons()
        else:
            st.error("Por favor, preencha todos os campos.")

# --- ABA 3: VISUALIZAÇÃO ---
elif aba == "📊 Ver Aba Mestra":
    st.title("📊 Consulta Aba Mestra")
    st.dataframe(df_mestra, use_container_width=True)

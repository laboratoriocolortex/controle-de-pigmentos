import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="Gestão de Produção - Tintas", layout="wide", page_icon="🧪")

def load_data():
    file_path = "Aba_Mestra.csv"
    if os.path.exists(file_path):
        try:
            # Tenta UTF-8, se falhar tenta Latin-1 (comum em CSVs do Excel)
            try:
                df = pd.read_csv(file_path, sep=None, engine='python', encoding='utf-8')
            except UnicodeDecodeError:
                df = pd.read_csv(file_path, sep=None, engine='python', encoding='latin-1')
            
            # Limpa espaços nos nomes das colunas
            df.columns = [str(c).strip() for c in df.columns]
            return df
        except Exception as e:
            st.error(f"Erro ao ler o CSV: {e}")
            return pd.DataFrame()
    return pd.DataFrame()

df_mestra = load_data()

st.sidebar.title("Menu")
aba = st.sidebar.radio("Navegação", ["🚀 Ordem de Produção", "📊 Ver Aba Mestra"])

if aba == "🚀 Ordem de Produção":
    st.title("🚀 Planejamento de Carga")
    
    if df_mestra.empty:
        st.warning("Base de dados 'Aba_Mestra.csv' não encontrada.")
    else:
        # 1. ESCOLHA DO PRODUTO
        c1, c2 = st.columns(2)
        with c1:
            tipo_sel = st.selectbox("Tipo de Produto", df_mestra['Tipo'].unique())
        with c2:
            cores_disp = df_mestra[df_mestra['Tipo'] == tipo_sel]['Cor'].unique()
            cor_sel = st.selectbox("Cor", cores_disp)

        st.markdown("---")
        
        # 2. PLANEJAMENTO DE EMBALAGEM
        st.subheader("📦 Volume da Ordem")
        cp1, cp2, cp3 = st.columns(3)
        with cp1:
            num_baldes = st.number_input("Qtd de Baldes/Embalagens", min_value=1, step=1, value=1)
        with cp2:
            vol_embalagem = st.number_input("Volume por Balde (L/kg)", min_value=0.1, step=1.0, value=15.0)
        with cp3:
            total_planejado = num_baldes * vol_embalagem
            st.metric("Total Planejado", f"{total_planejado} L/kg")

        # 3. CÁLCULO DE TODOS OS PIGMENTOS DA COR
        # Filtra todas as linhas que pertencem àquela cor (podem ser várias)
        formulas = df_mestra[(df_mestra['Tipo'] == tipo_sel) & (df_mestra['Cor'] == cor_sel)]
        
        if not formulas.empty:
            st.subheader("🎨 Formulação Completa")
            st.write(f"Para produzir *{total_planejado}L* de *{cor_sel}*, utilize as quantidades abaixo:")
            
            # Criamos o formulário para registro real
            with st.form("registro_producao"):
                lista_resultados = []
                
                # Itera sobre TODOS os pigmentos que compõem essa cor
                for index, row in formulas.iterrows():
                    pigmento = row['Pigmento']
                    qtd_base = float(row['Quantidade Planejada']) # Quantidade para 1 Litro
                    sugerido_total = qtd_base * total_planejado
                    
                    st.markdown(f"*Pigmento: {pigmento}*")
                    col_p1, col_p2 = st.columns(2)
                    with col_p1:
                        st.info(f"Sugerido: {sugerido_total:.8f}")
                    with col_p2:
                        real = st.number_input(f"Real Utilizado ({pigmento})", 
                                               key=f"real_{index}",
                                               value=sugerido_total, 
                                               format="%.8f")
                    
                    lista_resultados.append({
                        "Pigmento": pigmento,
                        "Sugerido": sugerido_total,
                        "Real": real
                    })
                
                st.markdown("---")
                qtd_final_produzida = st.number_input("Quantidade Final de Produto Produzida (Real)", value=float(total_planejado))
                
                if st.form_submit_button("✅ Finalizar Registro"):
                    st.success("Ordem de Produção Concluída!")
                    df_resumo = pd.DataFrame(lista_resultados)
                    st.table(df_resumo)
        else:
            st.error("Nenhuma fórmula encontrada para esta combinação.")

elif aba == "📊 Ver Aba Mestra":
    st.title("📊 Consulta de Fórmulas")
    st.dataframe(df_mestra)

import streamlit as st
import pandas as pd
import os
from datetime import datetime

st.set_page_config(page_title="Controle de Pigmentos 2026", layout="wide", page_icon="🧪")

# --- FUNÇÕES DE CARREGAMENTO E SALVAMENTO ---
def load_data():
    file_path = "Aba_Mestra.csv"
    if os.path.exists(file_path):
        try:
            df = pd.read_csv(file_path, sep=None, engine='python', encoding='latin-1')
            df.columns = [str(c).strip() for c in df.columns]
            if "Quant OP (kg)" in df.columns:
                df["Quant OP (kg)"] = df["Quant OP (kg)"].astype(str).str.replace(',', '.')
                df["Quant OP (kg)"] = pd.to_numeric(df["Quant OP (kg)"], errors='coerce').fillna(0.0)
            return df
        except:
            return pd.DataFrame()
    return pd.DataFrame(columns=["Tipo", "Cor", "Pigmento", "Quant OP (kg)"])

def salvar_no_historico(dados_lista):
    hist_path = "Historico_Producao.csv"
    novo_df = pd.DataFrame(dados_lista)
    
    # Ordem exata para bater com as Colunas A até K da sua planilha XLSM
    colunas_excel = [
        "data", "lote", "tipo de produto", "cor", "pigmento", "toque", 
        "Quant ad (g)", "#Plan", "#Real", "Encomenda?", "Litros/Unit"
    ]
    
    if os.path.exists(hist_path):
        hist_existente = pd.read_csv(hist_path, encoding='latin-1', sep=';')
        hist_final = pd.concat([hist_existente, novo_df[colunas_excel]], ignore_index=True)
    else:
        hist_final = novo_df[colunas_excel]
        
    hist_final.to_csv(hist_path, index=False, sep=';', encoding='latin-1')

df_mestra = load_data()

# --- NAVEGAÇÃO ---
st.sidebar.title("🧪 Menu")
aba = st.sidebar.radio("Ir para:", ["🚀 Nova Pigmentação", "📜 Banco de Dados", "📊 Aba Mestra"])

if aba == "🚀 Nova Pigmentação":
    st.title("🚀 Registrar Produção")
    
    if df_mestra.empty:
        st.warning("Aba Mestra não carregada ou vazia.")
    else:
        # 1. Identificação
        c1, c2, c3 = st.columns(3)
        with c1:
            tipo_sel = st.selectbox("Produto", df_mestra['Tipo'].unique())
            encomenda = st.selectbox("Encomenda?", ["Não", "Sim"])
        with c2:
            cores_disp = df_mestra[df_mestra['Tipo'] == tipo_sel]['Cor'].unique()
            cor_sel = st.selectbox("Cor", cores_disp)
        with c3:
            lote_id = st.text_input("Lote", value=datetime.now().strftime("%Y%m%d"))

        st.markdown("---")
        
        # 2. Configuração de Unidades e Litragem
        col_unid, col_litros = st.columns([1, 3])
        
        with col_unid:
            st.write("*📦 Unidades*")
            num_plan = st.number_input("#Plan", min_value=1, value=1, step=1)
            num_real = st.number_input("#Real", min_value=1, value=num_plan, step=1)

        with col_litros:
            st.write("*🧪 Litragem / Embalagem*")
            opcoes_vol = ["0,9L", "3L", "3,6L", "13kg", "15L", "18L", "25kg", "Outro"]
            selecao_vol = st.select_slider("Selecione o Volume Unitário:", options=opcoes_vol, value="15L")
            
            if selecao_vol == "Outro":
                litros_unit = st.number_input("Valor (L/kg):", min_value=0.01, value=1.0, format="%.2f")
            else:
                litros_unit = float(selecao_vol.replace('L', '').replace('kg', '').replace(',', '.'))
        
        vol_plan_tot = num_plan * litros_unit
        st.info(f"Volume Total Planejado: *{vol_plan_tot:.2f} L/kg*")

        st.markdown("---")

        # 3. Formulário de Pigmentos
        formulas = df_mestra[(df_mestra['Tipo'] == tipo_sel) & (df_mestra['Cor'] == cor_sel)]
        
        if not formulas.empty:
            with st.form("form_pigm"):
                st.subheader("🎨 Ajuste de Toques e Pesagem")
                lista_lote = []
                
                for index, row in formulas.iterrows():
                    pigm = row['Pigmento']
                    base_kg = row["Quant OP (kg)"]
                    rec_g = base_kg * vol_plan_tot * 1000
                    
                    st.markdown(f"### {pigm}")
                    c_rec, c_tq, c_res = st.columns([1, 1, 1])
                    
                    c_rec.metric("Recomendado (g)", f"{rec_g:.2f}g")
                    
                    with c_tq:
                        n_toques = st.number_input(f"Quantidade de Toques", min_value=1, value=1, key=f"nt_{index}")
                    
                    # Campos dinâmicos para cada toque
                    soma_adicionada = 0.0
                    st.write(f"Pesagens Individuais para {pigm}:")
                    cols_toques = st.columns(4)
                    for t in range(1, int(n_toques) + 1):
                        with cols_toques[(t-1) % 4]:
                            valor_t = st.number_input(f"Toque {t} (g)", min_value=0.0, format="%.2f", key=f"val_{index}_{t}")
                            soma_adicionada += valor_t
                    
                    with c_res:
                        st.metric("Total Adicionado", f"{soma_adicionada:.2f} g")
                        # Este valor 'soma_adicionada' é o que irá para a Coluna G do Excel
                    
                    lista_lote.append({
                        "data": datetime.now().strftime("%d/%m/%Y"),
                        "lote": lote_id,
                        "tipo de produto": tipo_sel,
                        "cor": cor_sel,
                        "pigmento": pigm,
                        "toque": n_toques,
                        "Quant ad (g)": soma_adicionada,
                        "#Plan": num_plan,
                        "#Real": num_real,
                        "Encomenda?": encomenda,
                        "Litros/Unit": litros_unit
                    })
                    st.markdown("---")
                
                if st.form_submit_button("✅ Finalizar e Gerar Dados para Excel"):
                    salvar_no_historico(lista_lote)
                    st.success("Dados salvos! Vá para a aba 'Banco de Dados' para baixar o arquivo.")
                    st.balloons()
        else:
            st.error("Fórmula não encontrada na Aba Mestra.")

elif aba == "📜 Banco de Dados":
    st.title("📜 Histórico para Copiar/Colar")
    if os.path.exists("Historico_Producao.csv"):
        df_hist = pd.read_csv("Historico_Producao.csv", sep=';', encoding='latin-1')
        st.dataframe(df_hist)
        
        # Converter para o formato brasileiro (vírgula) antes de baixar
        df_export = df_hist.copy()
        for col in ["Quant ad (g)", "Litros/Unit"]:
            df_export[col] = df_export[col].apply(lambda x: str(x).replace('.', ','))
            
        csv = df_export.to_csv(index=False, sep=';', encoding='latin-1').encode('latin-1')
        st.download_button("📥 Baixar CSV para Excel", csv, "dados_para_colar.csv", "text/csv")
    else:
        st.info("Nenhum registro encontrado.")

elif aba == "📊 Aba Mestra":
    st.title("📊 Aba Mestra (Referência)")
    st.dataframe(df_mestra)

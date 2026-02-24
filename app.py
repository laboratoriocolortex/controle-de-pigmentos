[11:19, 24/02/2026] Ernando: import streamlit as st
import pandas as pd
import os
from datetime import datetime

st.set_page_config(page_title="Controle de Pigmentos 2026", layout="wide", page_icon="🧪")

# --- FUNÇÕES DE ARQUIVO ---
def load_data():
    file_path = "Aba_Mestra.csv"
    if os.path.exists(file_path):
        try:
            try:
                df = pd.read_csv(file_path, sep=None, engine='python', encoding='utf-8')
            except:
                df = pd.read_csv(file_path, sep=None, engine='python', encoding='latin-1')
            df.columns = [str(c).strip() for c in df.columns]
            if "Quant OP (kg)" in df.columns:
                df["Quant OP (kg)"] = df["Quant OP (kg)"].astype(str).str.replace(',', '.')
                df["Quant OP (kg)"] = pd.to_numer…
[11:24, 24/02/2026] Ernando: import streamlit as st
import pandas as pd
import os
from datetime import datetime

st.set_page_config(page_title="Controle de Pigmentos 2026", layout="wide", page_icon="🧪")

# --- FUNÇÕES DE CARREGAMENTO E TRATAMENTO ---
def load_data():
    file_path = "Aba_Mestra.csv"
    if os.path.exists(file_path):
        try:
            try:
                df = pd.read_csv(file_path, sep=None, engine='python', encoding='utf-8')
            except:
                df = pd.read_csv(file_path, sep=None, engine='python', encoding='latin-1')
            df.columns = [str(c).strip() for c in df.columns]
            if "Quant OP (kg)" in df.columns:
                df["Quant OP (kg)"] = df["Quant OP (kg)"].astype(str).str.replace(',', '.')
                df["Quant OP (kg)"] = pd.to_numeric(df["Quant OP (kg)"], errors='coerce').fillna(0.0)
            return df
        except Exception as e:
            st.error(f"Erro ao carregar Aba_Mestra: {e}")
            return pd.DataFrame()
    return pd.DataFrame(columns=["Tipo", "Cor", "Pigmento", "Quant OP (kg)"])

def salvar_no_historico(dados_lista):
    hist_path = "Historico_Producao.csv"
    novo_df = pd.DataFrame(dados_lista)
    
    colunas_excel = ["data", "lote", "tipo de produto", "cor", "pigmento", "toque", "Quant ad (g)", "#Plan", "#Real", "Litros/Unit", "Volume Planejado", "Volume Produzido", "Encomenda?"]
    
    if os.path.exists(hist_path):
        hist_existente = pd.read_csv(hist_path, encoding='latin-1', sep=';')
        # Limpeza para garantir que o Pandas não se perca com vírgulas lidas anteriormente
        for col in ["Quant ad (g)", "Volume Planejado", "Volume Produzido"]:
            if col in hist_existente.columns:
                hist_existente[col] = hist_existente[col].astype(str).str.replace(',', '.')
                hist_existente[col] = pd.to_numeric(hist_existente[col], errors='coerce')
        
        hist_final = pd.concat([hist_existente, novo_df[colunas_excel]], ignore_index=True)
    else:
        hist_final = novo_df[colunas_excel]
        
    hist_final.to_csv(hist_path, index=False, sep=';', encoding='latin-1')

def formatar_para_excel(df):
    df_excel = df.copy()
    colunas_numericas = df_excel.select_dtypes(include=['float64', 'float32', 'int64']).columns
    for col in colunas_numericas:
        if col not in ["#Plan", "#Real", "toque"]: # Mantém inteiros como inteiros
            df_excel[col] = df_excel[col].apply(lambda x: f"{x:.8f}".replace('.', ','))
    return df_excel

df_mestra = load_data()

# --- NAVEGAÇÃO ---
st.sidebar.title("🧪 Menu")
aba = st.sidebar.radio("Ir para:", ["🚀 Nova Pigmentação", "📜 Banco de Dados", "➕ Cadastro", "📊 Aba Mestra"])

if aba == "🚀 Nova Pigmentação":
    st.title("🚀 Registrar Produção")
    
    if df_mestra.empty:
        st.warning("Base de dados vazia.")
    else:
        # Identificação
        c1, c2, c3 = st.columns(3)
        with c1:
            tipo_sel = st.selectbox("Produto", df_mestra['Tipo'].unique())
            encomenda = st.selectbox("Encomenda?", ["Não", "Sim"])
        with c2:
            cores_disp = df_mestra[df_mestra['Tipo'] == tipo_sel]['Cor'].unique()
            cor_sel = st.selectbox("Cor", cores_disp)
        with c3:
            lote_id = st.text_input("Lote", value=datetime.now().strftime("%Y%m%d"))

        # Volumes
        cp1, cp2 = st.columns(2)
        with cp1:
            num_plan = st.number_input("#Plan (Unidades)", min_value=1, value=1)
        with cp2:
            litros_unit = st.number_input("Litros/Unit", min_value=0.01, value=15.0)
        
        vol_planejado = num_plan * litros_unit
        st.info(f"💡 *Volume Total Planejado:* {vol_planejado:.2f} Litros")

        formulas = df_mestra[(df_mestra['Tipo'] == tipo_sel) & (df_mestra['Cor'] == cor_sel)]
        
        if not formulas.empty:
            with st.form("form_pigm"):
                st.subheader("🎨 Dosagem de Pigmentos")
                lista_lote = []
                
                for index, row in formulas.iterrows():
                    pigm = row['Pigmento']
                    dosagem_base = row["Quant OP (kg)"] # valor p/ 1kg
                    
                    # CÁLCULO DA DOSAGEM RECOMENDADA
                    recomendado_kg = dosagem_base * vol_planejado
                    recomendado_g = recomendado_kg * 1000
                    
                    st.markdown(f"---")
                    st.markdown(f"### 🧪 {pigm}")
                    
                    # Visualização da Recomendação (O que você pediu de volta)
                    st.warning(f"📋 *Dosagem Recomendada:* {recomendado_kg:.8f} kg  ({recomendado_g:.2f} g)")
                    
                    col_a, col_b, col_c = st.columns(3)
                    with col_a:
                        tq = st.number_input(f"Toques", min_value=0, step=1, key=f"tq_{index}")
                    with col_b:
                        # Preenchemos o "Quant ad (g)" com o calculado, mas permitimos edição
                        q_ad = st.number_input(f"Quant ad (g) Real", value=float(recomendado_g), format="%.2f", key=f"ad_{index}")
                    with col_c:
                        # Registro em KG para o peso real
                        p_real = st.number_input(f"Peso Real (kg)", value=float(recomendado_kg), format="%.8f", key=f"re_{index}")

                    lista_lote.append({
                        "data": datetime.now().strftime("%d/%m/%Y"),
                        "lote": lote_id,
                        "tipo de produto": tipo_sel,
                        "cor": cor_sel,
                        "pigmento": pigm,
                        "toque": tq,
                        "Quant ad (g)": q_ad,
                        "#Plan": num_plan,
                        "Litros/Unit": litros_unit,
                        "Volume Planejado": vol_planejado,
                        "Encomenda?": encomenda
                    })
                
                st.markdown("---")
                num_real = st.number_input("#Real (Unidades Produzidas)", value=int(num_plan))
                
                if st.form_submit_button("✅ Salvar no Banco de Dados"):
                    for item in lista_lote:
                        item["#Real"] = num_real
                        item["Volume Produzido"] = num_real * litros_unit
                    
                    salvar_no_historico(lista_lote)
                    st.success("✅ Registro salvo com sucesso!")
                    st.balloons()
        else:
            st.error("Fórmula não encontrada.")

elif aba == "📜 Banco de Dados":
    st.title("📜 Histórico Geral")
    hist_path = "Historico_Producao.csv"
    if os.path.exists(hist_path):
        df_hist = pd.read_csv(hist_path, sep=';', encoding='latin-1')
        st.dataframe(df_hist, use_container_width=True)
        
        # Exportação com Vírgula Decimal
        df_excel = formatar_para_excel(df_hist)
        csv_ready = df_excel.to_csv(index=False, sep=';', encoding='latin-1').encode('latin-1')
        st.download_button("📥 Baixar Base para Excel (Vírgulas)", csv_ready, "Controle_2026.csv", "text/csv")
    else:
        st.info("Banco de dados vazio.")

elif aba == "➕ Cadastro":
    st.title("➕ Nova Cor")
    with st.form("cad"):
        t = st.text_input("Produto")
        c = st.text_input("Cor")
        p = st.text_input("Pigmento")
        q = st.number_input("Quant OP (kg) para 1L", format="%.8f")
        if st.form_submit_button("Salvar"):
            nl = pd.DataFrame([{"Tipo": t, "Cor": c, "Pigmento": p, "Quant OP (kg)": q}])
            df_mestra = pd.concat([df_mestra, nl], ignore_index=True)
            df_mestra.to_csv("Aba_Mestra.csv", index=False)
            st.success("Salvo!")

elif aba == "📊 Aba Mestra":
    st.title("📊 Dados da Aba Mestra")
    st.dataframe(df_mestra)

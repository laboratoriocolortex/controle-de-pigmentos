import streamlit as st
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
        if col not in ["#Plan", "#Real", "toque"]:
            df_excel[col] = df_excel[col].apply(lambda x: f"{x:.8f}".replace('.', ','))
    return df_excel

df_mestra = load_data()

# --- NAVEGAÇÃO ---
st.sidebar.title("🧪 Menu")
aba = st.sidebar.radio("Ir para:", ["🚀 Nova Pigmentação", "📜 Banco de Dados", "➕ Cadastro", "📊 Aba Mestra"])

if aba == "🚀 Nova Pigmentação":
    st.title("🚀 Registrar Produção")
    
    if df_mestra.empty:
        st.warning("Aba Mestra não carregada.")
    else:
        # 1. Identificação Geral
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
        
        # 2. Configuração Compacta de Unidades e Litragem
        col_unid, col_litros = st.columns([1, 3])
        
        with col_unid:
            st.write("*📦 Unidades*")
            num_plan = st.number_input("#Plan", min_value=1, value=1, step=1)
            num_real = st.number_input("#Real", min_value=1, value=num_plan, step=1)

        with col_litros:
            st.write("*🧪 Litragem / Embalagem*")
            # Lista compacta de opções
            opcoes_vol = ["0,9L", "3L", "3,6L", "13kg", "15L", "18L", "25kg", "Outro"]
            selecao_vol = st.select_slider("Selecione o Volume Unitário:", options=opcoes_vol, value="15L")
            
            if selecao_vol == "Outro":
                litros_unit = st.number_input("Valor (L/kg):", min_value=0.01, value=1.0, format="%.2f")
            else:
                litros_unit = float(selecao_vol.replace('L', '').replace('kg', '').replace(',', '.'))
        
        st.markdown("---")
        
        # Cálculos de Volume Total
        vol_planejado_total = num_plan * litros_unit
        vol_produzido_total = num_real * litros_unit
        
        v1, v2 = st.columns(2)
        v1.metric("Volume Planejado Total", f"{vol_planejado_total:.2f} L/kg")
        v2.metric("Volume Produzido Total", f"{vol_produzido_total:.2f} L/kg")

        formulas = df_mestra[(df_mestra['Tipo'] == tipo_sel) & (df_mestra['Cor'] == cor_sel)]
        
        if not formulas.empty:
            with st.form("form_pigm"):
                st.subheader("🎨 Composição e Dosagem")
                lista_lote = []
                
                for index, row in formulas.iterrows():
                    pigm = row['Pigmento']
                    dosagem_base = row["Quant OP (kg)"]
                    rec_kg = dosagem_base * vol_planejado_total
                    rec_g = rec_kg * 1000
                    
                    st.markdown(f"#### 🧪 {pigm}")
                    c_info, c_tq, c_ad, c_re = st.columns([1.5, 1, 1, 1])
                    
                    with c_info:
                        st.caption("📍 Recomendado")
                        st.code(f"{rec_kg:.4f} kg | {rec_g:.2f} g")
                    with c_tq:
                        tq = st.number_input(f"Toques", min_value=0, step=1, key=f"tq_{index}")
                    with c_ad:
                        q_ad = st.number_input(f"Quant ad (g)", value=float(rec_g), format="%.2f", key=f"ad_{index}")
                    with c_re:
                        p_real = st.number_input(f"Peso Real (kg)", value=float(rec_kg), format="%.8f", key=f"re_{index}")

                    lista_lote.append({
                        "data": datetime.now().strftime("%d/%m/%Y"),
                        "lote": lote_id,
                        "tipo de produto": tipo_sel,
                        "cor": cor_sel,
                        "pigmento": pigm,
                        "toque": tq,
                        "Quant ad (g)": q_ad,
                        "#Plan": num_plan,
                        "#Real": num_real,
                        "Litros/Unit": litros_unit,
                        "Volume Planejado": vol_planejado_total,
                        "Volume Produzido": vol_produzido_total,
                        "Encomenda?": encomenda
                    })
                
                if st.form_submit_button("✅ Finalizar e Salvar"):
                    salvar_no_historico(lista_lote)
                    st.success("Registro salvo no histórico!")
                    st.balloons()
        else:
            st.error("Fórmula não encontrada.")

# --- OUTRAS ABAS ---
elif aba == "📜 Banco de Dados":
    st.title("📜 Histórico")
    hist_path = "Historico_Producao.csv"
    if os.path.exists(hist_path):
        df_hist = pd.read_csv(hist_path, sep=';', encoding='latin-1')
        st.dataframe(df_hist, use_container_width=True)
        df_excel = formatar_para_excel(df_hist)
        csv_ready = df_excel.to_csv(index=False, sep=';', encoding='latin-1').encode('latin-1')
        st.download_button("📥 Baixar Base para Excel", csv_ready, "Controle_2026.csv", "text/csv")

elif aba == "➕ Cadastro":
    st.title("➕ Novo Pigmento")
    with st.form("cad"):
        t = st.text_input("Produto")
        c = st.text_input("Cor")
        p = st.text_input("Pigmento")
        q = st.number_input("Quant OP (kg) p/ 1L", format="%.8f")
        if st.form_submit_button("Salvar"):
            nl = pd.DataFrame([{"Tipo": t, "Cor": c, "Pigmento": p, "Quant OP (kg)": q}])
            df_mestra = pd.concat([df_mestra, nl], ignore_index=True)
            df_mestra.to_csv("Aba_Mestra.csv", index=False)
            st.success("Salvo!")

elif aba == "📊 Aba Mestra":
    st.title("📊 Dados Cadastrados")
    st.dataframe(df_mestra)

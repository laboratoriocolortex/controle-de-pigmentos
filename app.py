import streamlit as st
import pandas as pd
import os
from datetime import datetime

st.set_page_config(page_title="Controle 2026", layout="wide", page_icon="🧪")

# --- ESTILO CSS ---
st.markdown("""
    <style>
    div.stButton > button:first-child {
        background-color: #d4edda; color: #155724; border: 1px solid #c3e6cb;
        font-weight: bold; width: 100%; height: 3em;
    }
    .block-container { padding-top: 1.5rem; }
    .pigmento-header { 
        background-color: #f8f9fa; 
        padding: 10px; 
        border-radius: 5px; 
        margin-top: 10px;
        border-left: 5px solid #007bff;
    }
    h3 { margin-bottom: 0rem !important; font-size: 1.15rem !important; }
    hr { margin: 0.7rem 0rem !important; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNÇÃO PARA FORMATAR NÚMEROS (PADRÃO EXCEL) ---
def format_excel_num(valor):
    if valor is None or valor == "": return ""
    try:
        val_float = float(valor)
        if val_float == int(val_float):
            return str(int(val_float))
        return f"{val_float:.2f}".replace('.', ',')
    except:
        return str(valor)

# --- FUNÇÕES DE DADOS ---
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
            return pd.DataFrame(columns=["Tipo", "Cor", "Pigmento", "Quant OP (kg)"])
    return pd.DataFrame(columns=["Tipo", "Cor", "Pigmento", "Quant OP (kg)"])

def salvar_no_historico(dados_lista):
    hist_path = "Historico_Producao.csv"
    
    for i, item in enumerate(dados_lista):
        # Formatação de números
        item["Quantidade OP"] = format_excel_num(item["Quantidade OP"])
        item["Quant ad (g)"] = format_excel_num(item["Quant ad (g)"])
        
        # Preenchimento seletivo (apenas 1ª linha)
        if i == 0:
            item["#Plan"] = format_excel_num(item["#Plan"])
            item["#Real"] = format_excel_num(item["#Real"])
            item["Litros/Unit"] = format_excel_num(item["Litros/Unit"])
        else:
            item["#Plan"] = ""
            item["#Real"] = ""
            item["Litros/Unit"] = ""

    novo_df = pd.DataFrame(dados_lista)
    # ORDEM DAS COLUNAS: Quant ad (g) antes de Quantidade OP
    colunas_excel = [
        "data", "lote", "tipo de produto", "cor", "pigmento", "toque", 
        "Quant ad (g)", "Quantidade OP", "#Plan", "#Real", "Encomenda?", "Litros/Unit"
    ]
    
    if os.path.exists(hist_path):
        try:
            hist_existente = pd.read_csv(hist_path, encoding='latin-1', sep=';')
            hist_final = pd.concat([hist_existente, novo_df[colunas_excel]], ignore_index=True)
        except:
            hist_final = novo_df[colunas_excel]
    else:
        hist_final = novo_df[colunas_excel]
    
    hist_final.to_csv(hist_path, index=False, sep=';', encoding='latin-1')

df_mestra = load_data()

# --- INTERFACE ---
aba = st.sidebar.radio("Navegação:", ["🚀 Nova Pigmentação", "📜 Banco de Dados", "➕ Cadastro", "📊 Aba Mestra"])

if aba == "🚀 Nova Pigmentação":
    st.title("🚀 Registrar Pigmentação")
    
    if df_mestra.empty:
        st.warning("Aba Mestra vazia.")
    else:
        c1, c2, c3, c4 = st.columns([1.5, 1.5, 1, 1])
        with c1: tipo_sel = st.selectbox("Produto", df_mestra['Tipo'].unique())
        with c2: cor_sel = st.selectbox("Cor", df_mestra[df_mestra['Tipo'] == tipo_sel]['Cor'].unique())
        with c3: lote_id = st.text_input("Lote", value="", placeholder="Nº Lote")
        with c4: encomenda = st.selectbox("📦 Encomenda?", ["Não", "Sim"])

        st.markdown("---")
        
        u1, u2, u3 = st.columns([1, 1, 2])
        with u1: num_plan = st.number_input("#Unid Plan", min_value=1, step=1, value=None)
        with u2: num_real = st.number_input("#Unid Real", min_value=1, step=1, value=None)
        with u3:
            opcoes_vol = ["0,9L", "3L", "3,6L", "5kg", "13kg", "15L", "18L", "25kg", "Outro"]
            selecao_vol = st.select_slider("Embalagem:", options=opcoes_vol, value="15L")
            litros_unit = float(selecao_vol.replace('L', '').replace('kg', '').replace(',', '.')) if selecao_vol != "Outro" else st.number_input("Valor Unit:", value=None)
        
        vol_plan_tot = (num_plan * litros_unit) if (num_plan and litros_unit) else 0
        st.caption(f"Volume de Cálculo: {vol_plan_tot:.2f} Total")
        
        st.subheader("🎨 Pigmentos") # Identificação da seção
        st.markdown("---")

        formulas = df_mestra[(df_mestra['Tipo'] == tipo_sel) & (df_mestra['Cor'] == cor_sel)]
        
        if not formulas.empty:
            lista_lote = []
            for index, row in formulas.iterrows():
                pigm = row['Pigmento']
                rec_g = round(row["Quant OP (kg)"] * vol_plan_tot * 1000, 2)
                
                with st.container():
                    # Linha de cabeçalho do pigmento mais robusta
                    col_nome, col_info, col_tq_input = st.columns([2, 1, 1])
                    col_nome.markdown(f"### {pigm}")
                    col_info.caption(f"Sugestão Técnica: {rec_g}g")
                    with col_tq_input:
                        # TOQUES com label visível novamente
                        n_toques = st.number_input(f"Toques", min_value=1, value=1, step=1, key=f"nt_{index}")
                    
                    soma_adicionada = 0.0
                    cols_toques = st.columns(6)
                    for t in range(1, int(n_toques) + 1):
                        with cols_toques[(t-1) % 6]:
                            valor_t = st.number_input(f"T{t}", min_value=0.0, format="%.2f", value=None, key=f"val_{index}_{t}")
                            if valor_t: soma_adicionada += valor_t
                    
                    st.markdown(f"*Total Adicionado: {soma_adicionada:.2f} g*")
                    
                    lista_lote.append({
                        "data": datetime.now().strftime("%d/%m/%Y"), "lote": lote_id, "tipo de produto": tipo_sel,
                        "cor": cor_sel, "pigmento": pigm, "toque": n_toques, "Quantidade OP": rec_g, 
                        "Quant ad (g)": soma_adicionada, "#Plan": num_plan, "#Real": num_real, 
                        "Encomenda?": encomenda, "Litros/Unit": litros_unit
                    })
                    st.markdown("<hr>", unsafe_allow_html=True)
            
            if st.button("✅ FINALIZAR E SALVAR REGISTRO", use_container_width=True):
                if not lote_id or not num_plan:
                    st.error("Preencha Lote e Unidades!")
                else:
                    salvar_no_historico(lista_lote)
                    st.success("Salvo com sucesso!")
                    st.balloons()

elif aba == "📜 Banco de Dados":
    st.title("📜 Histórico")
    if os.path.exists("Historico_Producao.csv"):
        df_hist = pd.read_csv("Historico_Producao.csv", sep=';', encoding='latin-1')
        st.dataframe(df_hist, use_container_width=True)
        st.download_button("📥 Baixar CSV", df_hist.to_csv(index=False, sep=';', encoding='latin-1').encode('latin-1'), "Producao.csv", "text/csv")

elif aba == "➕ Cadastro":
    st.title("➕ Cadastro")
    with st.form("cad"):
        t = st.text_input("Produto")
        c = st.text_input("Cor")
        p = st.text_input("Pigmento")
        q = st.number_input("kg/1L", format="%.8f", value=None)
        if st.form_submit_button("Salvar"):
            pd.concat([df_mestra, pd.DataFrame([{"Tipo": t, "Cor": c, "Pigmento": p, "Quant OP (kg)": q}])], ignore_index=True).to_csv("Aba_Mestra.csv", index=False, encoding='latin-1')
            st.success("OK!")
            st.rerun()

elif aba == "📊 Aba Mestra":
    st.dataframe(df_mestra, use_container_width=True)


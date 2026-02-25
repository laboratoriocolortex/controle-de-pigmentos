import streamlit as st
import pandas as pd
import os
from datetime import datetime

st.set_page_config(page_title="Controle de Pigmentos 2026", layout="wide", page_icon="🧪")

# --- ESTILO CSS PARA BOTÃO VERDE E COMPACTAÇÃO ---
st.markdown("""
    <style>
    div.stButton > button:first-child {
        background-color: #d4edda;
        color: #155724;
        border: 1px solid #c3e6cb;
        font-weight: bold;
        width: 100%;
        height: 3em;
        transition: 0.3s;
    }
    div.stButton > button:first-child:hover {
        background-color: #c3e6cb;
    }
    .block-container { padding-top: 1.5rem; }
    h3 { margin-bottom: 0.5rem; font-size: 1.2rem !important; }
    hr { margin: 0.8rem 0rem !important; }
    </style>
    """, unsafe_allow_html=True)

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
    novo_df = pd.DataFrame(dados_lista)
    colunas_excel = ["data", "lote", "tipo de produto", "cor", "pigmento", "toque", "Quant ad (g)", "#Plan", "#Real", "Encomenda?", "Litros/Unit"]
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

# --- NAVEGAÇÃO ---
st.sidebar.title("🧪 Menu")
aba = st.sidebar.radio("Ir para:", ["🚀 Nova Pigmentação", "📜 Banco de Dados", "➕ Cadastro", "📊 Aba Mestra"])

if aba == "🚀 Nova Pigmentação":
    st.title("🚀 Registrar Produção")
    
    if df_mestra.empty:
        st.warning("Aba Mestra vazia. Vá em 'Cadastro' primeiro.")
    else:
        # Cabeçalho - VISIBILIDADE DA ENCOMENDA MELHORADA
        c1, c2, c3, c4 = st.columns([1.5, 1.5, 1, 1])
        with c1:
            tipo_sel = st.selectbox("Produto", df_mestra['Tipo'].unique())
        with c2:
            cor_sel = st.selectbox("Cor", df_mestra[df_mestra['Tipo'] == tipo_sel]['Cor'].unique())
        with c3:
            lote_id = st.text_input("Lote", value="", placeholder="Nº Lote")
        with c4:
            # Pergunta de encomenda bem visível
            encomenda = st.selectbox("📦 Encomenda?", ["Não", "Sim"])

        st.markdown("---")
        
        # Unidades e Litragem
        u1, u2, u3 = st.columns([1, 1, 2])
        with u1:
            num_plan = st.number_input("#Unidades Plan", min_value=1, step=1, value=None)
        with u2:
            num_real = st.number_input("#Unidades Real", min_value=1, step=1, value=None)
        with u3:
            opcoes_vol = ["0,9L", "3L", "3,6L", "13kg", "15L", "18L", "25kg", "Outro"]
            selecao_vol = st.select_slider("Litragem Embalagem:", options=opcoes_vol, value="15L")
            litros_unit = float(selecao_vol.replace('L', '').replace('kg', '').replace(',', '.')) if selecao_vol != "Outro" else st.number_input("Valor L/kg:", value=None)
        
        vol_plan_tot = (num_plan * litros_unit) if (num_plan and litros_unit) else 0
        st.info(f"Cálculo Base: *{vol_plan_tot:.2f} Total (L/kg)*")

        st.markdown("---")

        formulas = df_mestra[(df_mestra['Tipo'] == tipo_sel) & (df_mestra['Cor'] == cor_sel)]
        
        if not formulas.empty:
            lista_lote = []
            for index, row in formulas.iterrows():
                pigm = row['Pigmento']
                rec_g = row["Quant OP (kg)"] * vol_plan_tot * 1000
                
                with st.container():
                    # Ícones de paleta 🎨 retornados conforme pedido
                    col_tit, col_toque = st.columns([3, 1])
                    col_tit.markdown(f"### 🎨 {pigm}")
                    
                    with col_toque:
                        n_toques = st.number_input(f"Qtd Toques", min_value=1, value=1, step=1, key=f"nt_{index}")
                    
                    st.caption(f"💡 Sugestão Técnica: *{rec_g:.2f}g*")
                    
                    # Grade de pesagem compacta
                    soma_adicionada = 0.0
                    cols_toques = st.columns(6)
                    for t in range(1, int(n_toques) + 1):
                        with cols_toques[(t-1) % 6]:
                            valor_t = st.number_input(f"T{t} (g)", min_value=0.0, format="%.2f", value=None, key=f"val_{index}_{t}")
                            if valor_t: soma_adicionada += valor_t
                    
                    st.write(f"*Soma Total {pigm}: {soma_adicionada:.2f} g*")
                    
                    lista_lote.append({
                        "data": datetime.now().strftime("%d/%m/%Y"), "lote": lote_id, "tipo de produto": tipo_sel,
                        "cor": cor_sel, "pigmento": pigm, "toque": n_toques, "Quant ad (g)": soma_adicionada,
                        "#Plan": num_plan if num_plan else 0, "#Real": num_real if num_real else 0, 
                        "Encomenda?": encomenda, "Litros/Unit": litros_unit
                    })
                    st.markdown("<hr>", unsafe_allow_html=True)
            
            # Botão de Salvamento Verde Suave
            if st.button("✅ FINALIZAR E SALVAR REGISTRO", use_container_width=True):
                if not lote_id or not num_plan:
                    st.error("ERRO: Preencha o Lote e as Unidades!")
                else:
                    salvar_no_historico(lista_lote)
                    st.success("Dados salvos com sucesso!")
                    st.balloons()
        else:
            st.error("Fórmula não encontrada.")

elif aba == "📜 Banco de Dados":
    st.title("📜 Histórico")
    if os.path.exists("Historico_Producao.csv"):
        df_hist = pd.read_csv("Historico_Producao.csv", sep=';', encoding='latin-1')
        st.dataframe(df_hist, use_container_width=True)
        csv = df_hist.to_csv(index=False, sep=';', encoding='latin-1').encode('latin-1')
        st.download_button("📥 Baixar CSV para Excel", csv, "Producao.csv", "text/csv")

elif aba == "➕ Cadastro":
    st.title("➕ Cadastro")
    with st.form("cad_novo"):
        t = st.text_input("Tipo de Produto")
        c = st.text_input("Cor")
        p = st.text_input("Pigmento")
        q = st.number_input("kg por 1L", format="%.8f", value=None)
        if st.form_submit_button("Salvar"):
            if t and c and p and q:
                novo = pd.DataFrame([{"Tipo": t, "Cor": c, "Pigmento": p, "Quant OP (kg)": q}])
                pd.concat([df_mestra, novo], ignore_index=True).to_csv("Aba_Mestra.csv", index=False, encoding='latin-1')
                st.success("Cadastrado!")
                st.rerun()

elif aba == "📊 Aba Mestra":
    st.title("📊 Consulta Aba Mestra")
    st.dataframe(df_mestra, use_container_width=True)

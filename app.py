import streamlit as st
import pandas as pd
import os
from datetime import datetime

# 1. Configuração de Layout
st.set_page_config(page_title="Colortex 2026 - Controle de Pesagem", layout="wide")

# --- ESTILO CSS ---
st.markdown("""
    <style>
    .stNumberInput { margin-bottom: -1rem; }
    .stButton > button { width: 100%; background-color: #d4edda; color: #155724; font-weight: bold; }
    hr { margin: 0.5rem 0rem !important; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNÇÕES DE APOIO ---

def carregar_dados(arquivo):
    if not os.path.exists(arquivo): return pd.DataFrame()
    try:
        try:
            df = pd.read_csv(arquivo, sep=None, engine='python', encoding='latin-1')
        except:
            df = pd.read_csv(arquivo, sep=None, engine='python', encoding='utf-8')
        
        df.columns = [str(c).strip() for c in df.columns]
        # TRADUTOR DE ACENTOS (Oxido -> Óxido / Franca -> França)
        traducoes = {'Oxido': 'Óxido', 'Franca': 'França', 'oxido': 'óxido', 'franca': 'frança'}
        for col in df.select_dtypes(include=['object']).columns:
            df[col] = df[col].astype(str).str.strip().replace(traducoes, regex=True).str.title()
        return df
    except: return pd.DataFrame()

def salvar_csv(df, arquivo):
    df.to_csv(arquivo, index=False, encoding='latin-1')

# --- CARREGAMENTO ---
df_mestra = carregar_dados("Aba_Mestra.csv")
df_hist = carregar_dados("Historico_Producao.csv")

# --- NAVEGAÇÃO ---
menu = ["🚀 Produção (Toques)", "📈 Gráficos CEP", "📜 Banco de Dados", "➕ Cadastro Manual", "📊 Editor Aba Mestra", "📂 Importar CSV"]
aba = st.sidebar.radio("Navegação", menu)

# --- 🚀 ABA: PRODUÇÃO (COM SLIDERS E TOQUES) ---
if aba == "🚀 Produção (Toques)":
    st.title("🚀 Registrar Pesagem por Toques")
    
    if df_mestra.empty:
        st.warning("⚠️ Importe a 'Aba Mestra' na aba Importar CSV.")
    else:
        # Cabeçalho de Seleção
        c1, c2, c3, c4 = st.columns([1.5, 1.5, 1, 1])
        with c1: t_sel = st.selectbox("Produto", sorted(df_mestra['Tipo'].unique()))
        with c2: cor_sel = st.selectbox("Cor", sorted(df_mestra[df_mestra['Tipo'] == t_sel]['Cor'].unique()))
        with c3: lote = st.text_input("Lote")
        with c4: data_f = st.date_input("Data", datetime.now())

        # SLIDERS DE VOLUME (RESTAURADOS)
        v1, v2, v3 = st.columns([1, 1, 2])
        with v1: n_p = st.number_input("# Unid Plan", min_value=1, value=1)
        with v2: n_r = st.number_input("# Unid Real", min_value=1, value=1)
        with v3:
            opcoes_v = ["0,9L", "3,6L", "15L", "18L", "25kg", "Outro"]
            sel_v = st.select_slider("Embalagem:", options=opcoes_v, value="15L")
            litros_u = float(sel_v.replace('L','').replace('kg','').replace(',','.')) if sel_v != "Outro" else st.number_input("Valor Unit:", value=15.0)

        vol_p_tot = n_p * litros_u
        st.info(f"Volume Total Planejado: {vol_p_tot:.2f}L")
        
        formula = df_mestra[(df_mestra['Tipo'] == t_sel) & (df_mestra['Cor'] == cor_sel)]
        st.divider()

        registros_lote = []
        if not formula.empty:
            for i, row in formula.iterrows():
                pigm = row['Pigmento']
                coef = float(str(row['Quant OP (kg)']).replace(',', '.'))
                sugestao = round(coef * vol_p_tot * 1000, 2)
                
                with st.container():
                    col_p, col_inputs = st.columns([1.5, 3.5])
                    with col_p:
                        st.subheader(pigm)
                        st.write(f"Sugestão: **{sugestao}g**")
                        # CAIXA DE TOQUES (RESTAURADA)
                        n_toques = st.number_input(f"Toques", min_value=1, max_value=10, value=1, key=f"nt_{i}")
                    
                    with col_inputs:
                        soma_ad = 0.0
                        cols_t = st.columns(5)
                        for t in range(1, int(n_toques) + 1):
                            with cols_t[(t-1)%5]:
                                val_t = st.number_input(f"T{t} (g)", min_value=0.0, format="%.2f", key=f"val_{i}_{t}")
                                soma_ad += val_t
                        st.markdown(f"**Total Pesado: {soma_ad:.2f}g**")
                
                registros_lote.append({
                    "data": data_f.strftime("%d/%m/%Y"), "lote": lote, "tipo de produto": t_sel,
                    "cor": cor_sel, "pigmento": pigm, "Quant ad (g)": soma_ad,
                    "Quantidade OP": (sugestao/1000), "#Plan": n_p, "#Real": n_r, "Litros/Unit": litros_u, "toque": n_toques
                })
                st.divider()

            if st.button("💾 FINALIZAR E SALVAR LOTE"):
                if not lote: st.error("Por favor, insira o número do Lote!")
                else:
                    df_novo = pd.DataFrame(registros_lote)
                    df_hist = pd.concat([df_hist, df_novo], ignore_index=True)
                    salvar_csv(df_hist, "Historico_Producao.csv")
                    st.success(f"Lote {lote} salvo com sucesso!"); st.balloons()

# --- 📈 ABA: CEP (CORRIGIDA E FILTRADA) ---
elif aba == "📈 Gráficos CEP":
    st.title("📈 Controle Estatístico (CEP)")
    if df_hist.empty:
        st.info("O histórico está vazio.")
    else:
        # Filtros para o gráfico não misturar tudo
        f1, f2 = st.columns(2)
        with f1: p_filt = st.selectbox("Produto", sorted(df_hist['tipo de produto'].unique()))
        with f2: c_filt = st.selectbox("Cor", sorted(df_hist[df_hist['tipo de produto'] == p_filt]['cor'].unique()))
        
        df_cep = df_hist[(df_hist['tipo de produto'] == p_filt) & (df_hist['cor'] == c_filt)].copy()
        
        if not df_cep.empty:
            # Garante que os números são válidos
            df_cep['Quant ad (g)'] = pd.to_numeric(df_cep['Quant ad (g)'], errors='coerce')
            df_cep['Quantidade OP'] = pd.to_numeric(df_cep['Quantidade OP'], errors='coerce')
            
            # Cálculo de Desvio: (Real / Planejado) - 1
            df_cep['Desvio_%'] = ((df_cep['Quant ad (g)'] / (df_cep['Quantidade OP'] * 1000 + 0.000001)) - 1) * 100
            
            # Gráfico separado por Pigmento
            pivot_cep = df_cep.pivot_table(index='lote', columns='pigmento', values='Desvio_%')
            st.subheader(f"Variação % por Pigmento - {c_filt}")
            st.line_chart(pivot_cep)
            st.dataframe(df_cep[['data', 'lote', 'pigmento', 'Quant ad (g)', 'Desvio_%']])
        else:
            st.warning("Sem dados para esta combinação de Produto/Cor.")

# --- DEMAIS ABAS ---
elif aba == "➕ Cadastro Manual":
    st.title("➕ Cadastrar Novo Item")
    with st.form("cad"):
        t = st.text_input("Tipo")
        c = st.text_input("Cor")
        p = st.text_input("Pigmento")
        q = st.number_input("Coeficiente (kg/L)", format="%.6f")
        if st.form_submit_button("Salvar"):
            n = pd.DataFrame([{"Tipo":t,"Cor":c,"Pigmento":p,"Quant OP (kg)":q}])
            df_mestra = pd.concat([df_mestra, n], ignore_index=True)
            salvar_csv(df_mestra, "Aba_Mestra.csv")
            st.success("Cadastrado!")

elif aba == "📂 Importar CSV":
    st.title("📂 Importar Planilha")
    up = st.file_uploader("Arquivo CSV", type="csv")
    alvo = st.selectbox("Destino", ["Aba_Mestra.csv", "Historico_Producao.csv"])
    if up and st.button("Confirmar"):
        df_imp = pd.read_csv(up, encoding='latin-1', sep=None, engine='python')
        salvar_csv(df_imp, alvo)
        st.success("Importado!"); st.rerun()

elif aba == "📜 Banco de Dados":
    st.dataframe(df_hist)
    if st.button("🗑️ Deletar Histórico"):
        if os.path.exists("Historico_Producao.csv"): os.remove("Historico_Producao.csv")
        st.rerun()

elif aba == "📊 Editor Aba Mestra":
    ed = st.data_editor(df_mestra, num_rows="dynamic")
    if st.button("Salvar"):
        salvar_csv(ed, "Aba_Mestra.csv")
        st.success("Salvo!")

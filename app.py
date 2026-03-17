import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# Configuração da página
st.set_page_config(page_title="Controle Colortex 2026", layout="wide", page_icon="📊")

# URL DA SUA PLANILHA
URL_PLANILHA = "https://docs.google.com/spreadsheets/d/19OfTga1-LFrsYS4PHcdx3nB3EAgf1oviNvp3qIuwtq8/edit?usp=sharing"

# Conexão
conn = st.connection("gsheets", type=GSheetsConnection)

# Função para garantir que os dados sejam números e não texto
def limpar_numeros(df, colunas):
    for col in colunas:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce').fillna(0.0)
    return df

@st.cache_data(ttl=5) # Cache curto para atualizar rápido
def carregar_dados():
    try:
        # Carrega Aba Mestra (Gid 1870828680)
        mestra = conn.read(spreadsheet=URL_PLANILHA, worksheet="1870828680")
        mestra.columns = [str(c).strip() for c in mestra.columns]
        mestra = limpar_numeros(mestra, ['Quant OP (kg)'])
        
        # Carrega Aba Controle (Gid 0)
        controle = conn.read(spreadsheet=URL_PLANILHA, worksheet="0")
        controle.columns = [str(c).strip() for c in controle.columns]
        # Limpa colunas numéricas do histórico para o gráfico não quebrar
        controle = limpar_numeros(controle, ['Variação %', 'Quant ad (g)'])
        
        return mestra, controle
    except Exception as e:
        st.error(f"Erro ao conectar com o Google Sheets: {e}")
        return pd.DataFrame(), pd.DataFrame()

# --- EXECUÇÃO ---
df_mestra, df_controle = carregar_dados()

st.sidebar.title("MENU DE CONTROLE")
aba = st.sidebar.radio("Navegação:", ["🚀 Registro de Produção", "📊 Banco de Dados (Controle)", "📈 Gráficos CEP", "⚙️ Ajustar Aba Mestra"])

if df_mestra.empty:
    st.warning("Aguardando conexão com a planilha ou Aba Mestra vazia...")
else:
    # 1. ABA REGISTRO
    if aba == "🚀 Registro de Produção":
        st.title("🚀 Novo Lote")
        
        # Nomes fixos conforme sua planilha
        col_tipo = "Tipo de Produto"
        col_cor = "Cor"
        
        with st.form("form_final"):
            c1, c2 = st.columns(2)
            with c1:
                t_sel = st.selectbox("Tipo de Produto", sorted(df_mestra[col_tipo].unique()))
                c_sel = st.selectbox("Cor", sorted(df_mestra[df_mestra[col_tipo] == t_sel][col_cor].unique()))
            with c2:
                lote_id = st.text_input("Número do Lote")
                data_fab = st.date_input("Data", datetime.now())

            v1, v2, v3 = st.columns(3)
            with v1: n_p = st.number_input("#Plan", min_value=1.0, value=1.0)
            with v2: n_r = st.number_input("#Real", min_value=1.0, value=1.0)
            with v3: l_u = st.number_input("Litros/Unit", value=15.0)

            st.divider()
            formulas = df_mestra[(df_mestra[col_tipo] == t_sel) & (df_mestra[col_cor] == c_sel)]
            pesos = {}
            for i, row in formulas.iterrows():
                sug = float(row['Quant OP (kg)']) * n_p * l_u * 1000
                pesos[i] = st.number_input(f"Quant ad (g) - {row['Pigmento']} (Sug: {sug:.1f}g)", min_value=0.0)

            # Botão de submissão (CORRIGE O ERRO "MISSING SUBMIT BUTTON")
            if st.form_submit_button("SALVAR NA PLANILHA"):
                if not lote_id:
                    st.error("Informe o Lote!")
                else:
                    novas_linhas = []
                    for i, row in formulas.iterrows():
                        lit_p, lit_r = n_p * l_u, n_r * l_u
                        f_base = float(row['Quant OP (kg)'])
                        util = (pesos[i] / 1000) / lit_r if lit_r > 0 else 0
                        
                        novas_linhas.append({
                            "Data": data_fab.strftime("%d/%m/%Y"), "Lote": lote_id, "Tipo de produto": t_sel,
                            "Cor": c_sel, "Pigmento": row['Pigmento'], "Toque": 1, "Quant ad (g)": pesos[i],
                            "Quant OP(kg)": f_base * lit_p, "#Plan": n_p, "#Real": n_r, "Litros/Unit": l_u,
                            "Encomenda?": "Não", "Litros Planejados": lit_p, "Litros Produzidos": lit_r,
                            "Formulação (kg/L)": f_base, "Utilizado (kg/L)": util,
                            "Variação %": (util / f_base) - 1 if f_base > 0 else 0,
                            "Variação ABS": (pesos[i]/1000) - (lit_r * f_base)
                        })
                    
                    df_novo = pd.concat([df_controle, pd.DataFrame(novas_linhas)], ignore_index=True)
                    conn.update(spreadsheet=URL_PLANILHA, worksheet="0", data=df_novo)
                    st.success("✅ Lote salvo! As abas serão atualizadas.")
                    st.cache_data.clear()

    # 2. ABA BANCO DE DADOS
    elif aba == "📊 Banco de Dados (Controle)":
        st.title("📊 Histórico Controle")
        st.dataframe(df_controle, use_container_width=True)

    # 3. ABA CEP (GRÁFICOS)
    elif aba == "📈 Gráficos CEP":
        st.title("📈 Controle Estatístico")
        if not df_controle.empty:
            prod = st.selectbox("Escolha o Produto", df_controle['Tipo de produto'].unique())
            df_plot = df_controle[df_controle['Tipo de produto'] == prod]
            st.line_chart(df_plot.pivot_table(index='Lote', columns='Pigmento', values='Variação %'))
        else:
            st.info("Sem dados para gerar gráficos.")

    # 4. ABA AJUSTAR MESTRA
    elif aba == "⚙️ Ajustar Aba Mestra":
        st.title("⚙️ Padrões da Aba Mestra")
        editado = st.data_editor(df_mestra, num_rows="dynamic")
        if st.button("Salvar Alterações na Mestra"):
            conn.update(spreadsheet=URL_PLANILHA, worksheet="1870828680", data=editado)
            st.success("Padrões atualizados!")
            st.cache_data.clear()

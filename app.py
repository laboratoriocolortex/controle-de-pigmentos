import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# Configuração da página
st.set_page_config(page_title="Controle Colortex 2026", layout="wide", page_icon="📊")

# --- URL ATUALIZADA ---
URL_PLANILHA = "https://docs.google.com/spreadsheets/d/19OfTga1-LFrsYS4PHcdx3nB3EAgf1oviNvp3qIuwtq8/edit?usp=sharing"

# Conexão
conn = st.connection("gsheets", type=GSheetsConnection)

def limpar_dados(df):
    """Limpa nomes de colunas e converte números de texto para float."""
    df.columns = [str(c).strip() for c in df.columns]
    # Colunas que devem ser numéricas
    cols_num = ['Quant OP (kg)', 'Variação %', 'Quant ad (g)', 'Quant OP(kg)', 'Formulação (kg/L)', 'Utilizado (kg/L)']
    for col in cols_num:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce').fillna(0.0)
    return df

@st.cache_data(ttl=2)
def carregar_dados():
    try:
        # Lendo abas pelos nomes para evitar erro 404
        mestra = conn.read(spreadsheet=URL_PLANILHA, worksheet="Aba Mestra")
        mestra = limpar_dados(mestra)
        
        controle = conn.read(spreadsheet=URL_PLANILHA, worksheet="controle")
        controle = limpar_dados(controle)
        
        return mestra, controle
    except Exception as e:
        st.error(f"Erro ao conectar: {e}")
        return pd.DataFrame(), pd.DataFrame()

# --- EXECUÇÃO ---
df_mestra, df_controle = carregar_dados()

if not df_mestra.empty:
    st.sidebar.title("MENU COLORTEX")
    aba = st.sidebar.radio("Navegação:", ["🚀 Registro de Produção", "📊 Banco de Dados", "📈 Gráficos CEP", "⚙️ Ajustar Aba Mestra"])

    # 1. REGISTRO
    if aba == "🚀 Registro de Produção":
        st.title("🚀 Novo Lote")
        
        with st.form("form_registro"):
            c1, c2 = st.columns(2)
            with c1:
                t_sel = st.selectbox("Tipo de Produto", sorted(df_mestra['Tipo de Produto'].unique()))
                c_sel = st.selectbox("Cor", sorted(df_mestra[df_mestra['Tipo de Produto'] == t_sel]['Cor'].unique()))
            with c2:
                lote_id = st.text_input("Número do Lote")
                data_fab = st.date_input("Data", datetime.now())

            v1, v2, v3 = st.columns(3)
            with v1: n_p = st.number_input("#Plan", min_value=1.0, value=1.0)
            with v2: n_r = st.number_input("#Real", min_value=1.0, value=1.0)
            with v3: l_u = st.number_input("Litros/Unit", value=15.0)

            st.divider()
            formulas = df_mestra[(df_mestra['Tipo de Produto'] == t_sel) & (df_mestra['Cor'] == c_sel)]
            pesos = {}
            for i, row in formulas.iterrows():
                f_base = float(row['Quant OP (kg)'])
                sug = f_base * n_p * l_u * 1000
                pesos[i] = st.number_input(f"Quant ad (g) - {row['Pigmento']} (Sug: {sug:.1f}g)", min_value=0.0)

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
                            "Data": data_fab.strftime("%d/%m/%Y"),
                            "Lote": lote_id,
                            "Tipo de produto": t_sel,
                            "Cor": c_sel,
                            "Pigmento": row['Pigmento'],
                            "Toque": 1,
                            "Quant ad (g)": pesos[i],
                            "Quant OP(kg)": f_base * lit_p,
                            "#Plan": n_p,
                            "#Real": n_r,
                            "Litros/Unit": l_u,
                            "Encomenda?": "Não",
                            "Litros Planejados": lit_p,
                            "Litros Produzidos": lit_r,
                            "Formulação (kg/L)": f_base,
                            "Utilizado (kg/L)": util,
                            "Variação %": (util / f_base) - 1 if f_base > 0 else 0,
                            "Variação ABS": (pesos[i]/1000) - (lit_r * f_base)
                        })
                    
                    df_final = pd.concat([df_controle, pd.DataFrame(novas_linhas)], ignore_index=True)
                    conn.update(spreadsheet=URL_PLANILHA, worksheet="controle", data=df_final)
                    st.success("✅ Salvo!")
                    st.balloons()
                    st.cache_data.clear()

    # 2. BANCO DE DADOS
    elif aba == "📊 Banco de Dados":
        st.title("📊 Histórico Controle")
        st.dataframe(df_controle, use_container_width=True)

    # 3. CEP
    elif aba == "📈 Gráficos CEP":
        st.title("📈 Gráficos de Variação")
        
        if not df_controle.empty:
            p_sel = st.selectbox("Produto", df_controle['Tipo de produto'].unique())
            df_p = df_controle[df_controle['Tipo de produto'] == p_sel]
            st.line_chart(df_p.pivot_table(index='Lote', columns='Pigmento', values='Variação %'))

    # 4. AJUSTAR MESTRA
    elif aba == "⚙️ Ajustar Aba Mestra":
        st.title("⚙️ Padrões")
        editado = st.data_editor(df_mestra, num_rows="dynamic", use_container_width=True)
        if st.button("Salvar Alterações"):
            conn.update(spreadsheet=URL_PLANILHA, worksheet="Aba Mestra", data=editado)
            st.success("Mestra Atualizada!")
            st.cache_data.clear()
else:
    st.info("Conectando ao Google Sheets... Verifique as permissões de 'Editor' no link.")

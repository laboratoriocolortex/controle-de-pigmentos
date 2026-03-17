import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# Configuração da página
st.set_page_config(page_title="Controle Colortex 2026", layout="wide")

# URL LIMPA
URL = "https://docs.google.com/spreadsheets/d/19OfTga1-LFrsYS4PHcdx3nB3EAgf1oviNvp3qIuwtq8/edit?gid=1870828680#gid=1870828680"

conn = st.connection("gsheets", type=GSheetsConnection)

def forcar_numero(valor):
    """Transforma qualquer entrada da planilha em número real."""
    if pd.isna(valor) or valor == "": return 0.0
    try:
        if isinstance(valor, str):
            # Remove espaços e troca vírgula por ponto
            valor = valor.strip().replace(',', '.')
        return float(valor)
    except:
        return 0.0

@st.cache_data(ttl=2)
def carregar_dados():
    try:
        # Lendo abas pelos GIDs (Mais estável que nomes)
        mestra = conn.read(spreadsheet=URL, worksheet="1870828680")
        mestra.columns = [str(c).strip() for c in mestra.columns]
        
        controle = conn.read(spreadsheet=URL, worksheet="0")
        controle.columns = [str(c).strip() for c in controle.columns]
        
        return mestra, controle
    except Exception as e:
        st.error(f"Erro ao conectar: {e}")
        return pd.DataFrame(), pd.DataFrame()

# --- EXECUÇÃO ---
df_mestra, df_controle = carregar_dados()

# Interface lateral sempre visível
st.sidebar.title("MENU COLORTEX")
aba = st.sidebar.radio("Navegação:", ["🚀 Registro", "📊 Banco de Dados", "📈 Gráficos CEP", "⚙️ Configurações"])

if not df_mestra.empty:
    if aba == "🚀 Registro":
        st.title("🚀 Novo Registro de Lote")
        
        with st.form("form_final_v3"):
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
            pesos_entregues = {}
            
            for i, row in formulas.iterrows():
                # Forçamos o valor da mestra a ser número aqui
                f_base = forcar_numero(row['Quant OP (kg)'])
                sugestao = f_base * n_p * l_u * 1000
                pesos_entregues[i] = st.number_input(f"Quant ad (g) - {row['Pigmento']} (Sugerido: {sugestao:.2f}g)", min_value=0.0, format="%.2f")

            if st.form_submit_button("SALVAR NA PLANILHA"):
                if not lote_id:
                    st.error("Preencha o Lote!")
                else:
                    novas_linhas = []
                    for i, row in formulas.iterrows():
                        lit_p, lit_r = n_p * l_u, n_r * l_u
                        f_base = forcar_numero(row['Quant OP (kg)'])
                        util_real = (pesos_entregues[i] / 1000) / lit_r if lit_r > 0 else 0
                        
                        novas_linhas.append({
                            "Data": data_fab.strftime("%d/%m/%Y"),
                            "Lote": lote_id,
                            "Tipo de produto": t_sel,
                            "Cor": c_sel,
                            "Pigmento": row['Pigmento'],
                            "Toque": 1,
                            "Quant ad (g)": pesos_entregues[i],
                            "Quant OP(kg)": f_base * lit_p,
                            "#Plan": n_p,
                            "#Real": n_r,
                            "Litros/Unit": l_u,
                            "Encomenda?": "Não",
                            "Litros Planejados": lit_p,
                            "Litros Produzidos": lit_r,
                            "Formulação (kg/L)": f_base,
                            "Utilizado (kg/L)": util_real,
                            "Variação %": (util_real / f_base) - 1 if f_base > 0 else 0,
                            "Variação ABS": (pesos_entregues[i]/1000) - (lit_r * f_base)
                        })
                    
                    df_final = pd.concat([df_controle, pd.DataFrame(novas_linhas)], ignore_index=True)
                    conn.update(spreadsheet=URL, worksheet="0", data=df_final)
                    st.success("✅ Salvo com Sucesso!")
                    st.cache_data.clear()

    elif aba == "📊 Banco de Dados":
        st.title("📊 Histórico Controle")
        st.dataframe(df_controle)

    elif aba == "📈 Gráficos CEP":
        st.title("📈 Variação %")
        
        if not df_controle.empty:
            df_controle['Variação %'] = df_controle['Variação %'].apply(forcar_numero)
            p_sel = st.selectbox("Selecione o Produto", df_controle['Tipo de produto'].unique())
            df_p = df_controle[df_controle['Tipo de produto'] == p_sel]
            st.line_chart(df_p.pivot_table(index='Lote', columns='Pigmento', values='Variação %'))

    elif aba == "⚙️ Configurações":
        st.title("⚙️ Ajustar Aba Mestra")
        editado = st.data_editor(df_mestra, num_rows="dynamic")
        if st.button("Atualizar Padrões"):
            conn.update(spreadsheet=URL, worksheet="1870828680", data=editado)
            st.success("Mestra atualizada!")
            st.cache_data.clear()
else:
    st.warning("⚠️ Planilha não encontrada ou link sem permissão de Editor.")

import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# Configuração da página
st.set_page_config(page_title="Controle Colortex 2026", layout="wide", page_icon="📊")

# --- LINK DA PLANILHA (Limpo de caracteres invisíveis) ---
URL_PLANILHA = "https://docs.google.com/spreadsheets/d/19OfTga1-LFrsYS4PHcdx3nB3EAgf1oviNvp3qIuwtq8/edit?usp=sharing".strip()

# Conexão
conn = st.connection("gsheets", type=GSheetsConnection)

def tratar_numeros(df):
    """Garante que colunas de peso sejam números, não texto."""
    df.columns = [str(c).strip() for c in df.columns]
    cols_para_fixar = ['Quant OP (kg)', 'Variação %', 'Quant ad (g)', 'Quant OP(kg)']
    for col in cols_para_fixar:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce').fillna(0.0)
    return df

@st.cache_data(ttl=2)
def carregar_tudo():
    try:
        # Lendo as duas abas principais
        mestra = conn.read(spreadsheet=URL_PLANILHA, worksheet="Aba Mestra")
        mestra = tratar_numeros(mestra)
        
        controle = conn.read(spreadsheet=URL_PLANILHA, worksheet="controle")
        controle = tratar_numeros(controle)
        
        return mestra, controle
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return pd.DataFrame(), pd.DataFrame()

# --- INTERFACE ---
df_mestra, df_controle = carregar_tudo()

# Menu Lateral (Isso fará as abas voltarem)
st.sidebar.title("MENU PRINCIPAL")
aba = st.sidebar.radio("Selecione a tarefa:", 
                       ["🚀 Registro de Produção", "📊 Banco de Dados", "📈 Gráficos CEP", "⚙️ Ajustar Aba Mestra"])

if not df_mestra.empty:
    if aba == "🚀 Registro de Produção":
        st.title("🚀 Novo Registro")
        with st.form("meu_form_seguro"):
            c1, c2 = st.columns(2)
            with c1:
                t_sel = st.selectbox("Tipo de Produto", sorted(df_mestra['Tipo de Produto'].unique()))
                c_sel = st.selectbox("Cor", sorted(df_mestra[df_mestra['Tipo de Produto'] == t_sel]['Cor'].unique()))
            with c2:
                lote_id = st.text_input("Lote")
                data_fab = st.date_input("Data", datetime.now())

            v1, v2, v3 = st.columns(3)
            with v1: n_p = st.number_input("#Plan", min_value=1.0, value=1.0)
            with v2: n_r = st.number_input("#Real", min_value=1.0, value=1.0)
            with v3: l_u = st.number_input("Litros/Unit", value=15.0)

            st.divider()
            formulas = df_mestra[(df_mestra['Tipo de Produto'] == t_sel) & (df_mestra['Cor'] == c_sel)]
            pesos_input = {}
            for i, row in formulas.iterrows():
                # Forçamos o cálculo para ser numérico aqui (Evita o erro 'non-int of type float')
                sugestao = float(row['Quant OP (kg)']) * n_p * l_u * 1000
                pesos_input[i] = st.number_input(f"Quant ad (g) - {row['Pigmento']} (Sug: {sugestao:.1f}g)", min_value=0.0)

            # BOTÃO DE SUBMIT (Resolve o erro "Missing Submit Button")
            if st.form_submit_button("GRAVAR NA PLANILHA"):
                if not lote_id:
                    st.error("Preencha o número do lote!")
                else:
                    novas_linhas = []
                    for i, row in formulas.iterrows():
                        lit_p, lit_r = n_p * l_u, n_r * l_u
                        f_base = float(row['Quant OP (kg)'])
                        util = (pesos_input[i] / 1000) / lit_r if lit_r > 0 else 0
                        
                        novas_linhas.append({
                            "Data": data_fab.strftime("%d/%m/%Y"), "Lote": lote_id, "Tipo de produto": t_sel,
                            "Cor": c_sel, "Pigmento": row['Pigmento'], "Toque": 1, "Quant ad (g)": pesos_input[i],
                            "Quant OP(kg)": f_base * lit_p, "#Plan": n_p, "#Real": n_r, "Litros/Unit": l_u,
                            "Encomenda?": "Não", "Litros Planejados": lit_p, "Litros Produzidos": lit_r,
                            "Formulação (kg/L)": f_base, "Utilizado (kg/L)": util,
                            "Variação %": (util / f_base) - 1 if f_base > 0 else 0,
                            "Variação ABS": (pesos_input[i]/1000) - (lit_r * f_base)
                        })
                    
                    df_final = pd.concat([df_controle, pd.DataFrame(novas_linhas)], ignore_index=True)
                    conn.update(spreadsheet=URL_PLANILHA, worksheet="controle", data=df_final)
                    st.success("✅ Lote salvo com sucesso!")
                    st.cache_data.clear()

    elif aba == "📊 Banco de Dados":
        st.title("📊 Histórico Completo")
        st.dataframe(df_controle, use_container_width=True)

    elif aba == "📈 Gráficos CEP":
        st.title("📈 Controle Estatístico")
        if not df_controle.empty:
            p_sel = st.selectbox("Filtrar por Produto", df_controle['Tipo de produto'].unique())
            df_plot = df_controle[df_controle['Tipo de produto'] == p_sel]
            st.line_chart(df_plot.pivot_table(index='Lote', columns='Pigmento', values='Variação %'))

    elif aba == "⚙️ Ajustar Aba Mestra":
        st.title("⚙️ Gerenciar Aba Mestra")
        editado = st.data_editor(df_mestra, num_rows="dynamic")
        if st.button("Salvar Mudanças na Mestra"):
            conn.update(spreadsheet=URL_PLANILHA, worksheet="Aba Mestra", data=editado)
            st.success("Aba Mestra atualizada!")
            st.cache_data.clear()
else:
    st.warning("⚠️ Conectando ao Google Sheets... Se demorar, verifique se o link da planilha está como 'Editor' para 'Qualquer pessoa com o link'.")

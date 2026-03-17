import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# Configuração da página
st.set_page_config(page_title="Controle Colortex 2026", layout="wide")

# URL DA SUA PLANILHA
URL_PLANILHA = "https://docs.google.com/spreadsheets/d/19OfTga1-LFrsYS4PHcdx3nB3EAgf1oviNvp3qIuwtq8/edit?usp=sharing"

# Conexão
conn = st.connection("gsheets", type=GSheetsConnection)

def carregar_mestra():
    # Aba Mestra (GID 1870828680)
    df = conn.read(spreadsheet=URL_PLANILHA, worksheet="1870828680", ttl=0)
    df.columns = [str(c).strip() for c in df.columns]
    
    # CORREÇÃO DO ERRO DE MULTIPLICAÇÃO: Força a coluna Quant OP (kg) a ser número
    if 'Quant OP (kg)' in df.columns:
        df['Quant OP (kg)'] = pd.to_numeric(df['Quant OP (kg)'].astype(str).str.replace(',', '.'), errors='coerce').fillna(0.0)
    return df

def carregar_controle():
    # Aba Controle (GID 0)
    df = conn.read(spreadsheet=URL_PLANILHA, worksheet="0", ttl=0)
    df.columns = [str(c).strip() for c in df.columns]
    return df

# --- APP ---
try:
    df_mestra = carregar_mestra()
    
    st.sidebar.title("Navegação")
    aba = st.sidebar.radio("Ir para:", ["🚀 Registrar Produção", "📊 Banco de Dados"])

    # Nomes das colunas da Mestra
    col_tipo = "Tipo de Produto"
    col_cor = "Cor"
    col_pig = "Pigmento"
    col_quant = "Quant OP (kg)"

    if aba == "🚀 Registrar Produção":
        st.title("🚀 Registro de Pigmentação")
        
        # O formulário PRECISA de um botão de submit no final
        with st.form("form_lote_final"):
            c1, c2 = st.columns(2)
            with c1:
                t_sel = st.selectbox("Tipo de Produto", sorted(df_mestra[col_tipo].unique()))
                c_sel = st.selectbox("Cor", sorted(df_mestra[df_mestra[col_tipo] == t_sel][col_cor].unique()))
            with c2:
                lote_id = st.text_input("Número do Lote")
                data_fab = st.date_input("Data de Fabricação", datetime.now())

            st.divider()
            
            # Filtro das fórmulas
            formulas = df_mestra[(df_mestra[col_tipo] == t_sel) & (df_mestra[col_cor] == c_sel)]
            
            # Volumes
            v1, v2, v3 = st.columns(3)
            with v1: n_plan = st.number_input("#Plan", min_value=1.0, value=1.0, step=1.0)
            with v2: n_real = st.number_input("#Real", min_value=1.0, value=1.0, step=1.0)
            with v3: lit_unit = st.number_input("Litros/Unit", value=15.0, step=0.1)
            
            st.write("### Pesagem (g)")
            pesos_reais = {}
            for i, row in formulas.iterrows():
                # Calcula sugestão para ajudar o operador
                sug_g = float(row[col_quant]) * n_plan * lit_unit * 1000
                pesos_reais[i] = st.number_input(f"Quant ad (g) - {row[col_pig]} (Sug: {sug_g:.2f}g)", min_value=0.0, format="%.2f")

            # BOTÃO DE SALVAR (Resolve o erro "Missing Submit Button")
            submit = st.form_submit_button("SALVAR NA PLANILHA")

            if submit:
                if not lote_id:
                    st.error("Preencha o Lote!")
                else:
                    novas_linhas = []
                    for i, row in formulas.iterrows():
                        lit_p = n_plan * lit_unit
                        lit_r = n_real * lit_unit
                        f_base = float(row[col_quant])
                        util = (pesos_reais[i] / 1000) / lit_r if lit_r > 0 else 0
                        
                        # Estrutura exata da sua aba "Controle"
                        novas_linhas.append({
                            "Data": data_fab.strftime("%d/%m/%Y"),
                            "Lote": lote_id,
                            "Tipo de produto": t_sel,
                            "Cor": c_sel,
                            "Pigmento": row[col_pig],
                            "Toque": 1,
                            "Quant ad (g)": pesos_reais[i],
                            "Quant OP(kg)": f_base * lit_p,
                            "#Plan": n_plan,
                            "#Real": n_real,
                            "Litros/Unit": lit_unit,
                            "Encomenda?": "Não",
                            "Litros Planejados": lit_p,
                            "Litros Produzidos": lit_r,
                            "Formulação (kg/L)": f_base,
                            "Utilizado (kg/L)": util,
                            "Variação %": (util / f_base) - 1 if f_base > 0 else 0,
                            "Variação ABS": (pesos_reais[i]/1000) - (lit_r * f_base)
                        })
                    
                    df_historico = carregar_controle()
                    df_final = pd.concat([df_historico, pd.DataFrame(novas_linhas)], ignore_index=True)
                    
                    conn.update(spreadsheet=URL_PLANILHA, worksheet="0", data=df_final)
                    st.success("✅ Salvo com sucesso no Google Sheets!")
                    st.balloons()

    elif aba == "📊 Banco de Dados":
        st.title("📊 Histórico Controle")
        df_c = carregar_controle()
        st.dataframe(df_c, use_container_width=True)

except Exception as e:
    st.error(f"Erro detectado: {e}")

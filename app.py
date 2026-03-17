import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Controle Colortex 2026", layout="wide")

# URL DA SUA PLANILHA
URL_PLANILHA = "https://docs.google.com/spreadsheets/d/19OfTga1-LFrsYS4PHcdx3nB3EAgf1oviNvp3qIuwtq8/edit?usp=sharing"

# 2. CONEXÃO COM GOOGLE SHEETS
conn = st.connection("gsheets", type=GSheetsConnection)

def carregar_mestra():
    # Carrega a Aba Mestra (GID 1870828680)
    df = conn.read(spreadsheet=URL_PLANILHA, worksheet="1870828680", ttl=0)
    # Remove espaços extras nos nomes das colunas para evitar erros
    df.columns = [str(c).strip() for c in df.columns]
    return df

def carregar_controle():
    # Carrega a primeira aba: "controle" (GID 0)
    df = conn.read(spreadsheet=URL_PLANILHA, worksheet="0", ttl=0)
    df.columns = [str(c).strip() for c in df.columns]
    return df

# --- INÍCIO DO APP ---
try:
    df_mestra = carregar_mestra()
    
    st.sidebar.title("Navegação")
    aba = st.sidebar.radio("Ir para:", ["🚀 Registrar Produção", "📊 Banco de Dados"])

    if aba == "🚀 Registrar Produção":
        st.title("🚀 Registro de Pigmentação")
        
        # DEFINIÇÃO DOS NOMES DAS COLUNAS DA MESTRA CONFORME SUA CORREÇÃO
        col_tipo_mestra = "Tipo de Produto"
        col_cor_mestra = "Cor"
        col_pig_mestra = "Pigmento"
        col_quant_mestra = "Quant OP (kg)"

        with st.form("form_lote"):
            c1, c2 = st.columns(2)
            with c1:
                # Busca na Mestra usando "Tipo de Produto"
                t_sel = st.selectbox("Selecione o Produto", sorted(df_mestra[col_tipo_mestra].unique()))
                c_sel = st.selectbox("Selecione a Cor", sorted(df_mestra[df_mestra[col_tipo_mestra] == t_sel][col_cor_mestra].unique()))
            with c2:
                lote_id = st.text_input("Número do Lote")
                data_fab = st.date_input("Data de Fabricação", datetime.now())

            st.divider()
            
            # Filtra a fórmula baseada na seleção
            formulas = df_mestra[(df_mestra[col_tipo_mestra] == t_sel) & (df_mestra[col_cor_mestra] == c_sel)]
            
            # Inputs de Volume
            v1, v2, v3 = st.columns(3)
            with v1: n_plan = st.number_input("#Plan", min_value=1, value=1)
            with v2: n_real = st.number_input("#Real", min_value=1, value=1)
            with v3: lit_unit = st.number_input("Litros/Unit", value=15.0)
            
            st.write("### Registro de Pesagem (g)")
            pesos_reais = {}
            for i, row in formulas.iterrows():
                # Sugestão baseada na formulação unitária da mestra
                sug_g = row[col_quant_mestra] * n_plan * lit_unit * 1000
                pesos_reais[i] = st.number_input(f"Quant ad (g) - {row[col_pig_mestra]} (Sugerido: {sug_g:.2f}g)", min_value=0.0, format="%.2f")

            # BOTÃO DE SUBMISSÃO (Obrigatório para processar o form)
            submit = st.form_submit_button("SALVAR NA PLANILHA GOOGLE")

            if submit:
                if not lote_id:
                    st.error("Por favor, informe o número do lote!")
                else:
                    novas_linhas = []
                    for i, row in formulas.iterrows():
                        lit_p = n_plan * lit_unit
                        lit_r = n_real * lit_unit
                        f_base = row[col_quant_mestra] # Padrão kg/L
                        util_kgl = (pesos_reais[i] / 1000) / lit_r if lit_r > 0 else 0
                        
                        # ESTRUTURA EXATA DAS COLUNAS DA ABA "CONTROLE"
                        novas_linhas.append({
                            "Data": data_fab.strftime("%d/%m/%Y"),
                            "Lote": lote_id,
                            "Tipo de produto": t_sel,
                            "Cor": c_sel,
                            "Pigmento": row[col_pig_mestra],
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
                            "Utilizado (kg/L)": util_kgl,
                            "Variação %": (util_kgl / f_base) - 1 if f_base > 0 else 0,
                            "Variação ABS": (pesos_reais[i]/1000) - (lit_r * f_base)
                        })
                    
                    # Processo de anexar ao histórico existente
                    df_controle_atual = carregar_controle()
                    df_final = pd.concat([df_controle_atual, pd.DataFrame(novas_linhas)], ignore_index=True)
                    
                    # Atualiza a aba "controle" (Gid 0)
                    conn.update(spreadsheet=URL_PLANILHA, worksheet="0", data=df_final)
                    st.success(f"✅ Lote {lote_id} registrado com sucesso!")
                    st.balloons()

    elif aba == "📊 Banco de Dados":
        st.title("📊 Histórico (Aba Controle)")
        st.dataframe(carregar_controle(), use_container_width=True)

except Exception as e:
    st.error(f"Erro detectado: {e}")
    st.info("Dica: Verifique se os cabeçalhos da Aba Mestra são: Tipo de Produto, Cor, Pigmento, Quant OP (kg)")

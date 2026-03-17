import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# Configuração da página
st.set_page_config(page_title="Controle Colortex 2026", layout="wide", page_icon="🧪")

# URL da sua planilha
URL_PLANILHA = "https://docs.google.com/spreadsheets/d/19OfTga1-LFrsYS4PHcdx3nB3EAgf1oviNvp3qIuwtq8/edit?usp=sharing"

# Conexão
conn = st.connection("gsheets", type=GSheetsConnection)

# --- FUNÇÕES DE TRATAMENTO (O ESCUDO CONTRA ERROS) ---

def limpar_e_converter(df):
    """Garante que colunas numéricas sejam números reais, tratando vírgulas e nulos."""
    if df.empty: return df
    df.columns = [str(c).strip() for c in df.columns]
    
    # Lista de colunas que precisam ser números para não dar erro de multiplicação
    cols_num = ['Quant OP (kg)', 'Quant ad (g)', 'Quantidade OP', '#Plan', '#Real', 'Litros/Unit']
    
    for col in cols_num:
        if col in df.columns:
            # Transforma em string, troca vírgula por ponto e converte para float
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce').fillna(0.0)
    return df

@st.cache_data(ttl=5)
def carregar_dados_sheets():
    try:
        # Lendo abas pelo nome (Certifique-se que os nomes batem no Sheets)
        df_mestra = conn.read(spreadsheet=URL_PLANILHA, worksheet="Aba Mestra")
        df_mestra = limpar_e_converter(df_mestra)
        
        df_controle = conn.read(spreadsheet=URL_PLANILHA, worksheet="controle")
        df_controle = limpar_e_converter(df_controle)
        
        return df_mestra, df_controle
    except Exception as e:
        st.error(f"Erro ao conectar com Google Sheets: {e}")
        return pd.DataFrame(), pd.DataFrame()

# --- CARREGAMENTO INICIAL ---
df_mestra, df_controle = carregar_dados_sheets()

# --- NAVEGAÇÃO ---
st.sidebar.title("MENU COLORTEX")
aba = st.sidebar.radio("Navegação:", ["🚀 Nova Pigmentação", "📈 Variações & CEP", "📋 Histórico de Padrões", "📊 Aba Mestra"])

if not df_mestra.empty:
    if aba == "🚀 Nova Pigmentação":
        st.title("🚀 Registrar Produção")
        
        # Identificação do Lote
        c1, c2, c3 = st.columns(3)
        with c1:
            t_sel = st.selectbox("Produto", sorted(df_mestra['Tipo'].unique()))
            c_sel = st.selectbox("Cor", sorted(df_mestra[df_mestra['Tipo'] == t_sel]['Cor'].unique()))
        with c2:
            lote_id = st.text_input("Número do Lote")
            data_fab = st.date_input("Data de Fabricação", datetime.now())
        with c3:
            encomenda = st.selectbox("📦 Encomenda?", ["Não", "Sim"])

        # Volumes
        v1, v2, v3 = st.columns(3)
        with v1: n_p = st.number_input("#Unid Plan", min_value=1.0, value=1.0)
        with v2: n_r = st.number_input("#Unid Real", min_value=1.0, value=1.0)
        with v3: 
            l_u = st.number_input("Litros/Unit", value=15.0)

        vol_p_tot = n_p * l_u
        vol_r_tot = n_r * l_u
        st.info(f"Volume Planejado: {vol_p_tot:.2f}L | Volume Real: {vol_r_tot:.2f}L")

        st.divider()
        formulas = df_mestra[(df_mestra['Tipo'] == t_sel) & (df_mestra['Cor'] == c_sel)]
        pesos_inputs = {}

        for i, row in formulas.iterrows():
            pigm = row['Pigmento']
            coef = float(row['Quant OP (kg)'])
            sugestao_g = coef * vol_p_tot * 1000
            
            st.markdown(f"### {pigm}")
            col_info, col_input = st.columns([1, 2])
            col_info.write(f"Padrão: {coef:.6f} kg/L\n\n**Sugestão: {sugestao_g:.2f}g**")
            pesos_inputs[i] = col_input.number_input(f"Quantidade Adicionada (g) - {pigm}", min_value=0.0, format="%.2f", key=f"p_{i}")
            st.markdown("---")

        marcar_p = st.checkbox("⚠️ Atualizar Padrão Técnico na Aba Mestra?")

        if st.button("✅ FINALIZAR E GRAVAR NO GOOGLE SHEETS", use_container_width=True):
            if not lote_id:
                st.error("Por favor, informe o Lote!")
            else:
                novas_linhas = []
                alteracoes_padrao = []
                
                for i, row in formulas.iterrows():
                    f_base = float(row['Quant OP (kg)'])
                    util_real_kgl = (pesos_inputs[i] / 1000) / vol_r_tot if vol_r_tot > 0 else 0
                    
                    # Linha para o histórico
                    novas_linhas.append({
                        "data": data_fab.strftime("%d/%m/%Y"), "lote": lote_id, "tipo de produto": t_sel,
                        "cor": c_sel, "pigmento": row['Pigmento'], "toque": 1, "Quant ad (g)": pesos_inputs[i],
                        "Quantidade OP": f_base * vol_p_tot, "#Plan": n_p, "#Real": n_r, 
                        "Encomenda?": encomenda, "Litros/Unit": l_u
                    })

                    if marcar_p:
                        # Se marcar para atualizar, mudamos o coeficiente na Mestra
                        df_mestra.loc[(df_mestra['Tipo'] == t_sel) & (df_mestra['Cor'] == c_sel) & (df_mestra['Pigmento'] == row['Pigmento']), 'Quant OP (kg)'] = util_real_kgl
                        alteracoes_padrao.append({
                            "Data Alteração": datetime.now().strftime("%d/%m/%Y"), "Data Fabricação": data_fab.strftime("%d/%m/%Y"),
                            "Produto": t_sel, "Cor": c_sel, "Pigmento": row['Pigmento'], "Novo Coef (kg/L)": util_real_kgl, "Lote Origem": lote_id
                        })

                # --- UPLOAD PARA O GOOGLE SHEETS ---
                # 1. Atualiza Controle
                df_controle_atualizado = pd.concat([df_controle, pd.DataFrame(novas_linhas)], ignore_index=True)
                conn.update(spreadsheet=URL_PLANILHA, worksheet="controle", data=df_controle_atualizado)
                
                # 2. Se houve alteração de padrão, atualiza Aba Mestra e Log de Padrões
                if marcar_p:
                    conn.update(spreadsheet=URL_PLANILHA, worksheet="Aba Mestra", data=df_mestra)
                    # Tenta ler aba de padrões ou cria se não existir
                    try:
                        df_p_antigo = conn.read(spreadsheet=URL_PLANILHA, worksheet="Padroes")
                        df_p_novo = pd.concat([df_p_antigo, pd.DataFrame(alteracoes_padrao)], ignore_index=True)
                        conn.update(spreadsheet=URL_PLANILHA, worksheet="Padroes", data=df_p_novo)
                    except:
                        conn.update(spreadsheet=URL_PLANILHA, worksheet="Padroes", data=pd.DataFrame(alteracoes_padrao))

                st.success("✅ Dados sincronizados com o Google Sheets!")
                st.balloons()
                st.cache_data.clear()

    elif aba == "📈 Variações & CEP":
        st.title("📈 Controle Estatístico")
        
        if not df_controle.empty:
            p_sel = st.selectbox("Produto", df_controle['tipo de produto'].unique())
            df_plot = df_controle[df_controle['tipo de produto'] == p_sel]
            # Cálculo de desvio simples para o gráfico
            df_plot['Desvio %'] = ((df_plot['Quant ad (g)'] / (df_plot['Quantidade OP'] * 1000 + 0.00001)) - 1) * 100
            st.line_chart(df_plot.pivot_table(index='lote', columns='pigmento', values='Desvio %'))
        else:
            st.info("Histórico vazio.")

    elif aba == "📊 Aba Mestra":
        st.title("📊 Gestão Aba Mestra")
        df_edit = st.data_editor(df_mestra, num_rows="dynamic")
        if st.button("💾 Salvar Alterações na Nuvem"):
            conn.update(spreadsheet=URL_PLANILHA, worksheet="Aba Mestra", data=df_edit)
            st.success("Aba Mestra atualizada no Google Sheets!")
            st.cache_data.clear()

else:
    st.warning("⚠️ Verifique se o link da planilha está como 'Editor' e os nomes das abas estão corretos.")

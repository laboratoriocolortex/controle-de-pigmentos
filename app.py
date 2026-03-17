import streamlit as st
import pandas as pd
import os
from datetime import datetime

# 1. Configuração e Estilo
st.set_page_config(page_title="Colortex 2026 - Controle de Produção", layout="wide")

# --- FUNÇÕES DE APOIO ---

def carregar_dados(arquivo):
    if not os.path.exists(arquivo):
        return pd.DataFrame()
    try:
        # Tenta carregar com fallback de codificação
        try:
            df = pd.read_csv(arquivo, sep=None, engine='python', encoding='latin-1')
        except:
            df = pd.read_csv(arquivo, sep=None, engine='python', encoding='utf-8')
        
        # Limpeza de nomes e acentos (Oxido -> Óxido / Franca -> França)
        df.columns = [str(c).strip() for c in df.columns]
        traducoes = {'Oxido': 'Óxido', 'Franca': 'França', 'oxido': 'óxido', 'franca': 'frança'}
        for col in df.select_dtypes(include=['object']).columns:
            df[col] = df[col].astype(str).str.strip().replace(traducoes, regex=True).str.title()
        return df
    except:
        return pd.DataFrame()

def salvar_csv(df, arquivo):
    df.to_csv(arquivo, index=False, encoding='latin-1')

# --- CARREGAMENTO ---
df_mestra = carregar_dados("Aba_Mestra.csv")
df_hist = carregar_dados("Historico_Producao.csv")
df_padr = carregar_dados("Padroes_Registrados.csv")

# --- MENU ---
menu = ["🚀 Registrar Produção", "📈 Gráficos CEP", "📋 Evolução Padrões", "📜 Banco de Dados", "➕ Cadastro de Produtos", "📊 Editor Aba Mestra", "📂 Importar CSV"]
aba = st.sidebar.radio("Navegação", menu)

# --- 🚀 REGISTRAR PRODUÇÃO (RECONSTRUÍDO) ---
if aba == "🚀 Registrar Produção":
    st.title("🚀 Registro de Pigmentação")
    if df_mestra.empty:
        st.warning("⚠️ Importe a 'Aba Mestra' para liberar o registro.")
    else:
        # Filtros de seleção
        c1, c2, c3, c4 = st.columns([1.5, 1.5, 1, 1])
        with c1: t_sel = st.selectbox("Produto", sorted(df_mestra['Tipo'].unique()))
        with c2: c_sel = st.selectbox("Cor", sorted(df_mestra[df_mestra['Tipo'] == t_sel]['Cor'].unique()))
        with c3: lote = st.text_input("Lote")
        with c4: data_f = st.date_input("Data", datetime.now())

        # Configuração de Volumes
        v1, v2, v3 = st.columns(3)
        with v1: n_p = st.number_input("# Unid Plan", min_value=1.0, value=1.0)
        with v2: n_r = st.number_input("# Unid Real", min_value=1.0, value=1.0)
        with v3: vol_u = st.number_input("Litros por Unidade", value=15.0)

        vol_p_tot = n_p * vol_u
        
        # BUSCAR FÓRMULA
        formula = df_mestra[(df_mestra['Tipo'] == t_sel) & (df_mestra['Cor'] == c_sel)]
        st.divider()
        
        pesos_inputs = []
        if not formula.empty:
            st.subheader(f"🎨 Pesagem: {t_sel} - {c_sel}")
            for i, row in formula.iterrows():
                pigm = row['Pigmento']
                coef = float(str(row['Quant OP (kg)']).replace(',', '.'))
                sugestao = round(coef * vol_p_tot * 1000, 2) # g
                
                peso = st.number_input(f"Adicionar {pigm} (Sugestão: {sugestao}g)", min_value=0.0, format="%.2f", key=f"p_{i}")
                pesos_inputs.append({"pigmento": pigm, "peso": peso, "op": sugestao/1000})

            marcar_p = st.checkbox("Atualizar Padrão Técnico na Aba Mestra?")
            
            if st.button("✅ GRAVAR PRODUÇÃO"):
                novos_registros = []
                for item in pesos_inputs:
                    novos_registros.append({
                        "data": data_f.strftime("%d/%m/%Y"), "lote": lote, "tipo de produto": t_sel,
                        "cor": c_sel, "pigmento": item['pigmento'], "Quant ad (g)": item['peso'],
                        "Quantidade OP": item['op'], "#Plan": n_p, "#Real": n_r, "Litros/Unit": vol_u
                    })
                
                df_hist = pd.concat([df_hist, pd.DataFrame(novos_registros)], ignore_index=True)
                salvar_csv(df_hist, "Historico_Producao.csv")
                st.success("Lote gravado com sucesso!")

# --- 📈 GRÁFICOS CEP (SEPARADO POR PRODUTO/COR) ---
elif aba == "📈 Gráficos CEP":
    st.title("📈 Análise de Desvios (CEP)")
    if df_hist.empty:
        st.info("Sem dados no histórico.")
    else:
        # Filtros do Gráfico
        f1, f2 = st.columns(2)
        with f1: p_filt = st.selectbox("Filtrar Produto", sorted(df_hist['tipo de produto'].unique()))
        with f2: c_filt = st.selectbox("Filtrar Cor", sorted(df_hist[df_hist['tipo de produto'] == p_filt]['cor'].unique()))
        
        df_view = df_hist[(df_hist['tipo de produto'] == p_filt) & (df_hist['cor'] == c_filt)].copy()
        
        if not df_view.empty:
            # Cálculos de desvio
            df_view['Quant ad (g)'] = pd.to_numeric(df_view['Quant ad (g)'], errors='coerce')
            df_view['Quantidade OP'] = pd.to_numeric(df_view['Quantidade OP'], errors='coerce')
            df_view['Desvio_%'] = ((df_view['Quant ad (g)'] / (df_view['Quantidade OP'] * 1000 + 0.00001)) - 1) * 100
            
            # GRÁFICO SEPARADO POR PIGMENTO
            pivot_cep = df_view.pivot_table(index='lote', columns='pigmento', values='Desvio_%')
            st.line_chart(pivot_cep)
            st.dataframe(df_view)

# --- ➕ CADASTRO DE PRODUTOS (RESTAURADO) ---
elif aba == "➕ Cadastro de Produtos":
    st.title("➕ Cadastrar Nova Fórmula")
    with st.form("cad_novo"):
        c1, c2 = st.columns(2)
        with c1: t = st.text_input("Tipo de Produto (Ex: Acetinado)")
        with c2: c = st.text_input("Cor (Ex: Azul França)")
        p = st.text_input("Pigmento (Ex: Óxido Amarelo)")
        q = st.number_input("Coeficiente (kg/L)", format="%.6f")
        
        if st.form_submit_button("Salvar na Aba Mestra"):
            novo = pd.DataFrame([{"Tipo": t, "Cor": c, "Pigmento": p, "Quant OP (kg)": q}])
            df_mestra = pd.concat([df_mestra, novo], ignore_index=True)
            salvar_csv(df_mestra, "Aba_Mestra.csv")
            st.success("Produto cadastrado!")

# --- 📂 IMPORTAR CSV (SANEAMENTO ÓXIDO/FRANÇA) ---
elif aba == "📂 Importar CSV":
    st.title("📂 Importar Planilhas")
    up = st.file_uploader("Selecione o arquivo", type="csv")
    alvo = st.selectbox("Salvar em:", ["Aba_Mestra.csv", "Historico_Producao.csv"])
    if up and st.button("Confirmar Importação"):
        df_imp = pd.read_csv(up, encoding='latin-1', sep=None, engine='python')
        # Aplica a limpeza de acentos na importação
        df_imp.columns = [str(c).strip() for c in df_imp.columns]
        traducoes = {'Oxido': 'Óxido', 'Franca': 'França'}
        for col in df_imp.select_dtypes(include=['object']).columns:
            df_imp[col] = df_imp[col].astype(str).str.replace('Oxido', 'Óxido').str.replace('Franca', 'França')
        
        salvar_csv(df_imp, alvo)
        st.success("Importado e Saneado!")
        st.rerun()

# --- OUTRAS ABAS ---
elif aba == "📜 Banco de Dados":
    st.dataframe(df_hist)
    if st.button("Limpar Histórico"):
        if os.path.exists("Historico_Producao.csv"): os.remove("Historico_Producao.csv")
        st.rerun()

elif aba == "📊 Editor Aba Mestra":
    ed = st.data_editor(df_mestra, num_rows="dynamic")
    if st.button("Salvar Edição"):
        salvar_csv(ed, "Aba_Mestra.csv")
        st.success("Salvo!")

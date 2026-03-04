import streamlit as st
import pandas as pd
import os
from datetime import datetime
import numpy as np

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Controle de Pigmentos 2026", layout="wide", page_icon="🧪")

# --- ESTILO CSS PARA MELHORAR VISUALIZAÇÃO ---
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; border: 1px solid #e0e0e0; }
    div.stButton > button:first-child {
        background-color: #28a745; color: white; font-weight: bold; height: 3em; border-radius: 5px;
    }
    .titulo-secao { color: #1f4e79; font-weight: bold; border-bottom: 2px solid #1f4e79; padding-bottom: 5px; }
    </style>
    """, unsafe_allow_html=True)

# 2. FUNÇÕES DE CARREGAMENTO E PROCESSAMENTO
def load_mestra():
    file = "Aba_Mestra.csv"
    if os.path.exists(file):
        try:
            df = pd.read_csv(file, sep=None, engine='python', encoding='latin-1')
            df.columns = [str(c).strip() for c in df.columns]
            if "Quant OP (kg)" in df.columns:
                df["Quant OP (kg)"] = pd.to_numeric(df["Quant OP (kg)"].astype(str).str.replace(',', '.'), errors='coerce').fillna(0.0)
            return df
        except:
            return pd.DataFrame()
    return pd.DataFrame()

def salvar_registro_total(lista_lote, df_mestra):
    hist_path = "Historico_Producao.csv"
    df_novo = pd.DataFrame(lista_lote)
    
    # Cálculos Automáticos de Volume (L e M)
    df_novo['Volume Planejado'] = df_novo['#Plan'] * df_novo['Litros/Unit']
    df_novo['volume produzido'] = df_novo['#Real'] * df_novo['Litros/Unit']
    
    # Cruzamento com a Mestra para buscar a Formulação Padrão (N)
    df_novo = pd.merge(
        df_novo, 
        df_mestra[['Tipo', 'Cor', 'Pigmento', 'Quant OP (kg)']], 
        left_on=['tipo de produto', 'cor', 'pigmento'], 
        right_on=['Tipo', 'Cor', 'Pigmento'], 
        how='left'
    )
    
    # Cálculos Técnicos (O, P e Q)
    df_novo['Formulação'] = df_novo['Quant OP (kg)_y']
    # Consumo Real (kg/L) = (Gramas / 1000) / Volume Real
    df_novo['consumo real (kg/L)'] = (df_novo['Quant ad (g_num)'] / 1000) / df_novo['volume produzido'].replace(0, 1)
    # Variação % = (Real / Padrão) - 1
    df_novo['variação %'] = (df_novo['consumo real (kg/L)'] / df_novo['Formulação'].replace(0, np.nan)) - 1
    # Variação Absoluta = Peso Real - (Volume Real * Coeficiente Padrão)
    df_novo['variação absoluta'] = (df_novo['Quant ad (g_num)'] / 1000) - (df_novo['volume produzido'] * df_novo['Formulação'].fillna(0))

    # Seleção e Ordenação Final das Colunas (A até Q + extras)
    cols_aq = [
        'data', 'lote', 'tipo de produto', 'cor', 'pigmento', 'toque', 
        'Quant ad (g_num)', 'Quantidade OP', '#Plan', '#Real', 'Encomenda?', 'Litros/Unit',
        'Volume Planejado', 'volume produzido', 'Formulação', 'consumo real (kg/L)', 'variação %', 'variação absoluta'
    ]
    
    df_final = df_novo[cols_aq]
    
    # Salva mantendo o histórico anterior
    if os.path.exists(hist_path):
        try:
            hist_old = pd.read_csv(hist_path, sep=';', encoding='latin-1', decimal=',')
            df_final = pd.concat([hist_old, df_final], ignore_index=True)
        except:
            pass
    
    df_final.to_csv(hist_path, index=False, sep=';', encoding='latin-1', decimal=',')

# 3. INTERFACE DE NAVEGAÇÃO
df_mestra = load_mestra()
menu = ["🚀 Nova Pigmentação", "📈 Variações & CEP", "📜 Banco de Dados", "📊 Aba Mestra"]
aba = st.sidebar.radio("Navegação:", menu)

# --- ABA 1: REGISTRO ---
if aba == "🚀 Nova Pigmentação":
    st.title("🚀 Registrar Produção")
    if df_mestra.empty:
        st.error("Erro: Arquivo 'Aba_Mestra.csv' não encontrado ou vazio.")
    else:
        with st.container():
            c1, c2, c3 = st.columns(3)
            with c1: t_sel = st.selectbox("Produto", sorted(df_mestra['Tipo'].unique()))
            with c2: c_sel = st.selectbox("Cor", sorted(df_mestra[df_mestra['Tipo'] == t_sel]['Cor'].unique()))
            with c3: lote_id = st.text_input("Nº do Lote", placeholder="Digite o lote...")

            c4, c5, c6 = st.columns(3)
            with c4: n_p = st.number_input("Unidades Planejadas", min_value=1, value=1)
            with c5: n_r = st.number_input("Unidades Reais (Envase)", min_value=1, value=1)
            with c6: lit = st.number_input("Litros por Unidade", value=15.0, step=0.1)

        st.markdown("### 🎨 Pesagem de Pigmentos")
        formulas = df_mestra[(df_mestra['Tipo'] == t_sel) & (df_mestra['Cor'] == c_sel)]
        lista_registro = []
        
        for i, row in formulas.iterrows():
            rec_g = row["Quant OP (kg)"] * n_p * lit * 1000
            with st.expander(f"Pigmento: {row['Pigmento']}", expanded=True):
                col_info, col_input = st.columns([1, 2])
                col_info.metric("Sugestão (g)", f"{rec_g:.2f}g")
                g_real = col_input.number_input(f"Peso Real (g) - {row['Pigmento']}", key=f"p_{i}", format="%.2f", min_value=0.0)
                
                lista_registro.append({
                    "data": datetime.now().strftime("%d/%m/%Y"), "lote": lote_id, 
                    "tipo de produto": t_sel, "cor": c_sel, "pigmento": row['Pigmento'],
                    "toque": 1, "Quant ad (g_num)": g_real, "Quantidade OP": rec_g,
                    "#Plan": n_p, "#Real": n_r, "Encomenda?": "Não", "Litros/Unit": lit
                })

        if st.button("✅ FINALIZAR E SALVAR REGISTRO"):
            if not lote_id:
                st.error("Por favor, informe o número do lote.")
            else:
                salvar_registro_total(lista_registro, df_mestra)
                st.success(f"Lote {lote_id} registrado com sucesso!")
                st.balloons()

# --- ABA 2: BANCO DE DADOS E CÁLCULOS ---
elif aba == "📜 Banco de Dados":
    st.title("📜 Histórico e Resultados Técnicos")
    
    if os.path.exists("Historico_Producao.csv"):
        df_h = pd.read_csv("Historico_Producao.csv", sep=';', encoding='latin-1', decimal=',')
        
        # --- SEÇÃO SUPERIOR: DADOS DE PRODUÇÃO (A-L) ---
        st.markdown("<h3 class='titulo-secao'>📋 Dados de Produção (A-L)</h3>", unsafe_allow_html=True)
        cols_producao = ['data', 'lote', 'tipo de produto', 'cor', 'pigmento', 'Quant ad (g_num)', 'Quantidade OP', '#Plan', '#Real', 'Litros/Unit']
        st.dataframe(df_h[cols_producao].rename(columns={'Quant ad (g_num)': 'Quant ad (g)'}), use_container_width=True)
        
        # --- SEÇÃO INFERIOR: RESULTADOS DOS CÁLCULOS (M-Q) ---
        st.markdown("<h3 class='titulo-secao'>🧪 Resultados dos Cálculos Técnicos (M-Q)</h3>", unsafe_allow_html=True)
        
        lote_f = st.selectbox("Filtrar por Lote específico:", ["Todos"] + list(df_h['lote'].unique()))
        df_tec = df_h if lote_f == "Todos" else df_h[df_h['lote'] == lote_f]
        
        cols_tecnicas = ['lote', 'pigmento', 'Volume Planejado', 'volume produzido', 'Formulação', 'consumo real (kg/L)', 'variação %', 'variação absoluta']
        
        st.dataframe(
            df_tec[cols_tecnicas].style.format({
                'variação %': '{:.2%}',
                'consumo real (kg/L)': '{:.6f}',
                'Formulação': '{:.6f}',
                'variação absoluta': '{:.3f} kg'
            }), use_container_width=True
        )
        
        # Exportação
        csv_final = df_h.to_csv(index=False, sep=';', decimal=',', encoding='latin-1').encode('latin-1')
        st.download_button("📥 Baixar Planilha Completa (A-Q)", csv_final, "Relatorio_Controle_Pigmentos.csv", "text/csv")
    else:
        st.info("Nenhum registro encontrado. Vá em 'Nova Pigmentação' para começar.")

# --- ABA 3: CEP ---
elif aba == "📈 Variações & CEP":
    st.title("📈 Gráfico de Controle Estatístico (CEP)")
    
    if os.path.exists("Historico_Producao.csv"):
        df_h = pd.read_csv("Historico_Producao.csv", sep=';', encoding='latin-1', decimal=',')
        
        prod_sel = st.selectbox("Selecione o Produto para Análise", df_h['tipo de produto'].unique())
        df_plot = df_h[df_h['tipo de produto'] == prod_sel]
        
        st.subheader(f"Tendência de Variação % - {prod_sel}")
        # Pivot para o gráfico: X = Lote, Linhas = Pigmentos, Y = Variação %
        try:
            chart_data = df_plot.pivot_table(index='lote', columns='pigmento', values='variação %')
            st.line_chart(chart_data)
            st.caption("A linha central (0%) representa a meta ideal conforme a Aba Mestra.")
        except:
            st.warning("Dados insuficientes para gerar o gráfico deste produto.")
    else:
        st.error("Histórico não encontrado.")

# --- ABA 4: ABA MESTRA ---
elif aba == "📊 Aba Mestra":
    st.title("📊 Gestão da Aba Mestra (Padrões)")
    if not df_mestra.empty:
        st.info("Os valores de 'Quant OP (kg)' representam a quantidade de pigmento para 1 Litro de tinta base.")
        df_edit = st.data_editor(df_mestra, num_rows="dynamic", use_container_width=True)
        if st.button("💾 SALVAR ALTERAÇÕES NA MESTRA"):
            df_edit.to_csv("Aba_Mestra.csv", index=False, encoding='latin-1')
            st.success("Aba Mestra atualizada!")
    else:
        st.warning("Arquivo Aba_Mestra.csv não detectado.")

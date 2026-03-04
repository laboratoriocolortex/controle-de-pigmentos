import streamlit as st
import pandas as pd
import os
from datetime import datetime
import numpy as np

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Gestão de Produção 2026", layout="wide", page_icon="🧪")

# --- ESTILO CSS PARA INTERFACE ---
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; border: 1px solid #dce1e6; }
    div.stButton > button:first-child {
        background-color: #007bff; color: white; font-weight: bold; height: 3em; border-radius: 8px;
    }
    .titulo-tabela { color: #2c3e50; font-weight: bold; border-left: 5px solid #007bff; padding-left: 10px; margin-top: 20px; }
    </style>
    """, unsafe_allow_html=True)

# 2. MOTOR DE DADOS (CRIAÇÃO E CÁLCULO)
def inicializar_base_dados():
    """Cria os ficheiros CSV se não existirem no diretório"""
    if not os.path.exists("Aba_Mestra.csv"):
        # Estrutura inicial da Aba Mestra (Padrões)
        df_mestra_init = pd.DataFrame(columns=['Tipo', 'Cor', 'Pigmento', 'Quant OP (kg)'])
        df_mestra_init.to_csv("Aba_Mestra.csv", index=False, encoding='latin-1')

def load_data():
    inicializar_base_dados()
    try:
        df = pd.read_csv("Aba_Mestra.csv", encoding='latin-1')
        df['Quant OP (kg)'] = pd.to_numeric(df['Quant OP (kg)'].astype(str).str.replace(',', '.'), errors='coerce').fillna(0.0)
        return df
    except:
        return pd.DataFrame(columns=['Tipo', 'Cor', 'Pigmento', 'Quant OP (kg)'])

def processar_e_salvar(lista_lote, df_mestra):
    hist_path = "Historico_Producao.csv"
    df_novo = pd.DataFrame(lista_lote)
    
    # --- CÁLCULOS TÉCNICOS AUTOMÁTICOS (COLUNAS L ATÉ Q) ---
    # L e M: Volumes
    df_novo['Volume Planejado'] = df_novo['#Plan'] * df_novo['Litros/Unit']
    df_novo['volume produzido'] = df_novo['#Real'] * df_novo['Litros/Unit']
    
    # N: Busca Formulação na Mestra
    df_novo = pd.merge(
        df_novo, 
        df_mestra[['Tipo', 'Cor', 'Pigmento', 'Quant OP (kg)']], 
        left_on=['tipo de produto', 'cor', 'pigmento'], 
        right_on=['Tipo', 'Cor', 'Pigmento'], 
        how='left'
    )
    df_novo['Formulação'] = df_novo['Quant OP (kg)_y']
    
    # O: Consumo Real (kg/L)
    df_novo['consumo real (kg/L)'] = (df_novo['Quant ad (g_num)'] / 1000) / df_novo['volume produzido'].replace(0, 1)
    
    # P: Variação Percentual
    df_novo['variação %'] = (df_novo['consumo real (kg/L)'] / df_novo['Formulação'].replace(0, np.nan)) - 1
    
    # Q: Variação Absoluta (kg)
    df_novo['variação absoluta'] = (df_novo['Quant ad (g_num)'] / 1000) - (df_novo['volume produzido'] * df_novo['Formulação'].fillna(0))

    # Seleção da estrutura A-Q completa
    cols_finais = [
        'data', 'lote', 'tipo de produto', 'cor', 'pigmento', 'toque', 
        'Quant ad (g_num)', 'Quantidade OP', '#Plan', '#Real', 'Encomenda?', 'Litros/Unit',
        'Volume Planejado', 'volume produzido', 'Formulação', 'consumo real (kg/L)', 'variação %', 'variação absoluta'
    ]
    
    df_final = df_novo[cols_finais]
    
    # Guardar mantendo o histórico
    if os.path.exists(hist_path):
        try:
            hist_antigo = pd.read_csv(hist_path, sep=';', encoding='latin-1', decimal=',')
            df_final = pd.concat([hist_antigo, df_final], ignore_index=True)
        except:
            pass
            
    df_final.to_csv(hist_path, index=False, sep=';', encoding='latin-1', decimal=',')

# 3. INTERFACE STREAMLIT
df_mestra = load_data()
menu = ["🚀 Produção", "📊 Banco de Dados & Cálculos", "📈 Gráficos CEP", "⚙️ Configurações (Mestra)"]
aba = st.sidebar.radio("Menu de Navegação:", menu)

# --- ABA: REGISTRO DE PRODUÇÃO ---
if aba == "🚀 Produção":
    st.title("🚀 Novo Registro de Produção")
    
    if df_mestra.empty:
        st.warning("⚠️ A Aba Mestra está vazia. Cadastre os produtos nas 'Configurações' primeiro.")
    else:
        with st.form("reg_lote"):
            c1, c2, c3 = st.columns(3)
            with c1: t_sel = st.selectbox("Produto", sorted(df_mestra['Tipo'].unique()))
            with c2: c_sel = st.selectbox("Cor", sorted(df_mestra[df_mestra['Tipo'] == t_sel]['Cor'].unique()))
            with c3: lote_id = st.text_input("Número do Lote")

            c4, c5, c6 = st.columns(3)
            with c4: n_p = st.number_input("Unid. Planejadas", min_value=1, value=1)
            with c5: n_r = st.number_input("Unid. Reais (Envase)", min_value=1, value=1)
            with c6: lit = st.number_input("Litros/Unidade", value=15.0)
            
            st.divider()
            formulas = df_mestra[(df_mestra['Tipo'] == t_sel) & (df_mestra['Cor'] == c_sel)]
            inputs_pesagem = {}
            
            for i, row in formulas.iterrows():
                sugestao = row["Quant OP (kg)"] * n_p * lit * 1000
                inputs_pesagem[i] = st.number_input(f"Peso Real (g) - {row['Pigmento']} [Sugestão: {sugestao:.2f}g]", min_value=0.0, format="%.2f")

            if st.form_submit_button("FINALIZAR E CALCULAR"):
                if not lote_id:
                    st.error("Erro: O número do lote é obrigatório.")
                else:
                    dados_lote = []
                    for i, row in formulas.iterrows():
                        dados_lote.append({
                            "data": datetime.now().strftime("%d/%m/%Y"), "lote": lote_id, 
                            "tipo de produto": t_sel, "cor": c_sel, "pigmento": row['Pigmento'],
                            "toque": 1, "Quant ad (g_num)": inputs_pesagem[i], 
                            "Quantidade OP": row["Quant OP (kg)"] * n_p * lit * 1000,
                            "#Plan": n_p, "#Real": n_r, "Encomenda?": "Não", "Litros/Unit": lit
                        })
                    processar_e_salvar(dados_lote, df_mestra)
                    st.success("Lote registado e cálculos A-Q arquivados!")

# --- ABA: BANCO DE DADOS E CÁLCULOS ---
elif aba == "📊 Banco de Dados & Cálculos":
    st.title("📊 Histórico Completo (A-Q)")
    
    if os.path.exists("Historico_Producao.csv"):
        df_h = pd.read_csv("Historico_Producao.csv", sep=';', encoding='latin-1', decimal=',')
        
        st.markdown("<div class='titulo-tabela'>Cálculos Técnicos e Variações</div>", unsafe_allow_html=True)
        # Formatação para visualização
        st.dataframe(df_h.style.format({
            'variação %': '{:.2%}',
            'consumo real (kg/L)': '{:.6f}',
            'Formulação': '{:.6f}',
            'Volume Planejado': '{:.1f} L',
            'volume produzido': '{:.1f} L'
        }), use_container_width=True)
        
        st.download_button("📥 Descarregar CSV Completo", df_h.to_csv(index=False, sep=';', decimal=',').encode('latin-1'), "historico_producao_final.csv")
    else:
        st.info("Ainda não existem registos no sistema.")

# --- ABA: CEP ---
elif aba == "📈 Gráficos CEP":
    st.title("📈 Controlo Estatístico de Processo")
    if os.path.exists("Historico_Producao.csv"):
        df_h = pd.read_csv("Historico_Producao.csv", sep=';', encoding='latin-1', decimal=',')
        prod_f = st.selectbox("Filtrar por Produto", df_h['tipo de produto'].unique())
        df_plot = df_h[df_h['tipo de produto'] == prod_f]
        
        st.line_chart(df_plot.pivot_table(index='lote', columns='pigmento', values='variação %'))
    else:
        st.error("Sem dados para gerar gráficos.")

# --- ABA: CONFIGURAÇÃO ---
elif aba == "⚙️ Configurações (Mestra)":
    st.title("⚙️ Gestão da Aba Mestra")
    st.write("Adicione aqui os produtos e os coeficientes padrão (kg por Litro).")
    
    # Editor de dados interativo
    df_edit = st.data_editor(df_mestra, num_rows="dynamic", use_container_width=True)
    
    if st.button("💾 Guardar Alterações na Mestra"):
        df_edit.to_csv("Aba_Mestra.csv", index=False, encoding='latin-1')
        st.success("Aba Mestra atualizada com sucesso!")

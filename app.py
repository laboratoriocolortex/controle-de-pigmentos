import streamlit as st
import pandas as pd
import os
from datetime import datetime

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Controle de Produção 2026", layout="wide", page_icon="🧪")

# --- FUNÇÕES DE ARQUIVO (SISTEMA DE PERSISTÊNCIA) ---

def carregar_mestra():
    """Lê a Aba Mestra do disco. Se não existir, cria uma vazia."""
    file = "Aba_Mestra.csv"
    if not os.path.exists(file):
        df = pd.DataFrame(columns=['Tipo', 'Cor', 'Pigmento', 'Quant_OP_kg'])
        df.to_csv(file, index=False, encoding='utf-8-sig')
        return df
    try:
        df = pd.read_csv(file, encoding='utf-8-sig')
        # Garante que números sejam lidos corretamente
        df['Quant_OP_kg'] = pd.to_numeric(df['Quant_OP_kg'].astype(str).str.replace(',', '.'), errors='coerce').fillna(0.0)
        return df
    except:
        return pd.DataFrame(columns=['Tipo', 'Cor', 'Pigmento', 'Quant_OP_kg'])

def carregar_historico():
    """Lê o histórico do disco."""
    file = "Historico_Producao.csv"
    if not os.path.exists(file):
        return pd.DataFrame()
    try:
        return pd.read_csv(file, sep=';', encoding='utf-8-sig', decimal=',')
    except:
        return pd.DataFrame()

def salvar_historico_fisico(df_novos):
    """Anexa novos dados ao arquivo CSV sem apagar o que já existe."""
    file = "Historico_Producao.csv"
    
    # Definição das colunas A-Q (Estrutura Completa)
    cols_aq = [
        'Data_Fabricacao', 'Lote', 'Tipo_Produto', 'Cor', 'Pigmento', 'Toque', 
        'Quant_ad_g', 'Quantidade_OP_g', 'Unid_Plan', 'Unid_Real', 
        'Encomenda', 'Litros_Unit', 'Vol_Plan', 'Vol_Real', 
        'Formula_kgL', 'Consumo_Real_kgL', 'Variacao_Perc', 'Variacao_Abs_kg'
    ]
    
    df_novos = df_novos[cols_aq]

    if os.path.exists(file):
        df_antigo = carregar_historico()
        df_final = pd.concat([df_antigo, df_novos], ignore_index=True)
    else:
        df_final = df_novos
    
    # Gravação robusta: separador ; e decimal , (Padrão Excel BR)
    df_final.to_csv(file, index=False, sep=';', encoding='utf-8-sig', decimal=',')
    return True

# --- INTERFACE ---

# Carregamento inicial (fora do cache para atualizar sempre)
df_mestra = carregar_mestra()
df_historico = carregar_historico()

menu = ["🚀 Registrar Produção", "📊 Banco de Dados (A-Q)", "📈 Gráficos CEP", "⚙️ Ajustar Padrões"]
aba = st.sidebar.radio("Navegação:", menu)

# --- ABA 1: REGISTRO ---
if aba == "🚀 Registrar Produção":
    st.title("🚀 Registrar Lote")
    
    if df_mestra.empty:
        st.warning("⚠️ A Aba Mestra está vazia. Cadastre os padrões na aba 'Ajustar Padrões' primeiro.")
    else:
        with st.form("form_registro", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            with c1: t_sel = st.selectbox("Produto", sorted(df_mestra['Tipo'].unique()))
            with c2: c_sel = st.selectbox("Cor", sorted(df_mestra[df_mestra['Tipo'] == t_sel]['Cor'].unique()))
            with c3: lote_id = st.text_input("Número do Lote")

            c4, c5, c6 = st.columns(3)
            # CAMPO SOLICITADO: Data de Fabricação
            with c4: data_fab = st.date_input("Data de Fabricação", datetime.now())
            with c5: n_p = st.number_input("Unid Planejadas", min_value=1, value=1)
            with c6: n_r = st.number_input("Unid Reais (Envase)", min_value=1, value=1)
            
            lit_u = st.number_input("Litros por Unidade", value=15.0)
            
            st.divider()
            formulas = df_mestra[(df_mestra['Tipo'] == t_sel) & (df_mestra['Cor'] == c_sel)]
            pesos_reais = {}
            
            for i, row in formulas.iterrows():
                sugestao = row["Quant_OP_kg"] * n_p * lit_u * 1000
                pesos_reais[i] = st.number_input(f"Peso Real (g): {row['Pigmento']} (Sug: {sugestao:.2f}g)", key=f"p_{i}", min_value=0.0)

            if st.form_submit_button("SALVAR NO BANCO DE DADOS"):
                if not lote_id:
                    st.error("Erro: Informe o número do lote!")
                else:
                    novas_linhas = []
                    for i, row in formulas.iterrows():
                        v_p, v_r = n_p * lit_u, n_r * lit_u
                        c_r = (pesos_reais[i] / 1000) / v_r if v_r > 0 else 0
                        v_p_val = (c_r / row["Quant_OP_kg"]) - 1 if row["Quant_OP_kg"] > 0 else 0
                        
                        novas_linhas.append({
                            'Data_Fabricacao': data_fab.strftime("%d/%m/%Y"),
                            'Lote': lote_id, 'Tipo_Produto': t_sel, 'Cor': c_sel, 'Pigmento': row['Pigmento'],
                            'Toque': 1, 'Quant_ad_g': pesos_reais[i], 
                            'Quantidade_OP_g': row["Quant_OP_kg"] * v_p * 1000,
                            'Unid_Plan': n_p, 'Unid_Real': n_r, 'Encomenda': "Não",
                            'Litros_Unit': lit_u, 'Vol_Plan': v_p, 'Vol_Real': v_r,
                            'Formula_kgL': row["Quant_OP_kg"], 'Consumo_Real_kgL': c_r,
                            'Variacao_Perc': v_p_val, 'Variacao_Abs_kg': (pesos_reais[i]/1000) - (v_r * row["Quant_OP_kg"])
                        })
                    
                    if salvar_historico_fisico(pd.DataFrame(novas_linhas)):
                        st.success(f"Lote {lote_id} salvo com sucesso!")
                        st.rerun() # Força a atualização da tela para mostrar no banco

# --- ABA 2: BANCO DE DADOS ---
elif aba == "📊 Banco de Dados (A-Q)":
    st.title("📜 Histórico de Produção Completo")
    if not df_historico.empty:
        st.dataframe(df_historico, use_container_width=True)
        csv = df_historico.to_csv(index=False, sep=';', encoding='utf-8-sig', decimal=',').encode('utf-8-sig')
        st.download_button("📥 Baixar Planilha Excel", csv, "Historico_Producao.csv", "text/csv")
    else:
        st.info("Nenhum registro encontrado no arquivo CSV.")

# --- ABA 3: CEP ---
elif aba == "📈 Gráficos CEP":
    st.title("📈 Gráfico de Controle (Variação %)")
    if not df_historico.empty:
        # Limpeza forçada para o gráfico
        df_historico['Variacao_Perc'] = pd.to_numeric(df_historico['Variacao_Perc'], errors='coerce')
        
        prod_sel = st.selectbox("Filtrar por Produto", df_historico['Tipo_Produto'].unique())
        df_f = df_historico[df_historico['Tipo_Produto'] == prod_sel]
        
        if not df_f.empty:
            chart_data = df_f.pivot_table(index='Lote', columns='Pigmento', values='Variacao_Perc')
            st.line_chart(chart_data)
    else:
        st.error("Sem dados registrados para gerar gráficos.")

# --- ABA 4: AJUSTAR PADRÕES ---
elif aba == "⚙️ Ajustar Padrões":
    st.title("⚙️ Gerenciar Aba Mestra")
    st.write("Edite os coeficientes (kg de pigmento por 1L de base).")
    
    df_edit = st.data_editor(df_mestra, num_rows="dynamic", use_container_width=True)
    
    if st.button("💾 Salvar Alterações nos Padrões"):
        # Salva fisicamente no disco
        df_edit.to_csv("Aba_Mestra.csv", index=False, encoding='utf-8-sig')
        st.success("Aba Mestra salva no arquivo com sucesso!")
        st.rerun()

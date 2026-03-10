import streamlit as st
import pandas as pd
import os
from datetime import datetime
import numpy as np

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Controle de Produção 2026", layout="wide", page_icon="🧪")

# --- ESTILO CSS ---
st.markdown("""
    <style>
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; border: 1px solid #dce1e6; }
    div.stButton > button:first-child {
        background-color: #28a745; color: white; font-weight: bold; height: 3em; border-radius: 8px;
    }
    .titulo-secao { color: #1f4e79; font-weight: bold; border-left: 5px solid #1f4e79; padding-left: 10px; }
    </style>
    """, unsafe_allow_html=True)

# 2. FUNÇÕES DE PERSISTÊNCIA DE DADOS
def inicializar_arquivos():
    """Garante que os arquivos existam antes de qualquer operação"""
    if not os.path.exists("Aba_Mestra.csv"):
        df_m = pd.DataFrame(columns=['Tipo', 'Cor', 'Pigmento', 'Quant OP (kg)'])
        df_m.to_csv("Aba_Mestra.csv", index=False, encoding='latin-1')
    
    # O Histórico é criado automaticamente na primeira gravação se não existir

def load_mestra():
    inicializar_arquivos()
    try:
        df = pd.read_csv("Aba_Mestra.csv", encoding='latin-1')
        df['Quant OP (kg)'] = pd.to_numeric(df['Quant OP (kg)'].astype(str).str.replace(',', '.'), errors='coerce').fillna(0.0)
        return df
    except:
        return pd.DataFrame(columns=['Tipo', 'Cor', 'Pigmento', 'Quant OP (kg)'])

def salvar_no_csv_fisico(df_para_salvar):
    """Função robusta para anexar dados ao CSV sem perder o que já existe"""
    hist_path = "Historico_Producao.csv"
    
    if os.path.exists(hist_path):
        try:
            # Lê o histórico existente
            df_antigo = pd.read_csv(hist_path, sep=';', encoding='latin-1', decimal=',')
            # Une com o novo
            df_completo = pd.concat([df_antigo, df_para_salvar], ignore_index=True)
        except Exception as e:
            # Se o arquivo estiver corrompido ou vazio, começa um novo
            df_completo = df_para_salvar
    else:
        df_completo = df_para_salvar
    
    # Grava o arquivo fisicamente no disco
    df_completo.to_csv(hist_path, index=False, sep=';', encoding='latin-1', decimal=',')
    return True

# 3. INTERFACE DE NAVEGAÇÃO
df_mestra = load_mestra()
menu = ["🚀 Registrar Lote", "📊 Banco de Dados (A-Q)", "📈 CEP", "⚙️ Configurar Mestra"]
aba = st.sidebar.radio("Navegação:", menu)

# --- ABA 1: REGISTRO DE PRODUÇÃO ---
if aba == "🚀 Registrar Lote":
    st.title("🚀 Registrar Produção de Lote")
    
    if df_mestra.empty:
        st.warning("⚠️ Cadastre produtos na aba 'Configurar Mestra' primeiro.")
    else:
        with st.form("form_producao", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            with c1: t_sel = st.selectbox("Produto", sorted(df_mestra['Tipo'].unique()))
            with c2: c_sel = st.selectbox("Cor", sorted(df_mestra[df_mestra['Tipo'] == t_sel]['Cor'].unique()))
            with c3: lote_id = st.text_input("Número do Lote")

            c4, c5, c6 = st.columns(3)
            # NOVO: Opção para registrar a data de produção manual
            with c4: data_prod = st.date_input("Data de Produção", datetime.now())
            with c5: n_p = st.number_input("# Plan (Unid)", min_value=1, value=1)
            with c6: n_r = st.number_input("# Real (Unid)", min_value=1, value=1)
            
            lit = st.number_input("Litros por Unidade (Ex: 15.0)", value=15.0)
            
            st.markdown("---")
            formulas = df_mestra[(df_mestra['Tipo'] == t_sel) & (df_mestra['Cor'] == c_sel)]
            pesagens = {}
            
            for i, row in formulas.iterrows():
                sugestao = row["Quant OP (kg)"] * n_p * lit * 1000
                pesagens[i] = st.number_input(f"Peso Real (g) - {row['Pigmento']} [Sugestão: {sugestao:.2f}g]", min_value=0.0, format="%.2f", key=f"input_{i}")

            if st.form_submit_button("SALVAR E CALCULAR"):
                if not lote_id:
                    st.error("❌ Erro: O número do lote é obrigatório.")
                else:
                    dados_novos = []
                    vol_plan = n_p * lit
                    vol_real = n_r * lit
                    
                    for i, row in formulas.iterrows():
                        padrão_kg_l = row["Quant OP (kg)"]
                        peso_g = pesagens[i]
                        # Cálculo das colunas técnicas O, P e Q
                        consumo_real = (peso_g / 1000) / vol_real if vol_real > 0 else 0
                        var_perc = (consumo_real / padrão_kg_l) - 1 if padrão_kg_l > 0 else 0
                        var_abs = (peso_g / 1000) - (vol_real * padrão_kg_l)

                        dados_novos.append({
                            "data": data_prod.strftime("%d/%m/%Y"), # Data escolhida pelo usuário
                            "lote": lote_id,
                            "tipo de produto": t_sel,
                            "cor": c_sel,
                            "pigmento": row['Pigmento'],
                            "toque": 1,
                            "Quant ad (g)": peso_g,
                            "Quantidade OP": padrão_kg_l * vol_plan * 1000,
                            "#Plan": n_p,
                            "#Real": n_r,
                            "Encomenda?": "Não",
                            "Litros/Unit": lit,
                            "Volume Planejado": vol_plan,
                            "volume produzido": vol_real,
                            "Formulação": padrão_kg_l,
                            "consumo real (kg/L)": consumo_real,
                            "variação %": var_perc,
                            "variação absoluta": var_abs
                        })
                    
                    if salvar_no_csv_fisico(pd.DataFrame(dados_novos)):
                        st.success(f"✅ Lote {lote_id} salvo com sucesso no Banco de Dados!")
                        st.balloons()

# --- ABA 2: BANCO DE DADOS ---
elif aba == "📊 Banco de Dados (A-Q)":
    st.title("📜 Histórico de Registros e Cálculos")
    
    if os.path.exists("Historico_Producao.csv"):
        # Lê sempre a versão mais recente do arquivo
        df_h = pd.read_csv("Historico_Producao.csv", sep=';', encoding='latin-1', decimal=',')
        
        st.markdown("<h3 class='titulo-secao'>Tabela Completa (Colunas A-Q)</h3>", unsafe_allow_html=True)
        st.dataframe(df_h.style.format({
            'variação %': '{:.2%}',
            'consumo real (kg/L)': '{:.6f}',
            'Formulação': '{:.6f}',
            'variação absoluta': '{:.3f} kg'
        }), use_container_width=True)
        
        # Botão de Download
        csv = df_h.to_csv(index=False, sep=';', decimal=',', encoding='latin-1').encode('latin-1')
        st.download_button("📥 Baixar Planilha Excel", csv, "Historico_Producao.csv", "text/csv")
        
        if st.button("🗑️ Limpar Todo o Histórico (CUIDADO)"):
            if os.path.exists("Historico_Producao.csv"):
                os.remove("Historico_Producao.csv")
                st.rerun()
    else:
        st.info("O arquivo de histórico ainda não existe. Registre o primeiro lote para gerá-lo.")

# --- ABA 3: CEP ---
elif aba == "📈 CEP":
    st.title("📈 Análise de Variação (CEP)")
    if os.path.exists("Historico_Producao.csv"):
        df_h = pd.read_csv("Historico_Producao.csv", sep=';', encoding='latin-1', decimal=',')
        p_sel = st.selectbox("Escolha o Produto", df_h['tipo de produto'].unique())
        df_p = df_h[df_h['tipo de produto'] == p_sel]
        
        st.line_chart(df_p.pivot_table(index='lote', columns='pigmento', values='variação %'))
    else:
        st.warning("Sem dados para análise.")

# --- ABA 4: CONFIGURAÇÕES ---
elif aba == "⚙️ Configurar Mestra":
    st.title("⚙️ Gerenciar Padrões (Aba Mestra)")
    st.write("Insira os produtos e a gramatura padrão por Litro (kg/L).")
    
    df_edit = st.data_editor(df_mestra, num_rows="dynamic", use_container_width=True)
    
    if st.button("💾 Salvar Padrões"):
        df_edit.to_csv("Aba_Mestra.csv", index=False, encoding='latin-1')
        st.success("Aba Mestra atualizada!")
        st.rerun()

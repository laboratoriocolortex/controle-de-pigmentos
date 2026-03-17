import streamlit as st
import pandas as pd
import os
from datetime import datetime
import numpy as np

# Configuração inicial da página
st.set_page_config(page_title="Controle Colortex 2026", layout="wide", page_icon="🧪")

# --- ESTILO CSS ---
st.markdown("""
    <style>
    div.stButton > button:first-child {
        background-color: #d4edda; color: #155724; border: 1px solid #c3e6cb;
        font-weight: bold; width: 100%; height: 3em;
    }
    .block-container { padding-top: 1.5rem; }
    h3 { margin-bottom: 0rem !important; font-size: 1.10rem !important; }
    hr { margin: 0.5rem 0rem !important; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNÇÕES DE PADRONIZAÇÃO E LIMPEZA ---

def corrigir_acentos_e_nomes(df):
    """Padroniza termos técnicos e nomes de cores para garantir compatibilidade no CEP."""
    if df.empty: return df
    
    # Dicionário de Tradução Automática
    traducoes = {
        'Oxido': 'Óxido',
        'oxido': 'óxido',
        'Franca': 'França',
        'franca': 'frança',
        'Tintometrico': 'Tintométrico',
        'tintometrico': 'tintométrico',
        'Padrao': 'Padrão',
        'padrao': 'padrão'
    }
    
    # Colunas que precisam ser idênticas para o cruzamento de dados
    cols_texto = ['tipo de produto', 'cor', 'pigmento', 'Tipo', 'Cor', 'Pigmento', 'Produto']
    
    for col in df.columns:
        if col in cols_texto:
            # Remove espaços em branco e garante que é string
            df[col] = df[col].astype(str).str.strip()
            # Aplica as correções do dicionário
            for errado, correto in traducoes.items():
                df[col] = df[col].str.replace(errado, correto, regex=False)
            # Padroniza para Formato Título (Ex: azul frança -> Azul França)
            df[col] = df[col].str.title()
    return df

def load_data(file):
    """Carrega dados tentando diferentes codificações para evitar erro de acento."""
    if os.path.exists(file):
        try:
            # Tenta ler com detecção automática de separador
            try:
                df = pd.read_csv(file, sep=None, engine='python', encoding='latin-1')
            except:
                df = pd.read_csv(file, sep=None, engine='python', encoding='utf-8')
            
            df.columns = [str(c).strip() for c in df.columns]
            df = corrigir_acentos_e_nomes(df)
            return df
        except:
            return pd.DataFrame()
    return pd.DataFrame()

# --- FUNÇÕES DE PERSISTÊNCIA ---

def atualizar_padroes_e_mestra(df_mestra, lista_lote, vol_plan_calculo, vol_real_calculo, data_fab):
    padroes_file = "Padroes_Registrados.csv"
    novos_registros_padrao = []
    
    if vol_real_calculo <= 0: return df_mestra, False

    for item in lista_lote:
        concentracao_real_g_l = item["Quant ad (g_num)"] / vol_real_calculo
        novo_coef = (concentracao_real_g_l / 1000) 
        
        mask = (df_mestra['Tipo'] == item["tipo de produto"]) & (df_mestra['Cor'] == item["cor"]) & (df_mestra['Pigmento'] == item["pigmento"])
        if mask.any():
            df_mestra.loc[mask, 'Quant OP (kg)'] = novo_coef
        
        novos_registros_padrao.append({
            "Data Alteração": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "Data Fabricação": data_fab,
            "Produto": item["tipo de produto"],
            "Cor": item["cor"],
            "Pigmento": item["pigmento"],
            "Novo Coef (kg/L)": novo_coef,
            "Lote Origem": item["lote"]
        })

    df_mestra.to_csv("Aba_Mestra.csv", index=False, encoding='latin-1')
    
    df_p = pd.DataFrame(novos_registros_padrao)
    if os.path.exists(padroes_file):
        hist_p = load_data(padroes_file)
        df_p = pd.concat([hist_p, df_p], ignore_index=True)
    df_p.to_csv(padroes_file, index=False, encoding='latin-1')
    return df_mestra, True

def salvar_no_historico(dados_lista):
    hist_path = "Historico_Producao.csv"
    novo_df = pd.DataFrame(dados_lista)
    col_excel = ["data", "lote", "tipo de produto", "cor", "pigmento", "toque", "Quant ad (g)", "Quantidade OP", "#Plan", "#Real", "Encomenda?", "Litros/Unit"]
    
    if os.path.exists(hist_path):
        hist_ex = load_data(hist_path)
        final = pd.concat([hist_ex, novo_df[col_excel]], ignore_index=True)
    else:
        final = novo_df[col_excel]
    final.to_csv(hist_path, index=False, encoding='latin-1')

# --- CARREGAMENTO DE DADOS INICIAL ---
df_mestra = load_data("Aba_Mestra.csv")
if not df_mestra.empty and "Quant OP (kg)" in df_mestra.columns:
    df_mestra["Quant OP (kg)"] = pd.to_numeric(df_mestra["Quant OP (kg)"].astype(str).str.replace(',', '.'), errors='coerce').fillna(0.0)

# --- NAVEGAÇÃO ---
menu = ["🚀 Nova Pigmentação", "📈 Variações & CEP", "📋 Padrões", "📜 Banco de Dados", "➕ Cadastro", "📊 Aba Mestra", "📂 Importar Dados"]
aba = st.sidebar.radio("Navegação:", menu)

if aba == "🚀 Nova Pigmentação":
    st.title("🚀 Registrar Produção")
    if df_mestra.empty:
        st.error("Aba Mestra vazia! Vá em 'Importar Dados' para carregar sua planilha.")
    else:
        c1, c2, c3, c4 = st.columns([1.5, 1.5, 1, 1])
        with c1: tipo_sel = st.selectbox("Produto", sorted(df_mestra['Tipo'].unique()))
        with c2: cor_sel = st.selectbox("Cor", sorted(df_mestra[df_mestra['Tipo'] == tipo_sel]['Cor'].unique()))
        with c3: lote_id = st.text_input("Lote", placeholder="Nº Lote")
        with c4: data_prod = st.date_input("Data Fabricação", datetime.now())

        u1, u2, u3, u4 = st.columns([1, 1, 1.5, 1])
        with u1: num_plan = st.number_input("#Unid Plan", min_value=1, step=1, value=1)
        with u2: num_real = st.number_input("#Unid Real", min_value=1, step=1, value=1)
        with u3:
            opcoes_vol = ["0,9L", "3L", "3,6L", "5kg", "13kg", "15L", "18L", "25kg", "Outro"]
            sel_vol = st.select_slider("Embalagem:", options=opcoes_vol, value="15L")
            litros_unit = float(sel_vol.replace('L','').replace('kg','').replace(',','.')) if sel_vol != "Outro" else st.number_input("Valor Unit:", value=15.0)
        with u4: encomenda = st.selectbox("📦 Encomenda?", ["Não", "Sim"])

        vol_plan_tot = num_plan * litros_unit
        vol_real_tot = num_real * litros_unit
        st.info(f"Base Planejada: {vol_plan_tot:.2f}L | Base Real: {vol_real_tot:.2f}L")
        
        formulas = df_mestra[(df_mestra['Tipo'] == tipo_sel) & (df_mestra['Cor'] == cor_sel)]
        if not formulas.empty:
            lista_lote = []
            for index, row in formulas.iterrows():
                pigm = row['Pigmento']
                rec_g = round(row["Quant OP (kg)"] * vol_plan_tot * 1000, 2)
                with st.container():
                    col_p, col_pes = st.columns([1.5, 3.5])
                    with col_p:
                        st.markdown(f"### {pigm}")
                        st.write(f"Sugestão: **{rec_g}g**")
                        n_toques = st.number_input(f"Toques", min_value=1, value=1, step=1, key=f"nt_{index}")
                    with col_pes:
                        soma_ad = 0.0
                        cols_t = st.columns(5)
                        for t in range(1, int(n_toques) + 1):
                            with cols_t[(t-1)%5]:
                                val_t = st.number_input(f"T{t} (g)", min_value=0.0, format="%.2f", key=f"val_{index}_{t}")
                                if val_t: soma_ad += val_t
                        st.write(f"Total: **{soma_ad:.2f}g**")
                
                lista_lote.append({
                    "data": data_prod.strftime("%d/%m/%Y"), "lote": lote_id, "tipo de produto": tipo_sel,
                    "cor": cor_sel, "pigmento": pigm, "toque": n_toques, "Quantidade OP": rec_g, 
                    "Quant ad (g)": soma_ad, "Quant ad (g_num)": soma_ad,
                    "#Plan": num_plan, "#Real": num_real, "Encomenda?": encomenda, "Litros/Unit": litros_unit
                })
                st.markdown("---")
            
            marcar_p = st.checkbox("⚠️ ATUALIZAR PADRÃO TÉCNICO (Aba Mestra)?")
            if st.button("✅ FINALIZAR REGISTRO", use_container_width=True):
                if not lote_id: st.error("Lote obrigatório!")
                else:
                    if marcar_p: atualizar_padroes_e_mestra(df_mestra, lista_lote, vol_plan_tot, vol_real_tot, data_prod.strftime("%d/%m/%Y"))
                    salvar_no_historico(lista_lote)
                    st.success("Salvo!"); st.balloons()

elif aba == "📈 Variações & CEP":
    st.title("📈 Gráfico de Controle (CEP)")
    df_h = load_data("Historico_Producao.csv")
    if not df_h.empty:
        for c in ["Quant ad (g)", "Quantidade OP", "#Plan", "#Real", "Litros/Unit"]:
            df_h[c] = pd.to_numeric(df_h[c].astype(str).str.replace(',','.'), errors='coerce').fillna(0)
        df_h['Vol_Real'] = df_h['#Real'] * df_h['Litros/Unit']
        df_h['Real_gL'] = df_h['Quant ad (g)'] / (df_h['Vol_Real'] + 0.0001)
        df_h['Pad_gL'] = (df_h['Quantidade OP'] * 1000) / (df_h['#Plan'] * df_h['Litros/Unit'] + 0.0001)
        df_h['Desvio_%'] = ((df_h['Real_gL'] / (df_h['Pad_gL'] + 0.000001)) - 1) * 100
        
        p_sel = st.selectbox("Produto", sorted(df_h['tipo de produto'].unique()))
        c_sel = st.selectbox("Cor", sorted(df_h[df_h['tipo de produto']==p_sel]['cor'].unique()))
        df_f = df_h[(df_h['tipo de produto']==p_sel) & (df_h['cor']==c_sel)].copy()
        
        if not df_f.empty:
            st.line_chart(df_f.pivot_table(index='lote', columns='pigmento', values='Desvio_%'))
            st.dataframe(df_f[['data', 'lote', 'pigmento', 'Desvio_%']])
    else: st.info("Sem dados para exibir.")

elif aba == "📜 Banco de Dados":
    st.title("📜 Histórico Completo")
    df_h = load_data("Historico_Producao.csv")
    if not df_h.empty:
        st.dataframe(df_h, use_container_width=True)
        st.divider()
        st.subheader("⚠️ Zona de Perigo")
        if st.button("🗑️ APAGAR TODO O HISTÓRICO"):
            if os.path.exists("Historico_Producao.csv"):
                os.remove("Historico_Producao.csv")
                st.success("Histórico apagado!"); st.rerun()
    else: st.info("Vazio.")

elif aba == "📂 Importar Dados":
    st.title("📂 Importação com Padronização (Óxido/França)")
    up_file = st.file_uploader("Selecione o CSV", type="csv")
    tipo_imp = st.radio("Destino:", ["Histórico de Produção", "Aba Mestra", "Padrões Registrados"])
    
    if up_file:
        try:
            df_up = pd.read_csv(up_file, sep=None, engine='python', encoding='latin-1')
            df_up = corrigir_acentos_e_nomes(df_up)
            st.write("Prévia (Corrigida):")
            st.dataframe(df_up.head(5))
            if st.button("CONFIRMAR IMPORTAÇÃO"):
                arqs = {"Histórico de Produção":"Historico_Producao.csv", "Aba Mestra":"Aba_Mestra.csv", "Padrões Registrados":"Padroes_Registrados.csv"}
                df_up.to_csv(arqs[tipo_imp], index=False, encoding='latin-1')
                st.success("Dados importados e padronizados!"); st.rerun()
        except Exception as e: st.error(f"Erro: {e}")

elif aba == "📊 Aba Mestra":
    st.title("📊 Editor da Mestra")
    if not df_mestra.empty:
        df_edit = st.data_editor(df_mestra, num_rows="dynamic")
        if st.button("💾 SALVAR"):
            df_edit.to_csv("Aba_Mestra.csv", index=False, encoding='latin-1')
            st.success("Salvo!"); st.rerun()

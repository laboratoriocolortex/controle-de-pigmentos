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

# --- FUNÇÕES DE PERSISTÊNCIA ---

def format_num_padrao(valor, casas=2):
    if valor is None or valor == "": return ""
    try:
        val_float = float(str(valor).replace(',', '.'))
        return f"{val_float:.{casas}f}"
    except:
        return str(valor)

def load_data(file):
    if os.path.exists(file):
        try:
            df = pd.read_csv(file, sep=None, engine='python', encoding='latin-1')
            df.columns = [str(c).strip() for c in df.columns]
            return df
        except:
            return pd.DataFrame()
    return pd.DataFrame()

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
        hist_p = pd.read_csv(padroes_file, encoding='latin-1')
        df_p = pd.concat([hist_p, df_p], ignore_index=True)
    df_p.to_csv(padroes_file, index=False, encoding='latin-1')
    
    return df_mestra, True

def salvar_no_historico(dados_lista):
    hist_path = "Historico_Producao.csv"
    novo_df = pd.DataFrame(dados_lista)
    col_excel = ["data", "lote", "tipo de produto", "cor", "pigmento", "toque", "Quant ad (g)", "Quantidade OP", "#Plan", "#Real", "Encomenda?", "Litros/Unit"]
    
    if os.path.exists(hist_path):
        hist_ex = pd.read_csv(hist_path, encoding='latin-1')
        final = pd.concat([hist_ex, novo_df[col_excel]], ignore_index=True)
    else:
        final = novo_df[col_excel]
        
    final.to_csv(hist_path, index=False, encoding='latin-1')

# --- CARREGAMENTO DE DADOS ---
df_mestra = load_data("Aba_Mestra.csv")
if not df_mestra.empty and "Quant OP (kg)" in df_mestra.columns:
    df_mestra["Quant OP (kg)"] = pd.to_numeric(df_mestra["Quant OP (kg)"].astype(str).str.replace(',', '.'), errors='coerce').fillna(0.0)

# --- NAVEGAÇÃO ---
menu = ["🚀 Nova Pigmentação", "📈 Variações & CEP", "📋 Padrões", "📜 Banco de Dados", "➕ Cadastro", "📊 Aba Mestra", "📂 Importar Dados"]
aba = st.sidebar.radio("Navegação:", menu)

# --- CÓDIGO DAS ABAS ORIGINAIS ---
if aba == "🚀 Nova Pigmentação":
    st.title("🚀 Registrar Produção")
    if df_mestra.empty:
        st.error("Aba Mestra não encontrada! Por favor, importe o arquivo na aba 'Importar Dados'.")
    else:
        c1, c2, c3, c4 = st.columns([1.5, 1.5, 1, 1])
        with c1: tipo_sel = st.selectbox("Produto", sorted(df_mestra['Tipo'].unique()))
        with c2: cor_sel = st.selectbox("Cor", sorted(df_mestra[df_mestra['Tipo'] == tipo_sel]['Cor'].unique()))
        with c3: lote_id = st.text_input("Lote", placeholder="Ex: 2024001")
        with c4: data_prod = st.date_input("Data Fabricação", datetime.now())

        u1, u2, u3, u4 = st.columns([1, 1, 1.5, 1])
        with u1: num_plan = st.number_input("#Unid Plan", min_value=1, step=1, value=1)
        with u2: num_real = st.number_input("#Unid Real", min_value=1, step=1, value=1)
        with u3:
            opcoes_vol = ["0,9L", "3L", "3,6L", "5kg", "13kg", "15L", "18L", "25kg", "Outro"]
            sel_vol = st.select_slider("Embalagem:", options=opcoes_vol, value="15L")
            litros_unit = float(sel_vol.replace('L','').replace('kg','').replace(',','.')) if sel_vol != "Outro" else st.number_input("Valor Unit (L/kg):", value=15.0)
        with u4: encomenda = st.selectbox("📦 Encomenda?", ["Não", "Sim"])

        vol_plan_tot = num_plan * litros_unit
        vol_real_tot = num_real * litros_unit
        st.info(f"Cálculo: Planejado {vol_plan_tot:.2f}L | Real {vol_real_tot:.2f}L")
        
        st.subheader("🎨 Composição e Pesagem")
        formulas = df_mestra[(df_mestra['Tipo'] == tipo_sel) & (df_mestra['Cor'] == cor_sel)]
        
        if not formulas.empty:
            lista_lote = []
            for index, row in formulas.iterrows():
                pigm = row['Pigmento']
                coef = row["Quant OP (kg)"]
                rec_g = round(coef * vol_plan_tot * 1000, 2)
                with st.container():
                    col_p, col_esp, col_pes = st.columns([1.2, 0.3, 3.5])
                    with col_p:
                        st.markdown(f"### {pigm}")
                        st.caption(f"Padrão: {coef:.6f} kg/L")
                        st.markdown(f"**Sugestão: {rec_g}g**")
                        n_toques = st.number_input(f"Toques", min_value=1, value=1, step=1, key=f"nt_{index}")
                    with col_pes:
                        soma_ad = 0.0
                        cols_t = st.columns(5)
                        for t in range(1, int(n_toques) + 1):
                            with cols_t[(t-1)%5]:
                                val_t = st.number_input(f"T{t} (g)", min_value=0.0, format="%.2f", key=f"val_{index}_{t}")
                                if val_t: soma_ad += val_t
                        st.write(f"**Total Adicionado: {soma_ad:.2f} g**")
                lista_lote.append({
                    "data": data_prod.strftime("%d/%m/%Y"), "lote": lote_id, "tipo de produto": tipo_sel,
                    "cor": cor_sel, "pigmento": pigm, "toque": n_toques, "Quantidade OP": rec_g, 
                    "Quant ad (g)": soma_ad, "Quant ad (g_num)": soma_ad,
                    "#Plan": num_plan, "#Real": num_real, "Encomenda?": encomenda, "Litros/Unit": litros_unit
                })
                st.markdown("---")
            
            if st.button("✅ FINALIZAR E SALVAR REGISTRO", use_container_width=True):
                if not lote_id: st.error("LOTE obrigatório!")
                else:
                    if st.checkbox("⚠️ Atualizar Padrão Técnico?"):
                        df_mestra, ok = atualizar_padroes_e_mestra(df_mestra, lista_lote, vol_plan_tot, vol_real_tot, data_prod.strftime("%d/%m/%Y"))
                    salvar_no_historico(lista_lote)
                    st.success("Salvo!"); st.balloons()

elif aba == "📈 Variações & CEP":
    st.title("📈 Controle Estatístico de Processo (CEP)")
    df_h = load_data("Historico_Producao.csv")
    if not df_h.empty:
        for c in ["Quant ad (g)", "Quantidade OP", "#Plan", "#Real", "Litros/Unit"]:
            df_h[c] = pd.to_numeric(df_h[c].astype(str).str.replace(',','.'), errors='coerce').fillna(0)
        df_h['Vol_Real'] = df_h['#Real'] * df_h['Litros/Unit']
        df_h['Real_gL'] = df_h['Quant ad (g)'] / df_h['Vol_Real']
        df_h['Padrao_gL'] = (df_h['Quantidade OP'] * 1000) / (df_h['#Plan'] * df_h['Litros/Unit'])
        df_h['Desvio_%'] = ((df_h['Real_gL'] / (df_h['Padrao_gL'] + 0.000001)) - 1) * 100
        p_sel = st.selectbox("Produto", sorted(df_h['tipo de produto'].unique()))
        c_sel = st.selectbox("Cor", sorted(df_h[df_h['tipo de produto']==p_sel]['cor'].unique()))
        df_f = df_h[(df_h['tipo de produto']==p_sel) & (df_h['cor']==c_sel)].copy()
        if not df_f.empty:
            chart_data = df_f.pivot_table(index='lote', columns='pigmento', values='Desvio_%')
            st.line_chart(chart_data)
            st.dataframe(df_f[['data', 'lote', 'pigmento', 'Quant ad (g)', 'Desvio_%']])

elif aba == "📋 Padrões":
    st.title("📋 Evolução de Padrões")
    df_p = load_data("Padroes_Registrados.csv")
    if not df_p.empty: st.dataframe(df_p, use_container_width=True)
    else: st.info("Sem registros.")

elif aba == "📜 Banco de Dados":
    st.title("📜 Histórico de Produção")
    df_h = load_data("Historico_Producao.csv")
    if not df_h.empty:
        st.dataframe(df_h, use_container_width=True)
        st.download_button("📥 Baixar CSV", df_h.to_csv(index=False, encoding='latin-1'), "historico.csv")

elif aba == "➕ Cadastro":
    st.title("➕ Novo Cadastro")
    with st.form("cad"):
        t = st.text_input("Tipo"); c = st.text_input("Cor"); p = st.text_input("Pigmento")
        q = st.number_input("kg/L", format="%.8f")
        if st.form_submit_button("Salvar"):
            pd.concat([df_mestra, pd.DataFrame([{"Tipo":t,"Cor":c,"Pigmento":p,"Quant OP (kg)":q}])]).to_csv("Aba_Mestra.csv", index=False, encoding='latin-1')
            st.success("Salvo!")

elif aba == "📊 Aba Mestra":
    st.title("📊 Gestão da Aba Mestra")
    if not df_mestra.empty:
        df_edit = st.data_editor(df_mestra, num_rows="dynamic", use_container_width=True)
        if st.button("💾 SALVAR ALTERAÇÕES"):
            df_edit.to_csv("Aba_Mestra.csv", index=False, encoding='latin-1')
            st.success("Atualizado!")

# --- NOVA ABA: IMPORTAR DADOS ---
elif aba == "📂 Importar Dados":
    st.title("📂 Importação de Dados via CSV")
    st.warning("⚠️ O arquivo deve estar no formato CSV com codificação Latin-1 ou UTF-8.")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("1. Importar Aba Mestra")
        st.caption("Colunas esperadas: Tipo, Cor, Pigmento, Quant OP (kg)")
        up_mestra = st.file_uploader("Upload Aba_Mestra.csv", type="csv", key="up_m")
        if up_mestra:
            try:
                df_up = pd.read_csv(up_mestra, sep=None, engine='python', encoding='latin-1')
                st.write("Prévia dos dados:")
                st.dataframe(df_up.head(3))
                if st.button("Confirmar Importação Mestra"):
                    df_up.to_csv("Aba_Mestra.csv", index=False, encoding='latin-1')
                    st.success("Aba Mestra atualizada com sucesso!")
                    st.rerun()
            except Exception as e: st.error(f"Erro: {e}")

    with col2:
        st.subheader("2. Importar Histórico")
        st.caption("Colunas esperadas: data, lote, tipo de produto, cor, pigmento, toque, Quant ad (g), Quantidade OP, #Plan, #Real, Encomenda?, Litros/Unit")
        up_hist = st.file_uploader("Upload Historico_Producao.csv", type="csv", key="up_h")
        if up_hist:
            try:
                df_up_h = pd.read_csv(up_hist, sep=None, engine='python', encoding='latin-1')
                st.write("Prévia dos dados:")
                st.dataframe(df_up_h.head(3))
                if st.button("Confirmar Importação Histórico"):
                    df_up_h.to_csv("Historico_Producao.csv", index=False, encoding='latin-1')
                    st.success("Histórico de produção atualizado!")
                    st.rerun()
            except Exception as e: st.error(f"Erro: {e}")

    st.divider()
    st.subheader("3. Importar Histórico de Padrões")
    st.caption("Colunas esperadas: Data Alteração, Data Fabricação, Produto, Cor, Pigmento, Novo Coef (kg/L), Lote Origem")
    up_pad = st.file_uploader("Upload Padroes_Registrados.csv", type="csv", key="up_p")
    if up_pad:
        try:
            df_up_p = pd.read_csv(up_pad, sep=None, engine='python', encoding='latin-1')
            st.write("Prévia dos dados:")
            st.dataframe(df_up_p.head(3))
            if st.button("Confirmar Importação Padrões"):
                df_up_p.to_csv("Padroes_Registrados.csv", index=False, encoding='latin-1')
                st.success("Histórico de padrões atualizado!")
                st.rerun()
        except Exception as e: st.error(f"Erro: {e}")

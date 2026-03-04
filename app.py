import streamlit as st
import pandas as pd
import os
from datetime import datetime
import numpy as np

# Configuração inicial da página
st.set_page_config(page_title="Controle 2026", layout="wide", page_icon="🧪")

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

# --- FUNÇÕES AUXILIARES E DE CARREGAMENTO ---
def format_num_padrao(valor, casas=2):
    if valor is None or valor == "": return ""
    try:
        val_float = float(str(valor).replace(',', '.'))
        return f"{val_float:.{casas}f}"
    except:
        return str(valor)

def load_data(file="Aba_Mestra.csv"):
    if os.path.exists(file):
        try:
            df = pd.read_csv(file, sep=None, engine='python', encoding='latin-1')
            df.columns = [str(c).strip() for c in df.columns]
            if "Quant OP (kg)" in df.columns:
                df["Quant OP (kg)"] = df["Quant OP (kg)"].astype(str).str.replace(',', '.')
                df["Quant OP (kg)"] = pd.to_numeric(df["Quant OP (kg)"], errors='coerce').fillna(0.0)
            return df
        except:
            return pd.DataFrame()
    return pd.DataFrame()

# --- NOVA LÓGICA DE CÁLCULO A-Q ---
def processar_colunas_A_Q(lista_lote, df_mestra):
    df = pd.DataFrame(lista_lote)
    
    # L: Volume Planejado | M: volume produzido
    df['Volume Planejado'] = df['n_plan'] * df['Litros/Unit']
    df['volume produzido'] = df['n_real'] * df['Litros/Unit']

    # N: Formulação (Busca na Aba Mestra)
    mestra_ref = df_mestra.rename(columns={'Tipo': 'Tipo de Produto', 'Quant OP (kg)': 'Formulação', 'Pigmento': 'pigmento_mestra'})
    df = pd.merge(df, mestra_ref[['Tipo de Produto', 'Cor', 'pigmento_mestra', 'Formulação']], 
                  left_on=['Tipo de Produto', 'Cor', 'pigmento'], 
                  right_on=['Tipo de Produto', 'Cor', 'pigmento_mestra'], how='left')

    # O: consumo real | P: variação percentual | Q: variação absoluta
    df['consumo real de pigmento (utilizado kg/L)'] = (df['Quant ad (g)'] / 1000) / df['volume produzido'].replace(0, 1)
    df['variação percentual'] = (df['consumo real de pigmento (utilizado kg/L)'] / df['Formulação'].replace(0, np.nan)) - 1
    df['variação absoluta'] = (df['Quant ad (g)'] / 1000) - (df['volume produzido'] * df['Formulação'].fillna(0))

    # Reordenar para o padrão solicitado
    col_ordem = [
        'lote', 'Tipo de Produto', 'Cor', 'pigmento', 'Toques', 
        'Quant ad (g)', 'Quant OP (kg)', 'n_plan', 'n_real', 
        'Litros/Unit', 'Encomenda?', 'Volume Planejado', 
        'volume produzido', 'Formulação', 
        'consumo real de pigmento (utilizado kg/L)', 
        'variação percentual', 'variação absoluta'
    ]
    return df[col_ordem]

def atualizar_padroes_e_mestra(df_mestra, lista_lote, vol_real_calculo):
    padroes_file = "Padroes_Registrados.csv"
    novos_registros_padrao = []
    data_atual = datetime.now().strftime("%d/%m/%Y %H:%M")
    
    if vol_real_calculo <= 0: return df_mestra

    for item in lista_lote:
        concentracao_real_g_l = item["Quant ad (g)"] / vol_real_calculo
        novo_coef = (concentracao_real_g_l / 1000) 
        mask = (df_mestra['Tipo'] == item["Tipo de Produto"]) & (df_mestra['Cor'] == item["Cor"]) & (df_mestra['Pigmento'] == item["pigmento"])
        
        if mask.any():
            df_mestra.loc[mask, 'Quant OP (kg)'] = novo_coef
        
        novos_registros_padrao.append({
            "Data Alteração": data_atual, "Produto": item["Tipo de Produto"], "Cor": item["Cor"],
            "Pigmento": item["pigmento"], "Novo Coef (kg/L)": format_num_padrao(novo_coef, 6),
            "Lote Origem": item["lote"], "Qtd Usada Real (g)": format_num_padrao(item["Quant ad (g)"], 2),
            "Vol Real (L)": format_num_padrao(vol_real_calculo, 2)
        })
        
    df_mestra.to_csv("Aba_Mestra.csv", index=False, encoding='latin-1')
    if novos_registros_padrao:
        df_p = pd.DataFrame(novos_registros_padrao)
        if os.path.exists(padroes_file):
            hist_p = pd.read_csv(padroes_file, encoding='latin-1', sep=';')
            df_p = pd.concat([hist_p, df_p], ignore_index=True)
        df_p.to_csv(padroes_file, index=False, sep=';', encoding='latin-1')
    return df_mestra

def salvar_no_historico(df_final):
    hist_path = "Historico_Producao.csv"
    if os.path.exists(hist_path):
        hist_ex = pd.read_csv(hist_path, encoding='latin-1', sep=';')
        final = pd.concat([hist_ex, df_final], ignore_index=True)
    else: final = df_final
    final.to_csv(hist_path, index=False, sep=';', encoding='latin-1', decimal=',')

# --- NAVEGAÇÃO ---
df_mestra = load_data()
menu = ["🚀 Nova Pigmentação", "📈 Variações & CEP", "📋 Padrões", "📜 Banco de Dados", "➕ Cadastro", "📊 Aba Mestra"]
aba = st.sidebar.radio("Navegação:", menu)

if aba == "🚀 Nova Pigmentação":
    st.title("🚀 Registrar Produção")
    if df_mestra.empty: st.warning("Aba Mestra vazia.")
    else:
        c1, c2, c3, c4 = st.columns([1.5, 1.5, 1, 1])
        with c1: tipo_sel = st.selectbox("Produto", sorted(df_mestra['Tipo'].unique()))
        with c2: cor_sel = st.selectbox("Cor", sorted(df_mestra[df_mestra['Tipo'] == tipo_sel]['Cor'].unique()))
        with c3: lote_id = st.text_input("Lote", value="", placeholder="Nº Lote")
        with c4: encomenda = st.selectbox("📦 Encomenda?", ["Não", "Sim"])
        
        u1, u2, u3 = st.columns([1, 1, 2])
        with u1: num_plan = st.number_input("#Unid Plan", min_value=1, step=1, value=1)
        with u2: num_real = st.number_input("#Unid Real", min_value=1, step=1, value=1)
        with u3:
            opcoes_vol = ["0,9L", "3,6L", "15L", "18L", "Outro"]
            sel_vol = st.select_slider("Embalagem:", options=opcoes_vol, value="15L")
            litros_unit = float(sel_vol.replace('L','').replace(',','.')) if sel_vol != "Outro" else st.number_input("Valor Unit:", value=0.9)
        
        vol_plan_tot = num_plan * litros_unit
        vol_real_tot = num_real * litros_unit
        st.info(f"📏 Base: {vol_plan_tot:.2f}L Plan | {vol_real_tot:.2f}L Real")
        
        st.subheader("🎨 Pigmentos")
        formulas = df_mestra[(df_mestra['Tipo'] == tipo_sel) & (df_mestra['Cor'] == cor_sel)]
        lista_lote = []
        
        for index, row in formulas.iterrows():
            pigm = row['Pigmento']
            rec_g = round(row["Quant OP (kg)"] * vol_plan_tot * 1000, 2)
            with st.container():
                col_p, col_pes = st.columns([1.5, 3.5])
                with col_p:
                    st.markdown(f"### {pigm}")
                    st.caption(f"Sugestão OP: {rec_g}g")
                    n_toques = st.number_input(f"Toques", min_value=1, value=1, step=1, key=f"nt_{index}")
                with col_pes:
                    soma_ad = 0.0
                    cols_t = st.columns(5)
                    for t in range(1, int(n_toques) + 1):
                        with cols_t[(t-1)%5]:
                            val_t = st.number_input(f"T{t}", min_value=0.0, format="%.2f", key=f"val_{index}_{t}")
                            if val_t: soma_ad += val_t
                    st.markdown(f"Total: {soma_ad:.2f} g")
                
                lista_lote.append({
                    "data": datetime.now().strftime("%d/%m/%Y"), "lote": lote_id, "Tipo de Produto": tipo_sel,
                    "Cor": cor_sel, "pigmento": pigm, "Toques": n_toques, "Quant ad (g)": soma_ad,
                    "Quant OP (kg)": rec_g/1000, "n_plan": num_plan, "n_real": num_real, 
                    "Litros/Unit": litros_unit, "Encomenda?": encomenda
                })
                st.markdown("<hr>", unsafe_allow_html=True)
            
        marcar_p = st.checkbox("⚠️ Atualizar Padrão Técnico na Aba Mestra?")
        if st.button("✅ FINALIZAR REGISTRO", use_container_width=True):
            if not lote_id: st.error("Erro: Campo 'Lote' é obrigatório!")
            else:
                df_final = processar_colunas_A_Q(lista_lote, df_mestra)
                salvar_no_historico(df_final)
                if marcar_p: atualizar_padroes_e_mestra(df_mestra, lista_lote, vol_real_tot)
                st.success(f"Lote {lote_id} registrado com sucesso!"); st.balloons()

elif aba == "📈 Variações & CEP":
    st.title("📈 Controle Estatístico de Processo")
    if os.path.exists("Historico_Producao.csv"):
        df_h = pd.read_csv("Historico_Producao.csv", sep=';', encoding='latin-1', decimal=',')
        p_sel = st.selectbox("Filtrar Produto", sorted(df_h['Tipo de Produto'].unique()))
        c_sel = st.selectbox("Filtrar Cor", sorted(df_h[df_h['Tipo de Produto']==p_sel]['Cor'].unique()))
        df_f = df_h[(df_h['Tipo de Produto']==p_sel) & (df_h['Cor']==c_sel)].copy()

        if not df_f.empty:
            df_f['Desvio_%'] = df_f['variação percentual'] * 100
            m1, m2 = st.columns(2)
            m1.metric("Variação Média", f"{df_f['Desvio_%'].mean():.2f}%")
            m2.metric("Desvio Padrão", f"{df_f['Desvio_%'].std():.2f}%")
            
            st.line_chart(df_f.pivot_table(index='lote', columns='pigmento', values='Desvio_%'))
            st.dataframe(df_f[['lote', 'pigmento', 'variação percentual', 'variação absoluta']], use_container_width=True)

elif aba == "📜 Banco de Dados":
    st.title("📜 Histórico de Produção")
    if os.path.exists("Historico_Producao.csv"):
        df_hist = pd.read_csv("Historico_Producao.csv", sep=';', encoding='latin-1', decimal=',')
        st.dataframe(df_hist, use_container_width=True)
        csv = df_hist.to_csv(index=False, sep=';', decimal=',', encoding='latin-1').encode('latin-1')
        st.download_button("📥 Baixar Base de Dados", csv, "historico_completo.csv", "text/csv")

elif aba == "📋 Padrões":
    st.title("📋 Histórico de Alterações Técnicas")
    if os.path.exists("Padroes_Registrados.csv"):
        st.dataframe(pd.read_csv("Padroes_Registrados.csv", sep=';', encoding='latin-1'), use_container_width=True)

elif aba == "➕ Cadastro":
    st.title("➕ Novo Cadastro Técnico")
    with st.form("cad_manual"):
        t = st.text_input("Produto"); c = st.text_input("Cor"); p = st.text_input("Pigmento")
        q = st.number_input("Formulação (kg/1L)", format="%.8f", value=0.0)
        if st.form_submit_button("Salvar na Mestra"):
            nova_linha = pd.DataFrame([{"Tipo":t, "Cor":c, "Pigmento":p, "Quant OP (kg)":q}])
            df_mestra = pd.concat([df_mestra, nova_linha], ignore_index=True)
            df_mestra.to_csv("Aba_Mestra.csv", index=False, encoding='latin-1')
            st.success("Cadastrado!"); st.rerun()

elif aba == "📊 Aba Mestra":
    st.title("📊 Editor da Aba Mestra")
    if not df_mestra.empty:
        df_editado = st.data_editor(df_mestra, num_rows="dynamic", use_container_width=True)
        if st.button("💾 SALVAR ALTERAÇÕES"):
            df_editado.to_csv("Aba_Mestra.csv", index=False, encoding='latin-1')
            st.success("Aba Mestra atualizada!"); st.rerun()

import streamlit as st
import pandas as pd
import os
from datetime import datetime
import numpy as np

# 1. Configuração inicial da página
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

# 2. Funções Auxiliares de Formatação e Carga
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

# 3. Motor de Cálculo e Gravação Física (A até Q)
def salvar_no_historico_aq(dados_lista, df_mestra):
    hist_path = "Historico_Producao.csv"
    df_novo = pd.DataFrame(dados_lista)
    
    # Cálculos de Volume (L e M)
    df_novo['Volume Planejado'] = df_novo['n_plan'] * df_novo['Litros/Unit']
    df_novo['volume produzido'] = df_novo['n_real'] * df_novo['Litros/Unit']
    
    # Busca Formulação (N) na Mestra
    df_novo = pd.merge(
        df_novo, 
        df_mestra[['Tipo', 'Cor', 'Pigmento', 'Quant OP (kg)']], 
        left_on=['tipo de produto', 'cor', 'pigmento'], 
        right_on=['Tipo', 'Cor', 'Pigmento'], 
        how='left'
    )
    
    # Cálculos Técnicos (O, P, Q)
    df_novo['Formulação'] = df_novo['Quant OP (kg)_y']
    df_novo['consumo real de pigmento (utilizado kg/L)'] = (df_novo['Quant ad (g_num)'] / 1000) / df_novo['volume produzido'].replace(0, 1)
    df_novo['variação percentual'] = (df_novo['consumo real de pigmento (utilizado kg/L)'] / df_novo['Formulação'].replace(0, np.nan)) - 1
    df_novo['variação absoluta'] = (df_novo['Quant ad (g_num)'] / 1000) - (df_novo['volume produzido'] * df_novo['Formulação'].fillna(0))

    # Organização das Colunas A-Q
    colunas_aq = [
        'lote', 'tipo de produto', 'cor', 'pigmento', 'toque', 
        'Quant ad (g)', 'Quantidade OP', 'n_plan', 'n_real', 
        'Litros/Unit', 'Encomenda?', 'Volume Planejado', 
        'volume produzido', 'Formulação', 
        'consumo real de pigmento (utilizado kg/L)', 
        'variação percentual', 'variação absoluta'
    ]
    
    df_final = df_novo[colunas_aq]

    if os.path.exists(hist_path):
        try:
            hist_existente = pd.read_csv(hist_path, sep=';', encoding='latin-1')
            final = pd.concat([hist_existente, df_final], ignore_index=True)
        except:
            final = df_final
    else:
        final = df_final
        
    final.to_csv(hist_path, index=False, sep=';', encoding='latin-1', decimal=',')

def atualizar_padroes_e_mestra(df_mestra, lista_lote, vol_real):
    pad_path = "Padroes_Registrados.csv"
    data_at = datetime.now().strftime("%d/%m/%Y %H:%M")
    novos_p = []
    
    for item in lista_lote:
        coef = (item["Quant ad (g_num)"] / vol_real) / 1000
        mask = (df_mestra['Tipo'] == item["tipo de produto"]) & (df_mestra['Cor'] == item["cor"]) & (df_mestra['Pigmento'] == item["pigmento"])
        if mask.any():
            df_mestra.loc[mask, 'Quant OP (kg)'] = coef
        novos_p.append({
            "Data": data_at, "Produto": item["tipo de produto"], "Cor": item["cor"], 
            "Pigmento": item["pigmento"], "Novo Coef": coef, "Lote": item["lote"]
        })
    
    df_mestra.to_csv("Aba_Mestra.csv", index=False, encoding='latin-1')
    pd.DataFrame(novos_p).to_csv(pad_path, mode='a', index=False, sep=';', header=not os.path.exists(pad_path), encoding='latin-1')

# 4. Interface e Navegação
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
        with c3: lote_id = st.text_input("Lote", placeholder="Ex: 2026-001")
        with c4: encom = st.selectbox("Encomenda?", ["Não", "Sim"])
        
        u1, u2, u3 = st.columns([1, 1, 2])
        with u1: n_plan = st.number_input("#Unid Plan", min_value=1, step=1, value=1)
        with u2: n_real = st.number_input("#Unid Real", min_value=1, step=1, value=1)
        with u3:
            sel_vol = st.select_slider("Embalagem:", options=["0,9L", "3,6L", "15L", "18L", "Outro"], value="15L")
            litros = float(sel_vol.replace('L','').replace(',','.')) if sel_vol != "Outro" else st.number_input("Litros Unit:", value=0.9)
        
        st.subheader("🎨 Pigmentos")
        formulas = df_mestra[(df_mestra['Tipo'] == tipo_sel) & (df_mestra['Cor'] == cor_sel)]
        lista_lote = []
        
        for idx, row in formulas.iterrows():
            rec_g = round(row["Quant OP (kg)"] * n_plan * litros * 1000, 2)
            with st.container():
                cp, cpes = st.columns([1, 3])
                with cp:
                    st.markdown(f"**{row['Pigmento']}**")
                    toques = st.number_input("Toques", min_value=1, value=1, key=f"t_{idx}")
                with cpes:
                    soma = 0.0
                    ts = st.columns(5)
                    for t in range(int(toques)):
                        with ts[t%5]:
                            v = st.number_input(f"T{t+1}", min_value=0.0, key=f"v_{idx}_{t}")
                            soma += v
                lista_lote.append({
                    "lote": lote_id, "tipo de produto": tipo_sel, "cor": cor_sel, "pigmento": row['Pigmento'],
                    "toque": toques, "Quant ad (g)": soma, "Quantidade OP": rec_g, "n_plan": n_plan,
                    "n_real": n_real, "Litros/Unit": litros, "Encomenda?": encom, "Quant ad (g_num)": soma
                })
        
        upd = st.checkbox("Atualizar Padrão Técnico?")
        if st.button("FINALIZAR REGISTRO", use_container_width=True):
            if not lote_id: st.error("Informe o Lote!")
            else:
                salvar_no_historico_aq(lista_lote, df_mestra)
                if upd: atualizar_padroes_e_mestra(df_mestra, lista_lote, n_real * litros)
                st.success("Registrado com sucesso!"); st.balloons()

elif aba == "📈 Variações & CEP":
    st.title("📈 Gráfico de Controle (CEP)")
    if os.path.exists("Historico_Producao.csv"):
        df_h = pd.read_csv("Historico_Producao.csv", sep=';', encoding='latin-1', decimal=',')
        p_sel = st.selectbox("Produto", sorted(df_h['tipo de produto'].unique()))
        df_f = df_h[df_h['tipo de produto'] == p_sel]
        st.line_chart(df_f.pivot_table(index='lote', columns='pigmento', values='variação percentual'))

elif aba == "📜 Banco de Dados":
    st.title("📜 Histórico A-Q")
    if os.path.exists("Historico_Producao.csv"):
        df_excl = pd.read_csv("Historico_Producao.csv", sep=';', encoding='latin-1')
        st.dataframe(df_excl, use_container_width=True)
        st.download_button("📥 Baixar CSV", df_excl.to_csv(index=False, sep=';', decimal=',').encode('latin-1'), "historico.csv")

elif aba == "➕ Cadastro":
    st.title("➕ Novo Cadastro")
    with st.form("cad"):
        t, c, p = st.text_input("Produto"), st.text_input("Cor"), st.text_input("Pigmento")
        q = st.number_input("kg/L", format="%.6f")
        if st.form_submit_button("Salvar"):
            nova = pd.DataFrame([{"Tipo":t, "Cor":c, "Pigmento":p, "Quant OP (kg)":q}])
            pd.concat([df_mestra, nova]).to_csv("Aba_Mestra.csv", index=False, encoding='latin-1')
            st.rerun()

elif aba == "📊 Aba Mestra":
    st.title("📊 Editor Aba Mestra")
    ed = st.data_editor(df_mestra, num_rows="dynamic", use_container_width=True)
    if st.button("Salvar Alterações"):
        ed.to_csv("Aba_Mestra.csv", index=False, encoding='latin-1')
        st.success("Mestra Atualizada!")

elif aba == "📋 Padrões":
    st.title("📋 Evolução de Padrões")
    if os.path.exists("Padroes_Registrados.csv"):
        st.dataframe(pd.read_csv("Padroes_Registrados.csv", sep=';', encoding='latin-1'))

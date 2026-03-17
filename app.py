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

# --- FUNÇÕES DE PERSISTÊNCIA (Garantem que os dados fiquem registrados) ---

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
            # Tenta ler com latin-1 e detectando o separador
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
        
        # Atualiza a Aba Mestra em memória
        mask = (df_mestra['Tipo'] == item["tipo de produto"]) & (df_mestra['Cor'] == item["cor"]) & (df_mestra['Pigmento'] == item["pigmento"])
        if mask.any():
            df_mestra.loc[mask, 'Quant OP (kg)'] = novo_coef
        
        # Prepara o log de evolução de padrão
        novos_registros_padrao.append({
            "Data Alteração": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "Data Fabricação": data_fab,
            "Produto": item["tipo de produto"],
            "Cor": item["cor"],
            "Pigmento": item["pigmento"],
            "Novo Coef (kg/L)": novo_coef,
            "Lote Origem": item["lote"]
        })

    # Salva Aba Mestra atualizada
    df_mestra.to_csv("Aba_Mestra.csv", index=False, encoding='latin-1')
    
    # Salva Histórico de Padrões
    df_p = pd.DataFrame(novos_registros_padrao)
    if os.path.exists(padroes_file):
        hist_p = pd.read_csv(padroes_file, encoding='latin-1')
        df_p = pd.concat([hist_p, df_p], ignore_index=True)
    df_p.to_csv(padroes_file, index=False, encoding='latin-1')
    
    return df_mestra, True

def salvar_no_historico(dados_lista):
    hist_path = "Historico_Producao.csv"
    novo_df = pd.DataFrame(dados_lista)
    
    # Colunas organizadas para o CSV
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
menu = ["🚀 Nova Pigmentação", "📈 Variações & CEP", "📋 Padrões", "📜 Banco de Dados", "➕ Cadastro", "📊 Aba Mestra"]
aba = st.sidebar.radio("Navegação:", menu)

if aba == "🚀 Nova Pigmentação":
    st.title("🚀 Registrar Produção")
    
    if df_mestra.empty:
        st.error("Aba Mestra não encontrada! Por favor, cadastre produtos ou importe o arquivo.")
    else:
        # Linha 1: Identificação
        c1, c2, c3, c4 = st.columns([1.5, 1.5, 1, 1])
        with c1:
            tipo_sel = st.selectbox("Produto", sorted(df_mestra['Tipo'].unique()))
        with c2:
            cor_sel = st.selectbox("Cor", sorted(df_mestra[df_mestra['Tipo'] == tipo_sel]['Cor'].unique()))
        with c3:
            lote_id = st.text_input("Lote", placeholder="Ex: 2024001")
        with c4:
            data_prod = st.date_input("Data Fabricação", datetime.now())

        # Linha 2: Volume e Encomenda
        u1, u2, u3, u4 = st.columns([1, 1, 1.5, 1])
        with u1:
            num_plan = st.number_input("#Unid Plan", min_value=1, step=1, value=1)
        with u2:
            num_real = st.number_input("#Unid Real", min_value=1, step=1, value=1)
        with u3:
            opcoes_vol = ["0,9L", "3L", "3,6L", "5kg", "13kg", "15L", "18L", "25kg", "Outro"]
            sel_vol = st.select_slider("Embalagem:", options=opcoes_vol, value="15L")
            litros_unit = float(sel_vol.replace('L','').replace('kg','').replace(',','.')) if sel_vol != "Outro" else st.number_input("Valor Unit (L/kg):", value=15.0)
        with u4:
            encomenda = st.selectbox("📦 Encomenda?", ["Não", "Sim"])

        vol_plan_tot = num_plan * litros_unit
        vol_real_tot = num_real * litros_unit
        
        st.info(f"Cálculo: Planejado {vol_plan_tot:.2f}L | Real {vol_real_tot:.2f}L")
        
        # Pigmentos
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
                    "data": data_prod.strftime("%d/%m/%Y"),
                    "lote": lote_id,
                    "tipo de produto": tipo_sel,
                    "cor": cor_sel,
                    "pigmento": pigm,
                    "toque": n_toques,
                    "Quantidade OP": rec_g, 
                    "Quant ad (g)": soma_ad,
                    "Quant ad (g_num)": soma_ad,
                    "#Plan": num_plan,
                    "#Real": num_real,
                    "Encomenda?": encomenda,
                    "Litros/Unit": litros_unit
                })
                st.markdown("---")
            
            c_p1, c_p2 = st.columns(2)
            with c_p1:
                marcar_p = st.checkbox("⚠️ ATUALIZAR PADRÃO TÉCNICO? (Ajusta a Aba Mestra com base no Real)")
            
            if st.button("✅ FINALIZAR E SALVAR REGISTRO", use_container_width=True):
                if not lote_id:
                    st.error("O número do LOTE é obrigatório!")
                else:
                    if marcar_p:
                        df_mestra, ok = atualizar_padroes_e_mestra(df_mestra, lista_lote, vol_plan_tot, vol_real_tot, data_prod.strftime("%d/%m/%Y"))
                    
                    salvar_no_historico(lista_lote)
                    st.success(f"Lote {lote_id} registrado com sucesso!")
                    st.balloons()

elif aba == "📈 Variações & CEP":
    st.title("📈 Controle Estatístico de Processo (CEP)")
    df_h = load_data("Historico_Producao.csv")
    
    if not df_h.empty:
        # Conversão numérica para cálculos
        for c in ["Quant ad (g)", "Quantidade OP", "#Plan", "#Real", "Litros/Unit"]:
            df_h[c] = pd.to_numeric(df_h[c].astype(str).str.replace(',','.'), errors='coerce').fillna(0)
        
        df_h['Vol_Real'] = df_h['#Real'] * df_h['Litros/Unit']
        df_h['Real_gL'] = df_h['Quant ad (g)'] / df_h['Vol_Real']
        df_h['Padrao_gL'] = (df_h['Quantidade OP'] * 1000) / (df_h['#Plan'] * df_h['Litros/Unit'])
        df_h['Desvio_%'] = ((df_h['Real_gL'] / df_h['Padrao_gL']) - 1) * 100
        
        p_sel = st.selectbox("Produto", sorted(df_h['tipo de produto'].unique()))
        c_sel = st.selectbox("Cor", sorted(df_h[df_h['tipo de produto']==p_sel]['cor'].unique()))
        
        df_f = df_h[(df_h['tipo de produto']==p_sel) & (df_h['cor']==c_sel)].copy()
        
        if not df_f.empty:
            st.subheader(f"Análise: {p_sel} - {c_sel}")
            # Gráfico CEP
            chart_data = df_f.pivot_table(index='lote', columns='pigmento', values='Desvio_%')
            chart_data['Limite Sup'] = 10.0
            chart_data['Limite Inf'] = -10.0
            chart_data['Meta'] = 0.0
            st.line_chart(chart_data)
            
            st.dataframe(df_f[['data', 'lote', 'pigmento', 'Quant ad (g)', 'Desvio_%']].style.format({"Desvio_%": "{:.2f}%"}))
    else:
        st.info("Nenhum dado histórico encontrado.")

elif aba == "📋 Padrões":
    st.title("📋 Histórico de Evolução de Padrões")
    df_p = load_data("Padroes_Registrados.csv")
    if not df_p.empty:
        st.dataframe(df_p, use_container_width=True)
    else:
        st.info("Nenhuma alteração de padrão registrada.")

elif aba == "📜 Banco de Dados":
    st.title("📜 Histórico de Produção")
    df_h = load_data("Historico_Producao.csv")
    if not df_h.empty:
        st.dataframe(df_h, use_container_width=True)
        
        # Opção de baixar o backup
        csv = df_h.to_csv(index=False, encoding='latin-1').encode('latin-1')
        st.download_button("📥 Baixar Backup (CSV)", csv, "historico_backup.csv", "text/csv")
    else:
        st.info("Histórico vazio.")

elif aba == "➕ Cadastro":
    st.title("➕ Cadastrar Novo Produto/Cor")
    with st.form("novo_cad"):
        t = st.text_input("Tipo de Produto (Ex: Acrílico Fosco)")
        c = st.text_input("Nome da Cor")
        p = st.text_input("Nome do Pigmento")
        q = st.number_input("Coeficiente (kg de pigmento por 1L de base)", format="%.8f", step=0.000001)
        if st.form_submit_button("Salvar Cadastro"):
            if t and c and p:
                nova_linha = pd.DataFrame([{"Tipo":t, "Cor":c, "Pigmento":p, "Quant OP (kg)":q}])
                df_mestra = pd.concat([df_mestra, nova_linha], ignore_index=True)
                df_mestra.to_csv("Aba_Mestra.csv", index=False, encoding='latin-1')
                st.success("Cadastrado com sucesso!")
            else:
                st.error("Preencha todos os campos.")

elif aba == "📊 Aba Mestra":
    st.title("📊 Gestão da Aba Mestra")
    if not df_mestra.empty:
        df_edit = st.data_editor(df_mestra, num_rows="dynamic", use_container_width=True)
        if st.button("💾 SALVAR ALTERAÇÕES NA MESTRA"):
            df_edit.to_csv("Aba_Mestra.csv", index=False, encoding='latin-1')
            st.success("Dados mestre atualizados!")

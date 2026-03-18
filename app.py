import streamlit as st
import pandas as pd
import numpy as np
import os
import time
from datetime import datetime, date

# 1. Configuração de Layout
st.set_page_config(page_title="Colortex 2026 - Gestão de R&D", layout="wide", page_icon="🧪")

# --- ESTILO CSS ---
st.markdown("""
    <style>
    .stNumberInput { margin-bottom: -1rem; }
    .stButton > button { width: 100%; background-color: #d4edda; color: #155724; font-weight: bold; height: 3em; }
    .btn-delete > div > button { background-color: #f8d7da !important; color: #721c24 !important; border: 1px solid #f5c6cb !important; }
    hr { margin: 0.8rem 0rem !important; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNÇÕES DE TRATAMENTO DE DADOS ---
def carregar_dados(arquivo):
    if not os.path.exists(arquivo): return pd.DataFrame()
    try:
        try:
            df = pd.read_csv(arquivo, sep=None, engine='python', encoding='latin-1')
        except:
            df = pd.read_csv(arquivo, sep=None, engine='python', encoding='utf-8')
        
        df.columns = [str(c).strip() for c in df.columns]
        
        # Limpeza de strings e conversão de números (vírgula para ponto)
        for col in df.columns:
            if df[col].dtype == 'object':
                df[col] = df[col].astype(str).str.strip()
        
        cols_num = ['Quantidade OP', 'Quant ad (g)', '#Plan', 'Litros/Unit']
        for col in cols_num:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce')
        
        if 'data' in df.columns:
            df['data_dt'] = pd.to_datetime(df['data'], format='%d/%m/%Y', errors='coerce')
        return df
    except: return pd.DataFrame()

def salvar_csv(df, arquivo):
    df_save = df.drop(columns=['data_dt', 'toque'], errors='ignore').copy()
    if 'Quantidade OP' in df_save.columns:
        df_save['Quantidade OP'] = pd.to_numeric(df_save['Quantidade OP'], errors='coerce').map('{:.5f}'.format)
    df_save.to_csv(arquivo, index=False, encoding='latin-1')

# --- CARREGAMENTO INICIAL ---
df_mestra = carregar_dados("Aba_Mestra.csv")
df_hist = carregar_dados("Historico_Producao.csv")
df_padr = carregar_dados("Padroes_Registrados.csv")

# --- 🔄 LÓGICA DE SINCRONIZAÇÃO INTELIGENTE ---
# Esta parte garante que o histórico sempre tenha a Quantidade OP correta da Aba Mestra
if not df_hist.empty and not df_mestra.empty:
    # Criamos um dicionário de mapeamento da Aba Mestra para busca rápida
    mapeamento = df_mestra.set_index(['Tipo', 'Cor', 'Pigmento'])['Quant OP (kg)'].to_dict()
    
    def buscar_coeficiente(row):
        chave = (row['tipo de produto'], row['cor'], row['pigmento'])
        return mapeamento.get(chave, row['Quantidade OP'])

    # Atualiza apenas onde está NaN ou se você quiser forçar a atualização da Mestra:
    df_hist['Quantidade OP'] = df_hist.apply(buscar_coeficiente, axis=1)

# --- NAVEGAÇÃO ---
menu = ["🚀 Produção", "📈 Gráficos CEP", "📋 Padrões Registrados", "📜 Banco de Dados", "➕ Cadastro de Produtos", "📊 Editor Aba Mestra", "📂 Importar CSV"]
aba = st.sidebar.radio("Navegação:", menu)

# --- 🚀 ABA: PRODUÇÃO --- (Mantida)
if aba == "🚀 Produção":
    st.title("🚀 Registro de Pesagem")
    if df_mestra.empty:
        st.warning("⚠️ Aba Mestra vazia.")
    else:
        c1, c2, c3, c4 = st.columns([1.5, 1.5, 1, 1])
        with c1: t_sel = st.selectbox("Produto", sorted(df_mestra['Tipo'].unique()))
        with c2: cor_sel = st.selectbox("Cor", sorted(df_mestra[df_mestra['Tipo'] == t_sel]['Cor'].unique()))
        with c3: lote_id = st.text_input("Lote")
        with c4: data_f = st.date_input("Data", datetime.now(), format="DD/MM/YYYY")

        v1, v2, v3, v4 = st.columns([1, 1, 2, 1.5])
        with v1: n_p = st.number_input("# Unid Plan", min_value=1, value=1)
        with v2: n_r = st.number_input("# Unid Real", min_value=1, value=1)
        with v3:
            opcoes_v = ["0,9L", "3L", "3,6L", "14L", "15L", "18L", "5kg", "18kg", "25kg", "Outro"]
            sel_v = st.select_slider("Embalagem:", options=opcoes_v, value="15L")
            litros_u = float(sel_v.replace('L','').replace('kg','').replace(',','.')) if sel_v != "Outro" else st.number_input("Valor Unit:", value=15.0)
        with v4:
            st.write("") 
            salvar_como_padrao = st.checkbox("🌟 Salvar como novo padrão")

        vol_p_tot = n_p * litros_u
        formula = df_mestra[(df_mestra['Tipo'] == t_sel) & (df_mestra['Cor'] == cor_sel)]
        st.divider()

        registros_lote = []
        for i, row in formula.iterrows():
            pigm = row['Pigmento']
            coef = float(row['Quant OP (kg)'])
            sugestao_g = round(coef * vol_p_tot * 1000, 2)
            
            with st.container():
                col_i, col_p = st.columns([1.5, 3.5])
                with col_i:
                    st.subheader(pigm)
                    st.write(f"Sugestão: {sugestao_g}g")
                    n_t = st.number_input(f"Toques", min_value=1, value=1, key=f"nt_{i}")
                with col_p:
                    s_ad = 0.0
                    cols = st.columns(5)
                    for t in range(1, int(n_t) + 1):
                        with cols[(t-1)%5]:
                            v = st.number_input(f"T{t}", min_value=0.0, format="%.2f", key=f"v_{i}_{t}")
                            s_ad += v
                    st.markdown(f"**Total: {s_ad:.2f} g**")
            registros_lote.append({
                "data": data_f.strftime("%d/%m/%Y"), "lote": lote_id, "tipo de produto": t_sel,
                "cor": cor_sel, "pigmento": pigm, "Quant ad (g)": s_ad,
                "Quantidade OP": coef, "#Plan": n_p, "#Real": n_r, "Litros/Unit": litros_u
            })
            st.divider()

        if st.button("💾 SALVAR LOTE"):
            if not lote_id: st.error("Preencha o Lote.")
            else:
                df_hist = pd.concat([df_hist, pd.DataFrame(registros_lote)], ignore_index=True)
                salvar_csv(df_hist, "Historico_Producao.csv")
                st.balloons(); st.success("Lote salvo!"); time.sleep(1.2); st.rerun()

# --- 📈 ABA: GRÁFICOS CEP ---
elif aba == "📈 Gráficos CEP":
    st.title("📈 Dashboard de Qualidade")
    if df_hist.empty: st.info("Sem dados.")
    else:
        with st.expander("🔍 Filtros", expanded=True):
            f1, f2, f3, f4, f5 = st.columns([1.2, 1, 1, 1.5, 1.5])
            with f1: usar_filtro = st.checkbox("Filtrar Data?", value=False)
            with f2: d_ini = st.date_input("Início", date(datetime.now().year, datetime.now().month, 1), format="DD/MM/YYYY", disabled=not usar_filtro)
            with f3: d_fim = st.date_input("Fim", datetime.now(), format="DD/MM/YYYY", disabled=not usar_filtro)
            with f4: p_sel = st.selectbox("Produto", sorted(df_hist['tipo de produto'].unique()))
            with f5: c_sel = st.selectbox("Cor", sorted(df_hist[df_hist['tipo de produto'] == p_sel]['cor'].unique()))

        df_plot = df_hist[(df_hist['tipo de produto'] == p_sel) & (df_hist['cor'] == c_sel)].copy()
        if usar_filtro: df_plot = df_plot[(df_plot['data_dt'].dt.date >= d_ini) & (df_plot['data_dt'].dt.date <= d_fim)]

        if not df_plot.empty:
            # Cálculos baseados no volume planejado do lote
            df_plot['OP_Sugerida_g'] = df_plot['Quantidade OP'] * (df_plot['#Plan'] * df_plot['Litros/Unit']) * 1000
            df_plot['Desvio (g)'] = df_plot['Quant ad (g)'] - df_plot['OP_Sugerida_g']
            df_plot['Var %'] = ((df_plot['Quant ad (g)'] / df_plot['OP_Sugerida_g'].replace(0, np.nan)) - 1) * 100
            
            st.subheader("Tendência de Desvios (%)")
            st.line_chart(df_plot.pivot_table(index='lote', columns='pigmento', values='Var %'))
            
            st.subheader("📋 Dados Brutos Filtrados")
            df_table = df_plot.drop(columns=['data_dt', 'OP_Sugerida_g', 'Var %'], errors='ignore').copy()
            df_table['Situação'] = df_table.apply(lambda r: "✅ Ok" if r['Quant ad (g)'] <= (r['Quantidade OP'] * (r['#Plan'] * r['Litros/Unit']) * 1100) else "⚠️ Alerta", axis=1)
            
            st.dataframe(df_table.style.format({'Quantidade OP': '{:.5f}', 'Desvio (g)': '{:.1f}'}), use_container_width=True)
            
            csv_data = df_plot.to_csv(index=False).encode('utf-8-sig')
            st.download_button(label="📥 Baixar Relatório (CSV)", data=csv_data, file_name=f"CEP_{p_sel}_{c_sel}.csv", mime="text/csv")

# --- 📜 ABA: BANCO DE DADOS (COM EXPORTAÇÃO COMPLETA) ---
elif aba == "📜 Banco de Dados":
    st.title("📜 Banco de Dados - Histórico de Produção")
    
    if not df_hist.empty:
        # Criar DataFrame de visualização e exportação com cálculos automáticos
        df_export = df_hist.copy()
        
        # Cálculo: Quantidade OP (kg/L) * Volume Total Planejado (L) * 1000 = Gramas teóricas
        df_export['Sugestão OP (g)'] = df_export['Quantidade OP'] * (df_export['#Plan'] * df_export['Litros/Unit']) * 1000
        df_export['Desvio (g)'] = df_export['Quant ad (g)'] - df_export['Sugestão OP (g)']
        df_export['Var %'] = ((df_export['Quant ad (g)'] / df_export['Sugestão OP (g)'].replace(0, np.nan)) - 1) * 100
        
        st.subheader("Visualização dos Registros")
        st.dataframe(df_export.drop(columns=['data_dt'], errors='ignore'), use_container_width=True)
        
        # Botão de Download do Banco Completo com os cálculos
        csv_full = df_export.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
        st.download_button(
            label="📥 Exportar Banco de Dados Completo (com Desvios)",
            data=csv_full,
            file_name=f"Backup_Producao_{datetime.now().strftime('%d_%m_%Y')}.csv",
            mime="text/csv"
        )
    else:
        st.info("Banco de dados vazio.")

    st.divider()
    # Manutenção de Lotes (Apagar)
    st.subheader("🗑️ Manutenção: Apagar Lote")
    lote_d = st.text_input("Lote para EXCLUIR:", key="del_in")
    if lote_d:
        res_d = df_hist[df_hist['lote'].astype(str) == lote_d]
        if not res_d.empty:
            st.warning(f"Isso apagará {len(res_d)} linhas de pigmentos.")
            st.markdown('<div class="btn-delete">', unsafe_allow_html=True)
            if st.button(f"🚨 EXCLUIR LOTE {lote_d}"):
                df_hist = df_hist[df_hist['lote'].astype(str) != lote_d]
                salvar_csv(df_hist, "Historico_Producao.csv")
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

# --- OUTRAS ABAS (CADASTRO, EDITOR, IMPORTAR) ---
elif aba == "➕ Cadastro de Produtos":
    st.title("➕ Novo Pigmento")
    with st.form("f_cad"):
        c1, c2 = st.columns(2)
        t = c1.text_input("Tipo"); p = c1.text_input("Pigmento"); cor = c2.text_input("Cor"); coef = c2.number_input("Coef (kg/L)", format="%.6f")
        if st.form_submit_button("Cadastrar"):
            if t and cor and p:
                n = pd.DataFrame([{"Tipo": t.title(), "Cor": cor.title(), "Pigmento": p.title(), "Quant OP (kg)": coef}])
                df_mestra = pd.concat([df_mestra, n], ignore_index=True); salvar_csv(df_mestra, "Aba_Mestra.csv"); st.success("Salvo!")

elif aba == "📊 Editor Aba Mestra":
    ed = st.data_editor(df_mestra, num_rows="dynamic")
    if st.button("Salvar Alterações"): salvar_csv(ed, "Aba_Mestra.csv"); st.success("Atualizado!")

elif aba == "📂 Importar CSV":
    up = st.file_uploader("Selecione o arquivo CSV", type="csv")
    alvo = st.selectbox("Destino", ["Aba_Mestra.csv", "Historico_Producao.csv", "Padroes_Registrados.csv"])
    if up and st.button("Confirmar Importação"):
        df_imp = pd.read_csv(up, encoding='latin-1', sep=None, engine='python')
        salvar_csv(df_imp, alvo); st.success("Importado!"); st.rerun()

elif aba == "📋 Padrões Registrados":
    st.title("📋 Padrões")
    st.dataframe(df_padr, use_container_width=True)

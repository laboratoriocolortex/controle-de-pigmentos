import streamlit as st
import pandas as pd
import os
from datetime import datetime

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

# --- FUNÇÕES AUXILIARES ---
def format_excel_num(valor):
    if valor is None or valor == "": return ""
    try:
        val_float = float(valor)
        if val_float == int(val_float):
            return str(int(val_float))
        return f"{val_float:.2f}".replace('.', ',')
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

def atualizar_padroes_e_mestra(df_mestra, lista_lote, vol_plan_calculo, vol_real_calculo):
    """
    Converte a quantidade usada no Real para a proporção do Planejado
    e salva como novo padrão (Coeficiente técnico ideal).
    """
    padroes_file = "Padroes_Registrados.csv"
    novos_registros_padrao = []
    data_atual = datetime.now().strftime("%d/%m/%Y %H:%M")

    # Se não houver volume real ou planejado, não há como calcular proporção
    if vol_real_calculo <= 0 or vol_plan_calculo <= 0:
        return df_mestra, False

    for item in lista_lote:
        # 1. Descobrimos a concentração REAL (g por Litro que estava no tanque)
        concentracao_real_g_l = item["Quant ad (g_num)"] / vol_real_calculo
        
        # 2. Convertemos para o Coeficiente Técnico (kg/L) 
        # Como o objetivo é o Planejado, o coeficiente permanece o mesmo kg/L 
        # mas a base de cálculo garante que o desvio do envase real seja neutralizado.
        novo_coef = (concentracao_real_g_l / 1000) 
        
        mask = (df_mestra['Tipo'] == item["tipo de produto"]) & \
               (df_mestra['Cor'] == item["cor"]) & \
               (df_mestra['Pigmento'] == item["pigmento"])
        
        if mask.any():
            if item["Quant ad (g_num)"] <= 0:
                df_mestra = df_mestra.drop(df_mestra[mask].index)
            else:
                df_mestra.loc[mask, 'Quant OP (kg)'] = novo_coef
        
        novos_registros_padrao.append({
            "Data Alteração": data_atual,
            "Produto": item["tipo de produto"],
            "Cor": item["cor"],
            "Pigmento": item["pigmento"],
            "Novo Coef (kg/L)": round(novo_coef, 6),
            "Lote Origem": item["lote"],
            "Qtd Usada Real (g)": item["Quant ad (g_num)"],
            "Vol Real (L)": round(vol_real_calculo, 2),
            "Vol Plan (L)": round(vol_plan_calculo, 2)
        })

    df_mestra.to_csv("Aba_Mestra.csv", index=False, encoding='latin-1')
    
    df_p = pd.DataFrame(novos_registros_padrao)
    if os.path.exists(padroes_file):
        hist_p = pd.read_csv(padroes_file, encoding='latin-1', sep=';')
        df_p = pd.concat([hist_p, df_p], ignore_index=True)
    
    df_p.to_csv(padroes_file, index=False, sep=';', encoding='latin-1')
    return df_mestra, True

def salvar_no_historico(dados_lista):
    hist_path = "Historico_Producao.csv"
    processados = []
    for i, item in enumerate(dados_lista):
        temp = item.copy()
        temp["Quantidade OP"] = format_excel_num(temp["Quantidade OP"])
        temp["Quant ad (g)"] = format_excel_num(temp["Quant ad (g)"])
        if i == 0:
            temp["#Plan"] = format_excel_num(temp["#Plan"])
            temp["#Real"] = format_excel_num(temp["#Real"])
            temp["Litros/Unit"] = format_excel_num(temp["Litros/Unit"])
        else:
            temp["#Plan"] = ""; temp["#Real"] = ""; temp["Litros/Unit"] = ""
        if "Quant ad (g_num)" in temp: del temp["Quant ad (g_num)"]
        processados.append(temp)

    novo_df = pd.DataFrame(processados)
    colunas_excel = ["data", "lote", "tipo de produto", "cor", "pigmento", "toque", "Quant ad (g)", "Quantidade OP", "#Plan", "#Real", "Encomenda?", "Litros/Unit"]
    
    if os.path.exists(hist_path):
        hist_existente = pd.read_csv(hist_path, encoding='latin-1', sep=';')
        hist_final = pd.concat([hist_existente, novo_df[colunas_excel]], ignore_index=True)
    else:
        hist_final = novo_df[colunas_excel]
    hist_final.to_csv(hist_path, index=False, sep=';', encoding='latin-1')

# --- INÍCIO APP ---
df_mestra = load_data("Aba_Mestra.csv")
aba = st.sidebar.radio("Navegação:", ["🚀 Nova Pigmentação", "📋 Padrões", "📜 Banco de Dados", "➕ Cadastro", "📊 Aba Mestra"])

if aba == "🚀 Nova Pigmentação":
    st.title("🚀 Registrar Produção")
    
    if df_mestra.empty:
        st.warning("Aba Mestra vazia.")
    else:
        c1, c2, c3, c4 = st.columns([1.5, 1.5, 1, 1])
        with c1: tipo_sel = st.selectbox("Produto", df_mestra['Tipo'].unique())
        with c2: cor_sel = st.selectbox("Cor", df_mestra[df_mestra['Tipo'] == tipo_sel]['Cor'].unique())
        with c3: lote_id = st.text_input("Lote", value="", placeholder="Nº Lote")
        with c4: encomenda = st.selectbox("📦 Encomenda?", ["Não", "Sim"])

        st.markdown("---")
        u1, u2, u3 = st.columns([1, 1, 2])
        with u1: num_plan = st.number_input("#Unid Plan", min_value=1, step=1, value=None)
        with u2: num_real = st.number_input("#Unid Real", min_value=1, step=1, value=None)
        with u3:
            opcoes_vol = ["0,9L", "3L", "3,6L", "5kg", "13kg", "15L", "18L", "25kg", "Outro"]
            selecao_vol = st.select_slider("Embalagem:", options=opcoes_vol, value="15L")
            litros_unit = float(selecao_vol.replace('L', '').replace('kg', '').replace(',', '.')) if selecao_vol != "Outro" else st.number_input("Valor Unit:", value=None)
        
        # Cálculos de Volume
        vol_plan_tot = (num_plan * litros_unit) if (num_plan and litros_unit) else 0
        vol_real_tot = (num_real * litros_unit) if (num_real and litros_unit) else vol_plan_tot
        
        st.info(f"*Base Planejada:* {vol_plan_tot:.2f}L | *Base Real (Envase):* {vol_real_tot:.2f}L")
        
        st.subheader("🎨 Pigmentos")
        st.markdown("---")

        formulas = df_mestra[(df_mestra['Tipo'] == tipo_sel) & (df_mestra['Cor'] == cor_sel)]
        
        if not formulas.empty:
            lista_lote = []
            for index, row in formulas.iterrows():
                pigm = row['Pigmento']
                rec_g = round(row["Quant OP (kg)"] * vol_plan_tot * 1000, 2)
                
                with st.container():
                    col_pigm, col_espaco, col_pesagem = st.columns([1.2, 0.3, 3.5])
                    with col_pigm:
                        st.markdown(f"### {pigm}")
                        st.caption(f"Sugestão OP: {rec_g}g")
                        n_toques = st.number_input(f"Toques", min_value=1, value=1, step=1, key=f"nt_{index}")
                    
                    with col_pesagem:
                        st.write("Pesagens (g):")
                        soma_adicionada = 0.0
                        cols_t = st.columns(5)
                        for t in range(1, int(n_toques) + 1):
                            with cols_t[(t-1) % 5]:
                                valor_t = st.number_input(f"T{t}", min_value=0.0, format="%.2f", value=None, key=f"val_{index}_{t}")
                                if valor_t: soma_adicionada += valor_t
                        st.markdown(f"*Total Adicionado: {soma_adicionada:.2f} g*")
                    
                    lista_lote.append({
                        "data": datetime.now().strftime("%d/%m/%Y"), "lote": lote_id, "tipo de produto": tipo_sel,
                        "cor": cor_sel, "pigmento": pigm, "toque": n_toques, "Quantidade OP": rec_g, 
                        "Quant ad (g)": soma_adicionada, "Quant ad (g_num)": soma_adicionada,
                        "#Plan": num_plan, "#Real": num_real, "Encomenda?": encomenda, "Litros/Unit": litros_unit
                    })
                    st.markdown("<hr>", unsafe_allow_html=True)
            
            marcar_novo_padrao = st.checkbox("⚠️ Atualizar Padrão Técnico? (Converte Real → Planejado)")
            
            if st.button("✅ FINALIZAR E SALVAR REGISTRO", use_container_width=True):
                if not lote_id or not num_plan:
                    st.error("Preencha Lote e Unidades Planejadas!")
                else:
                    if marcar_novo_padrao:
                        if not num_real:
                            st.error("Para atualizar o padrão, informe a quantidade Real envasada!")
                        else:
                            df_mestra, sucesso = atualizar_padroes_e_mestra(df_mestra, lista_lote, vol_plan_tot, vol_real_tot)
                            if sucesso:
                                st.warning("Padrão Técnico recalibrado para a base Planejada!")
                    
                    salvar_no_historico(lista_lote)
                    st.success("Registro concluído!")
                    st.balloons()

elif aba == "📋 Padrões":
    st.title("📋 Evolução de Padrões Técnicos")
    if os.path.exists("Padroes_Registrados.csv"):
        df_p = pd.read_csv("Padroes_Registrados.csv", sep=';', encoding='latin-1')
        st.dataframe(df_p.style.format({"Novo Coef (kg/L)": "{:.6f}"}), use_container_width=True)
    else: st.info("Sem atualizações.")

elif aba == "📜 Banco de Dados":
    st.title("📜 Histórico Geral")
    if os.path.exists("Historico_Producao.csv"):
        df_hist = pd.read_csv("Historico_Producao.csv", sep=';', encoding='latin-1')
        st.dataframe(df_hist, use_container_width=True)

elif aba == "➕ Cadastro":
    st.title("➕ Cadastro Manual")
    with st.form("cad"):
        t = st.text_input("Produto"); c = st.text_input("Cor"); p = st.text_input("Pigmento")
        q = st.number_input("kg/1L", format="%.8f", value=None)
        if st.form_submit_button("Salvar"):
            pd.concat([df_mestra, pd.DataFrame([{"Tipo": t, "Cor": c, "Pigmento": p, "Quant OP (kg)": q}])], ignore_index=True).to_csv("Aba_Mestra.csv", index=False, encoding='latin-1')
            st.success("Cadastrado!"); st.rerun()

elif aba == "📊 Aba Mestra":
    st.title("📊 Aba Mestra (Atual)")
    st.dataframe(df_mestra.style.format({"Quant OP (kg)": "{:.6f}"}), use_container_width=True)

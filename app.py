import streamlit as st
import pandas as pd
import os
from datetime import datetime

# Configuração da página para aproveitar melhor o espaço
st.set_page_config(page_title="Gestão de Produção & Pigmentos", layout="wide", page_icon="🧪")

# --- FUNÇÃO PARA CARREGAR DADOS ---
def load_data():
    file_path = "Aba_Mestra.csv"
    if os.path.exists(file_path):
        try:
            # Tenta ler com diferentes encodings (Excel costuma usar latin-1)
            try:
                df = pd.read_csv(file_path, sep=None, engine='python', encoding='utf-8')
            except:
                df = pd.read_csv(file_path, sep=None, engine='python', encoding='latin-1')
            
            # Padronização de nomes de colunas
            df.columns = [str(c).strip() for c in df.columns]
            
            # Converte a coluna Quant OP para numérico (trata vírgula e erro)
            col_qtd = "Quant OP (kg)"
            if col_qtd in df.columns:
                df[col_qtd] = df[col_qtd].astype(str).str.replace(',', '.')
                df[col_qtd] = pd.to_numeric(df[col_qtd], errors='coerce').fillna(0.0)
            
            return df
        except Exception as e:
            st.error(f"Erro ao carregar Aba_Mestra.csv: {e}")
            return pd.DataFrame()
    else:
        # Se não existir, cria uma estrutura básica
        return pd.DataFrame(columns=["Tipo", "Cor", "Pigmento", "Quant OP (kg)"])

df_mestra = load_data()

# --- NAVEGAÇÃO LATERAL ---
st.sidebar.title("🧪 Menu de Gestão")
aba = st.sidebar.radio("Navegação:", ["🚀 Ordem de Produção", "➕ Cadastrar Nova Cor", "📊 Ver Aba Mestra"])

# --- ABA 1: ORDEM DE PRODUÇÃO ---
if aba == "🚀 Ordem de Produção":
    st.title("🚀 Registro de Pigmentação")
    
    if df_mestra.empty:
        st.warning("A base de dados está vazia. Cadastre cores na aba lateral.")
    else:
        # 1. Identificação da Ordem
        c1, c2, c3 = st.columns(3)
        with c1:
            tipo_sel = st.selectbox("Tipo de Produto", df_mestra['Tipo'].unique())
            encomenda = st.selectbox("Encomenda?", ["Não", "Sim"])
        with c2:
            cores_disp = df_mestra[df_mestra['Tipo'] == tipo_sel]['Cor'].unique()
            cor_sel = st.selectbox("Cor", cores_disp)
        with c3:
            lote_id = st.text_input("Nº do Lote", value=datetime.now().strftime("%Y%m%d-%H%M"))

        st.markdown("---")
        
        # 2. Definição da Litragem (Conforme sua planilha)
        st.subheader("📦 Volume e Unidades")
        cp1, cp2, cp3 = st.columns(3)
        with cp1:
            num_baldes_plan = st.number_input("Unidades (#Plan)", min_value=1, step=1, value=1)
        with cp2:
            litros_unit = st.number_input("Litros/Unit (L/kg)", min_value=0.01, value=15.0)
        with cp3:
            vol_planejado = num_baldes_plan * litros_unit
            st.metric("Volume Total Planejado", f"{vol_planejado:.2f} L")

        # Busca a formulação (pode ter várias linhas/pigmentos)
        formulas = df_mestra[(df_mestra['Tipo'] == tipo_sel) & (df_mestra['Cor'] == cor_sel)]
        
        if not formulas.empty:
            st.subheader("🎨 Registro de Pigmentos e Toques")
            with st.form("registro_producao"):
                dados_relatorio = []
                
                for index, row in formulas.iterrows():
                    pigm = row['Pigmento']
                    base_1kg = row["Quant OP (kg)"]
                    sugerido_total_kg = base_1kg * vol_planejado
                    
                    st.markdown(f"#### 🧪 Pigmento: {pigm}")
                    col_t1, col_t2, col_t3 = st.columns(3)
                    
                    with col_t1:
                        # Campo "toque" solicitado
                        toques = st.number_input(f"Toques", min_value=0, step=1, key=f"tq_{index}")
                    with col_t2:
                        # "Quant ad (g)" - Sugestão em gramas para facilitar a balança
                        sug_gramas = sugerido_total_kg * 1000
                        qtd_ad = st.number_input(f"Quant ad (g)", value=float(sug_gramas), format="%.2f", key=f"ad_{index}")
                    with col_t3:
                        # "Peso Real (kg)" - Registro final em kg
                        peso_real_kg = st.number_input(f"Peso Real (kg)", value=float(sugerido_total_kg), format="%.8f", key=f"re_{index}")

                    dados_relatorio.append({
                        "Data": datetime.now().strftime("%d/%m/%Y"),
                        "Lote": lote_id,
                        "Tipo de Produto": tipo_sel,
                        "Cor": cor_sel,
                        "Pigmento": pigm,
                        "Toque": toques,
                        "Quant ad (g)": qtd_ad,
                        "#Plan": num_baldes_plan,
                        "Litros/Unit": litros_unit,
                        "Volume Planejado": vol_planejado,
                        "Peso Real (kg)": peso_real_kg,
                        "Encomenda?": encomenda
                    })

                st.markdown("---")
                num_baldes_real = st.number_input("Unidades Produzidas (#Real)", value=int(num_baldes_plan))
                
                finalizar = st.form_submit_button("✅ Finalizar e Gerar Dados")

            if finalizar:
                df_rel = pd.DataFrame(dados_relatorio)
                df_rel["#Real"] = num_baldes_real
                df_rel["Volume Produzido"] = num_baldes_real * litros_unit
                
                st.success("Ordem Processada!")
                st.dataframe(df_rel, use_container_width=True)
                
                # Botão de download formatado para abrir direto no Excel (separador ;)
                csv_data = df_rel.to_csv(index=False, sep=';', encoding='latin-1').encode('latin-1')
                st.download_button(
                    label="📥 Baixar Dados para Controle Excel",
                    data=csv_data,
                    file_name=f"Controle_{lote_id}.csv",
                    mime="text/csv",
                )
        else:
            st.error("Nenhuma fórmula encontrada para este Tipo/Cor.")

# --- ABA 2: CADASTRO ---
elif aba == "➕ Cadastrar Nova Cor":
    st.title("➕ Cadastrar Nova Fórmula")
    st.info("Adicione os pigmentos um a um para compor a cor do produto.")
    
    with st.form("cadastro_cor"):
        c1, c2 = st.columns(2)
        with c1: novo_tipo = st.text_input("Tipo de Produto (Ex: Tinta Acrílica)")
        with c2: nova_cor = st.text_input("Nome da Cor")
        
        c3, c4 = st.columns(2)
        with c3: 
            novo_pigm = st.selectbox("Selecione o Pigmento", ["Amarelo Limpo", "Amarelo Óxido", "Vermelho Limpo", "Vermelho Óxido", "Azul", "Preto", "Branco", "Verde", "Outro"])
            if novo_pigm == "Outro": novo_pigm = st.text_input("Nome do Pigmento Especial")
        with c4: nova_quant = st.number_input("Quant OP (kg) para 1L/1kg", format="%.8f", step=0.00000001)
        
        if st.form_submit_button("💾 Salvar na Aba Mestra"):
            if novo_tipo and nova_cor:
                nova_linha = pd.DataFrame([{
                    "Tipo": novo_tipo.strip(),
                    "Cor": nova_cor.strip(),
                    "Pigmento": novo_pigm,
                    "Quant OP (kg)": nova_quant
                }])
                df_mestra = pd.concat([df_mestra, nova_linha], ignore_index=True)
                df_mestra.to_csv("Aba_Mestra.csv", index=False, encoding='utf-8')
                st.success("Dados salvos na Aba Mestra!")
                st.rerun()
            else:
                st.error("Preencha Produto e Cor.")

# --- ABA 3: VISUALIZAÇÃO ---
elif aba == "📊 Ver Aba Mestra":
    st.title("📊 Consulta de Dados Cadastrados")
    st.dataframe(df_mestra, use_container_width=True)

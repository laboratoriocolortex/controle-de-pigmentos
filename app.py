# --- 📈 ABA: CEP (VERSÃO CORRIGIDA COM PIVOT E CONVERSÃO FORÇADA) ---
elif aba == "📈 Gráficos CEP":
    st.title("📈 Controle Estatístico de Processo (CEP)")
    
    # Recarrega para garantir dados frescos
    df_cep_raw = carregar_dados("Historico_Producao.csv")
    
    if df_cep_raw.empty:
        st.info("O histórico está vazio. Registe uma produção primeiro.")
    else:
        # 1. LIMPEZA E CONVERSÃO FORÇADA
        df_cep = df_cep_raw.copy()
        
        # Colunas que precisam de ser números para o gráfico funcionar
        cols_calc = ['Quant ad (g)', 'Quantidade OP']
        for col in cols_calc:
            if col in df_cep.columns:
                # Remove espaços, troca vírgula por ponto e converte para float
                df_cep[col] = pd.to_numeric(df_cep[col].astype(str).str.replace(',', '.'), errors='coerce').fillna(0.0)

        # 2. CÁLCULO DO DESVIO % (Real vs Planeado)
        # Se Quantidade OP estiver em kg na Mestra, multiplicamos por 1000 para comparar com gramas (Quant ad)
        df_cep['Desvio_%'] = ((df_cep['Quant ad (g)'] / (df_cep['Quantidade OP'] * 1000 + 0.000001)) - 1) * 100

        # 3. FILTROS LATERAIS (Para não misturar cores no gráfico)
        st.subheader("Filtros de Visualização")
        f1, f2 = st.columns(2)
        with f1:
            lista_produtos = sorted(df_cep['tipo de produto'].unique())
            p_filt = st.selectbox("Escolha o Produto", lista_produtos)
        with f2:
            lista_cores = sorted(df_cep[df_cep['tipo de produto'] == p_filt]['cor'].unique())
            c_filt = st.selectbox("Escolha a Cor", lista_cores)

        # 4. FILTRAGEM DOS DADOS
        df_plot = df_cep[(df_cep['tipo de produto'] == p_filt) & (df_cep['cor'] == c_filt)]

        if not df_plot.empty:
            st.markdown(f"### Desvios para: {p_filt} {c_filt}")
            
            # 5. CRIAÇÃO DA TABELA PARA O GRÁFICO (Lote no eixo X, Pigmentos nas Linhas)
            try:
                # O pivot organiza os dados para o Streamlit entender as múltiplas linhas
                chart_data = df_plot.pivot_table(
                    index='lote', 
                    columns='pigmento', 
                    values='Desvio_%', 
                    aggfunc='mean'
                )
                
                # Exibe o Gráfico
                st.line_chart(chart_data)
                
                # Exibe a Tabela de Apoio
                st.write("Dados Detalhados (Desvios em %):")
                st.dataframe(df_plot[['data', 'lote', 'pigmento', 'Quant ad (g)', 'Desvio_%']].style.format({"Desvio_%": "{:.2f}%"}))
                
            except Exception as e:
                st.error(f"Erro ao gerar gráfico: {e}")
                st.info("Dica: Verifique se os números das colunas 'Quant ad (g)' e 'Quantidade OP' no seu Banco de Dados estão corretos.")
        else:
            st.warning("Nenhum dado encontrado para esta combinação de Produto e Cor.")

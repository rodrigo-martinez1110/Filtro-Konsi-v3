# pages/2_Filtro_Simulacoes.py
import streamlit as st
import pandas as pd

# Importa as funções necessárias dos nossos módulos
from data_handler import carregar_arquivos_simulacoes, converter_df_para_csv
from ui_components import exibir_sidebar_simulacoes
from filters import aplicar_filtro_simulacoes

# --- 1. Configuração da Página ---
st.set_page_config(page_title="Processador de Simulações", layout="wide")
st.title("⚙️ Processador de Arquivos com Simulações")
st.info(
    "Esta página é projetada para processar arquivos que contêm uma coluna 'Simulacoes', "
    "extraindo a melhor oferta de saque benefício para cada cliente."
)

# --- 2. Interface do Usuário ---
params = exibir_sidebar_simulacoes()

st.header("📂 Upload de Arquivos")
uploaded_files = st.file_uploader(
    "Selecione os arquivos de simulação para processar",
    type="csv",
    accept_multiple_files=True,
    key="uploader_simulacoes"
)

# --- 3. Lógica Principal ---
if uploaded_files:
    # Carrega os dados usando a função específica para este tipo de arquivo
    base_bruta = carregar_arquivos_simulacoes(uploaded_files)

    if not base_bruta.empty:
        st.write("Amostra dos dados carregados:")
        st.dataframe(base_bruta.head())

        if st.button("🚀 Processar Arquivos e Gerar Campanha", type="primary", use_container_width=True):
            with st.spinner("Extraindo e processando simulações..."):
                # Aplica o filtro específico para simulações
                base_final = aplicar_filtro_simulacoes(base_bruta, params)

                if not base_final.empty:
                    st.success("Arquivos processados com sucesso!")
                    st.subheader("📊 Resultado Final")
                    st.dataframe(base_final)
                    st.metric("Total de registros na campanha final", f"{len(base_final)}")

                    # Download do resultado
                    csv = converter_df_para_csv(base_final)
                    nome_convenio = base_final["Convenio"].iloc[0] if pd.notna(base_final["Convenio"].iloc[0]) else "GERAL"
                    data_hoje = datetime.today().strftime('%d%m%Y')
                    
                    st.download_button(
                        label="📥 Baixar Resultado Final em CSV",
                        data=csv,
                        file_name=f'{nome_convenio}_BENEFICIO_SIMULACAO_{params["equipe"].upper()}_{data_hoje}.csv',
                        mime='text/csv',
                        use_container_width=True
                    )
                else:
                    st.warning("O processamento não resultou em dados válidos. Verifique o conteúdo dos arquivos e os filtros.")
    else:
        st.error("Não foi possível carregar os dados dos arquivos. Verifique se não estão corrompidos.")
else:
    st.info("Aguardando o upload de arquivos para iniciar o processamento.")
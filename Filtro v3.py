# app.py
import streamlit as st
import pandas as pd

# Importando as funções dos nossos módulos refatorados
from data_handler import (
    carregar_arquivos_csv, 
    init_supabase_client, 
    buscar_restricoes, 
    converter_df_para_csv
)
from ui_components import (
    exibir_sidebar, 
    exibir_configuracoes_banco
)
from filters import aplicar_filtros

# --- 1. Configuração da Página e Título ---
st.set_page_config(
    layout="wide", 
    page_title='Filtrador de Campanhas Otimizado',
    initial_sidebar_state='expanded'
)
st.title("🚀 Filtrador de Campanhas Otimizado")

# --- 2. Upload de Arquivos ---
st.sidebar.header("1. Carregue os arquivos de higienização")
arquivos_carregados = st.sidebar.file_uploader(
    'Arraste um ou mais arquivos CSV aqui',
    accept_multiple_files=True,
    type=['csv'],
    key='file_uploader'
)
st.sidebar.write("---")

if arquivos_carregados:
    st.session_state.df_bruto = carregar_arquivos_csv(arquivos_carregados)

# --- 3. Lógica Principal da Aplicação ---
if 'df_bruto' in st.session_state and not st.session_state.df_bruto.empty:
    df_bruto = st.session_state.df_bruto
    
    st.success(f"Arquivos carregados com sucesso! Total de {len(df_bruto)} registros.")
    st.dataframe(df_bruto.head(3))
    st.write("---")

    # Inicializa o cliente do Supabase
    supabase = init_supabase_client()
    
    # --- Lógica de Renderização Otimizada ---
    # Primeiro, determinamos qual campanha está selecionada na interface.
    # Usamos o 'st.session_state' para pegar o valor do selectbox, se já existir.
    tipo_campanha_selecionada = st.session_state.get('tipo_campanha_selectbox', 'Novo') 
    convenio_detectado = df_bruto['Convenio'].iloc[0] if 'Convenio' in df_bruto.columns else None

    # Com base na seleção, buscamos as restrições corretas no Supabase.
    if supabase and convenio_detectado:
        restricoes_db = buscar_restricoes(supabase, convenio_detectado, tipo_campanha_selecionada)
    else:
        restricoes_db = {}
    
    # AGORA, chamamos a função da sidebar UMA ÚNICA VEZ, passando os dados
    # do DataFrame e as restrições já carregadas do banco de dados.
    params_gerais = exibir_sidebar(df_bruto, restricoes_db)
    
    # --- Configuração dos Bancos (Área Principal) ---
    configs_banco = exibir_configuracoes_banco(
        params_gerais['tipo_campanha'],
        params_gerais['convenio'],
        df_bruto
    )

    # --- Ação Principal: Aplicar Filtros ---
    st.header("3. Gere a Campanha")
    if st.button("✨ Aplicar Filtros e Gerar Arquivo", type="primary", use_container_width=True):
        with st.spinner("Processando e aplicando filtros... Este processo pode levar alguns segundos."):
            try:
                base_filtrada = aplicar_filtros(df_bruto, params_gerais, configs_banco)

                if not base_filtrada.empty:
                    st.success("Filtros aplicados com sucesso!")
                    st.metric("Registros na campanha final:", f"{len(base_filtrada)} clientes")
                    st.dataframe(base_filtrada.head())

                    csv_pronto = converter_df_para_csv(base_filtrada)
                    nome_arquivo = f"{params_gerais['convenio']}_{params_gerais['tipo_campanha']}_{pd.Timestamp.now().strftime('%Y%m%d')}.csv"
                    
                    st.download_button(
                        label="📥 Baixar CSV da Campanha",
                        data=csv_pronto,
                        file_name=nome_arquivo,
                        mime='text/csv',
                        use_container_width=True
                    )
                else:
                    st.warning("Nenhum registro correspondeu aos filtros aplicados. Tente ajustar os parâmetros.")

            except Exception as e:
                st.error(f"Ocorreu um erro inesperado durante a filtragem:")
                st.exception(e)
else:
    st.info("Aguardando o carregamento dos arquivos CSV para iniciar a configuração da campanha.")
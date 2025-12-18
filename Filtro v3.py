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
    tipo_campanha_selecionada = st.session_state.get('tipo_campanha_selectbox', 'Novo') 
    convenio_detectado = df_bruto['Convenio'].iloc[0] if 'Convenio' in df_bruto.columns else None

    if supabase and convenio_detectado:
        restricoes_db = buscar_restricoes(
            supabase, 
            convenio_detectado, 
            tipo_campanha_selecionada
        )
    else:
        restricoes_db = {}
    
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
                base_filtrada = aplicar_filtros(
                    df_bruto, 
                    params_gerais, 
                    configs_banco
                )

                if not base_filtrada.empty:
                    # --- LOGS DE VALIDAÇÃO ---
                    with st.expander("🔬 Parâmetros de Validação Utilizados no Filtro"):
                        st.subheader("Parâmetros Gerais")
                        st.json(params_gerais)

                        st.subheader("Restrições Carregadas do Supabase")
                        st.json(restricoes_db or {})

                        st.subheader("Configurações de Banco e Produto")
                        st.json(configs_banco)

                    st.success("Filtros aplicados com sucesso!")
                    st.metric(
                        "Registros na campanha final:", 
                        f"{len(base_filtrada)} clientes"
                    )
                    st.dataframe(base_filtrada.head())

                    # =====================================================
                    # DOWNLOADS
                    # =====================================================
                    eh_campanha_novo = params_gerais['tipo_campanha'] == 'Novo'
                    data_hoje = pd.Timestamp.now().strftime('%Y%m%d')

                    st.subheader("📥 Downloads da Campanha")

                    # Arquivo completo (sempre disponível)
                    csv_completo = converter_df_para_csv(base_filtrada)

                    if eh_campanha_novo:
                        # NÃO TOMADORES
                        df_nao_tomadores = base_filtrada[
                            base_filtrada['MG_Emprestimo_Total'] ==
                            base_filtrada['MG_Emprestimo_Disponivel']
                        ]

                        # TOMADORES
                        df_tomadores = base_filtrada[
                            base_filtrada['MG_Emprestimo_Total'] !=
                            base_filtrada['MG_Emprestimo_Disponivel']
                        ]

                        csv_nao_tomadores = converter_df_para_csv(df_nao_tomadores)
                        csv_tomadores = converter_df_para_csv(df_tomadores)

                        col1, col2, col3 = st.columns(3)

                        with col1:
                            st.download_button(
                                "📄 Arquivo Completo",
                                csv_completo,
                                f"{params_gerais['convenio']}_novo_completo_{data_hoje}.csv",
                                "text/csv",
                                use_container_width=True
                            )

                        with col2:
                            st.download_button(
                                "🟢 Apenas Não Tomadores",
                                csv_nao_tomadores,
                                f"{params_gerais['convenio']}_nao_tomadores_{data_hoje}.csv",
                                "text/csv",
                                use_container_width=True
                            )

                        with col3:
                            st.download_button(
                                "🔵 Apenas Tomadores",
                                csv_tomadores,
                                f"{params_gerais['convenio']}_tomadores_{data_hoje}.csv",
                                "text/csv",
                                use_container_width=True
                            )

                    else:
                        st.download_button(
                            "📄 Baixar CSV da Campanha",
                            csv_completo,
                            f"{params_gerais['convenio']}_{params_gerais['tipo_campanha']}_{data_hoje}.csv",
                            "text/csv",
                            use_container_width=True
                        )

                else:
                    st.warning(
                        "Nenhum registro correspondeu aos filtros aplicados. "
                        "Tente ajustar os parâmetros."
                    )

            except Exception as e:
                st.error("Ocorreu um erro inesperado durante a filtragem:")
                st.exception(e)

else:
    st.info(
        "Aguardando o carregamento dos arquivos CSV "
        "para iniciar a configuração da campanha."
    )

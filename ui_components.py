# ui_components.py
import streamlit as st
import pandas as pd
from datetime import datetime
from config import BANCOS_MAPEAMENTO, COLUNAS_CONDICAO

def exibir_sidebar(df: pd.DataFrame, restricoes_db: dict):
    """
    Função principal que organiza e exibe toda a barra lateral.
    Ela chama funções menores para cada seção.
    Retorna um dicionário com todas as configurações.
    """
    st.sidebar.title("Configurações da Campanha")

    # --- 1. Seleção da Campanha ---
    tipo_campanha = st.sidebar.selectbox(
        "1. Tipo da Campanha:",
        ['Novo', 'Benefício', 'Cartão', 'Benefício & Cartão'],
        key="tipo_campanha_selectbox"
    )

    # --- 2. Configurações Gerais ---
    with st.sidebar.expander("2. Filtros Gerais", expanded=True):
        comissao_minima = st.number_input("Comissão Mínima (R$)", min_value=0.0, step=1.0)
        
        key_margem = f"margem_limite_{tipo_campanha.lower().replace(' & ', '_')}"
        margem_limite = st.number_input(
            f"Margem Mínima Empréstimo (para 'Novo') ou Limite (outros)", 
            value=20.0,
            step=5.0,
            key=key_margem
        )
        
        idade_max = st.number_input("Idade Máxima", 0, 120, 72)
        data_limite_idade = (datetime.today() - pd.DateOffset(years=idade_max)).date()

    # --- 3. Filtros de Exclusão (com dados do Supabase) ---
    with st.sidebar.expander("3. Excluir Grupos Específicos", expanded=False):
        convenio = df['Convenio'].iloc[0] if not df.empty and 'Convenio' in df.columns else "N/A"
        st.write(f"**Convênio Detectado:** {convenio}")

        if 'Lotacao' in df.columns:
            lotacoes_disponiveis = sorted(list(df['Lotacao'].dropna().unique()))
            selecao_lotacao = st.multiselect(
                "Excluir Lotações:",
                options=lotacoes_disponiveis,
                default=restricoes_db.get('lotacao', [])
            )
        else:
            selecao_lotacao = []

        if 'Vinculo_Servidor' in df.columns:
            vinculos_disponiveis = sorted(list(df['Vinculo_Servidor'].dropna().unique()))
            selecao_vinculos = st.multiselect(
                "Excluir Vínculos:",
                options=vinculos_disponiveis,
                default=restricoes_db.get('vinculo', [])
            )
        else:
            selecao_vinculos = []

    # --- 4. Configuração de Equipes ---
    with st.sidebar.expander("4. Atribuição de Equipes", expanded=True):
        equipes = st.selectbox(
            "Equipe Principal:",
            ['outbound', 'csapp', 'csativacao', 'cscdx', 'csport', 'outbound_virada'],
            key="equipe_campanha_selectbox"
        )
        convai_percent = st.slider(
            "Porcentagem para IA (ConvAI):", 0, 100, 0,
            key="convai_slider"
        )
    
    return {
        "tipo_campanha": tipo_campanha,
        "comissao_minima": comissao_minima,
        "margem_limite": margem_limite,
        "data_limite_idade": data_limite_idade,
        "selecao_lotacao": selecao_lotacao,
        "selecao_vinculos": selecao_vinculos,
        "equipes": equipes,
        "convai_percent": convai_percent,
        "convenio": convenio
    }


def exibir_configuracoes_banco(tipo_campanha: str, convenio: str, df: pd.DataFrame):
    """Cria dinamicamente os campos de configuração para cada banco."""
    st.header("2. Configure os Bancos e Produtos")
    
    quant_bancos = 1
    if tipo_campanha == 'Benefício & Cartão':
        quant_bancos = st.number_input("Quantidade de Configurações de Banco/Produto:", min_value=1, max_value=10, value=2, key="quant_bancos_misto")
    else:
        quant_bancos = st.number_input("Quantidade de Bancos:", min_value=1, max_value=10, value=1, key="quant_bancos_unico")
    
    configuracoes_banco = []
    for i in range(quant_bancos):
        expander_title = f"Configuração #{i + 1}"
        
        with st.expander(expander_title, expanded=True):
            config = {}
            
            config["coluna_condicional"] = st.selectbox('Aplicar esta regra em:', options=COLUNAS_CONDICAO, key=f"coluna_{i}")
            if config["coluna_condicional"] != "Aplicar a toda a base":
                modo_selecao = st.radio("Modo de Seleção:", ["Escolher valor único", "Usar palavras-chave"], key=f"modo_selecao_{i}", horizontal=True, label_visibility="collapsed")
                config["modo_condicional"] = modo_selecao
                if modo_selecao == "Escolher valor único":
                    valores_disponiveis = sorted(list(df[config["coluna_condicional"]].dropna().unique()))
                    config["valor_condicional"] = st.selectbox(f"Para o valor de '{config['coluna_condicional']}':", options=valores_disponiveis, key=f"valor_{i}")
                else:
                    config["valor_condicional"] = st.text_input(f"Palavras-chave para '{config['coluna_condicional']}' (separadas por ponto e vírgula):", placeholder="Ex: educacao; saude", key=f"valor_palavra_chave_{i}")
            else:
                config["valor_condicional"] = None
                config["modo_condicional"] = None
            
            st.write("---")

            if tipo_campanha == 'Benefício & Cartão':
                config["cartao_escolhido"] = st.radio("Tipo de Produto:", ['Benefício', 'Consignado'], key=f'opcao{i}', horizontal=True)

            # Adiciona o checkbox para a regra específica do GOVAM
            config["usar_margem_compra"] = False # Define um padrão
            if convenio == 'govam' and tipo_campanha == 'Benefício':
                config["usar_margem_compra"] = st.checkbox(
                    "Usar margem de compra (GOV AM)?", 
                    key=f"usar_margem_compra_{i}"
                )

            banco_selecionado = st.selectbox(f"Banco:", options=list(BANCOS_MAPEAMENTO.keys()), key=f"banco_{i}")
            config["banco"] = BANCOS_MAPEAMENTO[banco_selecionado]
            
            config["coeficiente"] = st.number_input(f"Coeficiente Principal:", min_value=0.0, step=0.0001, format="%.4f", key=f'coef_{i}')
            
            config["coeficiente2"] = None
            if convenio == 'goval' and (tipo_campanha in ['Benefício', 'Benefício & Cartão']):
                 config["coeficiente2"] = st.number_input(f"Coeficiente 2 (GOVAL):", min_value=0.0, step=0.0001, format="%.4f", key=f'coef2_{i}')

            config["comissao"] = st.number_input(f"Comissão (%):", min_value=0.0, max_value=100.0, step=0.01, key=f"comissao_{i}")
            config["parcelas"] = st.number_input(f"Parcelas:", min_value=1, max_value=200, step=1, key=f"parcelas_{i}")
            
            config["coeficiente_parcela"] = 1.0
            if tipo_campanha in ['Benefício', 'Cartão', 'Benefício & Cartão']:
                coef_str = st.text_input(f"Coeficiente da Parcela:", "1.0", key=f"coef_parcela{i}").replace(",",".")
                config["coeficiente_parcela"] = float(coef_str) if coef_str else 1.0
            
            config["margem_minima_cartao"] = 30.0
            if tipo_campanha == 'Benefício & Cartão':
                config["margem_minima_cartao"] = st.number_input(f"Margem Mínima Produto:", value=30.0, key=f"mg_minima{i}")
            
            use_margin = st.checkbox("Usar Margem de Segurança?", key=f"usa_margem_seg{i}")
            config["usa_margem_seguranca"] = use_margin

            if use_margin:
                col1, col2 = st.columns(2)
                with col1:
                    margin_type = st.radio(
                        "Tipo de cálculo:",
                        ["Percentual (%)", "Valor Fixo (R$)"],
                        key=f"tipo_margem_{i}",
                        horizontal=True
                    )
                    config["modo_margem_seguranca"] = margin_type
                with col2:
                    if margin_type == "Percentual (%)":
                        margin_value = st.number_input("Valor (%)", min_value=0.0, max_value=100.0, value=5.0, step=0.1, key=f"valor_margem_perc_{i}")
                    else:
                        margin_value = st.number_input("Valor (R$)", min_value=0.0, value=50.0, step=1.0, key=f"valor_margem_fixo_{i}")
                    config["valor_margem_seguranca"] = margin_value
            else:
                config["modo_margem_seguranca"] = None
                config["valor_margem_seguranca"] = None

            configuracoes_banco.append(config)
            
    return configuracoes_banco

# ======================================================================
# Filtro Master
def exibir_sidebar_simulacoes():
    """Cria a barra lateral com os parâmetros para o filtro de simulações."""
    st.sidebar.header("⚙️ Parâmetros de Saída")
    
    with st.sidebar.expander("Definir Parâmetros", expanded=True):
        equipes_konsi = ['outbound', 'csapp', 'csport', 'cscdx', 'csativacao', 'cscp']
        equipe = st.selectbox("Selecione a Equipe", equipes_konsi, key="equipe_simulacao")
        comissao_banco = st.number_input("Comissão do banco (%)", value=10.0, step=0.5, min_value=0.0) / 100
        comissao_minima = st.number_input("Comissão mínima (R$)", value=50.0, step=10.0, min_value=0.0)

    filtrar_saldo_devedor = st.sidebar.checkbox("Apenas com saldo devedor > 0", value=False)

    return {
        "equipe": equipe,
        "comissao_banco": comissao_banco,
        "comissao_minima": comissao_minima,
        "filtrar_saldo_devedor": filtrar_saldo_devedor
    }
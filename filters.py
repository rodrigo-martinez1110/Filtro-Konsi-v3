# filters.py
"""
Contém toda a lógica de filtragem.
"""

import pandas as pd
from datetime import datetime
from config import ORDEM_COLUNAS_FINAL, MAPEAMENTO_COLUNAS_FINAL
import re
import numpy as np

# Função Auxiliar de Margem de Segurança
def _aplicar_margem_seguranca(margem_disponivel_series: pd.Series, config: dict) -> pd.Series:
    """
    Aplica a margem de segurança a uma Série de margens com base na configuração.
    Retorna a Série com as margens ajustadas.
    """
    if not config.get("usa_margem_seguranca"):
        return margem_disponivel_series

    modo = config.get("modo_margem_seguranca")
    valor = config.get("valor_margem_seguranca", 0)

    if modo == "Percentual (%)":
        fator = 1 - (valor / 100)
        return margem_disponivel_series * fator
    
    elif modo == "Valor Fixo (R$)":
        margem_ajustada = margem_disponivel_series - valor
        return margem_ajustada.clip(lower=0)
    
    return margem_disponivel_series

# Função Auxiliar de Máscara Condicional (VERSÃO ÚNICA E CORRETA)
def _criar_mascara_condicional(base, config, coluna_tratado):
    """Função utilitária para criar a máscara de filtro de forma padronizada."""
    coluna_condicional = config.get('coluna_condicional')
    valor_condicional = config.get('valor_condicional')
    modo_condicional = config.get('modo_condicional')

    mascara = ~base[coluna_tratado]

    if coluna_condicional != "Aplicar a toda a base":
        if coluna_condicional in base.columns and base[coluna_condicional].notna().any() and valor_condicional:
            if modo_condicional == "Usar palavras-chave":
                palavras_chave = [item.strip() for item in str(valor_condicional).split(";") if item.strip()]
                if palavras_chave:
                    regex_pattern = "|".join(map(re.escape, palavras_chave))
                    mascara &= base[coluna_condicional].str.contains(regex_pattern, na=False, case=False)
            else:
                mascara &= (base[coluna_condicional] == valor_condicional)
    return mascara


def _preprocessar_base(df: pd.DataFrame, params: dict) -> pd.DataFrame:
    """Aplica filtros e limpezas comuns a todas as campanhas."""
    base = df.copy()

    if 'Nome_Cliente' in base.columns:
        base['Nome_Cliente'] = base['Nome_Cliente'].apply(
            lambda x: x.title() if isinstance(x, str) else x
        )
    if 'CPF' in base.columns:
        base['CPF'] = base['CPF'].str.replace(r"[.\-]", "", regex=True)

    if params.get('selecao_lotacao'):
        base = base[~base['Lotacao'].isin(params['selecao_lotacao'])]
    if params.get('selecao_vinculos'):
        base = base[~base['Vinculo_Servidor'].isin(params['selecao_vinculos'])]

    if 'Data_Nascimento' in base.columns and not base['Data_Nascimento'].isna().all():
        data_limite_idade = params.get('data_limite_idade')
        if data_limite_idade:
            base = base[pd.to_datetime(base["Data_Nascimento"], dayfirst=True, errors='coerce').dt.date >= data_limite_idade]
            
    return base


def _calcular_novo(base: pd.DataFrame, params: dict, configs_banco: list) -> pd.DataFrame: 
    convenio = params['convenio']
    if convenio == 'govsp':
        negativos = base.loc[base['MG_Emprestimo_Disponivel'] < 0, 'Matricula']
        base = base.loc[~base['Matricula'].isin(negativos)]
    elif convenio == 'govmt':
        base = base.loc[base['MG_Compulsoria_Disponivel'] >= 0]
        
    """Lógica de cálculo específica para a campanha 'Novo'."""
    base = base.loc[base['MG_Emprestimo_Disponivel'] >= params.get('margem_limite', 0)]
    
    base['tratado'] = False
    for config in configs_banco:
        mask = _criar_mascara_condicional(base, config, 'tratado')
        margem_disponivel = base.loc[mask, 'MG_Emprestimo_Disponivel']
        margem_ajustada = _aplicar_margem_seguranca(margem_disponivel, config)
        base.loc[mask, 'valor_liberado_emprestimo'] = (margem_ajustada * config.get('coeficiente', 0)).round(2)
        base.loc[mask, 'valor_parcela_emprestimo'] = margem_ajustada.round(2)
        base.loc[mask, 'comissao_emprestimo'] = (base.loc[mask, 'valor_liberado_emprestimo'] * (config.get('comissao', 0) / 100)).round(2)
        base.loc[mask, 'banco_emprestimo'] = config.get('banco')
        base.loc[mask, 'prazo_emprestimo'] = config.get('parcelas')
        base.loc[mask, 'tratado'] = True
    if 'comissao_emprestimo' in base.columns:
        base = base.loc[base['comissao_emprestimo'] >= params.get('comissao_minima', 0)]
    return base

def _calcular_beneficio(base: pd.DataFrame, params: dict, configs_banco: list) -> pd.DataFrame:
    convenio = params['convenio']
    usou_beneficio = pd.Series(dtype='object')
    if convenio == 'govsp':
        base['margem_beneficio_usado'] = base['MG_Beneficio_Saque_Total'] - base['MG_Beneficio_Saque_Disponivel']
        usou_beneficio = base.loc[base['margem_beneficio_usado'] > 0]
        base = base.loc[base['MG_Beneficio_Saque_Disponivel'] == base['MG_Beneficio_Saque_Total']]
        base = base[base['Lotacao'] != "ALESP"]
    conv_excluidos = ['prefrj', 'govpi', 'goval', 'govce']
    if convenio not in conv_excluidos:
        base = base.loc[base['MG_Beneficio_Saque_Disponivel'] == base['MG_Beneficio_Saque_Total']]
    
    """Lógica de cálculo específica para a campanha 'Benefício'."""
    base = base.loc[base['MG_Emprestimo_Disponivel'] < params.get('margem_limite', 999999)]
    
    base = base.sort_values(by='MG_Beneficio_Saque_Disponivel', ascending=False)
    base['tratado'] = False
    for config in configs_banco:
        coeficiente = config.get('coeficiente', 0)
        coeficiente2 = config.get('coeficiente2')
        mask = _criar_mascara_condicional(base, config, 'tratado')
        if convenio == 'goval':
            condicao_adicional = (base['MG_Beneficio_Saque_Disponivel'] == base['MG_Beneficio_Saque_Total']) & (base['MG_Beneficio_Compra_Disponivel'] == base['MG_Beneficio_Compra_Total'])
            margem_a_ser_usada = base['MG_Beneficio_Saque_Disponivel'].copy()
            coeficiente_a_ser_usado = pd.Series(coeficiente2, index=base.index)
            margem_a_ser_usada.loc[condicao_adicional] += base.loc[condicao_adicional, 'MG_Beneficio_Compra_Disponivel']
            coeficiente_a_ser_usado.loc[condicao_adicional] = coeficiente
            margem_ajustada = _aplicar_margem_seguranca(margem_a_ser_usada[mask], config)
            base.loc[mask, "valor_liberado_beneficio"] = (margem_ajustada * coeficiente_a_ser_usado[mask]).round(2)
        elif convenio == 'govam':
            usar_margem_compra = config.get('usar_margem_compra', False)
            if usar_margem_compra:
                mask_govam = mask & (base['MG_Beneficio_Compra_Total'] == base['MG_Beneficio_Compra_Disponivel']) & (base['MG_Beneficio_Saque_Total'] == base['MG_Beneficio_Saque_Disponivel'])
                margem_disponivel = base.loc[mask_govam, 'MG_Beneficio_Compra_Disponivel']
                margem_ajustada = _aplicar_margem_seguranca(margem_disponivel, config)
                base.loc[mask_govam, 'valor_liberado_beneficio'] = (margem_ajustada * coeficiente).round(2)
            else:
                mask_govam = mask & (base['MG_Beneficio_Compra_Total'] != base['MG_Beneficio_Compra_Disponivel']) & (base['MG_Beneficio_Saque_Total'] == base['MG_Beneficio_Saque_Disponivel'])
                margem_disponivel = base.loc[mask_govam, 'MG_Beneficio_Saque_Disponivel']
                margem_ajustada = _aplicar_margem_seguranca(margem_disponivel, config)
                base.loc[mask_govam, 'valor_liberado_beneficio'] = (margem_ajustada * coeficiente).round(2)
        elif convenio == 'govsp':
            margem_disponivel = base.loc[mask, 'MG_Beneficio_Saque_Disponivel']
            margem_ajustada = _aplicar_margem_seguranca(margem_disponivel, config)
            base.loc[mask, 'valor_liberado_beneficio'] = (margem_ajustada * coeficiente).round(2)
            if not usou_beneficio.empty:
                base.loc[base['Matricula'].isin(usou_beneficio['Matricula']), 'valor_liberado_beneficio'] = 0
        else:
            margem_disponivel = base.loc[mask, 'MG_Beneficio_Saque_Disponivel']
            margem_ajustada = _aplicar_margem_seguranca(margem_disponivel, config)
            base.loc[mask, 'valor_liberado_beneficio'] = (margem_ajustada * coeficiente).round(2)
        base.loc[mask, 'valor_parcela_beneficio'] = (base.loc[mask, 'valor_liberado_beneficio'] / config.get('coeficiente_parcela', 1.0)).round(2)
        base.loc[mask, 'comissao_beneficio'] = (base.loc[mask, 'valor_liberado_beneficio'] * (config.get('comissao', 0) / 100)).round(2)
        base.loc[mask, 'banco_beneficio'] = config.get('banco')
        base.loc[mask, 'prazo_beneficio'] = config.get('parcelas')
        base.loc[mask, 'tratado'] = True
    if 'comissao_beneficio' in base.columns:
        base = base.loc[base['comissao_beneficio'] >= params.get('comissao_minima', 0)]
    return base

def _calcular_cartao(base: pd.DataFrame, params: dict, configs_banco: list) -> pd.DataFrame:
    convenio = params['convenio']
    usou_cartao = pd.Series(dtype='object')
    
    if convenio == 'govsp':
        base = base[base['Lotacao'] != "ALESP"]
        base['margem_cartao_usado'] = base['MG_Cartao_Total'] - base['MG_Cartao_Disponivel']
        usou_cartao = base.loc[base['margem_cartao_usado'] > 0]
        
    base = base.loc[base['MG_Emprestimo_Disponivel'] < params.get('margem_limite', 999999)]
    base['tratado'] = False
    for config in configs_banco:
        mask = _criar_mascara_condicional(base, config, 'tratado')
        
        # Lógica da nova regra do cartão consignado
        filtro_margem_cartao_igual = base.loc[mask, 'MG_Cartao_Total'] == base.loc[mask, 'MG_Cartao_Disponivel']
        
        margem_disponivel = base.loc[mask, 'MG_Cartao_Disponivel']
        margem_ajustada = _aplicar_margem_seguranca(margem_disponivel, config)
        
        valor_calculado = (margem_ajustada * config.get('coeficiente', 0)).round(2)
        
        # Aplica a regra: valor é zero se as margens não forem iguais
        base.loc[mask, 'valor_liberado_cartao'] = np.where(filtro_margem_cartao_igual, valor_calculado, 0)

        if convenio == 'govsp' and not usou_cartao.empty:
            base.loc[base['Matricula'].isin(usou_cartao['Matricula']), 'valor_liberado_cartao'] = 0
            
        base.loc[mask, 'valor_parcela_cartao'] = (base.loc[mask, 'valor_liberado_cartao'] / config.get('coeficiente_parcela', 1.0)).round(2)
        base.loc[mask, 'comissao_cartao'] = (base.loc[mask, 'valor_liberado_cartao'] * (config.get('comissao', 0) / 100)).round(2)
        base.loc[mask, 'banco_cartao'] = config.get('banco')
        base.loc[mask, 'prazo_cartao'] = config.get('parcelas')
        base.loc[mask, 'tratado'] = True
        
    if 'comissao_cartao' in base.columns:
        base = base.loc[base['comissao_cartao'] >= params.get('comissao_minima', 0)]
    return base

def _calcular_beneficio_e_cartao(base: pd.DataFrame, params: dict, configs_banco: list) -> pd.DataFrame:
    convenio = params['convenio']
    base['valor_liberado_beneficio'] = 0.0
    base['valor_liberado_cartao'] = 0.0
    base['comissao_beneficio'] = 0.0
    base['comissao_cartao'] = 0.0
    base['valor_parcela_beneficio'] = 0.0
    base['valor_parcela_cartao'] = 0.0
    base['banco_beneficio'] = ''
    base['banco_cartao'] = ''
    base['prazo_beneficio'] = 0
    base['prazo_cartao'] = 0
    base['tratado_beneficio'] = False
    base['tratado_cartao'] = False
    usou_beneficio, usou_cartao = pd.Series(dtype='object'), pd.Series(dtype='object')
    if convenio == 'govsp':
        base = base[base['Lotacao'] != 'ALESP']
        usou_beneficio = base[base['MG_Beneficio_Saque_Total'] > base['MG_Beneficio_Saque_Disponivel']]
        usou_cartao = base[base['MG_Cartao_Total'] > base['MG_Cartao_Disponivel']]
        
    """Lógica de cálculo para a campanha 'Benefício & Cartão', com todas as regras de negócio."""
    base = base.loc[base['MG_Emprestimo_Disponivel'] < params.get('margem_limite', 999999)]
    
    for config in configs_banco:
        produto = config.get('cartao_escolhido')
        
        if produto == 'Benefício':
            mask = _criar_mascara_condicional(base, config, 'tratado_beneficio')
            if convenio == 'goval':
                coeficiente = config.get('coeficiente', 0)
                coeficiente2 = config.get('coeficiente2')
                condicao_adicional = (base['MG_Beneficio_Saque_Disponivel'] == base['MG_Beneficio_Saque_Total']) & (base['MG_Beneficio_Compra_Disponivel'] == base['MG_Beneficio_Compra_Total'])
                margem_a_ser_usada = base['MG_Beneficio_Saque_Disponivel'].copy()
                coeficiente_a_ser_usado = pd.Series(coeficiente2, index=base.index)
                margem_a_ser_usada.loc[condicao_adicional] += base.loc[condicao_adicional, 'MG_Beneficio_Compra_Disponivel']
                coeficiente_a_ser_usado.loc[condicao_adicional] = coeficiente
                margem_ajustada = _aplicar_margem_seguranca(margem_a_ser_usada[mask], config)
                base.loc[mask, "valor_liberado_beneficio"] = (margem_ajustada * coeficiente_a_ser_usado[mask]).round(2)
            else:
                margem_disponivel = base.loc[mask, 'MG_Beneficio_Saque_Disponivel']
                margem_ajustada = _aplicar_margem_seguranca(margem_disponivel, config)
                base.loc[mask, 'valor_liberado_beneficio'] = (margem_ajustada * config.get('coeficiente', 0)).round(2)
                if convenio == 'govsp' and not usou_beneficio.empty:
                    base.loc[base['Matricula'].isin(usou_beneficio['Matricula']), 'valor_liberado_beneficio'] = 0
            base.loc[mask, 'valor_parcela_beneficio'] = (base.loc[mask, 'valor_liberado_beneficio'] / config.get('coeficiente_parcela', 1.0)).round(2)
            base.loc[mask, 'comissao_beneficio'] = (base.loc[mask, 'valor_liberado_beneficio'] * (config.get('comissao', 0) / 100)).round(2)
            base.loc[mask, 'banco_beneficio'] = config.get('banco')
            base.loc[mask, 'prazo_beneficio'] = config.get('parcelas')
            base.loc[mask, 'tratado_beneficio'] = True
            
        elif produto == 'Consignado':
            mask = _criar_mascara_condicional(base, config, 'tratado_cartao')
            
            # --- INÍCIO DA CORREÇÃO ---
            # 1. Cria o filtro para a nova regra de negócio (apenas nas linhas da máscara)
            filtro_margem_cartao_igual = base.loc[mask, 'MG_Cartao_Total'] == base.loc[mask, 'MG_Cartao_Disponivel']
            
            # 2. Calcula o valor liberado normalmente
            margem_disponivel = base.loc[mask, 'MG_Cartao_Disponivel']
            margem_ajustada = _aplicar_margem_seguranca(margem_disponivel, config)
            valor_calculado = (margem_ajustada * config.get('coeficiente', 0)).round(2)

            # 3. Usa np.where para aplicar a regra: se a condição for True, usa o valor_calculado, senão, usa 0.
            base.loc[mask, 'valor_liberado_cartao'] = np.where(filtro_margem_cartao_igual, valor_calculado, 0)
            # --- FIM DA CORREÇÃO ---

            if convenio == 'govsp' and not usou_cartao.empty:
                 base.loc[base['Matricula'].isin(usou_cartao['Matricula']), 'valor_liberado_cartao'] = 0
            
            base.loc[mask, 'valor_parcela_cartao'] = (base.loc[mask, 'valor_liberado_cartao'] / config.get('coeficiente_parcela', 1.0)).round(2)
            base.loc[mask, 'comissao_cartao'] = (base.loc[mask, 'valor_liberado_cartao'] * (config.get('comissao', 0) / 100)).round(2)
            base.loc[mask, 'banco_cartao'] = config.get('banco')
            base.loc[mask, 'prazo_cartao'] = config.get('parcelas')
            base.loc[mask, 'tratado_cartao'] = True
    
    base['comissao_total'] = (base['comissao_beneficio'] + base['comissao_cartao']).round(2)
    base = base[base['comissao_total'] >= params.get('comissao_minima', 0)]
    return base

def _finalizar_base(df: pd.DataFrame, params: dict) -> pd.DataFrame:
    """Aplica formatação final, adiciona colunas, nome de campanha e limpa o DF."""
    base = df.copy()
    for col in ORDEM_COLUNAS_FINAL:
        if col not in base.columns:
            base[col] = ""
    if 'CPF' in base.columns:
         base = base.drop_duplicates(subset=['CPF'])
    
    colunas_presentes = [col for col in ORDEM_COLUNAS_FINAL if col in base.columns]
    base = base[colunas_presentes]
    base.rename(columns=MAPEAMENTO_COLUNAS_FINAL, inplace=True)
    
    data_hoje = datetime.today().strftime('%d%m%Y')
    campanha_map = {'Novo': 'novo', 'Benefício': 'benef', 'Cartão': 'cartao', 'Benefício & Cartão': 'benef-cartao'}
    tipo_campanha_str = campanha_map.get(params['tipo_campanha'], 'campanha')
    convenio = params.get('convenio', 'geral')
    equipe = params.get('equipes', 'geral')
    
    base['Campanha'] = f"{convenio}_{data_hoje}_{tipo_campanha_str}_{equipe}"
    
    convai_percent = params.get('convai_percent', 0)
    if convai_percent > 0 and len(base) > 0:
        n_convai = int((convai_percent / 100) * len(base))
        if n_convai > 0:
            indices_convai = base.sample(n=n_convai, random_state=42).index
            base.loc[indices_convai, 'Campanha'] = f"{convenio}_{data_hoje}_{tipo_campanha_str}_convai"
            
    colunas_para_remover = ['tratado', 'tratado_beneficio', 'tratado_cartao', 'comissao_total', 'margem_beneficio_usado', 'margem_cartao_usado']
    base.drop(columns=[col for col in colunas_para_remover if col in base.columns], inplace=True, errors='ignore')
            
    return base

def aplicar_filtros(df: pd.DataFrame, params: dict, configs_banco: list) -> pd.DataFrame:
    """
    Função principal que orquestra todo o processo de filtragem.
    """
    base_pre_processada = _preprocessar_base(df, params)
    
    base_calculada = pd.DataFrame()
    tipo_campanha = params.get('tipo_campanha')

    if tipo_campanha == 'Novo':
        base_calculada = _calcular_novo(base_pre_processada, params, configs_banco)
        base_calculada = base_calculada.sort_values(by='valor_liberado_emprestimo', ascending=False)
    elif tipo_campanha == 'Cartão':
        base_calculada = _calcular_cartao(base_pre_processada, params, configs_banco)
        base_calculada = base_calculada.sort_values(by='valor_liberado_cartao', ascending=False)
    elif tipo_campanha == 'Benefício':
        base_calculada = _calcular_beneficio(base_pre_processada, params, configs_banco)
        base_calculada = base_calculada.sort_values(by='valor_liberado_beneficio', ascending=False)
    elif tipo_campanha == 'Benefício & Cartão':
        base_calculada = _calcular_beneficio_e_cartao(base_pre_processada, params, configs_banco)
        base_calculada = base_calculada.sort_values(by='comissao_total', ascending=False)

    if base_calculada.empty:
        return pd.DataFrame()

    base_final = _finalizar_base(base_calculada, params)
    
    return base_final

#============================================================================

# ----------------------------
# Filtro Master
# ----------------------------
def _encontrar_melhor_item(linha_simulacoes):
    """
    Percorre as simulações de uma linha e retorna a que tiver o maior número de parcelas.
    """
    maior_parcela = 0
    melhor_item = None
    for item in linha_simulacoes:
        if pd.notna(item):
            match = re.search(r'(\d+)x:', str(item))
            if match:
                parcela = int(match.group(1))
                if parcela > maior_parcela:
                    maior_parcela = parcela
                    melhor_item = item
    return melhor_item


# ----------------------------
# Função auxiliar
# ----------------------------
def normalizar_numero(valor: str) -> float:
    """
    Converte strings numéricas em float, tratando formatos BR (16.000,50) e US (4880.46).
    """
    if ',' in valor:
        # Formato brasileiro: remove separador de milhar e troca vírgula por ponto
        valor = valor.replace('.', '').replace(',', '.')
    return pd.to_numeric(valor, errors='coerce')

def aplicar_filtro_simulacoes(df: pd.DataFrame, params: dict) -> pd.DataFrame:
    """
    Processa um DataFrame que contém uma coluna 'Simulacoes' para extrair a melhor oferta.
    """
    base = df.copy()

    if 'Simulacoes' not in base.columns:
        st.error("Erro fatal: A coluna 'Simulacoes' não foi encontrada nos arquivos carregados.")
        return pd.DataFrame()

    # Divide as simulações em colunas separadas
    colunas_separadas = base['Simulacoes'].fillna('').astype(str).str.split('|', expand=True)
    base['Melhor_Item'] = colunas_separadas.apply(_encontrar_melhor_item, axis=1)

    # Extrai prazo, valor e parcela
    extracoes = base['Melhor_Item'].str.extract(
        r'(?P<prazo>\d+)x: (?P<valor>[\d.,]+) \(parcela: (?P<parcela>[\d.,]+)\)',
        expand=True
    )

    if extracoes.empty:
        st.warning("Não foi possível extrair dados do formato esperado na coluna 'Melhor_Item'.")
        return pd.DataFrame()

    base['prazo_beneficio'] = pd.to_numeric(extracoes['prazo'], errors='coerce')

    # Corrige parsing de números em valor e parcela
    for col_name in ['valor', 'parcela']:
        col_series = extracoes[col_name].copy().astype(str)
        extracoes[col_name] = col_series.apply(normalizar_numero)

    base['valor_liberado_beneficio'] = extracoes['valor']
    base['valor_parcela_beneficio'] = extracoes['parcela']

    # Tratamento de CPF e nome
    if 'CPF' in base.columns:
        base.loc[:, 'CPF'] = base['CPF'].str.replace(r'\D', '', regex=True)
    if 'Nome_Cliente' in base.columns:
        base.loc[:, 'Nome_Cliente'] = base['Nome_Cliente'].apply(
            lambda x: x.title() if isinstance(x, str) else x
        )

    # Remove valores inválidos
    base = base.loc[base['valor_liberado_beneficio'].fillna(0) > 0]
    if 'MG_Beneficio_Saque_Disponivel' in base.columns:
        base = base.loc[
            pd.to_numeric(base['MG_Beneficio_Saque_Disponivel'].fillna(0), errors='coerce') >= 0
        ]

    # Filtro opcional de saldo devedor
    if params.get('filtrar_saldo_devedor', False) and "Saldo_Devedor" in base.columns:
        base.loc[:, "Saldo_Devedor"] = pd.to_numeric(base["Saldo_Devedor"], errors="coerce").fillna(0)
        base = base.loc[base["Saldo_Devedor"] > 0]

    # Calcula comissão
    base.loc[:, 'comissao_beneficio'] = (
        base['valor_liberado_beneficio'].fillna(0) * params.get('comissao_banco', 0)
    ).round(2)

    # Filtra por comissão mínima
    base = base.query('comissao_beneficio >= @params["comissao_minima"]')

    # Adiciona informações fixas
    base.loc[:, 'banco_beneficio'] = '243'
    params['tipo_campanha'] = 'Benefício'

    # Finaliza base
    base_final = _finalizar_base(base, params)
    return base_final

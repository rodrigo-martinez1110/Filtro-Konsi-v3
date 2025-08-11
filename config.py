# config.py
"""
Módulo para armazenar constantes e configurações da aplicação.
"""

# Mapeamento de nomes de bancos para seus respectivos códigos
BANCOS_MAPEAMENTO = {
    "2 - MeuCashCard": "2",
    "33 - Santander": "33",
    "74 - Banco do Brasil": "74",
    "243 - Banco Master": "243",
    "318 - BMG": "318",
    "335 - Banco Digio": "335",
    "389 - Banco Mercantil": "389",
    "422 - Banco Safra": "422",
    "465 - Capital Consig": "465",
    "604 - Banco Industrial": "604",
    "623 - Banco PAN": "623",
    "643 - Banco Pine": "643",
    "654 - Banco DigiMais": "654",
    "707- Banco Daycoval": "707",
    "955 - Banco Olé": "955",
    "6613 - VemCard": "6613"
}

# Colunas que podem ser usadas para aplicar condições específicas de bancos
COLUNAS_CONDICAO = ['Vinculo_Servidor', 'Lotacao', 'Secretaria', 'Aplicar a toda a base']

# Mapeamento de nomes de colunas para o formato final no CSV
MAPEAMENTO_COLUNAS_FINAL = {
    'Origem_Dado': 'ORIGEM DO DADO',
    'MG_Emprestimo_Total': 'Mg_Emprestimo_Total',
    'MG_Emprestimo_Disponivel': 'Mg_Emprestimo_Disponivel',
    'MG_Beneficio_Saque_Total': 'Mg_Beneficio_Saque_Total',
    'MG_Beneficio_Saque_Disponivel': 'Mg_Beneficio_Saque_Disponivel',
    'MG_Cartao_Total': 'Mg_Cartao_Total',
    'MG_Cartao_Disponivel': 'Mg_Cartao_Disponivel',
}

# Ordem final das colunas no arquivo de saída
ORDEM_COLUNAS_FINAL = [
    'Origem_Dado', 'Nome_Cliente', 'Matricula', 'CPF', 'Data_Nascimento',
    'MG_Emprestimo_Total', 'MG_Emprestimo_Disponivel',
    'MG_Beneficio_Saque_Total', 'MG_Beneficio_Saque_Disponivel',
    'MG_Cartao_Total', 'MG_Cartao_Disponivel',
    'Convenio', 'Vinculo_Servidor', 'Lotacao', 'Secretaria',
    'FONE1', 'FONE2', 'FONE3', 'FONE4',
    'valor_liberado_emprestimo', 'valor_liberado_beneficio', 'valor_liberado_cartao',
    'comissao_emprestimo', 'comissao_beneficio', 'comissao_cartao',
    'valor_parcela_emprestimo', 'valor_parcela_beneficio', 'valor_parcela_cartao',
    'banco_emprestimo', 'banco_beneficio', 'banco_cartao',
    'prazo_emprestimo', 'prazo_beneficio', 'prazo_cartao',
    'Campanha'
]
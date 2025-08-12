# data_handler.py
import streamlit as st
import pandas as pd
from supabase import create_client, Client
from typing import List, Dict

# Usa o cache do Streamlit para evitar recarregar os mesmos arquivos repetidamente.
# A função só será re-executada se os arquivos carregados mudarem.
@st.cache_data
def carregar_arquivos_csv(files: List[st.runtime.uploaded_file_manager.UploadedFile]) -> pd.DataFrame:
    """Junta múltiplos arquivos CSV carregados em um único DataFrame."""
    if not files:
        st.warning("Nenhum arquivo CSV foi carregado.")
        return pd.DataFrame()

    dataframes = []
    for arquivo in files:
        try:
            # Garante que o ponteiro do arquivo esteja no início
            arquivo.seek(0)
            df = pd.read_csv(arquivo, low_memory=False)
            if not df.empty:
                dataframes.append(df)
            else:
                st.warning(f"O arquivo {arquivo.name} está vazio e será ignorado.")
        except Exception as e:
            st.error(f"Erro ao ler o arquivo {arquivo.name}: {e}")
            
    if not dataframes:
        st.error("Nenhum arquivo CSV válido pôde ser processado.")
        return pd.DataFrame()
        
    return pd.concat(dataframes, ignore_index=True)

# Usa o cache de recursos para criar o cliente Supabase apenas uma vez.
@st.cache_resource
def init_supabase_client() -> Client:
    """Inicializa e retorna o cliente Supabase, lendo as credenciais do st.secrets."""
    try:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
        return create_client(url, key)
    except Exception as e:
        st.error(f"Erro ao conectar com o Supabase. Verifique suas credenciais em st.secrets: {e}")
        return None

# Usa o cache de dados para evitar buscar as mesmas restrições repetidamente.
# A função agora será re-executada se o 'convenio' ou o 'produto' mudarem.
@st.cache_data
def buscar_restricoes(_supabase_client: Client, convenio: str, produto: str) -> Dict[str, List[str]]:
    """
    Busca restrições para um convênio e produto específicos no Supabase.
    Busca tanto as regras do produto quanto as regras 'todos' (globais para o convênio).
    """
    restricoes = {
        "lotacao": [],
        "secretaria": [],
        "vinculo": []
    }
    
    if not _supabase_client or not convenio or not produto:
        return restricoes

    # Mapeia o nome da campanha do Streamlit para o nome no DB para consistência
    produto_map = {
        'Novo': 'novo', 
        'Benefício': 'beneficio', 
        'Cartão': 'cartao', 
        'Benefício & Cartão': 'benef-cartao'
    }
    produto_db = produto_map.get(produto, produto.lower())

    try:
        # A consulta busca pelo convênio E por produtos ('específico' OU 'todos')
        query = _supabase_client.table("restricoes") \
            .select("tipo_restricao, valor_restrito") \
            .eq("convenio", convenio) \
            .in_("produto", [produto_db, 'todos'])
            
        data = query.execute().data
        
        if data:
            for item in data:
                tipo = item['tipo_restricao']
                valor = item['valor_restrito']
                
                # Adiciona na lista correspondente se o tipo for conhecido
                if tipo in restricoes:
                    if valor not in restricoes[tipo]: # Evita adicionar valores duplicados
                        restricoes[tipo].append(valor)
        
        return restricoes

    except Exception as e:
        st.warning(f"Não foi possível buscar restrições para '{convenio}/{produto}': {e}")
        return restricoes

def converter_df_para_csv(df: pd.DataFrame) -> bytes:
    """Converte um DataFrame para CSV em formato UTF-8, pronto para download."""
    return df.to_csv(index=False, sep=';').encode('utf-8')


# ===========================================================================
# Filtro Master - 

import io

@st.cache_data
def carregar_arquivos_simulacoes(files: List[st.runtime.uploaded_file_manager.UploadedFile]) -> pd.DataFrame:
    """Carrega arquivos de simulação, detectando o separador e usando codificação latin1."""
    if not files:
        return pd.DataFrame()

    lista_dfs = []
    for file in files:
        try:
            file.seek(0)
            content_bytes = file.read()
            
            # Detecta o separador (vírgula ou ponto e vírgula)
            primeira_linha = content_bytes.splitlines()[0].decode('latin1')
            sep = ';' if primeira_linha.count(';') > primeira_linha.count(',') else ','
            
            file_buffer = io.BytesIO(content_bytes)
            df = pd.read_csv(file_buffer, sep=sep, encoding='latin1', low_memory=False, dtype=str)
            lista_dfs.append(df)
        except Exception as e:
            st.error(f"Não foi possível ler o arquivo {file.name}. Erro: {e}")
            continue
    
    if not lista_dfs:
        return pd.DataFrame()

    return pd.concat(lista_dfs, ignore_index=True)
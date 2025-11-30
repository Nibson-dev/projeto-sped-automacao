# ler_pdf.py (COMPLETO E CORRIGIDO)
import os
import fitz  # Este é o PyMuPDF
import re
import sys
import json
from decimal import Decimal, InvalidOperation
from collections import defaultdict

# --- CONFIGURAÇÕES GLOBAIS ---
MARCADOR_SECAO_APURACAO_LIVRO = "Apuração do Saldo"
MARCADOR_PARADA_LIVRO = "Observações"
CODIGOS_APURACAO_LIVRO = ["013", "014"]
MARCADOR_SECAO_INF_COMP = "INFORMAÇÕES COMPLEMENTARES"
CHAVES_PRINCIPAIS_ES = ["total_operacao", "base_de_calculo_icms", "total_icms"]
CHAVES_COMPLETAS_ES = [
    "total_operacao", "base_de_calculo_icms", "total_icms",
    "base_de_calculo_icms_st", "total_icms_st", "total_ipi"
]
CHAVES_LAYOUT_HORIZONTAL_SAIDAS = [
    "total_operacao", "base_de_calculo_icms", "total_icms",
    "isentas_nao_trib", "outras"
]
ETIQUETA_TOTAIS_SPED = "TOTAL"
ETIQUETA_TOTAIS_LIVRO = "Totais"
MARCADOR_PAGINA_ENTRADAS = "ENTRADAS"
MARCADOR_PAGINA_SAIDAS = "SAÍDAS"

# --- LÓGICA DE APURAÇÃO PADRÃO ---
ETIQUETA_APURACAO_SPED_1 = "VALOR TOTAL DO ICMS A RECOLHER"
ETIQUETA_APURACAO_SPED_2 = "VALOR TOTAL DO SALDO CREDOR A TRANSPORTAR PARA O PERÍODO SEGUINTE"

# --- DICIONÁRIO MESTRE PARA EXTRAÇÃO AVANÇADA (COM OS NOMES EXATOS) ---
DICIONARIO_APURACAO_SPED_AVANCADO = {
    "AP_DEBITO_SAIDAS": "SAÍDAS E PRESTAÇÕES COM DÉBITO DO IMPOSTO",
    "AP_AJUSTES_DEBITO_DOC": "VALOR TOTAL DOS AJUSTES A DÉBITO (decorrentes do documento fiscal)",
    "AP_AJUSTES_DEBITO_IMP": "VALOR TOTAL DOS AJUSTES A DÉBITO DO IMPOSTO",
    "AP_ESTORNO_CREDITOS": "VALOR TOTAL DOS ESTORNOS DE CRÉDITOS",
    "AP_CREDITO_ENTRADAS": "VALOR TOTAL DOS CRÉDITOS POR ENTRADAS E AQUISIÇÕES COM CRÉDITO DO IMPOSTO",
    "AP_AJUSTES_CREDITO_DOC": "VALOR TOTAL DOS AJUSTES A CRÉDITO (decorrentes do documento fiscal)",
    "AP_AJUSTES_CREDITO_IMP": "VALOR TOTAL DOS AJUSTES A CRÉDITO DO IMPOSTO",
    "AP_ESTORNO_DEBITOS": "VALOR TOTAL DOS ESTORNOS DE DÉBITOS",
    "AP_SALDO_ANTERIOR": "VALOR TOTAL DO SALDO CREDOR DO período ANTERIOR",
    "AP_SALDO_DEVEDOR": "VALOR DO SALDO DEVEDOR",
    "AP_DEDUCOES": "VALOR TOTAL DAS DEDUÇÕES",
    "AP_RECOLHER": "VALOR TOTAL DO ICMS A RECOLHER",
    "AP_SALDO_CREDOR": "VALOR TOTAL DO SALDO CREDOR A TRANSPORTAR PARA O período SEGUINTE",
    "AP_EXTRA_APURACAO": "VALORES RECOLHIDOS OU A RECOLHER, EXTRA-APURAÇÃO"
}

# --- FUNÇÕES AUXILIARES ---
def limpar_e_converter_numero(texto_numero):
    if texto_numero is None: return 0.0
    if "," not in texto_numero: return 0.0
    try:
        texto_limpo = texto_numero.strip().replace(" ", "")
        texto_limpo = texto_limpo.replace(".", "")
        texto_limpo = texto_limpo.replace(",", ".")
        texto_limpo = re.sub(r"[^0-9\.]", "", texto_limpo)
        if not texto_limpo: return 0.0
        return float(texto_limpo)
    except Exception:
        return 0.0

def _extrair_valor_da_linha(linha, regex_valor):
    match = re.search(regex_valor, linha)
    if match: return match.group(0)
    if "0" in linha and not re.search(r'[1-9]', linha): return "0,00"
    return "0,00"

def _limpar_valor_decimal(valor_str):
    try:
        valor_sem_ponto = valor_str.replace('.', '')
        valor_com_ponto = valor_sem_ponto.replace(',', '.')
        valor_limpo = re.sub(r"[^0-9\.]", "", valor_com_ponto)
        if not valor_limpo: return Decimal('0.0')
        return Decimal(valor_limpo)
    except InvalidOperation:
        print(f"   > (DETALHAMENTO) Aviso: falha ao converter valor decimal: {valor_str}", file=sys.stderr)
        return Decimal('0.0')

# --- FUNÇÕES DE DETALHAMENTO ---
def analisar_detalhamento_por_codigo(caminho_pdf):
    if not caminho_pdf or not os.path.exists(caminho_pdf):
        print("   > (DETALHAMENTO) ERRO: Caminho do Livro Fiscal está vazio ou arquivo não existe.", file=sys.stderr)
        return {}
    print(f"Iniciando Análise de Detalhamento por Código em: {os.path.basename(caminho_pdf)}", file=sys.stderr)
    somas_por_codigo = defaultdict(Decimal)
    regex_codigo = r'\b([A-Z]{2}\d{5,12})\b'
    regex_valor = r'(\d{1,3}(?:\.\d{3})*,\d{2})'
    try:
        doc = fitz.open(caminho_pdf)
        for pagina in doc:
            for linha in pagina.get_text().split('\n'):
                match_codigo = re.search(regex_codigo, linha)
                if match_codigo:
                    codigo_encontrado = match_codigo.group(1)
                    matches_valor = re.findall(regex_valor, linha)
                    if matches_valor:
                        valor_str = matches_valor[-1]
                        valor_decimal = _limpar_valor_decimal(valor_str)
                        if valor_decimal > Decimal('0.0'):
                            somas_por_codigo[codigo_encontrado] += valor_decimal
        doc.close()
        print(f"   > (DETALHAMENTO) Análise de códigos concluída. {len(somas_por_codigo)} códigos somados.", file=sys.stderr)
        return dict(somas_por_codigo)
    except Exception as e:
        print(f"   > (DETALHAMENTO) ERRO CRÍTICO ao processar o PDF: {e}", file=sys.stderr)
        return {}

def verificar_codigos_no_livro(caminho_pdf, lista_codigos_sped):
    if not caminho_pdf or not os.path.exists(caminho_pdf):
        print("   > (CROSS-CHECK) ERRO: Caminho do Livro Fiscal está vazio ou arquivo não existe.", file=sys.stderr)
        return lista_codigos_sped or ["Erro: Livro PDF não encontrado"]
    if not lista_codigos_sped: return []
    print(f"Iniciando Cross-Check de {len(lista_codigos_sped)} códigos E111 no Livro Fiscal...", file=sys.stderr)
    full_text_livro = ""
    try:
        doc = fitz.open(caminho_pdf)
        for pagina in doc:
            full_text_livro += pagina.get_text()
        doc.close()
    except Exception as e:
        print(f"   > (CROSS-CHECK) ERRO ao ler PDF do Livro: {e}", file=sys.stderr)
        return ["Erro ao ler PDF do Livro"]
    if not full_text_livro:
        print("   > (CROSS-CHECK) ERRO: PDF do Livro Fiscal está vazio ou ilegível.", file=sys.stderr)
        return lista_codigos_sped
    codigos_ausentes = [codigo for codigo in lista_codigos_sped if codigo not in full_text_livro]
    if codigos_ausentes:
        print(f"   > (CROSS-CHECK) ALERTA! Códigos ausentes no Livro: {codigos_ausentes}", file=sys.stderr)
    else:
        print("   > (CROSS-CHECK) SUCESSO! Todos os códigos E111 foram encontrados no Livro.", file=sys.stderr)
    return codigos_ausentes

# --- FUNÇÕES DE EXTRAÇÃO (PRINCIPAL) ---
def encontrar_e_extrair_totais_es(caminho_pdf, marcador_pagina, etiqueta_valor, chaves):
    if not caminho_pdf or not os.path.exists(caminho_pdf): return {}
    print(f"Lendo E/S... Procurando pág '{marcador_pagina}' e etiqueta '{etiqueta_valor}' em {os.path.basename(caminho_pdf)}", file=sys.stderr)
    
    valores_encontrados = {}
    regex_valor = r'(\d{1,3}(?:\.\d{3})*,\d{2})'
    
    try:
        doc = fitz.open(caminho_pdf)
        pagina_alvo_texto = ""
        for pagina in doc:
            texto_da_pagina = pagina.get_text()
            if marcador_pagina.upper() in texto_da_pagina.upper():
                pagina_alvo_texto = texto_da_pagina
                if etiqueta_valor in texto_da_pagina:
                    break
        
        if not pagina_alvo_texto:
            print(f"   > (E/S) ERRO: Não encontrei nenhuma página com o marcador '{marcador_pagina}'.", file=sys.stderr)
            doc.close(); return {}

        linhas = pagina_alvo_texto.split('\n')
        
        if etiqueta_valor == "Totais": # MODO HORIZONTAL (LIVRO)
            for linha in linhas:
                if linha.strip().startswith(etiqueta_valor):
                    valores = re.findall(regex_valor, linha)
                    if len(valores) >= 3:
                        for i, chave in enumerate(chaves):
                            if i < len(valores): valores_encontrados[chave] = valores[i]
                        doc.close(); return valores_encontrados
            
        elif etiqueta_valor == "TOTAL": # MODO VERTICAL (SPED PDF)
            for i, linha in enumerate(linhas):
                if linha.strip() == etiqueta_valor:
                    try:
                        if marcador_pagina == MARCADOR_PAGINA_ENTRADAS:
                            valores_encontrados["total_operacao"] = _extrair_valor_da_linha(linhas[i+1], regex_valor)
                            valores_encontrados["base_de_calculo_icms"] = _extrair_valor_da_linha(linhas[i+4], regex_valor)
                            valores_encontrados["total_icms"] = _extrair_valor_da_linha(linhas[i+3], regex_valor)
                            valores_encontrados["base_de_calculo_icms_st"] = _extrair_valor_da_linha(linhas[i+2], regex_valor)
                            valores_encontrados["total_icms_st"] = _extrair_valor_da_linha(linhas[i+5], regex_valor)
                            valores_encontrados["total_ipi"] = "0,00"
                        elif marcador_pagina == MARCADOR_PAGINA_SAIDAS:
                            valores_encontrados["total_icms"] = _extrair_valor_da_linha(linhas[i-1], regex_valor)
                            valores_encontrados["total_operacao"] = _extrair_valor_da_linha(linhas[i+1], regex_valor)
                            valores_encontrados["base_de_calculo_icms"] = _extrair_valor_da_linha(linhas[i+2], regex_valor)
                            valores_encontrados["base_de_calculo_icms_st"] = _extrair_valor_da_linha(linhas[i+3], regex_valor)
                            valores_encontrados["total_icms_st"] = _extrair_valor_da_linha(linhas[i+4], regex_valor)
                            valores_encontrados["total_ipi"] = _extrair_valor_da_linha(linhas[i+5], regex_valor)
                        doc.close(); return valores_encontrados
                    except IndexError:
                        print(f"   > (E/S) ERRO: 'TOTAL' muito perto do fim/início da página.", file=sys.stderr)
                        doc.close(); return {}
        
        print(f"   > (E/S) ERRO FINAL: Achei a página, mas não a linha '{etiqueta_valor}'.", file=sys.stderr)
        doc.close(); return {}
    except Exception as e:
        print(f"   > (E/S) ERRO CRÍTICO ao ler PDF: {e}", file=sys.stderr)
        return {}

# --- [FUNÇÃO CORRIGIDA] LÓGICA DE APURAÇÃO AGORA É ROBUSTA ---
def encontrar_valor_apuracao_SPED(caminho_pdf, etiqueta):
    if not caminho_pdf or not os.path.exists(caminho_pdf): return None
    print(f"Lendo Apuração SPED... Procurando por: '{etiqueta}' em {os.path.basename(caminho_pdf)}", file=sys.stderr)
    
    regex_valor = r'(\d{1,3}(?:\.\d{3})*,\d{2})'
    
    try:
        doc = fitz.open(caminho_pdf)
        texto_completo_doc = ""
        for pagina in doc:
            texto_completo_doc += pagina.get_text("text")
        
        doc.close()

        # [NOVA LÓGICA ROBUSTA]
        # 1. Prepara a etiqueta para a RegEx (escapa caracteres especiais como '(', ')')
        etiqueta_regex = re.escape(etiqueta)
        
        # 2. Cria a RegEx de "caça":
        #    - (etiqueta_regex) -> Encontra a etiqueta
        #    - (.*?) -> Pega qualquer caractere (incluindo quebras de linha)
        #    - (regex_valor) -> Pega o PRIMEIRO valor numérico que aparecer depois
        #    - re.DOTALL -> Faz o ".*?" funcionar através de quebras de linha
        #    - re.IGNORECASE -> Faz a busca da etiqueta ignorar maiúsculas/minúsculas
        
        search_regex = f"({etiqueta_regex})(.*?)({regex_valor})"
        
        # Usamos re.IGNORECASE pois o PDF pode ter 'periodo' ou 'PERÍODO'
        match = re.search(search_regex, texto_completo_doc, re.DOTALL | re.IGNORECASE)
        
        if match:
            valor_encontrado = match.group(3) # O grupo 3 é o (regex_valor)
            print(f"   > (SPED Apuração) SUCESSO. Etiqueta '{etiqueta}' encontrou valor '{valor_encontrado}'", file=sys.stderr)
            return valor_encontrado
        else:
            print(f"   > (SPED Apuração) FALHA. Etiqueta '{etiqueta}' não foi encontrada ou não foi seguida por um valor.", file=sys.stderr)
            return None
            
    except Exception as e:
        print(f"   > (SPED Apuração) ERRO ao ler PDF: {e}", file=sys.stderr)
        return None

def encontrar_apuracao_LIVRO(caminho_pdf, marcador_secao, codigos_alvo):
    if not caminho_pdf or not os.path.exists(caminho_pdf): return {}
    print(f"Lendo Apuração (Livro)... Procurando Seção '{marcador_secao}' pelos códigos {codigos_alvo}", file=sys.stderr)
    
    valores_encontrados_dict = {}
    regex_valor = r'(\d{1,3}(?:\.\d{3})*,\d{2})'
    try:
        doc = fitz.open(caminho_pdf)
        texto_completo = ""
        for page in doc: texto_completo += page.get_text()
        secao_apuracao_match = re.search(f"{marcador_secao}(.*?)(?={MARCADOR_PARADA_LIVRO}|$)", texto_completo, re.DOTALL | re.IGNORECASE)
        
        if secao_apuracao_match:
            texto_secao = secao_apuracao_match.group(1)
            for linha in texto_secao.split('\n'):
                palavras = linha.strip().split()
                if not palavras: continue
                for codigo in codigos_alvo:
                    if palavras[0] == codigo:
                        match_valor = re.search(regex_valor, linha)
                        if match_valor: valores_encontrados_dict[codigo] = match_valor.group(0)
        doc.close()
        return valores_encontrados_dict
    except Exception as e:
        print(f"   > (APURAÇÃO - LIVRO) ERRO ao ler PDF: {e}", file=sys.stderr)
        return {}

def somar_informacoes_complementares(caminho_pdf, marcador_secao, marcador_parada):
    if not caminho_pdf or not os.path.exists(caminho_pdf): return 0.0
    print(f"Lendo Soma (Livro)... Procurando Seção '{marcador_secao}'", file=sys.stderr)
    total_soma = 0.0
    try:
        doc = fitz.open(caminho_pdf)
        texto_completo = "".join([page.get_text() for page in doc])
        secao_match = re.search(f"{marcador_secao}(.*?)(?={marcador_parada}|$)", texto_completo, re.DOTALL | re.IGNORECASE)

        if secao_match:
            texto_secao = secao_match.group(1)
            for palavra in texto_secao.split():
                valor_num = limpar_e_converter_numero(palavra)
                if valor_num > 0:
                    total_soma += valor_num
        doc.close()
        return total_soma
    except Exception as e:
        print(f"   > (SOMA INF-COMP) ERRO ao ler PDF: {e}", file=sys.stderr)
        return 0.0

# --- FUNÇÃO DE EXTRAÇÃO AVANÇADA (MODIFICADA) ---
def extrair_campos_avancados(caminho_apuracao_sped, advanced_fields_str):
    resultados_avancados = []
    try:
        advanced_keys = json.loads(advanced_fields_str)
        if not advanced_keys:
            print("   > (AVANÇADO) Nenhum campo avançado solicitado.", file=sys.stderr)
            return []
            
        print(f"   > (AVANÇADO) Iniciando extração de {len(advanced_keys)} campos avançados...", file=sys.stderr)
        
        for key in advanced_keys:
            etiqueta_texto_pdf = DICIONARIO_APURACAO_SPED_AVANCADO.get(key)
            
            if not etiqueta_texto_pdf:
                print(f"   > (AVANÇADO) ERRO: Chave desconhecida '{key}' no dicionário.", file=sys.stderr)
                resultados_avancados.append({"campo_nome": key, "valor_sped": "Erro de Chave"})
                continue
            
            # [MODIFICADO] O "campo_nome" agora é o texto exato do relatório
            etiqueta_nome_amigavel = etiqueta_texto_pdf
            valor_encontrado = encontrar_valor_apuracao_SPED(caminho_apuracao_sped, etiqueta_texto_pdf)
            
            resultados_avancados.append({
                "campo_nome": etiqueta_nome_amigavel,
                "valor_sped": valor_encontrado if valor_encontrado else "Não Encontrado"
            })
        
        print("   > (AVANÇADO) Extração avançada concluída.", file=sys.stderr)
        return resultados_avancados

    except json.JSONDecodeError:
        print(f"   > (AVANÇADO) ERRO: Não foi possível decodificar a string de campos avançados: {advanced_fields_str}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"   > (AVANÇADO) ERRO Inesperado: {e}", file=sys.stderr)
        return []


# --- PONTO DE PARTIDA ---
if __name__ == "__main__":
    
    if len(sys.argv) < 7:
        print(json.dumps({"error": "ERRO DE USO! Faltando 6 argumentos: livro.pdf, entradas.pdf, saidas.pdf, apuracao.pdf, 'cod1,cod2', '[]'"}))
        sys.exit(1)

    caminho_livro_fiscal = sys.argv[1]
    caminho_entradas_sped = sys.argv[2]
    caminho_saidas_sped = sys.argv[3]
    caminho_apuracao_sped = sys.argv[4]
    codigos_e111_str = sys.argv[5]
    advanced_fields_str = sys.argv[6]
    
    LISTA_CODIGOS_E111_SPED = codigos_e111_str.split(',') if codigos_e111_str else []
    
    resultados = {
        "entradas": {"sped": {}, "livro": {}, "status": "Falha", "status_detalhado": {}},
        "saidas": {"sped": {}, "livro": {}, "status": "Falha", "status_detalhado": {}},
        "apuracao": {
            "sped_recolher": "ERRO", "sped_saldo_credor": "ERRO",
            "livro_valores": {}, "status_recolher": "Falha", "status_saldo_credor": "Falha"
        },
        "detalhamento_codigos": {},
        "codigos_ausentes_livro": None,
        "soma_livro_inf_comp": 0.0,
        "advanced_results": []
    }

    try:
        # 1. Processar SPED
        valores_sped_entradas = encontrar_e_extrair_totais_es(caminho_entradas_sped, MARCADOR_PAGINA_ENTRADAS, ETIQUETA_TOTAIS_SPED, CHAVES_COMPLETAS_ES)
        valores_sped_saidas = encontrar_e_extrair_totais_es(caminho_saidas_sped, MARCADOR_PAGINA_SAIDAS, ETIQUETA_TOTAIS_SPED, CHAVES_COMPLETAS_ES)
        valor_apuracao_sped_1 = encontrar_valor_apuracao_SPED(caminho_apuracao_sped, ETIQUETA_APURACAO_SPED_1)
        valor_apuracao_sped_2 = encontrar_valor_apuracao_SPED(caminho_apuracao_sped, ETIQUETA_APURACAO_SPED_2)
        
        # 2. Processar Livro Fiscal
        valores_livro_entradas_dict = encontrar_e_extrair_totais_es(caminho_livro_fiscal, MARCADOR_PAGINA_ENTRADAS, ETIQUETA_TOTAIS_LIVRO, CHAVES_COMPLETAS_ES)
        valores_livro_saidas_dict = encontrar_e_extrair_totais_es(caminho_livro_fiscal, MARCADOR_PAGINA_SAIDAS, ETIQUETA_TOTAIS_LIVRO, CHAVES_LAYOUT_HORIZONTAL_SAIDAS)
        dict_apuracao_livro = encontrar_apuracao_LIVRO(caminho_livro_fiscal, MARCADOR_SECAO_APURACAO_LIVRO, CODIGOS_APURACAO_LIVRO)
        soma_inf_comp = somar_informacoes_complementares(caminho_livro_fiscal, MARCADOR_SECAO_INF_COMP, MARCADOR_PARADA_LIVRO)
        somas_detalhamento_decimal = analisar_detalhamento_por_codigo(caminho_livro_fiscal)
        somas_detalhamento_str = {codigo: f"{soma:.2f}" for codigo, soma in somas_detalhamento_decimal.items()}
        codigos_ausentes = verificar_codigos_no_livro(caminho_livro_fiscal, LISTA_CODIGOS_E111_SPED)

        # 3. Processar Extração Avançada
        resultados_avancados = extrair_campos_avancados(caminho_apuracao_sped, advanced_fields_str)
        resultados["advanced_results"] = resultados_avancados

        # 4. Popular resultados
        resultados["detalhamento_codigos"] = somas_detalhamento_str
        resultados["codigos_ausentes_livro"] = codigos_ausentes
        resultados["soma_livro_inf_comp"] = soma_inf_comp
        
        # Entradas
        resultados["entradas"]["sped"] = valores_sped_entradas
        resultados["entradas"]["livro"] = valores_livro_entradas_dict
        status_geral_e = "OK"
        for key in CHAVES_PRINCIPAIS_ES:
            val_sped = limpar_e_converter_numero(valores_sped_entradas.get(key, "0,00"))
            val_livro = limpar_e_converter_numero(valores_livro_entradas_dict.get(key, "0,00"))
            if abs(val_sped - val_livro) < 0.01:
                resultados["entradas"]["status_detalhado"][key] = "OK"
            else:
                resultados["entradas"]["status_detalhado"][key] = "Divergente"
                status_geral_e = "Divergente"
        resultados["entradas"]["status"] = status_geral_e

        # Saídas
        resultados["saidas"]["sped"] = valores_sped_saidas
        resultados["saidas"]["livro"] = valores_livro_saidas_dict
        status_geral_s = "OK"
        for key in CHAVES_PRINCIPAIS_ES:
            val_sped = limpar_e_converter_numero(valores_sped_saidas.get(key, "0,00"))
            val_livro = limpar_e_converter_numero(valores_livro_saidas_dict.get(key, "0,00"))
            if abs(val_sped - val_livro) < 0.01:
                resultados["saidas"]["status_detalhado"][key] = "OK"
            else:
                resultados["saidas"]["status_detalhado"][key] = "Divergente"
                status_geral_s = "Divergente"
        resultados["saidas"]["status"] = status_geral_s

        # Apuração (Padrão)
        resultados["apuracao"]["sped_recolher"] = valor_apuracao_sped_1 or "Não lido"
        resultados["apuracao"]["sped_saldo_credor"] = valor_apuracao_sped_2 or "Não lido"
        resultados["apuracao"]["livro_valores"] = dict_apuracao_livro
        val_sped_a_1 = limpar_e_converter_numero(valor_apuracao_sped_1)
        val_livro_a_1 = limpar_e_converter_numero(dict_apuracao_livro.get("013"))
        resultados["apuracao"]["status_recolher"] = "OK" if abs(val_sped_a_1 - val_livro_a_1) < 0.01 else "Divergente"
        val_sped_a_2 = limpar_e_converter_numero(valor_apuracao_sped_2)
        val_livro_a_2 = limpar_e_converter_numero(dict_apuracao_livro.get("014"))
        resultados["apuracao"]["status_saldo_credor"] = "OK" if abs(val_sped_a_2 - val_livro_a_2) < 0.01 else "Divergente"

    except Exception as e:
        print(f"ERRO GERAL NO 'ler_pdf.py': {e}", file=sys.stderr)
        resultados["error"] = f"Erro geral no script ler_pdf: {e}"
    
    finally:
        print(json.dumps(resultados, indent=2))
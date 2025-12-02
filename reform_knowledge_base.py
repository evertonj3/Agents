"""
Reform Knowledge Base - v4.9
Base de conhecimento para leis complexas conhecidas (LC 214, etc.)

Este módulo contém dados estruturados sobre leis complexas que são difíceis
de extrair automaticamente via LLM devido ao seu tamanho e complexidade.

USO:
- Quando o sistema detecta uma lei conhecida (ex: LC 214), usa os dados daqui
- Garante informações corretas mesmo quando extração automática falha
"""

from typing import Dict, List, Optional


# ============================================================================
# DETECTOR DE LEIS CONHECIDAS
# ============================================================================

def detect_known_legislation(url: str, content: str, title: str = "") -> Optional[str]:
    """
    Detecta se a legislação é uma lei conhecida no knowledge base.
    
    Returns:
        Chave da lei (ex: "LC_214") ou None se não reconhecida
    """
    url_lower = url.lower()
    content_lower = content.lower()[:5000]  # Primeiros 5000 chars
    
    # LC 214 - Reforma Tributária
    if any([
        'lcp214' in url_lower,
        'lcp/lcp214' in url_lower,
        '/lcp/214' in url_lower,
        'lei complementar nº 214' in content_lower,
        'lei complementar n° 214' in content_lower,
        ('ibs' in content_lower and 'cbs' in content_lower and 'imposto seletivo' in content_lower),
        ('reforma tributária' in content_lower and 'ibs' in content_lower),
    ]):
        return "LC_214"
    
    # MPV 1318 - REDATA (já funciona bem, mas podemos adicionar fallback)
    if any([
        'mpv1318' in url_lower,
        'mpv/mpv1318' in url_lower,
        'redata' in content_lower,
    ]):
        return "MPV_1318"
    
    # Adicione outras leis conhecidas aqui conforme necessário
    
    return None


# ============================================================================
# LC 214 - REFORMA TRIBUTÁRIA (Lei Complementar 214/2025)
# ============================================================================

LC_214_DATA = {
    "identificacao": {
        "tipo": "LEI COMPLEMENTAR",
        "numero": "LC nº 214",
        "data": "16/01/2025",
        "ementa": "Institui o Imposto sobre Bens e Serviços (IBS), a Contribuição Social sobre Bens e Serviços (CBS) e o Imposto Seletivo (IS), cria o Comitê Gestor do IBS e dispõe sobre a transição do sistema tributário brasileiro.",
    },
    
    "vigencias": [
        {
            "data": "16/01/2025",
            "contexto": "Publicação e início da vigência da Lei Complementar nº 214",
            "tipo": "inicio_vigencia",
            "relevancia": "alta"
        },
        {
            "data": "2026",
            "contexto": "Início do período de teste - CBS 0,9% + IBS 0,1%",
            "tipo": "inicio_vigencia",
            "relevancia": "alta"
        },
        {
            "data": "2027",
            "contexto": "CBS entra em vigor com alíquota cheia (~8,8%); IS (Imposto Seletivo) entra em vigor",
            "tipo": "inicio_vigencia",
            "relevancia": "alta"
        },
        {
            "data": "2029-2032",
            "contexto": "Período de transição gradual - redução progressiva de PIS/COFINS/ICMS/ISS",
            "tipo": "prazo_transicao",
            "relevancia": "alta"
        },
        {
            "data": "31/12/2032",
            "contexto": "Último ano de coexistência dos sistemas tributários",
            "tipo": "prazo_final",
            "relevancia": "alta"
        },
        {
            "data": "01/01/2033",
            "contexto": "Extinção total de PIS, COFINS, ICMS e ISS - IBS e CBS em vigor pleno",
            "tipo": "prazo_final",
            "relevancia": "alta"
        },
    ],
    
    "tributos": {
        "IBS": {
            "nome_completo": "Imposto sobre Bens e Serviços",
            "competencia": "Estadual/Municipal",
            "substitui": ["ICMS", "ISS"],
            "aliquota_referencia": "17,7%",
            "caracteristicas": [
                "IVA dual - parte estadual/municipal",
                "Cobrança no destino (não na origem)",
                "Crédito amplo (inclusive serviços)",
                "Não cumulativo",
            ],
            "inicio_vigencia": "2026 (teste 0,1%), 2027+ (aumenta gradualmente)",
            "contexto": "Tributo que unifica ICMS estadual e ISS municipal em um único imposto sobre consumo."
        },
        "CBS": {
            "nome_completo": "Contribuição Social sobre Bens e Serviços",
            "competencia": "Federal",
            "substitui": ["PIS", "COFINS"],
            "aliquota_referencia": "8,8%",
            "caracteristicas": [
                "IVA dual - parte federal",
                "Não cumulativo com crédito amplo",
                "Incide sobre operações com bens e serviços",
                "Base de cálculo = valor da operação",
            ],
            "inicio_vigencia": "2026 (teste 0,9%), 2027 (alíquota cheia)",
            "contexto": "Contribuição federal que substitui PIS e COFINS, com regime não cumulativo."
        },
        "IS": {
            "nome_completo": "Imposto Seletivo",
            "competencia": "Federal",
            "substitui": [],
            "aliquota_referencia": "Variável por produto",
            "caracteristicas": [
                "Incide sobre produtos prejudiciais à saúde ou meio ambiente",
                "Também chamado 'Imposto do Pecado'",
                "Alíquotas específicas por categoria de produto",
            ],
            "produtos": [
                "Bebidas alcoólicas",
                "Cigarros e produtos de tabaco",
                "Bebidas açucaradas",
                "Veículos poluentes",
                "Embarcações e aeronaves",
                "Extração de recursos naturais não renováveis",
            ],
            "inicio_vigencia": "2027",
            "contexto": "Imposto extrafiscal com objetivo de desestimular consumo de produtos nocivos."
        },
    },
    
    "cronograma_transicao": [
        {"ano": "2026", "cbs": "0,9% (teste)", "ibs": "0,1% (teste)", "pis_cofins": "100%", "icms_iss": "100%", "is": "-"},
        {"ano": "2027", "cbs": "Alíquota cheia", "ibs": "Aumenta", "pis_cofins": "Reduz", "icms_iss": "100%", "is": "Entra em vigor"},
        {"ano": "2029", "cbs": "100%", "ibs": "Aumenta", "pis_cofins": "Reduz", "icms_iss": "90%", "is": "100%"},
        {"ano": "2030", "cbs": "100%", "ibs": "Aumenta", "pis_cofins": "Reduz", "icms_iss": "80%", "is": "100%"},
        {"ano": "2031", "cbs": "100%", "ibs": "Aumenta", "pis_cofins": "Reduz", "icms_iss": "70%", "is": "100%"},
        {"ano": "2032", "cbs": "100%", "ibs": "Aumenta", "pis_cofins": "Reduz", "icms_iss": "60%", "is": "100%"},
        {"ano": "2033", "cbs": "100%", "ibs": "100%", "pis_cofins": "EXTINTO", "icms_iss": "EXTINTO", "is": "100%"},
    ],
    
    "system_changes": [
        {
            "tributo": "IBS",
            "tipo_mudanca": "NOVO TRIBUTO",
            "situacao_anterior": "Não existia (ICMS + ISS eram separados)",
            "situacao_nova": "Novo tributo unificado estadual/municipal com alíquota de referência de 17,7%. Substitui gradualmente ICMS e ISS até 2033.",
            "condicoes": "Aplica-se a todas as operações com bens e serviços. Quem era contribuinte de ICMS ou ISS será contribuinte do IBS.",
            "vigencia": "2026 (teste) a 2033 (pleno)",
            "descricao_completa": "IBS: NOVO TRIBUTO (substitui ICMS+ISS)",
            "compliance_risks": "Necessidade de adaptar sistemas para novo tributo; período de convivência com ICMS/ISS gera complexidade."
        },
        {
            "tributo": "CBS",
            "tipo_mudanca": "NOVO TRIBUTO",
            "situacao_anterior": "Não existia (PIS + COFINS eram separados)",
            "situacao_nova": "Nova contribuição federal com alíquota de referência de 8,8%. Substitui gradualmente PIS e COFINS até 2033. Crédito amplo (inclusive serviços).",
            "condicoes": "Aplica-se a todas as operações com bens e serviços. Regime não cumulativo com crédito amplo.",
            "vigencia": "2026 (teste 0,9%) a 2027 (alíquota cheia)",
            "descricao_completa": "CBS: NOVO TRIBUTO (substitui PIS+COFINS)",
            "compliance_risks": "Necessidade de adaptar sistemas para novo tributo; mudança de regime de crédito."
        },
        {
            "tributo": "IS",
            "tipo_mudanca": "NOVO TRIBUTO",
            "situacao_anterior": "Não existia",
            "situacao_nova": "Imposto Seletivo incidente sobre produtos prejudiciais à saúde ou meio ambiente. Alíquotas variáveis por produto.",
            "condicoes": "Incide sobre: bebidas alcoólicas, cigarros, bebidas açucaradas, veículos poluentes, extração de recursos não renováveis.",
            "vigencia": "A partir de 2027",
            "descricao_completa": "IS: NOVO TRIBUTO (Imposto Seletivo)",
            "compliance_risks": "Verificar se produtos Dell se enquadram (ex: baterias, componentes eletrônicos com substâncias específicas)."
        },
    ],
    
    "impacto_dell": {
        "relevancia": "ALTA",
        "justificativa": """A Lei Complementar nº 214/2025 (Reforma Tributária) tem impacto direto e significativo na Dell Technologies Brazil:

1. SUBSTITUIÇÃO DE TRIBUTOS: PIS/COFINS serão substituídos por CBS; ICMS/ISS por IBS. A Dell precisará adaptar todos os sistemas para os novos tributos.

2. MUDANÇA DE REGIME: O novo sistema terá crédito amplo (inclusive serviços), o que pode beneficiar a Dell que contrata muitos serviços.

3. COBRANÇA NO DESTINO: O IBS será cobrado no destino, não na origem. Isso afeta operações interestaduais e pode beneficiar a Dell nas exportações.

4. PERÍODO DE TRANSIÇÃO: De 2026 a 2032, haverá convivência entre sistemas antigo e novo, aumentando a complexidade de compliance.

5. IMPOSTO SELETIVO: A Dell deve verificar se algum produto se enquadra no IS (ex: componentes com substâncias específicas).""",
        "areas_impactadas": [
            "TI/ERP - Atualização de sistemas para novos tributos",
            "Fiscal/Tax - Novo regime de créditos e apuração",
            "Operações - Mudança de cobrança na origem para destino",
            "Compliance - Período de transição com dois sistemas",
            "Todas as filiais (SP, RS, RJ)",
        ],
        "acoes_requeridas": [
            "Mapear impacto financeiro da mudança de alíquotas",
            "Planejar atualização de ERP para novos tributos (CBS, IBS, IS)",
            "Revisar contratos com fornecedores considerando novo regime de créditos",
            "Treinar equipe fiscal no novo sistema",
            "Acompanhar regulamentação complementar",
            "Verificar enquadramento de produtos no Imposto Seletivo",
        ],
    },
    
    "compliance_risks": [
        "Não adaptar sistemas a tempo para o período de teste (2026) - consequência: erros na apuração",
        "Não aproveitar crédito amplo do novo sistema - consequência: carga tributária maior que necessário",
        "Confundir regras do sistema antigo com o novo durante transição - consequência: autuações fiscais",
        "Não verificar enquadramento de produtos no IS - consequência: multas por não recolhimento",
        "Não treinar equipe adequadamente - consequência: erros operacionais",
    ],
    
    "parametrizacoes_erp": [
        "Cadastro de novos tributos (CBS, IBS, IS)",
        "Tabela de alíquotas por período de transição",
        "Regras de crédito amplo (CBS/IBS)",
        "Configuração de cobrança no destino (IBS)",
        "Regras de apuração split-payment",
        "Cadastro de produtos sujeitos ao IS",
        "Relatórios comparativos (sistema antigo vs novo)",
        "Controle de vigências por tributo e período",
    ],
}


# ============================================================================
# MPV 1318 - REDATA (já funciona bem, mas incluímos como backup)
# ============================================================================

MPV_1318_DATA = {
    "identificacao": {
        "tipo": "MEDIDA PROVISÓRIA",
        "numero": "MPV nº 1318",
        "data": "17/09/2025",
        "ementa": "Institui o Regime Especial de Tributação para Serviços de Datacenter (REDATA).",
    },
    # Adicione mais dados se necessário - o sistema já extrai bem automaticamente
}


# ============================================================================
# FUNÇÕES DE ACESSO
# ============================================================================

KNOWLEDGE_BASE = {
    "LC_214": LC_214_DATA,
    "MPV_1318": MPV_1318_DATA,
}


def get_known_legislation_data(key: str) -> Optional[Dict]:
    """Retorna dados completos de uma lei conhecida"""
    return KNOWLEDGE_BASE.get(key)


def get_vigencias_for_legislation(key: str) -> List[Dict]:
    """Retorna vigências conhecidas para uma lei"""
    data = KNOWLEDGE_BASE.get(key, {})
    return data.get("vigencias", [])


def get_system_changes_for_legislation(key: str) -> List[Dict]:
    """Retorna mudanças de sistema conhecidas para uma lei"""
    data = KNOWLEDGE_BASE.get(key, {})
    return data.get("system_changes", [])


def get_tributos_for_legislation(key: str) -> Dict:
    """Retorna informações de tributos para uma lei"""
    data = KNOWLEDGE_BASE.get(key, {})
    return data.get("tributos", {})


def get_compliance_risks_for_legislation(key: str) -> List[str]:
    """Retorna riscos de compliance para uma lei"""
    data = KNOWLEDGE_BASE.get(key, {})
    return data.get("compliance_risks", [])


def get_cronograma_transicao(key: str) -> List[Dict]:
    """Retorna cronograma de transição para uma lei"""
    data = KNOWLEDGE_BASE.get(key, {})
    return data.get("cronograma_transicao", [])


def get_dell_impact(key: str) -> Dict:
    """Retorna análise de impacto para Dell"""
    data = KNOWLEDGE_BASE.get(key, {})
    return data.get("impacto_dell", {})


def get_parametrizacoes_erp(key: str) -> List[str]:
    """Retorna parametrizações de ERP necessárias"""
    data = KNOWLEDGE_BASE.get(key, {})
    return data.get("parametrizacoes_erp", [])


# ============================================================================
# FUNÇÃO PRINCIPAL DE MERGE
# ============================================================================

def merge_with_extracted_data(
    extracted_vigencias: List[Dict],
    extracted_changes: List[Dict],
    known_legislation_key: str
) -> tuple:
    """
    Mescla dados extraídos automaticamente com dados do knowledge base.
    
    Prioriza dados extraídos quando disponíveis, mas usa knowledge base como fallback.
    
    Returns:
        Tuple[vigencias_merged, changes_merged]
    """
    kb_vigencias = get_vigencias_for_legislation(known_legislation_key)
    kb_changes = get_system_changes_for_legislation(known_legislation_key)
    
    # Merge vigências
    if not extracted_vigencias or len(extracted_vigencias) < 3:
        # Se extração automática encontrou pouco, usa knowledge base
        vigencias_merged = kb_vigencias
        print(f"   📚 Usando vigências do Knowledge Base para {known_legislation_key}")
    else:
        vigencias_merged = extracted_vigencias
    
    # Merge system changes
    has_valid_changes = (
        extracted_changes and 
        len(extracted_changes) > 0 and
        extracted_changes[0].get('tributo') != 'Análise detalhada necessária'
    )
    
    if not has_valid_changes:
        # Se extração automática falhou, usa knowledge base
        changes_merged = kb_changes
        print(f"   📚 Usando mudanças do Knowledge Base para {known_legislation_key}")
    else:
        changes_merged = extracted_changes
    
    return vigencias_merged, changes_merged
"""
Configuração do Sistema de Análise de Legislação Brasileira v4.8
VERSÃO COM REFORMA TRIBUTÁRIA - Suporte a IBS, CBS, IS
Com análise de relevância para Dell Technologies Brazil

NOVIDADES v4.8:
- Suporte a IBS (Imposto sobre Bens e Serviços) - estadual/municipal
- Suporte a CBS (Contribuição sobre Bens e Serviços) - federal
- Suporte a IS (Imposto Seletivo) - "imposto do pecado"
- Regras de transição 2026-2033
- Suporte melhorado a legislação estadual (ICMS)
- Suporte a Convênios CONFAZ
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ============================================================================
# DELL APIs CONFIGURATION
# ============================================================================

DEV_GENAI_API_URL = os.getenv("DEV_GENAI_API_URL", "https://genai-api-dev.dell.com/v1")
DEV_GENAI_API_KEY = os.getenv("DEV_GENAI_API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME", "llama-3-3-70b-instruct")

# ============================================================================
# SYSTEM SETTINGS
# ============================================================================

MAX_TOKENS_ANALYSIS = 4000  # ✅ CORRIGIDO: Valor realista e será usado
MAX_TOKENS_EXTRACTION = 3000
MAX_TOKENS_IMPACT = 2500
MAX_ENHANCEMENT_ITERATIONS = 2
MIN_COMPLETENESS_SCORE = 0.80

# ============================================================================
# INFORMAÇÕES DA DELL TECHNOLOGIES BRAZIL
# ============================================================================

DELL_COMPANY_INFO = """
Dell Technologies Brazil - Informações Corporativas:

REGIME TRIBUTÁRIO: Lucro Real

FILIAIS E ATIVIDADES:

1. Hortolândia/SP
   - Fabricação de equipamentos de informática
   - Comércio atacadista e varejista especializado de equipamentos e suprimentos de informática

2. Eldorado do Sul/RS
   - Suporte técnico, manutenção e outros serviços em tecnologia da informação

3. São Paulo/SP
   - Escritório de apoio administrativo (prestação de serviços de treinamento)

4. Barueri/SP
   - Prestação de Serviços Profissionais (Consultoria/Implementação)
   - Suporte Técnico de Software
   - Serviços de Manutenção de Hardware

5. Santana do Parnaíba/SP
   - Importação, exportação e comercialização de SW e HW
   - Revenda de produtos nacionais e importados

6. Cajamar/SP
   - Importação, exportação de partes e peças
   - Substituição no cliente com cobertura de contrato de garantia

7. Rio de Janeiro/RJ
   - Pesquisa e desenvolvimento nas áreas de tecnologia e comunicação
   - Relacionamento com universidades

ATIVIDADES PRINCIPAIS:
- Fabricação de equipamentos de TI
- Importação e exportação
- Comercialização de hardware e software
- Prestação de serviços técnicos
- Suporte e manutenção
- P&D em tecnologia
"""

# ============================================================================
# ✅ NOVO: REGRAS DE DESAMBIGUAÇÃO DE TRIBUTOS
# ============================================================================

TRIBUTO_DISAMBIGUATION_RULES = """
⚠️  REGRAS CRÍTICAS DE DESAMBIGUAÇÃO DE TRIBUTOS ⚠️

PROBLEMA COMUM: Confundir "II" (Imposto de Importação) com "inciso II" de lei.

1. TRIBUTOS ATUAIS (use SIGLAS em MAIÚSCULAS):
   - II = Imposto de Importação
     → Contexto: importação, alfândega, produtos estrangeiros, aduaneiro
     → Exemplo: "Suspensão do II na importação de componentes"
   
   - IPI = Imposto sobre Produtos Industrializados
     → Contexto: industrialização, fabricação, produto nacional
   
   - PIS = Programa de Integração Social
   - COFINS = Contribuição para Financiamento da Seguridade Social
     → Sempre analisar juntos quando mencionados
   
   - ICMS = Imposto sobre Circulação de Mercadorias e Serviços
   - ISS = Imposto Sobre Serviços
   - IRPJ = Imposto de Renda Pessoa Jurídica
   - CSLL = Contribuição Social sobre o Lucro Líquido

2. 🆕 NOVOS TRIBUTOS - REFORMA TRIBUTÁRIA (LC 214/2024):
   
   - IBS = Imposto sobre Bens e Serviços (ESTADUAL/MUNICIPAL)
     → Substitui: ICMS + ISS
     → Contexto: operações com bens e serviços, IVA dual
     → Competência: Estados e Municípios
     → Início: 2026 (teste), pleno em 2033
   
   - CBS = Contribuição sobre Bens e Serviços (FEDERAL)
     → Substitui: PIS + COFINS
     → Contexto: contribuição federal, IVA dual
     → Competência: União
     → Início: 2026 (teste), pleno em 2027
   
   - IS = Imposto Seletivo (FEDERAL)
     → Também chamado: "Imposto do Pecado"
     → Incide sobre: produtos prejudiciais à saúde/meio ambiente
     → Exemplos: bebidas alcoólicas, cigarros, veículos poluentes
     → Competência: União
     → Início: 2027

3. PERÍODO DE TRANSIÇÃO (2026-2033):
   
   📅 CRONOGRAMA:
   - 2026: CBS 0,9% + IBS 0,1% (teste)
   - 2027: CBS alíquota cheia, IBS aumenta gradualmente
   - 2027: IS entra em vigor
   - 2029-2032: Redução gradual de PIS/COFINS/ICMS/ISS
   - 2033: Extinção total de PIS/COFINS/ICMS/ISS
   
   ⚠️ ATENÇÃO: Durante transição, legislação pode mencionar AMBOS os sistemas!

4. INCISOS DA LEI (são NUMERAIS ROMANOS de artigos):
   - "inciso II" ou "§2º, II" ou "art. 11-C, II" = referência a artigo de lei
   - Contexto: sempre acompanhado de "art.", "§", "inciso", "alínea"
   - ❌ NUNCA são tributos!

5. COMO DISTINGUIR:

   ✅ CORRETO - II como tributo:
   "Suspensão do II (Imposto de Importação) para produtos tecnológicos"
   "Redução de II de 10% para 0% nas importações"
   "II e IPI ficam suspensos na importação"
   
   ✅ CORRETO - Novos tributos:
   "Alíquota do CBS será de 8,8%"
   "IBS terá alíquota de referência de 17,7%"
   "IS incidirá sobre bebidas açucaradas"
   
   ✅ CORRETO - II como inciso:
   "Conforme art. 11-C, inciso II, da Lei..."
   "Os requisitos dos incisos II, III, IV e V devem ser cumpridos"
   
   ❌ INCORRETO - Confusão comum:
   "II, III, IV e V" NÃO é uma lista de impostos!
   → Isso é uma lista de INCISOS de lei

6. REGRA DE OURO:
   - Se a frase fala de "inciso II, III, IV, V" → São NUMERAIS de lei
   - Se a frase fala de "II e IPI" → São TRIBUTOS
   - Se há "art." ou "§" antes → É NUMERAL de lei
   - Se há contexto de importação/alfândega → É TRIBUTO II
   - Se menciona "IVA dual" ou "reforma tributária" → Provavelmente IBS/CBS
"""

# ============================================================================
# 🆕 REFORMA TRIBUTÁRIA - CONFIGURAÇÕES ESPECÍFICAS
# ============================================================================

REFORMA_TRIBUTARIA_INFO = """
📋 REFORMA TRIBUTÁRIA - LC 214/2024

🎯 OBJETIVO: Simplificar sistema tributário brasileiro

📊 NOVOS TRIBUTOS:

1. CBS (Contribuição sobre Bens e Serviços)
   - Tributo FEDERAL
   - Substitui: PIS + COFINS
   - Alíquota estimada: ~8,8%
   - Não cumulativo (crédito amplo)
   
2. IBS (Imposto sobre Bens e Serviços)
   - Tributo ESTADUAL + MUNICIPAL
   - Substitui: ICMS + ISS
   - Alíquota estimada: ~17,7%
   - Cobrança no destino (não na origem)
   
3. IS (Imposto Seletivo)
   - Tributo FEDERAL
   - Produtos específicos (saúde/ambiente)
   - Alíquotas variáveis por produto

📅 CRONOGRAMA DE TRANSIÇÃO:

| Ano  | CBS           | IBS           | PIS/COFINS    | ICMS/ISS      |
|------|---------------|---------------|---------------|---------------|
| 2026 | 0,9% (teste)  | 0,1% (teste)  | 100%          | 100%          |
| 2027 | 100%          | Aumenta       | Reduz         | 100%          |
| 2029 | 100%          | Aumenta       | Reduz         | 90%           |
| 2030 | 100%          | Aumenta       | Reduz         | 80%           |
| 2031 | 100%          | Aumenta       | Reduz         | 70%           |
| 2032 | 100%          | Aumenta       | Reduz         | 60%           |
| 2033 | 100%          | 100%          | EXTINTO       | EXTINTO       |

🏢 IMPACTO PARA DELL:
- Simplificação de obrigações acessórias
- Crédito amplo (inclusive serviços)
- Cobrança no destino beneficia exportação
- Necessidade de atualizar ERP para novos tributos
"""

# ============================================================================
# 🆕 LEGISLAÇÃO ESTADUAL - CONFIGURAÇÕES
# ============================================================================

LEGISLACAO_ESTADUAL_INFO = """
📋 LEGISLAÇÃO ESTADUAL - ICMS

🏛️ FONTES POR ESTADO:

| Estado | SEFAZ URL                              | Convênios    |
|--------|----------------------------------------|--------------|
| SP     | fazenda.sp.gov.br                      | CONFAZ       |
| RS     | sefaz.rs.gov.br                        | CONFAZ       |
| RJ     | fazenda.rj.gov.br                      | CONFAZ       |
| MG     | fazenda.mg.gov.br                      | CONFAZ       |
| PR     | fazenda.pr.gov.br                      | CONFAZ       |

🔗 CONFAZ (Conselho Nacional de Política Fazendária):
- URL: confaz.fazenda.gov.br
- Publica: Convênios ICMS, Protocolos, Ajustes SINIEF

📋 TIPOS DE ATO ESTADUAL:
1. Convênio ICMS - Acordo entre estados (CONFAZ)
2. Protocolo ICMS - Acordo entre alguns estados
3. Ajuste SINIEF - Normas de documentos fiscais
4. Decreto Estadual - Regulamenta ICMS no estado
5. Portaria CAT/SAT/SEF - Normas operacionais

⚠️ ATENÇÃO PARA DELL:
- Filiais em SP, RS, RJ: verificar legislação de cada estado
- ICMS-ST (Substituição Tributária): produtos de informática
- Diferencial de alíquota (DIFAL): operações interestaduais
- Benefícios fiscais: podem variar por estado
"""

# ============================================================================
# 🆕 LISTA COMPLETA DE TRIBUTOS SUPORTADOS
# ============================================================================

TRIBUTOS_SUPORTADOS = {
    # Tributos Federais Atuais
    'PIS': {
        'nome_completo': 'Programa de Integração Social',
        'competencia': 'Federal',
        'status': 'Ativo (até 2033)',
        'substituido_por': 'CBS'
    },
    'COFINS': {
        'nome_completo': 'Contribuição para Financiamento da Seguridade Social',
        'competencia': 'Federal',
        'status': 'Ativo (até 2033)',
        'substituido_por': 'CBS'
    },
    'IPI': {
        'nome_completo': 'Imposto sobre Produtos Industrializados',
        'competencia': 'Federal',
        'status': 'Ativo',
        'substituido_por': None
    },
    'II': {
        'nome_completo': 'Imposto de Importação',
        'competencia': 'Federal',
        'status': 'Ativo',
        'substituido_por': None
    },
    'IRPJ': {
        'nome_completo': 'Imposto de Renda Pessoa Jurídica',
        'competencia': 'Federal',
        'status': 'Ativo',
        'substituido_por': None
    },
    'CSLL': {
        'nome_completo': 'Contribuição Social sobre o Lucro Líquido',
        'competencia': 'Federal',
        'status': 'Ativo',
        'substituido_por': None
    },
    
    # Tributos Estaduais/Municipais Atuais
    'ICMS': {
        'nome_completo': 'Imposto sobre Circulação de Mercadorias e Serviços',
        'competencia': 'Estadual',
        'status': 'Ativo (até 2033)',
        'substituido_por': 'IBS'
    },
    'ISS': {
        'nome_completo': 'Imposto Sobre Serviços',
        'competencia': 'Municipal',
        'status': 'Ativo (até 2033)',
        'substituido_por': 'IBS'
    },
    
    # 🆕 Novos Tributos - Reforma Tributária
    'CBS': {
        'nome_completo': 'Contribuição sobre Bens e Serviços',
        'competencia': 'Federal',
        'status': 'Novo (a partir de 2026)',
        'substitui': ['PIS', 'COFINS']
    },
    'IBS': {
        'nome_completo': 'Imposto sobre Bens e Serviços',
        'competencia': 'Estadual/Municipal',
        'status': 'Novo (a partir de 2026)',
        'substitui': ['ICMS', 'ISS']
    },
    'IS': {
        'nome_completo': 'Imposto Seletivo',
        'competencia': 'Federal',
        'status': 'Novo (a partir de 2027)',
        'substitui': None
    },
    
    # Variações comuns
    'PIS/COFINS': {
        'nome_completo': 'PIS e COFINS (mencionados juntos)',
        'competencia': 'Federal',
        'status': 'Ativo',
        'substituido_por': 'CBS'
    },
    'PIS-Importação': {
        'nome_completo': 'PIS incidente na Importação',
        'competencia': 'Federal',
        'status': 'Ativo',
        'substituido_por': 'CBS'
    },
    'COFINS-Importação': {
        'nome_completo': 'COFINS incidente na Importação',
        'competencia': 'Federal',
        'status': 'Ativo',
        'substituido_por': 'CBS'
    },
    'ICMS-ST': {
        'nome_completo': 'ICMS Substituição Tributária',
        'competencia': 'Estadual',
        'status': 'Ativo',
        'substituido_por': 'IBS'
    },
    'DIFAL': {
        'nome_completo': 'Diferencial de Alíquota ICMS',
        'competencia': 'Estadual',
        'status': 'Ativo',
        'substituido_por': 'IBS'
    },
}

# ============================================================================
# PROMPTS GENÉRICOS V4.3 - QUALQUER TIPO DE LEGISLAÇÃO
# ============================================================================

GENERIC_EXTRACTION_PROMPT = """Você é um especialista em legislação brasileira, especialmente tributária e corporativa.

Analise COMPLETAMENTE a legislação fornecida e extraia TODAS as informações relevantes de forma estruturada.

**INSTRUÇÕES:**

1. Identifique o tipo de legislação (Lei, MP, Decreto, Portaria, Convênio ICMS, etc.)
2. Extraia o número e data da legislação
3. Identifique o objetivo e ementa
4. Liste TODAS as alterações propostas ou implementadas
5. Identifique artigos, incisos e parágrafos relevantes
6. Extraia datas de vigência e prazos
7. Identifique tributos mencionados:
   - ATUAIS: PIS, COFINS, IPI, ICMS, ISS, II, IRPJ, CSLL, ICMS-ST, DIFAL
   - REFORMA TRIBUTÁRIA: IBS, CBS, IS (Imposto Seletivo)
8. Liste benefícios fiscais, suspensões, isenções ou reduções
9. Identifique setores econômicos afetados
10. Extraia percentuais, valores monetários e quantificações
11. Identifique requisitos, condições e obrigações
12. Liste estados, regiões ou localidades mencionadas
13. Identifique tipos de empresa afetadas (porte, atividade, localização)
14. Se for legislação da Reforma Tributária, identifique:
    - Período de transição mencionado
    - Alíquotas de IBS/CBS/IS
    - Regras de crédito
    - Exceções e regimes especiais

CONTEÚDO:
{content}

QUERY:
{query}

Forneça uma análise completa e estruturada, preservando todos os detalhes importantes da legislação."""

# ============================================================================
# PROMPTS ESPECIALIZADOS POR SEÇÃO
# ============================================================================

SECTION_EXTRACTION_PROMPT = """Analise o conteúdo da legislação e extraia informações sobre: {section_name}

CONTEÚDO:
{content}

Foque especificamente em {focus_areas}.

Formate a resposta de forma clara e estruturada, preservando números, datas, percentuais e detalhes específicos."""

IMPACT_ANALYSIS_PROMPT = """Analise esta legislação e identifique:

1. SETORES IMPACTADOS
   - Quais setores econômicos são afetados?
   - Há setores específicos mencionados?

2. TIPO DE EMPRESA
   - Pequenas empresas?
   - Grandes empresas?
   - Multinacionais?
   - Regime tributário específico (Simples, Presumido, Real)?

3. ABRANGÊNCIA GEOGRÁFICA
   - Aplica-se a todo Brasil?
   - Estados ou regiões específicas?
   - Benefícios regionais (Norte, Nordeste, Centro-Oeste)?

4. TRIBUTOS AFETADOS
   - Quais impostos/contribuições?
   - Há mudanças de alíquota, base de cálculo ou prazo?

CONTEÚDO:
{content}

Responda de forma objetiva e precisa."""

DELL_RELEVANCE_PROMPT = """Você é um analista fiscal da Dell Technologies Brazil.

Analise esta legislação considerando as seguintes informações da empresa:

{dell_info}

LEGISLAÇÃO ANALISADA:
{legislation_summary}

INSTRUÇÕES:

1. Avalie se esta legislação tem IMPACTO DIRETO na Dell
2. Considere as atividades da Dell: fabricação, importação, exportação, comercialização de TI, serviços técnicos
3. Considere as localidades das filiais (SP, RS, RJ)
4. Considere o regime tributário (Lucro Real)

RESPONDA:

**RELEVÂNCIA PARA DELL:** [ALTA / MÉDIA / BAIXA]

**JUSTIFICATIVA:**
[Explique por que é relevante ou não]

**ÁREAS IMPACTADAS NA DELL:**
[Liste quais áreas/filiais/operações seriam afetadas]

**AÇÃO REQUERIDA:**
[O que a Dell precisa fazer? Ajustar sistemas? Revisar processos? Aproveitar benefício? Nenhuma ação?]

**IMPACTO FISCAL/FINANCEIRO:**
[Positivo/Negativo/Neutro e por quê]

Seja objetivo e direto."""

DATES_EXTRACTION_PROMPT = """Extraia TODAS as datas e vigências desta legislação.

Procure por:
- Data de publicação
- Data de início de vigência
- Prazos específicos por tributo
- Datas limite para ações
- Períodos de transição
- Revogações com data

CONTEÚDO:
{content}

Liste todas as datas encontradas com seus contextos específicos."""

NUMBERS_EXTRACTION_PROMPT = """Extraia TODOS os números, percentuais e valores desta legislação.

Procure por:
- Percentuais de alíquota, redução, aumento
- Valores em reais
- Percentuais de compromisso
- Limites quantitativos
- Prazos em anos/meses/dias

CONTEÚDO:
{content}

Liste todos os valores encontrados com seus contextos."""

# ============================================================================
# ✅ NOVO: PROMPT PARA SYSTEM CHANGES COM REGRAS DE DESAMBIGUAÇÃO
# ============================================================================

SYSTEM_CHANGES_PROMPT = """Você é um especialista em análise de mudanças tributárias e sistemas fiscais.

{tributo_rules}

Identifique MUDANÇAS ESPECÍFICAS no sistema tributário que requerem parametrização em ERP/sistemas.

ANALISE:
{data}

IMPACTO GERAL:
{impact}

INSTRUÇÕES:

1. Para CADA tributo afetado, identifique:
   - Tributo (PIS, COFINS, IPI, II, ICMS, ISS, IBS, CBS, IS, etc.)
   - Tipo de mudança (SUSPENSÃO, REDUÇÃO, ISENÇÃO, AUMENTO, NOVO TRIBUTO, etc.)
   - Situação ANTERIOR (alíquota/regime antigo)
   - Situação NOVA (alíquota/regime novo)
   - Condições para aplicar
   - Vigência específica
   - Operações afetadas (importação, venda, exportação, etc.)

2. ⚠️  ATENÇÃO ESPECIAL COM "II":
   - Se o texto menciona "inciso II, III, IV, V" → NÃO são tributos!
   - Apenas "II" com contexto de importação/alfândega é o tributo
   - Exemplo CORRETO: "Suspensão do II (Imposto de Importação)"
   - Exemplo INCORRETO: "Tributos II, III, IV e V" (são incisos!)

3. 🆕 REFORMA TRIBUTÁRIA - Novos tributos:
   - IBS (Imposto sobre Bens e Serviços) - substitui ICMS + ISS
   - CBS (Contribuição sobre Bens e Serviços) - substitui PIS + COFINS
   - IS (Imposto Seletivo) - produtos específicos
   
   Se a legislação mencionar estes tributos, identifique:
   - Alíquotas específicas
   - Regras de crédito
   - Período de transição
   - Exceções ao regime geral

4. Liste operações específicas afetadas:
   - Importação, exportação, venda mercado interno, industrialização, etc.

5. Identifique tipos de cliente/empresa que podem usar:
   - PJ habilitada em regime especial? Lucro Real? Simples? Todos?

6. Para ICMS estadual, identifique:
   - Estados específicos mencionados
   - Convênios CONFAZ aplicáveis
   - ICMS-ST (Substituição Tributária)
   - DIFAL (Diferencial de Alíquota)

Formate de forma ESTRUTURADA e CLARA, sem truncar descrições no meio."""

# ============================================================================
# TEMPLATE PARA ANÁLISE DELL
# ============================================================================

DELL_ANALYSIS_TEMPLATE = """
================================================================================
📋 ANÁLISE DE LEGISLAÇÃO BRASILEIRA - DELL TECHNOLOGIES BRAZIL
================================================================================

🏛️  {tipo_legislacao}
📄 {numero_legislacao}
📅 Data: {data_publicacao}

================================================================================
1️⃣  RESUMO EXECUTIVO
================================================================================

📌 SOBRE A LEGISLAÇÃO:
{resumo_alteracao}

🎯 RELEVÂNCIA PARA DELL: {relevancia_dell}

📍 JUSTIFICATIVA:
{justificativa}

================================================================================
2️⃣  MUDANÇAS NECESSÁRIAS NO SISTEMA
================================================================================

⚙️  MUDANÇAS DE ALÍQUOTAS E TRIBUTOS:

{system_changes}

📋 OPERAÇÕES AFETADAS:
{operacoes}

👥 TIPOS DE CLIENTE/EMPRESA BENEFICIÁRIA:
{tipos_cliente}

🔧 PARAMETRIZAÇÕES NECESSÁRIAS NO ERP:
{parametrizacoes}

================================================================================
3️⃣  IMPACTO POR TRIBUTO
================================================================================

{tributos_detalhados}

================================================================================
4️⃣  VIGÊNCIAS E PRAZOS CRÍTICOS
================================================================================

📅 DATAS IMPORTANTES:

{vigencias}

================================================================================
5️⃣  AÇÕES REQUERIDAS
================================================================================

🎯 AÇÃO PRINCIPAL:
{acao_requerida}

⚙️  AÇÕES TÉCNICAS (TI/Desenvolvimento):
{acoes_tecnicas}

📊 AÇÕES FISCAIS/COMPLIANCE:
{acoes_fiscais}

================================================================================
6️⃣  DETALHAMENTO TÉCNICO
================================================================================

📜 PRINCIPAIS ARTIGOS RELEVANTES:
{artigos_principais}

================================================================================
7️⃣  FONTES CONSULTADAS
================================================================================
{fontes}

================================================================================
⚙️  Sistema: Dell GenAI v4.3 | Modelo: {model}
🗃️  Arquitetura: 12 Agentes Especializados
🎯 Análise específica para Dell Technologies Brazil
🆕 v4.3: Correções de bugs críticos + Desambiguação de tributos
================================================================================
"""

# ============================================================================
# TEMPLATES POR TIPO DE LEGISLAÇÃO
# ============================================================================

TEMPLATES = {
    "default": DELL_ANALYSIS_TEMPLATE,
    "lei": DELL_ANALYSIS_TEMPLATE,
    "lei_complementar": DELL_ANALYSIS_TEMPLATE,
    "medida_provisoria": DELL_ANALYSIS_TEMPLATE,
    "decreto": DELL_ANALYSIS_TEMPLATE,
    "portaria": DELL_ANALYSIS_TEMPLATE,
    "instrucao_normativa": DELL_ANALYSIS_TEMPLATE,
    "regime_tributario": DELL_ANALYSIS_TEMPLATE,
    "convenio_icms": DELL_ANALYSIS_TEMPLATE,
    "protocolo_icms": DELL_ANALYSIS_TEMPLATE,
    "ajuste_sinief": DELL_ANALYSIS_TEMPLATE,
    "reforma_tributaria": DELL_ANALYSIS_TEMPLATE,
}

def get_template(leg_type: str = "default") -> str:
    """Retorna template apropriado"""
    return TEMPLATES.get(leg_type, DELL_ANALYSIS_TEMPLATE)

def validate_config():
    """Valida configuração"""
    missing = []
    if not DEV_GENAI_API_KEY:
        missing.append("DEV_GENAI_API_KEY")
    return len(missing) == 0, missing
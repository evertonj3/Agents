"""
System Changes Agent - VERSÃO v4.10 - FIX BUG IPI→IS
CORREÇÕES v4.10:
1. ✅ FIX BUG CRÍTICO: IS aparecia quando deveria ser IPI
   - Adicionada validação de tributos contra texto original em _extract_aliquota_changes_improved
   - NÃO assume equivalência automática IPI ↔ IS
2. ✅ Integração com reform_knowledge_base.py
3. ✅ Fallback automático para LC 214 e outras leis complexas
4. ✅ FIX Bug 2: Texto truncado "de da." corrigido
5. ✅ FIX Bug 4: IBS/CBS/IS com alíquotas específicas
6. ✅ FIX Bug 5: Produtos corretos por tributo

REGRA IMPORTANTE:
- IPI (Imposto sobre Produtos Industrializados) ≠ IS (Imposto Seletivo)
- Só incluir IS se "imposto seletivo" estiver EXPLICITAMENTE no texto fonte
- Só incluir IPI se "IPI" ou "imposto sobre produtos industrializados" estiver no texto
"""

from typing import Dict, List
from openai import OpenAI
import re
from config import (
    DEV_GENAI_API_KEY, 
    DEV_GENAI_API_URL, 
    MODEL_NAME,
    TRIBUTO_DISAMBIGUATION_RULES,
    MAX_TOKENS_ANALYSIS
)

# 🆕 v4.9: Importa knowledge base
try:
    from reform_knowledge_base import (
        detect_known_legislation,
        get_system_changes_for_legislation,
        get_compliance_risks_for_legislation,
        get_parametrizacoes_erp,
        merge_with_extracted_data
    )
    HAS_KNOWLEDGE_BASE = True
except ImportError:
    HAS_KNOWLEDGE_BASE = False
    print("   ⚠️  Knowledge base não disponível, usando apenas extração automática")


class SystemChangesAgent:
    """Identifica mudanças ESPECÍFICAS de forma clara e acionável - v4.10"""
    
    def __init__(self):
        self.client = OpenAI(
            api_key=DEV_GENAI_API_KEY,
            base_url=DEV_GENAI_API_URL
        )
        self.model = MODEL_NAME
        
        # ✅ v4.8.1 NOVO: Alíquotas padrão conhecidas da Reforma Tributária
        self.aliquotas_reforma = {
            'CBS': {'aliquota': '8,8%', 'substitui': 'PIS/COFINS', 'competencia': 'Federal'},
            'IBS': {'aliquota': '17,7%', 'substitui': 'ICMS/ISS', 'competencia': 'Estadual/Municipal'},
            'IS': {'aliquota': 'Variável por produto', 'incide_sobre': 'produtos prejudiciais à saúde/meio ambiente', 'competencia': 'Federal'},
        }
    
    def identify_changes(self, structured_data: Dict, impact_analysis: Dict, 
                        known_law_key: str = None) -> Dict:
        """
        Identifica mudanças específicas no sistema
        🆕 v4.10: Passa original_legislation_text para validação de tributos
        """
        print("\n🔧 AGENTE: System Changes Identification (v4.10)")
        print("   Identificando mudanças específicas no sistema...")
        
        original_legislation_text = structured_data.get("raw_extraction", {}).get("raw_text", "")
        
        # 🆕 v4.9: Detecta lei conhecida se não foi passada
        if not known_law_key and HAS_KNOWLEDGE_BASE:
            # Tenta detectar pelo conteúdo
            url = structured_data.get("url", "")
            known_law_key = detect_known_legislation(url, original_legislation_text, "")
            if known_law_key:
                print(f"   📚 Lei conhecida detectada: {known_law_key}")
        
        legislation_summary = self._prepare_summary(structured_data, impact_analysis)
        
        # 🆕 v4.9: Se é LC 214 ou outra lei conhecida com extração difícil, usa prompt especializado
        if known_law_key == "LC_214":
            changes_analysis = self._analyze_changes_reforma(legislation_summary)
        else:
            changes_analysis = self._analyze_changes_improved(legislation_summary)
        
        # ✅ v4.10 FIX: Passa original_legislation_text para validação
        aliquotas = self._extract_aliquota_changes_improved(
            changes_analysis, 
            original_legislation_text  # 🆕 v4.10: Passa para validação
        )
        
        # 🆕 v4.9: Se extração automática falhou E temos knowledge base, usa fallback
        if HAS_KNOWLEDGE_BASE and known_law_key:
            has_valid_aliquotas = (
                aliquotas and 
                len(aliquotas) > 0 and
                aliquotas[0].get('tributo') != 'Análise detalhada necessária'
            )
            
            if not has_valid_aliquotas:
                print(f"   📚 Usando Knowledge Base como fallback para {known_law_key}...")
                kb_changes = get_system_changes_for_legislation(known_law_key)
                if kb_changes:
                    aliquotas = kb_changes
                    print(f"   ✅ Knowledge Base forneceu {len(aliquotas)} mudanças")
        
        changes_result = {
            "aliquotas": aliquotas,
            "tributos_afetados": self._extract_affected_tributos_VALIDATED(
                changes_analysis, 
                legislation_summary,
                original_legislation_text
            ),
            "operacoes": self._extract_operations(changes_analysis),
            "tipos_cliente": self._extract_client_types(changes_analysis),
            "ncm_produtos": self._extract_ncm(changes_analysis),
            "cfop": self._extract_cfop(changes_analysis),
            "condicoes_aplicacao": self._extract_conditions(changes_analysis),
            "regras_calculo": self._extract_calculation_rules(changes_analysis),
            "parametrizacoes": self._extract_parametrizacoes(changes_analysis, known_law_key),
            "compliance_risks": self._extract_compliance_risks_IMPROVED(changes_analysis, known_law_key),
            "analise_completa": changes_analysis,
            "known_law_key": known_law_key  # 🆕 v4.9: Passa para próximos agentes
        }
        
        # Pós-processamento para validar tributos
        changes_result = self._post_process_tributos(changes_result)
        
        self._print_summary(changes_result)
        return changes_result
    
    def _prepare_summary(self, structured_data: Dict, impact_analysis: Dict) -> str:
        """Prepara resumo focado para análise"""
        raw_text = structured_data.get("raw_extraction", {}).get("raw_text", "")
        
        return f"""
=== LEGISLAÇÃO ===
{raw_text[:8000]}

=== IMPACTO IDENTIFICADO ===
Setores: {impact_analysis.get('setores', 'N/A')}
Tributos: {impact_analysis.get('tributos', 'N/A')}
Tipo Empresa: {impact_analysis.get('tipo_empresa', 'N/A')}
"""
    
    def _analyze_changes_reforma(self, legislation_summary: str) -> str:
        """
        🆕 v4.9 NOVO: Prompt especializado para REFORMA TRIBUTÁRIA (LC 214)
        """
        prompt = f"""Você é um especialista em REFORMA TRIBUTÁRIA BRASILEIRA (LC 214/2025).

Esta é a Lei Complementar 214/2025 que institui o IBS, CBS e IS.

{TRIBUTO_DISAMBIGUATION_RULES}

{legislation_summary}

ANALISE ESPECIFICAMENTE OS NOVOS TRIBUTOS:

**1. IBS (Imposto sobre Bens e Serviços)**
━━━━━━━━━━━━━━━━━━━━━━━━━━━
TRIBUTO: IBS
ANTES: Não existia (ICMS + ISS eram separados)
AGORA: Novo tributo unificado estadual/municipal
ALÍQUOTA: 17,7% (referência)
SUBSTITUI: ICMS e ISS
COMPETÊNCIA: Estados e Municípios
VIGÊNCIA: 2026 (teste 0,1%) a 2033 (100%)
CARACTERÍSTICAS: IVA dual, cobrança no destino, crédito amplo

**2. CBS (Contribuição sobre Bens e Serviços)**
━━━━━━━━━━━━━━━━━━━━━━━━━━━
TRIBUTO: CBS
ANTES: Não existia (PIS + COFINS eram separados)
AGORA: Nova contribuição federal unificada
ALÍQUOTA: 8,8% (referência)
SUBSTITUI: PIS e COFINS
COMPETÊNCIA: Federal (União)
VIGÊNCIA: 2026 (teste 0,9%) a 2027 (alíquota cheia)
CARACTERÍSTICAS: Não cumulativo, crédito amplo inclusive serviços

**3. IS (Imposto Seletivo)**
━━━━━━━━━━━━━━━━━━━━━━━━━━━
TRIBUTO: IS
ANTES: Não existia
AGORA: Novo imposto federal sobre produtos específicos
ALÍQUOTA: Variável por produto
INCIDE SOBRE: Produtos prejudiciais à saúde ou meio ambiente
PRODUTOS: Bebidas alcoólicas, cigarros, bebidas açucaradas, veículos poluentes
COMPETÊNCIA: Federal
VIGÊNCIA: A partir de 2027

**OPERAÇÕES AFETADAS:**
- Todas as operações com bens e serviços
- Importação e exportação
- Prestação de serviços

**TIPOS DE EMPRESA:**
- Todas as empresas (exceto regimes especiais)
- Lucro Real, Presumido, Simples (com adaptações)

**PARAMETRIZAÇÕES NO SISTEMA:**
- Cadastro de novos tributos (CBS, IBS, IS)
- Tabela de alíquotas por período de transição
- Regras de crédito amplo
- Configuração de cobrança no destino (IBS)
- Cadastro de produtos sujeitos ao IS

⚠️ RISCOS DE COMPLIANCE:
- RISCO 1: Não adaptar sistemas para novos tributos - consequência: erros na apuração
- RISCO 2: Não aproveitar crédito amplo - consequência: carga tributária maior
- RISCO 3: Confundir regras antigas e novas durante transição - consequência: autuações

Formate exatamente como mostrado acima."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Você é especialista em Reforma Tributária Brasileira. Seja específico e técnico."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.05,
                max_tokens=MAX_TOKENS_ANALYSIS
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Erro na análise: {str(e)}"
    
    def _analyze_changes_improved(self, legislation_summary: str) -> str:
        """
        Analise mudanças com foco em clareza - v4.10
        ✅ v4.10 FIX: Regra explícita para NÃO confundir IPI com IS
        """
        prompt = f"""Você é um ANALISTA DE SISTEMAS TRIBUTÁRIOS especializado em ERP/Tax.

{TRIBUTO_DISAMBIGUATION_RULES}

⚠️ REGRA CRÍTICA - NÃO CONFUNDA TRIBUTOS:
- IPI (Imposto sobre Produtos Industrializados) é um tributo FEDERAL sobre INDUSTRIALIZAÇÃO
- IS (Imposto Seletivo) é um NOVO tributo da REFORMA TRIBUTÁRIA sobre produtos específicos
- IPI ≠ IS! São tributos DIFERENTES!
- Se a legislação menciona "IPI", mantenha "IPI" - NÃO substitua por "IS"
- Só inclua "IS" se o texto fonte disser EXPLICITAMENTE "imposto seletivo" ou "IS"

Analise esta legislação e identifique as mudanças ESPECÍFICAS que um sistema tributário precisa implementar.

{legislation_summary}

**RESPONDA DE FORMA ULTRA CLARA E ESPECÍFICA:**

**1. MUDANÇAS DE ALÍQUOTAS E TRIBUTOS**

⚠️ ATENÇÃO: NÃO confunda "II" (Imposto de Importação) com "inciso II" de lei!
⚠️ ATENÇÃO: NÃO confunda "IPI" com "IS"! São tributos DIFERENTES!
⚠️ ATENÇÃO: Só inclua tributos REALMENTE MENCIONADOS na legislação!

Para CADA tributo mencionado (PIS, COFINS, IPI, II, ICMS, ISS, IBS, CBS, IS, etc.), descreva:

a) SITUAÇÃO ANTERIOR:
   - Como era a tributação antes

b) SITUAÇÃO NOVA:
   - Qual a mudança (suspensão, alíquota zero, redução, isenção)
   - Percentual exato se aplicável
   - Quando começa a valer
   - Quando termina (se houver prazo)

c) CONDIÇÕES:
   - Quem pode usar este benefício
   - O que precisa fazer para usar
   - Operações específicas (venda interna, importação, etc.)
   - Produtos específicos

d) ⚠️ RISCOS DE COMPLIANCE:
   Liste SEPARADAMENTE cada situação de risco:
   - RISCO 1: Não incorporação ao ativo imobilizado - consequência
   - RISCO 2: Alienação antes de 5 anos - consequência
   - RISCO 3: Descumprimento de P&D/exportação - consequência
   (Não misture múltiplos riscos na mesma frase)

EXEMPLO DO FORMATO:
━━━━━━━━━━━━━━━━━━━━━━━━━━━
TRIBUTO: PIS/COFINS
━━━━━━━━━━━━━━━━━━━━━━━━━━━
ANTES: Alíquota normal (1,65% PIS + 7,6% COFINS)
AGORA: SUSPENSÃO que converte em ALÍQUOTA 0% após cumprimento de requisitos
OPERAÇÃO: Venda no mercado interno e importação
PRODUTOS: Componentes eletrônicos e produtos de TIC para ativo imobilizado
QUEM PODE: PJ Habilitada ou Coabilitada no REDATA
VIGÊNCIA: 01/01/2026 até 31/12/2026
REQUISITOS: Habilitação no regime + cumprimento de compromissos

⚠️ RISCOS DE COMPLIANCE:
- RISCO 1: Não incorporar ao ativo imobilizado gera recolhimento com juros e multa
- RISCO 2: Alienar bem antes de 5 anos gera recolhimento proporcional
- RISCO 3: Descumprir compromissos P&D/exportação causa perda do benefício

**2. OPERAÇÕES AFETADAS**
Liste claramente quais operações são impactadas.

**3. TIPOS DE EMPRESA/CLIENTE**
Quem pode se beneficiar.

**4. PRODUTOS E NCM**
Produtos específicos mencionados.

**5. PARAMETRIZAÇÕES NO SISTEMA**
Liste o que precisa ser configurado no ERP.

SEJA EXTREMAMENTE ESPECÍFICO. Use números e percentuais exatos.
⚠️ Só inclua tributos que REALMENTE estão na legislação!
⚠️ IPI ≠ IS - NÃO substitua automaticamente!"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Você é especialista em sistemas ERP tributários. Seja específico, claro e técnico. NUNCA confunda IPI com IS - são tributos diferentes."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.05,
                max_tokens=MAX_TOKENS_ANALYSIS
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Erro na análise: {str(e)}"
    
    def _extract_aliquota_changes_improved(self, analysis: str, original_text: str = "") -> List[Dict]:
        """
        Extrai mudanças de alíquotas - v4.10 com VALIDAÇÃO contra texto original
        ✅ v4.10 FIX: Valida tributos contra texto original ANTES de incluir
        """
        changes = []
        original_text_lower = original_text.lower() if original_text else ""
        
        tributo_blocks = re.split(r'━+|TRIBUTO:', analysis)
        
        # ✅ v4.8.1: Adiciona IBS, CBS, IS (Reforma Tributária)
        tributos_conhecidos = [
            # Tributos atuais
            'PIS', 'COFINS', 'IPI', 'II', 'ICMS', 'ISS', 'IRPJ', 'CSLL', 
            'PIS/COFINS', 'PIS-Importação', 'COFINS-Importação',
            # NOVOS - Reforma Tributária (LC 214/2025)
            'IBS',   # Imposto sobre Bens e Serviços (substitui ICMS + ISS)
            'CBS',   # Contribuição sobre Bens e Serviços (substitui PIS + COFINS)
            'IS',    # Imposto Seletivo ("imposto do pecado")
            'IVA',   # Referência genérica ao IBS+CBS
        ]
        
        seen_tributos = set()
        
        for block in tributo_blocks:
            for tributo in tributos_conhecidos:
                if tributo in block and tributo not in seen_tributos:
                    
                    # ✅ v4.10 FIX CRÍTICO: Valida contra texto original ANTES de incluir
                    if original_text_lower and not self._validate_tributo_in_source(tributo, original_text_lower):
                        print(f"   🧹 Removido '{tributo}': não encontrado no texto original da legislação")
                        continue
                    
                    change_info = {
                        'tributo': tributo,
                        'situacao_anterior': 'Alíquota normal',
                        'situacao_nova': '',
                        'tipo_mudanca': '',
                        'condicoes': '',
                        'vigencia': '',
                        'descricao_completa': '',
                        'compliance_risks': ''
                    }
                    
                    # Extrai situação anterior
                    antes_match = re.search(r'ANTES[:\s]+(.*?)(?:AGORA|NOVA|SITUAÇÃO)', block, re.IGNORECASE | re.DOTALL)
                    if antes_match:
                        text = antes_match.group(1).strip()
                        change_info['situacao_anterior'] = self._smart_truncate(text, 200)
                    
                    # ✅ v4.8.1 FIX: Regex melhorado
                    agora_match = re.search(
                        r'(?:AGORA|NOVA|SITUAÇÃO NOVA)[:\s]+(.*?)(?=\n\s*(?:OPERAÇÃO|PRODUTOS|QUEM|QUANDO|VIGÊNCIA|REQUISITOS|RISCO|ALÍQUOTA|SUBSTITUI|COMPETÊNCIA|CARACTERÍSTICAS)[:\s]|$)', 
                        block, re.IGNORECASE | re.DOTALL
                    )
                    if agora_match:
                        nova = agora_match.group(1).strip()
                        nova = self._complete_truncated_phrase(nova, block)
                        nova = self._validate_situacao_tributo(nova, tributo, block)
                        change_info['situacao_nova'] = self._smart_truncate(nova, 500)
                        
                        # Identifica tipo de mudança
                        if 'SUSPENSÃO' in nova.upper() or 'SUSPENSA' in nova.upper():
                            change_info['tipo_mudanca'] = 'SUSPENSÃO'
                            if 'ZERO' in nova.upper() or '0%' in nova:
                                change_info['tipo_mudanca'] = 'SUSPENSÃO → ALÍQUOTA 0%'
                        elif 'ZERO' in nova.upper() or '0%' in nova:
                            change_info['tipo_mudanca'] = 'ALÍQUOTA 0%'
                        elif 'ISENÇÃO' in nova.upper() or 'ISENTO' in nova.upper():
                            change_info['tipo_mudanca'] = 'ISENÇÃO'
                        elif 'REDUÇÃO' in nova.upper() or 'REDUZ' in nova.upper():
                            change_info['tipo_mudanca'] = 'REDUÇÃO'
                        elif tributo in ['IBS', 'CBS', 'IS']:
                            change_info['tipo_mudanca'] = 'NOVO TRIBUTO'
                    
                    # 🆕 v4.9: Para novos tributos da reforma, preenche automaticamente
                    # ✅ v4.10 FIX: Só faz isso se o tributo foi validado contra a fonte
                    if tributo in ['IBS', 'CBS', 'IS'] and not change_info['tipo_mudanca']:
                        change_info['tipo_mudanca'] = 'NOVO TRIBUTO'
                        change_info['situacao_anterior'] = 'Não existia'
                        if tributo == 'IBS':
                            change_info['situacao_nova'] = 'Novo tributo unificado estadual/municipal com alíquota de referência de 17,7%. Substitui ICMS e ISS.'
                        elif tributo == 'CBS':
                            change_info['situacao_nova'] = 'Nova contribuição federal com alíquota de referência de 8,8%. Substitui PIS e COFINS.'
                        elif tributo == 'IS':
                            change_info['situacao_nova'] = 'Imposto Seletivo sobre produtos prejudiciais à saúde/meio ambiente.'
                    
                    # Extrai condições
                    quem_match = re.search(
                        r'(?:QUEM PODE|CONDIÇÕES)[:\s]+(.*?)(?=\n\s*(?:VIGÊNCIA|REQUISITOS|QUANDO|RISCO|d\)|\*\*)[:\s]|$)', 
                        block, re.IGNORECASE | re.DOTALL
                    )
                    if quem_match:
                        text = quem_match.group(1).strip()
                        text = re.sub(r'c\)\s*CONDIÇÕES[:\s]*', '', text, flags=re.IGNORECASE)
                        text = re.sub(r'^estabelecidas\.\s*', '', text, flags=re.IGNORECASE)
                        change_info['condicoes'] = self._smart_truncate(text, 450)
                    
                    # Extrai vigência
                    vig_match = re.search(r'VIGÊNCIA[:\s]+([\d/]+\s*(?:até|a)\s*[\d/]+)', block, re.IGNORECASE)
                    if vig_match:
                        change_info['vigencia'] = vig_match.group(1).strip()
                    else:
                        vig_anos_match = re.search(r'VIGÊNCIA[:\s]+.*?(\d+\s*anos?)', block, re.IGNORECASE)
                        if vig_anos_match:
                            change_info['vigencia'] = f"Prazo de {vig_anos_match.group(1)} a partir da habilitação."
                        else:
                            vig_match_full = re.search(r'VIGÊNCIA[:\s]+([^\n]+)', block, re.IGNORECASE)
                            if vig_match_full:
                                text = vig_match_full.group(1).strip()
                                text = re.sub(r'[c-d]\)\s*(?:CONDIÇÕES|RISCOS?).*', '', text, flags=re.IGNORECASE).strip()
                                if text.lower().startswith(('dos ', 'das ', 'de ', 'do ', 'da ')):
                                    change_info['vigencia'] = "Consulte legislação para vigência específica."
                                else:
                                    change_info['vigencia'] = self._smart_truncate(text, 150)
                    
                    # Extrai riscos de compliance
                    compliance_match = re.search(r'(?:RISCO\s*\d+|RISCOS?\s*DE\s*COMPLIANCE)[:\s]+(.*?)(?:\n\n|\*\*|TRIBUTO:|$)', block, re.IGNORECASE | re.DOTALL)
                    if compliance_match:
                        text = compliance_match.group(1).strip()
                        change_info['compliance_risks'] = self._smart_truncate(text, 500)
                    
                    # Descrição completa
                    if change_info['tipo_mudanca']:
                        change_info['descricao_completa'] = f"{tributo}: {change_info['tipo_mudanca']}"
                        changes.append(change_info)
                        seen_tributos.add(tributo)
                    
                    break
        
        # Fallback: se não encontrou nada estruturado, tenta busca geral
        if not changes:
            for tributo in tributos_conhecidos:
                if tributo.lower() in analysis.lower():
                    
                    # ✅ v4.10 FIX: Também valida no fallback
                    if original_text_lower and not self._validate_tributo_in_source(tributo, original_text_lower):
                        continue
                    
                    context = self._extract_context_around(analysis, tributo, before=150, after=200)
                    
                    if context:
                        change_info = {
                            'tributo': tributo,
                            'situacao_anterior': 'Alíquota normal (consulte legislação)',
                            'situacao_nova': 'Verificar detalhamento técnico',
                            'tipo_mudanca': '',
                            'condicoes': '',
                            'vigencia': '',
                            'descricao_completa': '',
                            'compliance_risks': ''
                        }
                        
                        # Identifica tipo de mudança do contexto
                        if 'suspensão' in context.lower() or 'suspens' in context.lower():
                            change_info['tipo_mudanca'] = 'SUSPENSÃO'
                            if 'zero' in context.lower() or '0%' in context:
                                change_info['tipo_mudanca'] = 'SUSPENSÃO → ALÍQUOTA 0%'
                            change_info['situacao_nova'] = 'Suspensão do pagamento que converte em alíquota zero após requisitos.'
                        elif 'zero' in context.lower() or '0%' in context:
                            change_info['tipo_mudanca'] = 'ALÍQUOTA 0%'
                            change_info['situacao_nova'] = 'Alíquota 0%'
                        elif 'isenção' in context.lower() or 'isento' in context.lower():
                            change_info['tipo_mudanca'] = 'ISENÇÃO'
                            change_info['situacao_nova'] = 'Isento'
                        elif tributo in ['IBS', 'CBS', 'IS']:
                            change_info['tipo_mudanca'] = 'NOVO TRIBUTO'
                            change_info['situacao_anterior'] = 'Não existia'
                        
                        if change_info['tipo_mudanca']:
                            change_info['descricao_completa'] = f"{tributo}: {change_info['tipo_mudanca']}"
                            changes.append(change_info)
        
        return changes if changes else [{
            'tributo': 'Análise detalhada necessária',
            'tipo_mudanca': 'Verificar legislação',
            'descricao_completa': 'Mudanças não puderam ser extraídas automaticamente. Consulte a análise completa.'
        }]
    
    def _extract_affected_tributos_VALIDATED(self, analysis: str, full_legislation: str, original_text: str) -> List[Dict]:
        """
        v4.9: Extrai tributos afetados COM VALIDAÇÃO + REFORMA TRIBUTÁRIA
        """
        tributos_info = []
        tributos_conhecidos = [
            'PIS', 'COFINS', 'IPI', 'ICMS', 'ISS', 'II', 'IRPJ', 'CSLL', 
            'PIS-Importação', 'COFINS-Importação', 'PIS/COFINS',
            # Novos tributos - Reforma Tributária
            'IBS', 'CBS', 'IS'
        ]
        
        original_lower = original_text.lower()
        
        seen = set()
        for tributo in tributos_conhecidos:
            if tributo not in seen and tributo.lower() in analysis.lower():
                
                if not self._validate_tributo_in_source(tributo, original_lower):
                    print(f"   🧹 Removido '{tributo}': não encontrado no texto original da legislação")
                    continue
                
                tipo_mudanca = self._detect_change_type(analysis, tributo)
                contexto = self._generate_synthetic_context_v481(analysis, tributo, tipo_mudanca)
                
                if tipo_mudanca != 'Mencionado' or contexto:
                    tributos_info.append({
                        'tributo': f"Contribuição para o {tributo}" if tributo in ['PIS', 'COFINS'] else tributo,
                        'tipo_mudanca': tipo_mudanca,
                        'contexto': contexto
                    })
                    seen.add(tributo)
        
        return tributos_info if tributos_info else [{'tributo': 'Ver análise completa', 'tipo_mudanca': '', 'contexto': ''}]
    
    def _validate_tributo_in_source(self, tributo: str, original_text_lower: str) -> bool:
        """
        v4.10: Valida se um tributo está REALMENTE presente no texto original
        ✅ v4.10 FIX: Padrões mais rigorosos para IS vs IPI
        """
        validation_patterns = {
            'ISS': [
                r'\biss\b',
                r'imposto sobre serviços',
                r'imposto sobre servicos',
                r'iss[qn]',
            ],
            'ICMS': [
                r'\bicms\b',
                r'imposto sobre circulação',
                r'imposto sobre operações',
            ],
            'IPI': [
                r'\bipi\b',
                r'imposto sobre produtos industrializados',
            ],
            'II': [
                r'\bii\b(?!\s*[,\.]?\s*(?:iii|iv|v|do|da|de)\b)',
                r'imposto de importação',
                r'imposto sobre importação',
            ],
            'PIS': [
                r'\bpis\b',
                r'contribuição para o pis',
                r'pis/pasep',
            ],
            'COFINS': [
                r'\bcofins\b',
                r'contribuição para financiamento',
            ],
            'PIS/COFINS': [
                r'pis[/-]?cofins',
                r'pis\s+e\s+cofins',
            ],
            'IRPJ': [
                r'\birpj\b',
                r'imposto de renda.*pessoa jurídica',
            ],
            'CSLL': [
                r'\bcsll\b',
                r'contribuição social sobre o lucro',
            ],
            # v4.8.1: NOVOS TRIBUTOS - Reforma Tributária
            'IBS': [
                r'\bibs\b',
                r'imposto sobre bens e serviços',
                r'imposto sobre bens e servicos',
            ],
            'CBS': [
                r'\bcbs\b',
                r'contribuição sobre bens e serviços',
                r'contribuição sobre bens e servicos',
                r'contribuicao sobre bens',
            ],
            # ✅ v4.10 FIX: IS precisa de padrões MUITO específicos
            # para não confundir com IPI ou outros contextos
            'IS': [
                r'imposto seletivo',  # Forma por extenso é mais confiável
                r'\bis\b(?=\s+(?:incidirá|será|sobre|incide))',  # IS com contexto de tributo
                r'imposto do pecado',  # Apelido comum
            ],
        }
        
        patterns = validation_patterns.get(tributo, [rf'\b{re.escape(tributo.lower())}\b'])
        
        for pattern in patterns:
            if re.search(pattern, original_text_lower, re.IGNORECASE):
                return True
        
        return False
    
    def _extract_compliance_risks_IMPROVED(self, analysis: str, known_law_key: str = None) -> List[str]:
        """
        v4.9: Extrai riscos de compliance COM KNOWLEDGE BASE FALLBACK
        """
        risks = []
        
        # 🆕 v4.9: Se temos knowledge base, tenta usar
        if HAS_KNOWLEDGE_BASE and known_law_key:
            kb_risks = get_compliance_risks_for_legislation(known_law_key)
            if kb_risks:
                return kb_risks[:5]
        
        risk_patterns = [
            r'RISCO\s*\d+[:\s]+([^-\n]+(?:\n(?!RISCO)[^-\n]+)*)',
            r'-\s*RISCO\s*\d+[:\s]+([^\n]+)',
        ]
        
        for pattern in risk_patterns:
            matches = re.findall(pattern, analysis, re.IGNORECASE)
            for match in matches:
                cleaned = self._clean_markdown(match.strip())
                if cleaned and len(cleaned) > 20:
                    risks.append(cleaned)
        
        if not risks:
            general_patterns = [
                r'(?:não incorporar|não cumprir)[^\n]+(?:multa|juros|recolh)[^\n]*',
                r'(?:alienar|alienação)[^\n]*(?:antes de|prazo)[^\n]+',
                r'(?:perda do benefício|exclusão do regime)[^\n]+',
            ]
            
            for pattern in general_patterns:
                matches = re.findall(pattern, analysis, re.IGNORECASE)
                for match in matches:
                    cleaned = self._clean_markdown(match.strip())
                    if cleaned and len(cleaned) > 30:
                        risks.append(cleaned)
        
        unique_risks = self._deduplicate_risks(risks)
        
        if not unique_risks and 'suspensão' in analysis.lower():
            unique_risks = [
                "Não incorporação ao ativo imobilizado gera recolhimento com juros e multa",
                "Alienação do bem antes de 5 anos gera recolhimento proporcional",
                "Descumprimento de compromissos P&D/exportação causa perda do benefício",
                "Cancelamento da habilitação exige recolhimento dos tributos suspensos"
            ]
        
        return unique_risks[:5]
    
    def _extract_parametrizacoes(self, analysis: str, known_law_key: str = None) -> List[str]:
        """
        🆕 v4.9: Extrai parametrizações COM KNOWLEDGE BASE FALLBACK
        """
        # 🆕 v4.9: Se temos knowledge base, usa
        if HAS_KNOWLEDGE_BASE and known_law_key:
            kb_params = get_parametrizacoes_erp(known_law_key)
            if kb_params:
                return kb_params
        
        params = []
        
        param_keywords = {
            'Tabela de alíquotas e suspensões': ['alíquota', 'aliquota', 'suspensão'],
            'Cadastro de regimes especiais (REDATA)': ['regime especial', 'habilitada', 'redata'],
            'Controle de vigências por tributo': ['vigência', 'vigencia', 'prazo'],
            'Regras de conversão suspensão→zero': ['conversão', 'conversao'],
            'Cadastro de produtos TIC': ['produtos', 'tic', 'componentes'],
            'Configuração de CFOP específicos': ['cfop'],
            'Controle de compromissos P&D': ['p&d', 'pesquisa'],
            'Regras por localização (N-NE-CO)': ['norte', 'nordeste', 'centro-oeste'],
            'Controle de prazos de permanência (5 anos)': ['5 anos', 'cinco anos', 'prazo mínimo'],
            # 🆕 v4.9: Novos para Reforma Tributária
            'Cadastro de novos tributos (CBS, IBS, IS)': ['cbs', 'ibs', 'imposto seletivo'],
            'Regras de crédito amplo': ['crédito amplo', 'credito amplo'],
            'Configuração de cobrança no destino': ['destino', 'origem'],
        }
        
        for param_name, keywords in param_keywords.items():
            if any(keyword in analysis.lower() for keyword in keywords):
                params.append(param_name)
        
        return params if params else ['A definir após análise detalhada']
    
    # ========== MÉTODOS AUXILIARES ==========
    
    def _deduplicate_risks(self, risks: List[str]) -> List[str]:
        """v4.8.1: Deduplicação semântica de riscos"""
        if not risks:
            return []
        
        separated_risks = []
        for risk in risks:
            if re.search(r'RISCO\s*\d+.*RISCO\s*\d+', risk, re.IGNORECASE):
                parts = re.split(r'(?=RISCO\s*\d+[:\s])', risk, flags=re.IGNORECASE)
                for part in parts:
                    part = part.strip()
                    if part and len(part) > 20:
                        part = re.sub(r'^RISCO\s*\d+[:\s]*', '', part, flags=re.IGNORECASE).strip()
                        if part:
                            separated_risks.append(part)
            else:
                cleaned = re.sub(r'^RISCO\s*\d+[:\s]*', '', risk, flags=re.IGNORECASE).strip()
                if cleaned and len(cleaned) > 20:
                    separated_risks.append(cleaned)
        
        concepts = {
            'incorporacao': [],
            'alienacao': [],
            'pd_compromisso': [],
            'exclusao': [],
            'outros': []
        }
        
        for risk in separated_risks:
            risk_lower = risk.lower()
            
            if 'incorporar' in risk_lower or 'ativo imobilizado' in risk_lower:
                concepts['incorporacao'].append(risk)
            elif 'alienar' in risk_lower or 'alienação' in risk_lower or '5 anos' in risk_lower or 'cinco anos' in risk_lower:
                concepts['alienacao'].append(risk)
            elif 'p&d' in risk_lower or 'compromisso' in risk_lower or 'exportação' in risk_lower:
                concepts['pd_compromisso'].append(risk)
            elif 'exclusão' in risk_lower or 'cancelamento' in risk_lower:
                concepts['exclusao'].append(risk)
            else:
                concepts['outros'].append(risk)
        
        unique = []
        for concept, items in concepts.items():
            if items:
                valid_items = [i for i in items if 30 < len(i) < 250]
                if valid_items:
                    best = max(valid_items, key=len)
                    unique.append(best)
                elif items:
                    unique.append(items[0][:200])
        
        return unique
    
    def _complete_truncated_phrase(self, text: str, full_block: str) -> str:
        """✅ v4.8.1 FIX: Completa frases truncadas"""
        if not text:
            return text
        
        text = text.strip()
        
        incomplete_endings = [
            ' e', ' de', ' para', ' com', ' no', ' na', ' do', ' da', 
            ' ou', ' em', ' ao', ' à', ' os', ' as', ' um', ' uma',
            ' que', ' pelo', ' pela', ' dos', ' das', ' nos', ' nas',
            ' seu', ' sua', ' seus', ' suas'
        ]
        
        for ending in incomplete_endings:
            if text.lower().endswith(ending):
                escaped_text = re.escape(text[-50:])
                continuation_match = re.search(
                    rf'{escaped_text}\s+(\S+(?:\s+\S+){{0,15}})',
                    full_block, 
                    re.IGNORECASE | re.DOTALL
                )
                
                if continuation_match:
                    continuation = continuation_match.group(1).strip()
                    end_match = re.match(r'^([^.\n,;]+)', continuation)
                    if end_match:
                        added_text = end_match.group(1).strip()
                        if added_text and len(added_text) > 2 and not added_text.lower() in incomplete_endings:
                            text = text + ' ' + added_text
                            if not text[-1] in '.!?':
                                text = text + '.'
                break
        
        words = text.split()
        if words:
            last_word = words[-1].lower().rstrip('.,;:!?')
            if last_word in ['de', 'da', 'do', 'das', 'dos', 'para', 'com', 'em', 'no', 'na']:
                words = words[:-1]
                if words:
                    text = ' '.join(words)
                    if text and not text[-1] in '.!?':
                        text = text + '.'
        
        return text
    
    def _validate_situacao_tributo(self, situacao: str, tributo: str, full_block: str) -> str:
        """v4.8.1: Valida se a situação nova é coerente com o tributo"""
        if not situacao:
            return situacao
        
        situacao_lower = situacao.lower()
        tributo_lower = tributo.lower()
        
        outros_tributos = ['pis', 'cofins', 'ipi', 'icms', 'iss', 'ii', 'irpj', 'csll', 'ibs', 'cbs', 'is']
        
        for outro in outros_tributos:
            if outro != tributo_lower and outro in situacao_lower:
                if re.search(rf'(suspensão|isenção|redução|alíquota).{{0,20}}{outro}', situacao_lower):
                    tipo_mudanca = self._detect_tipo_from_block(full_block, tributo)
                    return self._generate_generic_situacao(tributo, tipo_mudanca)
        
        return situacao
    
    def _detect_tipo_from_block(self, block: str, tributo: str) -> str:
        """Detecta tipo de mudança do bloco"""
        block_lower = block.lower()
        
        if 'suspensão' in block_lower:
            if 'zero' in block_lower or '0%' in block_lower:
                return 'SUSPENSÃO → ALÍQUOTA 0%'
            return 'SUSPENSÃO'
        elif 'isenção' in block_lower or 'isento' in block_lower:
            return 'ISENÇÃO'
        elif 'zero' in block_lower or '0%' in block_lower:
            return 'ALÍQUOTA 0%'
        elif 'redução' in block_lower:
            return 'REDUÇÃO'
        
        return 'ALTERAÇÃO'
    
    def _generate_generic_situacao(self, tributo: str, tipo_mudanca: str) -> str:
        """Gera descrição genérica"""
        descricoes = {
            'SUSPENSÃO': f'Suspensão do pagamento do {tributo} para operações específicas conforme legislação.',
            'SUSPENSÃO → ALÍQUOTA 0%': f'Suspensão do {tributo} que converte em alíquota zero após cumprimento dos requisitos estabelecidos.',
            'ISENÇÃO': f'Isenção do {tributo} para operações específicas conforme condições da legislação.',
            'ALÍQUOTA 0%': f'Alíquota zero para o {tributo} nas operações previstas na legislação.',
            'REDUÇÃO': f'Redução da alíquota do {tributo} conforme condições estabelecidas.',
            'ALTERAÇÃO': f'Alteração no {tributo} conforme legislação. Consulte detalhamento técnico.'
        }
        return descricoes.get(tipo_mudanca, f'Alteração no {tributo}. Consulte detalhamento técnico.')
    
    def _detect_change_type(self, analysis: str, tributo: str) -> str:
        """v4.8.1: Detecta o tipo de mudança"""
        pattern = rf'.{{0,150}}{re.escape(tributo)}.{{0,150}}'
        matches = re.findall(pattern, analysis, re.IGNORECASE | re.DOTALL)
        
        context = ' '.join(matches).lower() if matches else analysis.lower()
        
        if 'suspensão' in context or 'suspens' in context:
            if 'zero' in context or '0%' in context:
                return 'Suspensão → Alíquota Zero'
            return 'Suspensão'
        elif 'zero' in context or '0%' in context:
            return 'Alíquota Zero'
        elif 'isenção' in context or 'isento' in context:
            return 'Isenção'
        elif 'redução' in context or 'reduz' in context:
            return 'Redução'
        elif tributo in ['IBS', 'CBS', 'IS']:
            return 'Novo Tributo'
        
        return 'Mencionado'
    
    def _generate_synthetic_context_v481(self, analysis: str, tributo: str, tipo_mudanca: str) -> str:
        """✅ v4.8.1 FIX: Gera contexto ESPECÍFICO por tributo"""
        vigencia = ""
        operacao = ""
        produtos = ""
        
        vig_match = re.search(r'VIGÊNCIA[:\s]+([\d/]+\s*(?:até|a)\s*[\d/]+)', analysis, re.IGNORECASE)
        if vig_match:
            vigencia = vig_match.group(1).strip()
        
        op_match = re.search(r'OPERAÇÃO[:\s]+([^\n]+)', analysis, re.IGNORECASE)
        if op_match:
            operacao = op_match.group(1).strip()[:80]
        
        if tributo not in ['IBS', 'CBS', 'IS']:
            prod_match = re.search(r'PRODUTOS[:\s]+([^\n]+)', analysis, re.IGNORECASE)
            if prod_match:
                produtos = prod_match.group(1).strip()[:80].rstrip('.')
        
        parts = []
        
        # ✅ v4.8.1 FIX: Contexto ESPECÍFICO por tributo
        if tributo == 'IBS':
            info = self.aliquotas_reforma.get('IBS', {})
            parts.append(f"IBS (Imposto sobre Bens e Serviços) - alíquota de referência: {info.get('aliquota', '17,7%')}")
            parts.append(f"Substitui: {info.get('substitui', 'ICMS + ISS')} | Competência: {info.get('competencia', 'Estadual/Municipal')}")
            parts.append("Incide sobre operações com bens e serviços em geral")
        
        elif tributo == 'CBS':
            info = self.aliquotas_reforma.get('CBS', {})
            parts.append(f"CBS (Contribuição sobre Bens e Serviços) - alíquota de referência: {info.get('aliquota', '8,8%')}")
            parts.append(f"Substitui: {info.get('substitui', 'PIS/COFINS')} | Competência: {info.get('competencia', 'Federal')}")
            parts.append("Incide sobre operações com bens e serviços em geral")
        
        elif tributo == 'IS':
            info = self.aliquotas_reforma.get('IS', {})
            parts.append(f"IS (Imposto Seletivo) - alíquota: {info.get('aliquota', 'Variável por produto')}")
            parts.append(f"Incide sobre: {info.get('incide_sobre', 'produtos prejudiciais à saúde/meio ambiente')}")
            parts.append("Exemplos: bebidas alcoólicas, cigarros, veículos poluentes, bebidas açucaradas")
        
        elif tipo_mudanca == 'Suspensão':
            parts.append(f"Suspensão do {tributo} que pode converter em alíquota zero após cumprimento de requisitos")
        elif tipo_mudanca == 'Suspensão → Alíquota Zero':
            parts.append(f"Suspensão do {tributo} que pode converter em alíquota zero após cumprimento de requisitos")
        elif tipo_mudanca == 'Alíquota Zero':
            parts.append(f"Alíquota reduzida a 0% para o {tributo}")
        elif tipo_mudanca == 'Isenção':
            parts.append(f"Isenção do {tributo} para operações específicas")
        elif tipo_mudanca == 'Redução':
            parts.append(f"Redução na alíquota do {tributo}")
        else:
            parts.append(f"{tributo} é mencionado na legislação")
        
        if produtos and tributo not in ['IBS', 'CBS', 'IS']:
            parts.append(f"Produtos: {produtos}")
        
        if vigencia:
            parts.append(f"Vigência: {vigencia}")
        
        result = '. '.join(parts)
        if result and not result.endswith('.'):
            result += '.'
        
        return result
    
    def _extract_context_around(self, text: str, term: str, before: int = 100, after: int = 150) -> str:
        """Extrai contexto ao redor de um termo"""
        match = re.search(rf'.{{0,{before}}}{re.escape(term)}.{{0,{after}}}', text, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(0)
        return ""
    
    def _clean_markdown(self, text: str) -> str:
        """Remove markdown e formatação do texto"""
        if not text:
            return text
        
        text = re.sub(r'\*\*+', '', text)
        text = re.sub(r'\*', '', text)
        text = re.sub(r'__+', '', text)
        text = re.sub(r'#+\s*', '', text)
        text = re.sub(r'━+', '', text)
        text = re.sub(r'─+', '', text)
        text = re.sub(r'-{3,}', '', text)
        text = re.sub(r'={3,}', '', text)
        text = re.sub(r'^\s*[-•]\s*', '', text, flags=re.MULTILINE)
        text = ' '.join(text.split())
        
        return text.strip()
    
    def _smart_truncate(self, text: str, max_length: int) -> str:
        """Trunca texto de forma inteligente"""
        if not text:
            return text
        
        text = self._clean_markdown(text)
        text = self._ensure_complete_phrase(text)
        text = ' '.join(text.split())
        
        if len(text) <= max_length:
            return text
        
        truncated = text[:max_length]
        
        last_period = truncated.rfind('.')
        last_exclamation = truncated.rfind('!')
        last_question = truncated.rfind('?')
        last_punct = max(last_period, last_exclamation, last_question)
        
        if last_punct > max_length * 0.5:
            return truncated[:last_punct + 1].strip()
        
        last_comma = truncated.rfind(',')
        last_semicolon = truncated.rfind(';')
        last_secondary = max(last_comma, last_semicolon)
        
        if last_secondary > max_length * 0.7:
            return truncated[:last_secondary].strip() + '.'
        
        last_space = truncated.rfind(' ')
        if last_space > max_length * 0.5:
            return truncated[:last_space].strip() + '...'
        
        return truncated.strip() + '...'
    
    def _ensure_complete_phrase(self, text: str) -> str:
        """✅ v4.8.1: Garante que o texto não termina com preposição/artigo isolado"""
        if not text:
            return text
        
        text_clean = text.rstrip('.!?…')
        words = text_clean.split()
        
        if not words:
            return text
        
        bad_endings = {'de', 'da', 'do', 'das', 'dos', 'para', 'com', 'em', 'no', 
                       'na', 'nos', 'nas', 'ao', 'à', 'aos', 'às', 'pelo', 'pela',
                       'pelos', 'pelas', 'e', 'ou', 'que', 'um', 'uma', 'uns', 'umas'}
        
        last_word = words[-1].lower()
        
        if last_word in bad_endings:
            words = words[:-1]
            if words:
                text = ' '.join(words)
                if not text.endswith(('.', '!', '?', '…')):
                    text += '.'
            else:
                return text
        else:
            if not text.endswith(('.', '!', '?', '…')):
                text = text_clean + '.'
        
        return text
    
    def _extract_operations(self, analysis: str) -> List[str]:
        """Extrai tipos de operação"""
        operations = []
        operation_keywords = {
            'Venda no mercado interno': ['venda.*mercado interno', 'venda nacional'],
            'Importação': ['importação', 'importacao'],
            'Exportação': ['exportação', 'exportacao'],
            'Prestação de serviços': ['prestação de serviços', 'prestacao de servicos'],
            'Industrialização': ['industrialização', 'industrializacao', 'fabricação'],
            'Incorporação ao ativo imobilizado': ['ativo imobilizado', 'incorporação ao ativo']
        }
        
        for op_name, patterns in operation_keywords.items():
            if any(re.search(pattern, analysis, re.IGNORECASE) for pattern in patterns):
                operations.append(op_name)
        
        return operations if operations else ['Verificar legislação']
    
    def _extract_client_types(self, analysis: str) -> List[str]:
        """Extrai tipos de cliente"""
        client_types = []
        client_keywords = {
            'PJ Habilitada no REDATA': ['habilitada', 'pj habilitada'],
            'PJ Coabilitada': ['coabilitada'],
            'Setor de TIC': ['tic', 'tecnologia da informação'],
            'Datacenter': ['datacenter', 'data center'],
            'Norte/Nordeste/Centro-Oeste': ['norte', 'nordeste', 'centro-oeste', 'n-ne-co'],
            'Lucro Real': ['lucro real'],
            # 🆕 v4.9: Novos para Reforma
            'Todas as empresas': ['todas as empresas', 'todos os contribuintes'],
        }
        
        for client_name, patterns in client_keywords.items():
            if any(re.search(pattern, analysis, re.IGNORECASE) for pattern in patterns):
                client_types.append(client_name)
        
        return client_types if client_types else ['Verificar legislação']
    
    def _extract_ncm(self, analysis: str) -> List[str]:
        """Extrai NCM/produtos"""
        ncm_list = []
        
        product_keywords = [
            'componentes eletrônicos',
            'produtos de TIC',
            'equipamentos de informática',
            'hardware',
            'infraestrutura de datacenter'
        ]
        
        for keyword in product_keywords:
            if keyword in analysis.lower():
                ncm_list.append(keyword.title())
        
        return list(set(ncm_list)) if ncm_list else ['Produtos de TIC conforme regulamento']
    
    def _extract_cfop(self, analysis: str) -> List[str]:
        """Extrai ou sugere CFOPs"""
        cfop_list = []
        
        if 'venda' in analysis.lower() and 'mercado interno' in analysis.lower():
            cfop_list.append('5.xxx / 6.xxx (Vendas internas)')
        if 'importação' in analysis.lower():
            cfop_list.append('3.xxx (Entradas de importação)')
        if 'ativo' in analysis.lower() or 'imobilizado' in analysis.lower():
            cfop_list.append('1.551 / 2.551 (Ativo imobilizado)')
        
        return list(set(cfop_list)) if cfop_list else ['A definir conforme operação']
    
    def _extract_conditions(self, analysis: str) -> List[str]:
        """Extrai condições de aplicação"""
        conditions = []
        
        condition_patterns = [
            r'(?:condição|requisito|exigência)[:\s][^\n]{30,200}',
            r'(?:desde que|quando)[^\n]{30,150}',
            r'(?:necessário|deve|obrigatório)[^\n]{30,150}'
        ]
        
        for pattern in condition_patterns:
            matches = re.findall(pattern, analysis, re.IGNORECASE)
            conditions.extend([self._clean_markdown(m.strip()) for m in matches[:5]])
        
        return list(dict.fromkeys(conditions))[:8] if conditions else ['Ver requisitos na legislação']
    
    def _extract_calculation_rules(self, analysis: str) -> List[str]:
        """Extrai regras de cálculo"""
        rules = []
        
        calc_patterns = [
            r'(?:cálculo|fórmula)[:\s][^\n]{30,180}',
            r'(?:base de cálculo)[^\n]{20,140}'
        ]
        
        for pattern in calc_patterns:
            matches = re.findall(pattern, analysis, re.IGNORECASE)
            rules.extend([self._clean_markdown(m.strip()) for m in matches[:3]])
        
        return list(dict.fromkeys(rules))[:6] if rules else ['Suspensão convertida em alíquota zero após requisitos']
    
    def _print_summary(self, changes_result: Dict):
        """Imprime resumo das mudanças"""
        print(f"   ✅ Mudanças identificadas: {len(changes_result['aliquotas'])}")
        print(f"   ✅ Tributos afetados: {len(changes_result['tributos_afetados'])}")
        print(f"   ✅ Operações: {len(changes_result['operacoes'])}")
        print(f"   ✅ Tipos de cliente: {len(changes_result['tipos_cliente'])}")
        if changes_result.get('compliance_risks'):
            print(f"   ⚠️  Riscos de compliance: {len(changes_result['compliance_risks'])}")
    
    def _post_process_tributos(self, changes_result: Dict) -> Dict:
        """Pós-processamento para validar tributos"""
        if "aliquotas" in changes_result:
            cleaned = []
            for aliq in changes_result["aliquotas"]:
                tributo = aliq.get("tributo", "")
                
                if "II" in tributo.upper() and len(tributo) <= 5:
                    descricao = str(aliq.get("descricao_completa", "")).lower()
                    condicoes = str(aliq.get("condicoes", "")).lower()
                    situacao = str(aliq.get("situacao_nova", "")).lower()
                    
                    contexto_completo = f"{descricao} {condicoes} {situacao}"
                    
                    import_markers = ['importação', 'importado', 'alfândega', 'aduaneiro', 'estrangeiro']
                    inciso_markers = ['inciso ii', 'incisos ii', 'art.', '§', 'iii', 'iv', 'v']
                    
                    has_import = any(m in contexto_completo for m in import_markers)
                    has_inciso = any(m in contexto_completo for m in inciso_markers)
                    
                    if not has_import or has_inciso:
                        print(f"   🧹 Removido: '{tributo}' (provável inciso de lei, não tributo)")
                        continue
                    
                    aliq["tributo"] = "II (Imposto de Importação)"
                
                cleaned.append(aliq)
            
            changes_result["aliquotas"] = cleaned
        
        if "tributos_afetados" in changes_result:
            cleaned = []
            for trib in changes_result["tributos_afetados"]:
                tributo_nome = trib.get("tributo", "")
                contexto = trib.get("contexto", "").lower()
                
                if "ii" in tributo_nome.lower() and len(tributo_nome) <= 30:
                    import_markers = ['importação', 'importado', 'alfândega', 'estrangeiro']
                    inciso_markers = ['inciso ii', 'art.', '§', 'iii', 'iv']
                    
                    has_import = any(m in contexto for m in import_markers)
                    has_inciso = any(m in contexto for m in inciso_markers)
                    
                    if not has_import or has_inciso:
                        print(f"   🧹 Removido de tributos_afetados: inciso, não tributo")
                        continue
                
                cleaned.append(trib)
            
            changes_result["tributos_afetados"] = cleaned
        
        return changes_result
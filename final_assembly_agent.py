"""
Final Assembly Agent - VERSÃO v4.9 COM KNOWLEDGE BASE
CORREÇÕES v4.9:
1. ✅ FIX Bug 1: ISS aparece indevidamente - validação mais rigorosa com regex word boundary
2. ✅ FIX Bug 3: LC 214 não identificada - padrão para Lei Complementar adicionado
3. ✅ NOVO: Seção de Cronograma de Transição para Reforma Tributária
4. ✅ NOVO: Validação de tributos contra fonte original ANTES de exibir
5. ✅ NOVO: Aceita known_law_key para integração com Knowledge Base
"""

from typing import List, Dict
from openai import OpenAI
import re
from config import *


class FinalAssemblyAgent:
    """Agente de montagem final - v4.9 com Knowledge Base integration"""
    
    def __init__(self):
        self.client = OpenAI(
            api_key=DEV_GENAI_API_KEY,
            base_url=DEV_GENAI_API_URL
        )
        self.model = MODEL_NAME
    
    def assemble(self, query: str, structured_data: Dict, date_extraction: Dict,
                 quantification: Dict, impact_analysis: Dict, dell_analysis: Dict,
                 system_changes: Dict, legislation_type: str, web_results: List[Dict],
                 validation_results: Dict, known_law_key: str = None) -> str:
        """Monta relatório final ultra claro - v4.9 com Knowledge Base"""
        print("   📝 Montando relatório final (v4.9)...")
        
        tipo_leg, numero_leg, data_pub = self._identify_legislation_info_v481(web_results, structured_data)
        
        # ✅ v4.8.1: Extrai texto original para validação
        original_text = ""
        if web_results:
            original_text = web_results[0].get('content', '').lower()
        
        report_sections = {
            'header': self._build_header(tipo_leg, numero_leg, data_pub),
            'resumo_executivo': self._build_resumo_executivo(structured_data, dell_analysis),
            'mudancas_sistema': self._build_mudancas_sistema_improved(system_changes),
            'impacto_tributos': self._build_impacto_tributos_v481(system_changes, web_results, original_text),
            'vigencias': self._build_vigencias_TYPED(date_extraction),
            'compliance_risks': self._build_compliance_risks(system_changes),
            'cronograma_transicao': self._build_cronograma_transicao(system_changes, original_text),  # ✅ NOVO
            'acoes_requeridas': self._build_acoes_requeridas(dell_analysis, system_changes),
            'detalhamento_tecnico': self._build_detalhamento_tecnico(structured_data),
            'fontes': self._build_fontes(web_results)
        }
        
        report = self._assemble_final_report(report_sections)
        return report
    
    def _identify_legislation_info_v481(self, web_results: List[Dict], structured_data: Dict) -> tuple:
        """
        ✅ v4.8.1 FIX Bug 3: Identifica tipo, número e data da legislação
        NOVO: Suporte a Lei Complementar (LC 214)
        """
        tipo = "LEGISLAÇÃO"
        numero = "Número não identificado"
        data = "Data não identificada"
        
        if web_results:
            title = web_results[0].get('title', '')
            url = web_results[0].get('url', '')
            content = web_results[0].get('content', '')[:2000]
            
            search_text = f"{title} {url} {content}"
            
            # ✅ v4.8.1 FIX: Lei Complementar ANTES de Lei simples
            if 'lei complementar' in search_text.lower() or 'lc ' in search_text.lower() or '/lcp/' in url.lower():
                tipo = "LEI COMPLEMENTAR"
                # Padrões para LC
                lc_patterns = [
                    r'Lei\s+Complementar\s*n?º?\s*(\d+(?:\.\d+)?)',
                    r'LC\s*n?º?\s*(\d+(?:\.\d+)?)',
                    r'/lcp?(\d+)',
                ]
                for pattern in lc_patterns:
                    match = re.search(pattern, search_text, re.IGNORECASE)
                    if match:
                        numero = f"LC nº {match.group(1)}"
                        break
            
            # Medida Provisória
            elif 'MP' in title.upper() or 'MEDIDA' in title.upper() or 'mpv' in url.lower():
                tipo = "MEDIDA PROVISÓRIA (MPV)"
                mp_patterns = [r'(?:MP|MPV)\s*n?º?\s*(\d+)', r'mpv(\d+)']
                for pattern in mp_patterns:
                    match = re.search(pattern, title + ' ' + url, re.IGNORECASE)
                    if match:
                        numero = f"MPV nº {match.group(1)}"
                        break
            
            # Lei (simples)
            elif 'LEI' in title.upper():
                tipo = "LEI"
                lei_match = re.search(r'Lei\s*n?º?\s*([\d.]+)', title, re.IGNORECASE)
                if lei_match:
                    numero = f"Lei nº {lei_match.group(1)}"
            
            # Decreto
            elif 'DECRETO' in title.upper():
                tipo = "DECRETO"
                dec_match = re.search(r'Decreto\s*n?º?\s*([\d.]+)', title, re.IGNORECASE)
                if dec_match:
                    numero = f"Decreto nº {dec_match.group(1)}"
            
            # Extrai data - APENAS ANOS RECENTES (2024+)
            date_patterns = [
                r'(\d{1,2})[/-](\d{1,2})[/-](202[4-9])',
                r'(\d{1,2})\s+de\s+(\w+)\s+de\s+(202[4-9])',
            ]
            
            for pattern in date_patterns:
                date_match = re.search(pattern, search_text, re.IGNORECASE)
                if date_match:
                    groups = date_match.groups()
                    if len(groups) == 3:
                        if groups[1].isdigit():
                            data = f"{groups[0]}/{groups[1]}/{groups[2]}"
                        else:
                            meses = {
                                'janeiro': '01', 'fevereiro': '02', 'março': '03', 'abril': '04',
                                'maio': '05', 'junho': '06', 'julho': '07', 'agosto': '08',
                                'setembro': '09', 'outubro': '10', 'novembro': '11', 'dezembro': '12'
                            }
                            mes_num = meses.get(groups[1].lower(), '??')
                            data = f"{groups[0]}/{mes_num}/{groups[2]}"
                    break
        
        return tipo, numero, data
    
    def _build_header(self, tipo: str, numero: str, data: str) -> str:
        """Cabeçalho do relatório"""
        return f"""
================================================================================
📋 ANÁLISE DE LEGISLAÇÃO BRASILEIRA - DELL TECHNOLOGIES BRAZIL
================================================================================

🏛️  {tipo}
📄 {numero}
📅 Data: {data}
"""
    
    def _build_resumo_executivo(self, structured_data: Dict, dell_analysis: Dict) -> str:
        """Resumo executivo"""
        raw_text = structured_data.get("raw_extraction", {}).get("raw_text", "")
        
        resumo = ""
        if raw_text:
            patterns = [
                r'(?:Objetivo|Ementa|Resumo)[:\s]+(.*?)(?:\n\n|\*\*|\d+\.)',
                r'(?:institui|altera|dispõe)[^\n]{50,600}',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, raw_text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
                if match:
                    try:
                        resumo = match.group(1) if match.lastindex and match.lastindex >= 1 else match.group(0)
                    except IndexError:
                        resumo = match.group(0)
                    resumo = resumo.strip()
                    if len(resumo) > 80:
                        break
            
            if not resumo or len(resumo) < 80:
                lines = [l.strip() for l in raw_text.split('\n') if l.strip()]
                summary_lines = []
                char_count = 0
                
                for line in lines:
                    if len(line) > 40 and not line.startswith('-') and not line.startswith('•'):
                        summary_lines.append(line)
                        char_count += len(line)
                        if char_count > 500:
                            break
                
                resumo = ' '.join(summary_lines[:4])
        
        if not resumo or len(resumo) < 50:
            resumo = "Resumo não disponível. Consulte o detalhamento técnico."
        
        resumo = self._smart_truncate(resumo, 800)
        
        relevancia = dell_analysis.get("relevancia", "NÃO DETERMINADA")
        justificativa_raw = dell_analysis.get("justificativa", "Justificativa não disponível")
        justificativa = self._smart_truncate(justificativa_raw, 700)
        
        return f"""
================================================================================
1️⃣  RESUMO EXECUTIVO
================================================================================

📌 SOBRE A LEGISLAÇÃO:
{resumo}

🎯 RELEVÂNCIA PARA DELL: {relevancia}

📍 JUSTIFICATIVA:
{justificativa}
"""
    
    def _build_mudancas_sistema_improved(self, system_changes: Dict) -> str:
        """Seção de mudanças no sistema"""
        aliquotas = system_changes.get('aliquotas', [])
        operacoes = system_changes.get('operacoes', [])
        tipos_cliente = system_changes.get('tipos_cliente', [])
        parametrizacoes = system_changes.get('parametrizacoes', [])
        
        section = f"""
================================================================================
2️⃣  MUDANÇAS NECESSÁRIAS NO SISTEMA
================================================================================

⚙️  MUDANÇAS DE ALÍQUOTAS E TRIBUTOS:
"""
        
        if aliquotas and len(aliquotas) > 0:
            for i, aliq in enumerate(aliquotas[:10], 1):
                tributo = aliq.get('tributo', 'N/A')
                tipo_mudanca = aliq.get('tipo_mudanca', '')
                
                situacao_nova = self._clean_field(aliq.get('situacao_nova', ''), 500)
                condicoes = self._clean_field(aliq.get('condicoes', ''), 450)
                vigencia = self._clean_field(aliq.get('vigencia', ''), 250)
                descricao = self._smart_truncate(aliq.get('descricao_completa', aliq.get('descricao', '')), 500)
                
                section += f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                section += f"{i}. TRIBUTO: {tributo}\n"
                
                if tipo_mudanca:
                    section += f"   MUDANÇA: {tipo_mudanca}\n"
                
                if situacao_nova and situacao_nova not in tipo_mudanca:
                    section += f"   NOVA SITUAÇÃO: {situacao_nova}\n"
                
                if condicoes:
                    if 'quem pode' in condicoes.lower()[:30]:
                        section += f"   QUEM PODE: {condicoes}\n"
                    else:
                        section += f"   CONDIÇÕES: {condicoes}\n"
                
                if vigencia:
                    section += f"   VIGÊNCIA: {vigencia}\n"
                
                if descricao and not all([tipo_mudanca, situacao_nova, condicoes, vigencia]):
                    section += f"   DETALHES: {descricao}\n"
        else:
            section += "\n⚠️  Mudanças de alíquotas não identificadas automaticamente."
            section += "\n   Consulte a seção 'Detalhamento Técnico' e a legislação completa.\n"
        
        section += f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        section += f"\n📋 OPERAÇÕES AFETADAS:"
        if operacoes:
            for op in operacoes[:8]:
                section += f"\n   • {op}"
        else:
            section += "\n   • Verificar legislação"
        
        section += f"\n\n👥 TIPOS DE CLIENTE/EMPRESA BENEFICIÁRIA:"
        if tipos_cliente:
            for cliente in tipos_cliente[:8]:
                section += f"\n   • {cliente}"
        else:
            section += "\n   • Verificar legislação"
        
        section += f"\n\n🔧 PARAMETRIZAÇÕES NECESSÁRIAS NO ERP:"
        if parametrizacoes:
            for param in parametrizacoes[:10]:
                section += f"\n   • {param}"
        else:
            section += "\n   • A definir após análise detalhada"
        
        return section
    
    def _build_impacto_tributos_v481(self, system_changes: Dict, web_results: List[Dict], original_text: str) -> str:
        """
        ✅ v4.8.1 FIX Bug 1: Impacto por tributo COM VALIDAÇÃO RIGOROSA
        ISS só aparece se realmente estiver na legislação original
        """
        tributos = system_changes.get('tributos_afetados', [])
        
        section = f"""
================================================================================
3️⃣  IMPACTO POR TRIBUTO
================================================================================
"""
        
        if tributos and len(tributos) > 0:
            tributos_validos = 0
            for trib in tributos[:15]:
                tributo_nome = trib.get('tributo', 'N/A')
                tipo_mudanca = trib.get('tipo_mudanca', '')
                contexto_raw = trib.get('contexto', '')
                
                # ✅ v4.8.1 FIX: Validação RIGOROSA antes de exibir
                if original_text and not self._validate_tributo_display_v481(tributo_nome, original_text):
                    print(f"   🧹 Removido da seção 3: '{tributo_nome}' - não encontrado na fonte original")
                    continue
                
                contexto = self._smart_truncate(contexto_raw, 300)
                
                if not tipo_mudanca and not contexto:
                    continue
                
                section += f"\n💰 {tributo_nome}:"
                if tipo_mudanca:
                    section += f" [{tipo_mudanca}]"
                
                if contexto:
                    section += f"\n   {contexto}"
                
                section += "\n"
                tributos_validos += 1
            
            if tributos_validos == 0:
                section += "\n⚠️  Detalhamento de tributos não disponível."
                section += "\n   Consulte a seção de mudanças no sistema.\n"
        else:
            section += "\n⚠️  Detalhamento de tributos não disponível."
            section += "\n   Consulte a seção de mudanças no sistema.\n"
        
        return section
    
    def _validate_tributo_display_v481(self, tributo_nome: str, original_content: str) -> bool:
        """
        ✅ v4.8.1 FIX Bug 1: Validação RIGOROSA de tributos
        Usa word boundaries para evitar falsos positivos
        """
        tributo_lower = tributo_nome.lower()
        
        # ✅ v4.8.1 FIX: Padrões RIGOROSOS com word boundaries
        validation_patterns = {
            'pis': [r'\bpis\b', r'programa de integração social'],
            'cofins': [r'\bcofins\b', r'contribuição para financiamento'],
            'ipi': [r'\bipi\b', r'imposto sobre produtos industrializados'],
            'icms': [r'\bicms\b', r'imposto sobre circulação'],
            # ✅ v4.8.1 FIX CRÍTICO: ISS precisa de validação rigorosa
            'iss': [
                r'\biss\b(?!\s*[oaO])',  # "iss" mas não "isso", "issa"
                r'\bissqn\b',
                r'imposto sobre serviços',
                r'imposto s(?:obre|/)?\s*serviços',
            ],
            'ii': [
                r'\bii\b(?!\s*[,\.]?\s*(?:iii|iv|v|do|da|de|e)\b)',  # II mas não "II, III" ou "II do"
                r'imposto de importação',
            ],
            # Novos tributos - Reforma Tributária
            'ibs': [r'\bibs\b', r'imposto sobre bens e serviços'],
            'cbs': [r'\bcbs\b', r'contribuição sobre bens e serviços'],
            'is': [
                r'\bimposto seletivo\b',
                r'\bis\b(?=\s+(?:incid|será|sobre|produto))',  # IS com contexto
            ],
        }
        
        # Identifica qual tributo verificar
        tributo_key = None
        for key in validation_patterns.keys():
            if key in tributo_lower:
                tributo_key = key
                break
        
        if tributo_key is None:
            return True  # Tributo não mapeado, permite por padrão
        
        patterns = validation_patterns[tributo_key]
        
        for pattern in patterns:
            if re.search(pattern, original_content, re.IGNORECASE):
                return True
        
        return False
    
    def _build_vigencias_TYPED(self, date_extraction: Dict) -> str:
        """Vigências organizadas por TIPO"""
        vigencias = date_extraction.get("vigencias", [])
        
        section = f"""
================================================================================
4️⃣  VIGÊNCIAS E PRAZOS CRÍTICOS
================================================================================

📅 DATAS IMPORTANTES:
"""
        
        if vigencias:
            inicio_vigencia = []
            prazos_aquisicao = []
            duracoes_beneficio = []
            outros = []
            
            for v in vigencias:
                tipo = v.get('tipo', '')
                if tipo == 'inicio_vigencia':
                    inicio_vigencia.append(v)
                elif tipo == 'prazo_aquisicao':
                    prazos_aquisicao.append(v)
                elif tipo in ['duracao_beneficio', 'prazo_permanencia']:
                    duracoes_beneficio.append(v)
                else:
                    outros.append(v)
            
            if inicio_vigencia:
                section += "\n🟢 INÍCIO DE VIGÊNCIA:\n"
                for v in inicio_vigencia:
                    data = v.get('data', 'Data não especificada')
                    contexto = self._smart_truncate(v.get('contexto', ''), 150)
                    section += f"   • {data}: {contexto}\n"
            
            if prazos_aquisicao:
                section += "\n⏰ PRAZOS-LIMITE PARA OPERAÇÃO:\n"
                for v in prazos_aquisicao:
                    data = v.get('data', 'Data não especificada')
                    contexto = self._smart_truncate(v.get('contexto', ''), 150)
                    section += f"   • {data}: {contexto}\n"
            
            if duracoes_beneficio:
                section += "\n📆 DURAÇÃO DO BENEFÍCIO / PRAZO DE PERMANÊNCIA:\n"
                for v in duracoes_beneficio:
                    data = v.get('data', 'Data não especificada')
                    contexto = self._smart_truncate(v.get('contexto', ''), 150)
                    section += f"   • {data}: {contexto}\n"
            
            if outros:
                section += "\n📋 OUTRAS DATAS:\n"
                for v in outros:
                    data = v.get('data', 'Data não especificada')
                    contexto = self._smart_truncate(v.get('contexto', ''), 150)
                    section += f"   • {data}: {contexto}\n"
            
            section += "\n💡 NOTA: Prazo-limite (ex: 31/12/2026) é a data máxima para realizar"
            section += "\n   a operação. Duração do benefício (ex: 5 anos) é contada a partir"
            section += "\n   da habilitação no regime especial.\n"
            
        else:
            section += "\n⚠️  Datas críticas não identificadas automaticamente."
            section += "\n   Consulte a legislação para vigências específicas.\n"
        
        return section
    
    def _build_compliance_risks(self, system_changes: Dict) -> str:
        """Seção de riscos de compliance"""
        risks = system_changes.get('compliance_risks', [])
        
        section = f"""
================================================================================
⚠️  RISCOS DE COMPLIANCE
================================================================================
"""
        
        if risks and len(risks) > 0:
            unique_risks = self._deduplicate_risks(risks)
            
            for i, risk in enumerate(unique_risks[:6], 1):
                risk_clean = self._smart_truncate(risk, 200)
                section += f"\n🔴 RISCO {i}: {risk_clean}\n"
        else:
            section += "\n⚠️  Riscos de compliance não identificados automaticamente."
            section += "\n   Recomenda-se análise detalhada da legislação para identificar"
            section += "\n   requisitos e consequências de descumprimento.\n"
        
        return section
    
    def _build_cronograma_transicao(self, system_changes: Dict, original_text: str) -> str:
        """
        ✅ v4.8.1 NOVO: Seção de Cronograma de Transição para Reforma Tributária
        """
        # Verifica se é legislação da Reforma Tributária
        is_reforma = False
        reforma_keywords = ['ibs', 'cbs', 'imposto seletivo', 'reforma tributária', 'lc 214', 'lei complementar 214']
        
        for keyword in reforma_keywords:
            if keyword in original_text.lower():
                is_reforma = True
                break
        
        if not is_reforma:
            return ""  # Não exibe seção se não for Reforma Tributária
        
        section = f"""
================================================================================
📅 CRONOGRAMA DE TRANSIÇÃO - REFORMA TRIBUTÁRIA
================================================================================

A Reforma Tributária estabelece período de transição de 2026 a 2033:

📊 CRONOGRAMA DE ALÍQUOTAS:

| Ano  | CBS (Federal)    | IBS (Est/Mun)    | PIS/COFINS   | ICMS/ISS     |
|------|------------------|------------------|--------------|--------------|
| 2026 | 0,9% (teste)     | 0,1% (teste)     | 100%         | 100%         |
| 2027 | Alíquota cheia   | Aumenta          | Reduz        | 100%         |
| 2029 | 100%             | Aumenta          | Reduz        | 90%          |
| 2030 | 100%             | Aumenta          | Reduz        | 80%          |
| 2031 | 100%             | Aumenta          | Reduz        | 70%          |
| 2032 | 100%             | Aumenta          | Reduz        | 60%          |
| 2033 | 100%             | 100%             | EXTINTO      | EXTINTO      |

📌 ALÍQUOTAS DE REFERÊNCIA:
   • CBS (Contribuição sobre Bens e Serviços): ~8,8%
   • IBS (Imposto sobre Bens e Serviços): ~17,7%
   • Total IVA Dual (CBS + IBS): ~26,5%

⚠️  IMPACTO PARA DELL:
   • Necessidade de atualizar ERP para novos tributos
   • Período de convivência entre sistemas antigo e novo
   • Crédito amplo (inclusive serviços) no novo sistema
   • Cobrança no destino beneficia operações interestaduais
"""
        return section
    
    def _deduplicate_risks(self, risks: List[str]) -> List[str]:
        """Remove duplicatas semânticas de riscos"""
        if not risks:
            return []
        
        concepts = {
            'incorporacao': [],
            'alienacao': [],
            'compromisso': [],
            'outros': []
        }
        
        for risk in risks:
            risk_lower = risk.lower()
            
            if 'incorporar' in risk_lower or 'ativo' in risk_lower:
                concepts['incorporacao'].append(risk)
            elif 'alienar' in risk_lower or '5 anos' in risk_lower:
                concepts['alienacao'].append(risk)
            elif 'compromisso' in risk_lower or 'p&d' in risk_lower:
                concepts['compromisso'].append(risk)
            else:
                concepts['outros'].append(risk)
        
        unique = []
        for concept, items in concepts.items():
            if items:
                best = max(items, key=len) if len(items) > 1 else items[0]
                unique.append(best)
        
        return unique
    
    def _build_acoes_requeridas(self, dell_analysis: Dict, system_changes: Dict) -> str:
        """Ações requeridas"""
        acao_raw = dell_analysis.get("acao_requerida", "Não determinada")
        acao_requerida = self._smart_truncate(acao_raw, 600)
        
        section = f"""
================================================================================
5️⃣  AÇÕES REQUERIDAS
================================================================================

🎯 AÇÃO PRINCIPAL:
{acao_requerida}

⚙️  AÇÕES TÉCNICAS (TI/Desenvolvimento):
   • Revisar parametrizações de tributos no ERP
   • Implementar regras de suspensão e conversão de alíquotas
   • Configurar controle de vigências
   • Atualizar cadastro de regimes especiais
   • ⚠️ Implementar alertas para prazos de permanência (5 anos)
   • Ver seção 'Mudanças no Sistema' para detalhes

📊 AÇÕES FISCAIS/COMPLIANCE:
   • Avaliar elegibilidade para o regime especial
   • Analisar impacto fiscal e oportunidades
   • Verificar requisitos e documentação necessária
   • Definir processo de habilitação se aplicável
   • ⚠️ Estabelecer controles para evitar riscos de compliance
"""
        
        return section
    
    def _build_detalhamento_tecnico(self, structured_data: Dict) -> str:
        """Detalhamento técnico"""
        raw_text = structured_data.get("raw_extraction", {}).get("raw_text", "")
        
        articles = []
        art_pattern = r'(Art\.?\s*\d+[A-Z-]*[^\n]{20,300})'
        matches = re.findall(art_pattern, raw_text, re.IGNORECASE)
        
        if matches:
            for match in matches:
                if any(keyword in match.lower() for keyword in 
                       ['suspensão', 'tributo', 'alíquota', 'vigência', 'benefício', 'isenção', 'redata']):
                    article_clean = self._smart_truncate(match.strip(), 250)
                    articles.append(f"   {article_clean}")
                if len(articles) >= 8:
                    break
        
        artigos_text = '\n'.join(articles) if articles else "   Consulte a legislação completa"
        
        section = f"""
================================================================================
6️⃣  DETALHAMENTO TÉCNICO
================================================================================

📜 PRINCIPAIS ARTIGOS RELEVANTES:
{artigos_text}
"""
        
        return section
    
    def _build_fontes(self, web_results: List[Dict]) -> str:
        """Fontes consultadas"""
        section = f"""
================================================================================
7️⃣  FONTES CONSULTADAS
================================================================================
"""
        
        for i, r in enumerate(web_results[:3], 1):
            section += f"\n{i}. {r.get('title', 'Sem título')}"
            section += f"\n   URL: {r.get('url', 'N/A')}"
            if r.get('is_official'):
                section += f"\n   ✓ Fonte Oficial Governo"
            section += "\n"
        
        return section
    
    def _assemble_final_report(self, sections: Dict) -> str:
        """Monta relatório final"""
        report = sections['header']
        report += sections['resumo_executivo']
        report += sections['mudancas_sistema']
        report += sections['impacto_tributos']
        report += sections['vigencias']
        report += sections['compliance_risks']
        
        # ✅ v4.8.1: Cronograma de transição (só aparece se for Reforma Tributária)
        if sections.get('cronograma_transicao'):
            report += sections['cronograma_transicao']
        
        report += sections['acoes_requeridas']
        report += sections['detalhamento_tecnico']
        report += sections['fontes']
        
        report += f"""
================================================================================
⚙️  Sistema: Dell GenAI | Modelo: {MODEL_NAME}
🗃️  Arquitetura: 13 Agentes Especializados
🎯 Análise específica para Dell Technologies Brazil
================================================================================
"""
        
        return report
    
    def _clean_field(self, text: str, max_length: int) -> str:
        """Limpa e trunca campos"""
        if not text:
            return text
        
        patterns_to_remove = [
            r'c\)\s*CONDIÇÕES[:\s]*',
            r'd\)\s*(?:RISCOS?|⚠️)[:\s]*',
            r'^estabelecidas\.\s*',
            r'\s+c\)\s*CONDIÇÕES.*$',
            r'\s+d\)\s*⚠️.*$',
        ]
        
        for pattern in patterns_to_remove:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        text = ' '.join(text.split())
        
        return self._smart_truncate(text, max_length)
    
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
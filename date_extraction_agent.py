"""
Date Extraction Agent - VERSÃO v5.2 COM KNOWLEDGE BASE FALLBACK
Extração inteligente via REASONING + Fallback para leis conhecidas

MUDANÇAS v5.2:
✅ NOVO: Integração com reform_knowledge_base.py
✅ NOVO: Fallback automático para LC 214 e outras leis complexas
✅ NOVO: Detecção de leis conhecidas antes da extração
- LLM extrai vigências com contexto semântico
- Entende diferença entre "data da lei" vs "vigência"
- Foco em datas críticas para compliance
- Regex apenas como fallback secundário
"""

from typing import List, Dict
from openai import OpenAI
import re
import json
from datetime import datetime
from config import (
    DEV_GENAI_API_KEY, 
    DEV_GENAI_API_URL, 
    MODEL_NAME,
    MAX_TOKENS_EXTRACTION
)

# 🆕 v5.2: Importa knowledge base
try:
    from reform_knowledge_base import (
        detect_known_legislation,
        get_vigencias_for_legislation,
        merge_with_extracted_data
    )
    HAS_KNOWLEDGE_BASE = True
except ImportError:
    HAS_KNOWLEDGE_BASE = False
    print("   ⚠️  Knowledge base não disponível, usando apenas extração automática")


class DateExtractionAgent:
    """Agente 5: Extrai vigências via LLM reasoning - VERSÃO v5.2"""
    
    def __init__(self):
        self.client = OpenAI(
            api_key=DEV_GENAI_API_KEY,
            base_url=DEV_GENAI_API_URL
        )
        self.model = MODEL_NAME
        self.current_year = datetime.now().year
    
    def extract(self, web_results: List[Dict], raw_extraction: Dict) -> Dict:
        """Extrai vigências usando LLM reasoning + Knowledge Base fallback"""
        print("   📅 Extraindo datas e vigências via LLM reasoning...")
        
        content = self._consolidate_content(web_results)
        raw_text = raw_extraction.get("raw_text", "")
        
        # 🆕 v5.2: Detecta se é uma lei conhecida ANTES de extrair
        known_law_key = None
        if HAS_KNOWLEDGE_BASE and web_results:
            url = web_results[0].get('url', '')
            title = web_results[0].get('title', '')
            known_law_key = detect_known_legislation(url, content, title)
            
            if known_law_key:
                print(f"   📚 Lei conhecida detectada: {known_law_key}")
        
        combined_content = f"{content[:8000]}\n\n{raw_text[:4000]}"
        
        # 🆕 v5.2: Se é lei conhecida e complexa, usa prompt especializado
        if known_law_key == "LC_214":
            vigencias = self._extract_via_llm_reforma(combined_content)
        else:
            vigencias = self._extract_via_llm(combined_content)
        
        # 🆕 v5.2: Se LLM encontrou pouco E temos knowledge base, usa fallback
        if HAS_KNOWLEDGE_BASE and known_law_key:
            if not vigencias or len(vigencias) < 3:
                print(f"   📚 Usando Knowledge Base como fallback para {known_law_key}...")
                kb_vigencias = get_vigencias_for_legislation(known_law_key)
                if kb_vigencias:
                    vigencias = kb_vigencias
                    print(f"   ✅ Knowledge Base forneceu {len(vigencias)} vigências")
        
        # Fallback secundário: regex (se ainda não temos dados suficientes)
        if not vigencias or len(vigencias) < 2:
            print("   ⚠️  Usando fallback regex...")
            vigencias_regex = self._extract_regex_fallback(combined_content)
            vigencias.extend(vigencias_regex)
            # Remove duplicatas
            seen = set()
            vigencias = [v for v in vigencias 
                        if v['data'] not in seen and not seen.add(v['data'])]
        
        return {
            "dates_text": "\n".join([f"{v['data']}: {v['contexto']}" for v in vigencias]),
            "vigencias": vigencias[:8],  # 🆕 v5.2: Aumentado para 8 (reforma tem muitas datas)
            "count": len(vigencias[:8]),
            "known_law_key": known_law_key  # 🆕 v5.2: Passa a chave para outros agentes
        }
    
    def _consolidate_content(self, web_results: List[Dict]) -> str:
        """Consolida conteúdo das fontes"""
        parts = []
        for r in web_results[:2]:
            if r.get('content'):
                parts.append(r['content'][:5000])
        return "\n\n".join(parts)
    
    def _extract_via_llm_reforma(self, content: str) -> List[Dict]:
        """
        🆕 v5.2 NOVO: Prompt especializado para REFORMA TRIBUTÁRIA (LC 214)
        """
        prompt = f"""Você é um especialista em REFORMA TRIBUTÁRIA BRASILEIRA (LC 214/2025).

TAREFA: Extraia TODAS as datas e prazos do CRONOGRAMA DE TRANSIÇÃO da reforma tributária.

TEXTO DA LEGISLAÇÃO:
{content[:12000]}

⚠️ ATENÇÃO ESPECIAL - REFORMA TRIBUTÁRIA:

Esta é a LC 214/2025 (Reforma Tributária). Procure ESPECIFICAMENTE por:

1. CRONOGRAMA DE TRANSIÇÃO 2026-2033:
   - Quando CBS começa (teste e alíquota cheia)
   - Quando IBS começa (teste e aumento gradual)
   - Quando IS (Imposto Seletivo) entra em vigor
   - Quando PIS/COFINS começam a reduzir
   - Quando ICMS/ISS começam a reduzir
   - Quando PIS/COFINS/ICMS/ISS são extintos

2. ALÍQUOTAS POR ANO:
   - 2026: CBS 0,9% + IBS 0,1% (teste)
   - 2027: CBS alíquota cheia
   - 2029-2032: Redução gradual
   - 2033: Extinção total

3. DATAS ESPECÍFICAS:
   - Data de publicação da lei
   - Prazos para regulamentação
   - Prazos para adesão a regimes especiais

FORMATO DE SAÍDA (JSON):
{{
  "vigencias": [
    {{
      "data": "16/01/2025",
      "contexto": "Publicação e início da vigência da LC 214",
      "tipo": "inicio_vigencia",
      "relevancia": "alta"
    }},
    {{
      "data": "2026",
      "contexto": "Início do período de teste - CBS 0,9% + IBS 0,1%",
      "tipo": "inicio_vigencia",
      "relevancia": "alta"
    }},
    {{
      "data": "2027",
      "contexto": "CBS entra em vigor com alíquota cheia; IS entra em vigor",
      "tipo": "inicio_vigencia",
      "relevancia": "alta"
    }},
    {{
      "data": "2029-2032",
      "contexto": "Período de transição - redução gradual de PIS/COFINS/ICMS/ISS",
      "tipo": "prazo_transicao",
      "relevancia": "alta"
    }},
    {{
      "data": "2033",
      "contexto": "Extinção total de PIS, COFINS, ICMS e ISS",
      "tipo": "prazo_final",
      "relevancia": "alta"
    }}
  ]
}}

TIPOS VÁLIDOS:
- "inicio_vigencia": quando algo começa
- "prazo_transicao": período de mudança gradual
- "prazo_final": data limite/extinção
- "publicacao": data de publicação

RESPONDA APENAS COM O JSON, SEM EXPLICAÇÕES."""

        return self._call_llm_and_parse(prompt)
    
    def _extract_via_llm(self, content: str) -> List[Dict]:
        """
        MÉTODO PRINCIPAL v5.1: Extrai vigências via LLM reasoning
        COM TIPOS DE VIGÊNCIA MAIS CLAROS
        """
        
        prompt = f"""Você é um especialista em análise de legislação brasileira.

TAREFA: Extraia APENAS as vigências e prazos CRÍTICOS para compliance fiscal.
⚠️ IMPORTANTE: Diferencie claramente os TIPOS de prazo!

TEXTO DA LEGISLAÇÃO:
{content[:10000]}

INSTRUÇÕES CRÍTICAS:
1. FOQUE em datas de VIGÊNCIA (quando a lei entra em vigor)
2. FOQUE em PRAZOS (até quando algo é válido)
3. IGNORE datas de publicação da própria lei
4. IGNORE datas de leis antigas citadas como referência
5. Se houver "vigência a partir de X", extraia X
6. Se houver "até DD/MM/AAAA", extraia essa data
7. Se houver "prazo de X anos/meses", extraia isso
8. LIMITE: Máximo 8 datas mais importantes

⚠️ DIFERENCIAÇÃO CRÍTICA DE PRAZOS (v5.1):

A) PRAZO-LIMITE PARA AQUISIÇÃO/OPERAÇÃO:
   - Data máxima para realizar a operação beneficiada
   - Ex: "até 31/12/2026" para comprar o bem
   - TIPO: "prazo_aquisicao"

B) DURAÇÃO DO BENEFÍCIO:
   - Quanto tempo o benefício dura APÓS a habilitação
   - Ex: "5 anos" contados da habilitação no regime
   - TIPO: "duracao_beneficio"

C) PRAZO DE PERMANÊNCIA DO BEM:
   - Quanto tempo o bem deve permanecer no ativo
   - Ex: "mínimo 5 anos" no ativo imobilizado
   - TIPO: "prazo_permanencia"

D) INÍCIO DE VIGÊNCIA:
   - Quando a lei passa a valer
   - TIPO: "inicio_vigencia"

ANO ATUAL: {self.current_year}
IMPORTANTE: Priorize datas >= {self.current_year}

FORMATO DE SAÍDA (JSON):
{{
  "vigencias": [
    {{
      "data": "01/01/2026",
      "contexto": "Início da vigência do regime REDATA",
      "tipo": "inicio_vigencia",
      "relevancia": "alta"
    }},
    {{
      "data": "31/12/2026",
      "contexto": "Prazo-limite para aquisição de bens com benefício fiscal (incorporação ao ativo)",
      "tipo": "prazo_aquisicao",
      "relevancia": "alta"
    }},
    {{
      "data": "5 anos",
      "contexto": "Duração do benefício fiscal a partir da habilitação no REDATA",
      "tipo": "duracao_beneficio",
      "relevancia": "alta"
    }},
    {{
      "data": "5 anos",
      "contexto": "Prazo mínimo de permanência do bem no ativo imobilizado (alienação antes disso gera recolhimento)",
      "tipo": "prazo_permanencia",
      "relevancia": "alta"
    }}
  ]
}}

TIPOS VÁLIDOS:
- "inicio_vigencia": quando a lei começa a valer
- "prazo_aquisicao": data limite para realizar a operação
- "duracao_beneficio": quanto tempo o benefício dura
- "prazo_permanencia": tempo mínimo que bem deve ficar no ativo
- "prazo_transicao": período de transição gradual
- "prazo_final": outras datas limite
- "publicacao": data de publicação (use APENAS se for a única data disponível)

RELEVÂNCIA:
- "alta": datas críticas para compliance
- "media": datas importantes mas não urgentes
- "baixa": datas de contexto/referência

RESPONDA APENAS COM O JSON, SEM EXPLICAÇÕES ADICIONAIS."""

        return self._call_llm_and_parse(prompt)
    
    def _call_llm_and_parse(self, prompt: str) -> List[Dict]:
        """
        🆕 v5.2: Método auxiliar para chamar LLM e parsear resposta
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=2000
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Remove markdown se houver
            result_text = re.sub(r'```json\s*', '', result_text)
            result_text = re.sub(r'```\s*', '', result_text)
            
            # Parse JSON
            result = json.loads(result_text)
            vigencias_raw = result.get("vigencias", [])
            
            # Filtra por relevância e valida
            vigencias = []
            for v in vigencias_raw:
                if v.get("relevancia") in ["alta", "media"]:
                    # ✅ v5.1: Adiciona emoji por tipo para clareza
                    tipo = v.get("tipo", "")
                    emoji = self._get_emoji_for_type(tipo)
                    
                    vigencias.append({
                        'data': v.get("data", ""),
                        'contexto': f"{emoji} {v.get('contexto', '')}".strip()[:180],
                        'tipo': tipo,
                        'relevancia': v.get("relevancia", "media")
                    })
            
            # Ordena por relevância e tipo
            vigencias.sort(key=lambda x: (
                x['relevancia'] == 'alta',
                x['tipo'] in ['inicio_vigencia', 'prazo_aquisicao', 'prazo_final']
            ), reverse=True)
            
            print(f"   ✅ LLM extraiu {len(vigencias)} vigências relevantes")
            return vigencias
            
        except json.JSONDecodeError as e:
            print(f"   ⚠️  Erro ao parsear JSON do LLM: {e}")
            return []
        except Exception as e:
            print(f"   ⚠️  Erro na extração via LLM: {e}")
            return []
    
    def _get_emoji_for_type(self, tipo: str) -> str:
        """
        ✅ v5.1 NOVO: Retorna emoji apropriado para cada tipo de vigência
        """
        emoji_map = {
            'inicio_vigencia': '🟢',      # Verde = início
            'prazo_aquisicao': '⏰',      # Relógio = prazo
            'duracao_beneficio': '📆',    # Calendário = duração
            'prazo_permanencia': '🔒',    # Cadeado = obrigação
            'prazo_transicao': '🔄',      # 🆕 v5.2: Setas = transição
            'prazo_final': '🔴',          # Vermelho = fim
            'publicacao': '📋',           # Documento
        }
        return emoji_map.get(tipo, '📅')
    
    def _extract_regex_fallback(self, content: str) -> List[Dict]:
        """
        Fallback simples: regex para capturar vigências óbvias
        Usado apenas se LLM falhar
        """
        vigencias = []
        seen = set()
        
        # Padrões simples e diretos
        patterns = [
            # "vigência a partir de DD/MM/AAAA"
            (r'vig[êe]ncia\s+a\s+partir\s+de\s+(\d{1,2}[/-]\d{1,2}[/-]\d{4})', 'Início da vigência', 'inicio_vigencia'),
            
            # "até DD/MM/AAAA"
            (r'at[ée]\s+(\d{1,2}[/-]\d{1,2}[/-]\d{4})', 'Prazo até', 'prazo_aquisicao'),
            
            # "prazo de X anos"
            (r'prazo\s+de\s+(\d+)\s+ano', 'Prazo de {} ano(s)', 'duracao_beneficio'),
            
            # "mínimo de X anos"
            (r'm[íi]nimo\s+(?:de\s+)?(\d+)\s+ano', 'Prazo mínimo de {} ano(s)', 'prazo_permanencia'),
            
            # 🆕 v5.2: Padrões para reforma tributária
            (r'a\s+partir\s+de\s+(202[5-9]|203[0-3])', 'A partir de {}', 'inicio_vigencia'),
            (r'em\s+(202[5-9]|203[0-3])', 'Em {}', 'inicio_vigencia'),
        ]
        
        for pattern, desc_template, tipo in patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                try:
                    groups = match.groups()
                    
                    if 'ano' in desc_template.lower() and '{}' in desc_template:
                        data = f"{groups[0]} ano(s)"
                        contexto = desc_template.format(groups[0])
                    else:
                        data = groups[0]
                        
                        # Valida ano >= atual
                        year_match = re.search(r'20\d{2}', str(data))
                        if year_match and int(year_match.group(0)) < self.current_year:
                            continue
                        
                        contexto = desc_template.format(groups[0]) if '{}' in desc_template else desc_template
                    
                    if data not in seen:
                        emoji = self._get_emoji_for_type(tipo)
                        vigencias.append({
                            'data': data,
                            'contexto': f"{emoji} {contexto}",
                            'tipo': tipo,
                            'relevancia': 'media'
                        })
                        seen.add(data)
                        
                except Exception:
                    continue
        
        return vigencias[:4]  # Limita a 4 no fallback
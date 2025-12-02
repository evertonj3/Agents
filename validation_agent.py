"""
Validation Agent - VERSÃO v1.0
Valida campos críticos extraídos contra o texto original da legislação

OBJETIVO:
- Garantir consistência entre execuções
- Validar TIPO DE MUDANÇA (SUSPENSÃO vs ISENÇÃO vs ALÍQUOTA 0%)
- Validar tributos realmente existem no texto fonte
- Corrigir automaticamente quando possível

INTEGRAÇÃO:
- Roda APÓS system_changes_agent
- Roda ANTES de dell_relevance ou final_assembly
"""

from typing import Dict, List, Tuple
from openai import OpenAI
import re
import json
from config import (
    DEV_GENAI_API_KEY, 
    DEV_GENAI_API_URL, 
    MODEL_NAME
)


class ValidationAgent:
    """Agente de Validação - Verifica extrações contra texto original"""
    
    def __init__(self):
        self.client = OpenAI(
            api_key=DEV_GENAI_API_KEY,
            base_url=DEV_GENAI_API_URL
        )
        self.model = MODEL_NAME
        
        # Padrões de validação para tipos de mudança
        self.change_type_patterns = {
            'SUSPENSÃO': [
                r'suspens[ãa]o',
                r'suspend[ea]',
                r'fica\s+suspenso',
                r'pagamento\s+suspenso',
                r'com\s+suspens[ãa]o',
            ],
            'ISENÇÃO': [
                r'isen[çc][ãa]o',
                r'isento[s]?',
                r'fica[m]?\s+isento',
                r'com\s+isen[çc][ãa]o',
            ],
            'ALÍQUOTA 0%': [
                r'al[íi]quota\s+(?:de\s+)?(?:0%|zero)',
                r'0%\s*\(?zero',
                r'zero\s*\(?0%',
                r'reduzida?\s+a\s+zero',
                r'convertida?\s+em\s+(?:al[íi]quota\s+)?zero',
            ],
            'REDUÇÃO': [
                r'redu[çc][ãa]o',
                r'reduzid[ao]',
                r'reduz(?:ir)?',
                r'al[íi]quota\s+reduzida',
            ],
            'CRÉDITO': [
                r'cr[ée]dito',
                r'direito\s+a\s+cr[ée]dito',
                r'creditamento',
            ],
        }
        
        # Padrões para validar tributos
        self.tributo_patterns = {
            'PIS': [r'\bpis\b', r'contribui[çc][ãa]o\s+para\s+o\s+pis'],
            'COFINS': [r'\bcofins\b', r'contribui[çc][ãa]o.*financiamento.*seguridade'],
            'IPI': [r'\bipi\b', r'imposto\s+sobre\s+produtos\s+industrializados'],
            'ICMS': [r'\bicms\b', r'imposto\s+sobre\s+(?:circula[çc][ãa]o|opera[çc][õo]es)'],
            'ISS': [r'\biss\b', r'imposto\s+sobre\s+servi[çc]os'],
            'II': [r'imposto\s+de\s+importa[çc][ãa]o', r'\bii\b(?!\s*[-,.]?\s*(?:do|da|de|iii|iv|v)\b)'],
            'IBS': [r'\bibs\b', r'imposto\s+sobre\s+bens\s+e\s+servi[çc]os'],
            'CBS': [r'\bcbs\b', r'contribui[çc][ãa]o\s+sobre\s+bens\s+e\s+servi[çc]os'],
            'IS': [r'imposto\s+seletivo', r'\bis\b(?=\s+(?:incid|ser[áa]|sobre))'],
        }
    
    def validate(self, state: Dict) -> Dict:
        """
        Valida extrações contra texto original
        
        Args:
            state: Estado do workflow com todas as extrações
            
        Returns:
            state: Estado atualizado com correções e flags de validação
        """
        print("\n🔍 AGENTE 12: Validation Agent (v1.0)")
        print("   Validando extrações contra texto original...")
        
        # Obtém texto original
        original_text = self._get_original_text(state)
        if not original_text:
            print("   ⚠️  Texto original não disponível, pulando validação")
            return state
        
        original_lower = original_text.lower()
        
        # 1. Valida e corrige tipos de mudança
        corrections_made = 0
        errors_found = []
        
        if "system_changes" in state and state["system_changes"]:
            aliquotas = state["system_changes"].get("aliquotas", [])
            
            for i, aliq in enumerate(aliquotas):
                tributo = aliq.get("tributo", "")
                tipo_mudanca = aliq.get("tipo_mudanca", "")
                
                # Valida tributo existe no texto
                tributo_valid = self._validate_tributo(tributo, original_lower)
                if not tributo_valid:
                    errors_found.append(f"⚠️ {tributo}: não encontrado no texto original")
                    continue
                
                # Valida tipo de mudança
                tipo_validated, tipo_correto = self._validate_change_type(
                    tributo, tipo_mudanca, original_lower
                )
                
                if not tipo_validated:
                    if tipo_correto:
                        # Corrige automaticamente
                        old_tipo = tipo_mudanca
                        aliquotas[i]["tipo_mudanca"] = tipo_correto
                        aliquotas[i]["descricao_completa"] = f"{tributo}: {tipo_correto}"
                        
                        # Atualiza situacao_nova baseado no tipo correto
                        aliquotas[i]["situacao_nova"] = self._get_situacao_nova(tipo_correto, tributo)
                        
                        corrections_made += 1
                        print(f"   ✅ CORREÇÃO: {tributo} '{old_tipo}' → '{tipo_correto}'")
                    else:
                        errors_found.append(f"❌ {tributo}: tipo '{tipo_mudanca}' não confirmado no texto")
            
            state["system_changes"]["aliquotas"] = aliquotas
        
        # 2. Validação via LLM para casos ambíguos (opcional, só se houver erros)
        if errors_found and len(errors_found) <= 3:
            print("   🤖 Usando LLM para validação de casos ambíguos...")
            llm_corrections = self._validate_via_llm(
                state["system_changes"].get("aliquotas", []),
                original_text[:8000]
            )
            
            if llm_corrections:
                for correction in llm_corrections:
                    tributo = correction.get("tributo")
                    tipo_correto = correction.get("tipo_correto")
                    
                    for aliq in state["system_changes"]["aliquotas"]:
                        if aliq.get("tributo") == tributo:
                            old_tipo = aliq.get("tipo_mudanca")
                            aliq["tipo_mudanca"] = tipo_correto
                            aliq["descricao_completa"] = f"{tributo}: {tipo_correto}"
                            aliq["situacao_nova"] = self._get_situacao_nova(tipo_correto, tributo)
                            corrections_made += 1
                            print(f"   ✅ CORREÇÃO (LLM): {tributo} '{old_tipo}' → '{tipo_correto}'")
        
        # 3. Valida vigências críticas
        if "date_extraction" in state:
            vigencias = state["date_extraction"].get("vigencias", [])
            vigencias_validated = self._validate_vigencias(vigencias, original_lower)
            state["date_extraction"]["vigencias"] = vigencias_validated
        
        # 4. Adiciona flag de validação ao state
        state["validation_status"] = {
            "validated": True,
            "corrections_made": corrections_made,
            "errors": errors_found,
            "confidence": "alta" if not errors_found else "media"
        }
        
        # Sumário
        if corrections_made > 0:
            print(f"   ✅ {corrections_made} correção(ões) aplicada(s)")
        
        if errors_found:
            print(f"   ⚠️  {len(errors_found)} aviso(s) de validação")
            for err in errors_found[:3]:
                print(f"      {err}")
        else:
            print("   ✅ Todas as extrações validadas com sucesso")
        
        return state
    
    def _get_original_text(self, state: Dict) -> str:
        """Obtém texto original da legislação do state"""
        # Tenta várias fontes
        sources = [
            state.get("raw_extraction", {}).get("raw_text", ""),
            state.get("structured_data", {}).get("raw_extraction", {}).get("raw_text", ""),
        ]
        
        # Também pode vir dos web_results
        if state.get("web_results"):
            for wr in state["web_results"]:
                if wr.get("content"):
                    sources.append(wr["content"])
        
        # Retorna o maior (mais completo)
        return max(sources, key=len) if sources else ""
    
    def _validate_tributo(self, tributo: str, original_lower: str) -> bool:
        """Valida se tributo está presente no texto original"""
        # Normaliza nome do tributo
        tributo_key = tributo.upper()
        tributo_key = tributo_key.replace("CONTRIBUIÇÃO PARA O ", "")
        tributo_key = tributo_key.replace("CONTRIBUIÇÃO PARA A ", "")
        tributo_key = tributo_key.strip()
        
        patterns = self.tributo_patterns.get(tributo_key, [rf'\b{re.escape(tributo.lower())}\b'])
        
        for pattern in patterns:
            if re.search(pattern, original_lower, re.IGNORECASE):
                return True
        
        return False
    
    def _validate_change_type(self, tributo: str, tipo_mudanca: str, original_lower: str) -> Tuple[bool, str]:
        """
        Valida tipo de mudança contra texto original
        
        Returns:
            (is_valid, tipo_correto): Se válido e qual é o tipo correto
        """
        tipo_upper = tipo_mudanca.upper()
        
        # Normaliza tipos compostos
        if "SUSPENSÃO" in tipo_upper and ("0%" in tipo_upper or "ZERO" in tipo_upper):
            tipo_to_check = "SUSPENSÃO"  # Verifica suspensão primeiro
            secondary_check = "ALÍQUOTA 0%"
        else:
            tipo_to_check = None
            for tipo_key in self.change_type_patterns.keys():
                if tipo_key in tipo_upper:
                    tipo_to_check = tipo_key
                    break
            secondary_check = None
        
        if not tipo_to_check:
            return False, None
        
        # Busca contexto do tributo no texto
        tributo_lower = tributo.lower().replace("contribuição para o ", "").replace("contribuição para a ", "")
        
        # Encontra trechos relevantes (200 chars antes e depois da menção do tributo)
        tributo_contexts = self._find_tributo_contexts(tributo_lower, original_lower)
        
        if not tributo_contexts:
            # Tributo não encontrado, mas pode estar implícito
            tributo_contexts = [original_lower]
        
        # Verifica padrões no contexto
        tipo_encontrado = None
        for context in tributo_contexts:
            for tipo_key, patterns in self.change_type_patterns.items():
                for pattern in patterns:
                    if re.search(pattern, context, re.IGNORECASE):
                        tipo_encontrado = tipo_key
                        break
                if tipo_encontrado:
                    break
            if tipo_encontrado:
                break
        
        # Valida
        if tipo_encontrado:
            # Verifica se o tipo encontrado bate com o extraído
            if tipo_to_check == tipo_encontrado:
                return True, tipo_encontrado
            
            # Verifica tipo secundário (para SUSPENSÃO → ALÍQUOTA 0%)
            if secondary_check and secondary_check == tipo_encontrado:
                return True, f"{tipo_to_check} → {secondary_check}"
            
            # Tipo diferente encontrado - retorna o correto
            return False, tipo_encontrado
        
        # Não encontrou evidência clara
        return False, None
    
    def _find_tributo_contexts(self, tributo: str, text: str, window: int = 300) -> List[str]:
        """Encontra contextos onde o tributo é mencionado"""
        contexts = []
        
        # Padrões para encontrar o tributo
        patterns = self.tributo_patterns.get(tributo.upper(), [rf'\b{re.escape(tributo)}\b'])
        
        for pattern in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                start = max(0, match.start() - window)
                end = min(len(text), match.end() + window)
                contexts.append(text[start:end])
        
        return contexts
    
    def _get_situacao_nova(self, tipo_correto: str, tributo: str) -> str:
        """Gera descrição da situação nova baseado no tipo"""
        descricoes = {
            'SUSPENSÃO': f"Suspensão do pagamento do {tributo} conforme condições da legislação.",
            'SUSPENSÃO → ALÍQUOTA 0%': f"Suspensão do {tributo} que converte em alíquota zero após cumprimento dos requisitos.",
            'ISENÇÃO': f"Isenção do {tributo} para operações específicas conforme condições da legislação.",
            'ALÍQUOTA 0%': f"Alíquota zero do {tributo} para operações específicas.",
            'REDUÇÃO': f"Redução da alíquota do {tributo} conforme legislação.",
            'CRÉDITO': f"Direito a crédito do {tributo} conforme condições estabelecidas.",
        }
        
        return descricoes.get(tipo_correto, f"Alteração no {tributo} conforme legislação.")
    
    def _validate_via_llm(self, aliquotas: List[Dict], original_text: str) -> List[Dict]:
        """
        Usa LLM para validar casos ambíguos
        IMPORTANTE: Usa temperature=0.0 para máxima consistência
        """
        if not aliquotas:
            return []
        
        # Prepara lista de tributos para validar
        tributos_to_validate = []
        for aliq in aliquotas:
            tributo = aliq.get("tributo", "")
            tipo = aliq.get("tipo_mudanca", "")
            if tributo and tipo:
                tributos_to_validate.append(f"- {tributo}: {tipo}")
        
        if not tributos_to_validate:
            return []
        
        prompt = f"""Você é um especialista em legislação tributária brasileira.

TAREFA: Validar se os tipos de mudança tributária estão CORRETOS com base no texto da legislação.

TEXTO DA LEGISLAÇÃO:
{original_text[:6000]}

EXTRAÇÕES A VALIDAR:
{chr(10).join(tributos_to_validate)}

INSTRUÇÕES:
1. Para cada tributo, verifique NO TEXTO se o tipo de mudança está correto
2. SUSPENSÃO = pagamento suspenso, pode ser recolhido depois se não cumprir requisitos
3. ISENÇÃO = não há pagamento, benefício permanente
4. ALÍQUOTA 0% = alíquota existe mas é zero
5. SUSPENSÃO → ALÍQUOTA 0% = começa suspenso, vira zero após cumprir requisitos

RESPONDA APENAS com JSON:
{{
  "validacoes": [
    {{
      "tributo": "PIS",
      "tipo_extraido": "ISENÇÃO",
      "tipo_correto": "SUSPENSÃO → ALÍQUOTA 0%",
      "correcao_necessaria": true,
      "evidencia": "Art. 11-C menciona 'suspensão do pagamento' que 'converte-se em alíquota zero'"
    }}
  ]
}}

Se todos estiverem corretos, retorne lista vazia de validacoes.
APENAS JSON, sem explicações."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,  # ZERO para máxima consistência!
                max_tokens=1500
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Limpa markdown
            result_text = re.sub(r'```json\s*', '', result_text)
            result_text = re.sub(r'```\s*', '', result_text)
            
            result = json.loads(result_text)
            validacoes = result.get("validacoes", [])
            
            # Filtra apenas correções necessárias
            corrections = [
                {"tributo": v["tributo"], "tipo_correto": v["tipo_correto"]}
                for v in validacoes
                if v.get("correcao_necessaria", False) and v.get("tipo_correto")
            ]
            
            return corrections
            
        except Exception as e:
            print(f"   ⚠️  Erro na validação LLM: {e}")
            return []
    
    def _validate_vigencias(self, vigencias: List[Dict], original_lower: str) -> List[Dict]:
        """Valida vigências extraídas"""
        validated = []
        
        for vig in vigencias:
            data = vig.get("data", "")
            
            # Se é período em anos, mantém (são inferidos)
            if "ano" in data.lower():
                validated.append(vig)
                continue
            
            # Verifica se a data aparece no texto original
            data_normalized = data.replace("/", "[-/]")
            
            # Tenta encontrar a data ou ano no texto
            if re.search(data_normalized, original_lower) or \
               re.search(r'\b' + re.escape(data) + r'\b', original_lower):
                validated.append(vig)
            else:
                # Verifica se pelo menos o ano está presente
                year_match = re.search(r'20\d{2}', data)
                if year_match:
                    year = year_match.group(0)
                    if year in original_lower:
                        validated.append(vig)
        
        return validated


# ============================================================================
# Função auxiliar para integração fácil no workflow
# ============================================================================

def create_validation_agent():
    """Factory function para criar o agente"""
    return ValidationAgent()


# ============================================================================
# Teste standalone
# ============================================================================

if __name__ == "__main__":
    print("🧪 Teste do Validation Agent")
    print("="*60)
    
    # Simula state com dados
    test_state = {
        "raw_extraction": {
            "raw_text": """
            Art. 11-C. Fica suspensa a exigência da Contribuição para o PIS/Pasep
            e da Cofins incidentes sobre a venda no mercado interno e na importação
            de componentes eletrônicos e outros produtos de tecnologias da informação
            e comunicação destinados ao ativo imobilizado de pessoa jurídica
            habilitada ao Redata.
            
            § 1º A suspensão de que trata o caput converte-se em alíquota zero
            após cumpridas as condições estabelecidas.
            
            § 2º Aplica-se o disposto neste artigo também ao IPI incidente na
            importação dos bens referidos no caput.
            """
        },
        "system_changes": {
            "aliquotas": [
                {
                    "tributo": "PIS",
                    "tipo_mudanca": "ISENÇÃO",  # ERRADO! Deveria ser SUSPENSÃO
                    "situacao_nova": "Isenção",
                    "descricao_completa": "PIS: ISENÇÃO"
                },
                {
                    "tributo": "COFINS", 
                    "tipo_mudanca": "SUSPENSÃO → ALÍQUOTA 0%",  # CORRETO
                    "situacao_nova": "Suspensão que converte em zero",
                    "descricao_completa": "COFINS: SUSPENSÃO → ALÍQUOTA 0%"
                },
                {
                    "tributo": "IPI",
                    "tipo_mudanca": "ISENÇÃO",  # ERRADO! Deveria ser SUSPENSÃO
                    "situacao_nova": "Isenção",
                    "descricao_completa": "IPI: ISENÇÃO"
                }
            ]
        },
        "date_extraction": {
            "vigencias": [
                {"data": "17/09/2025", "contexto": "Início vigência"},
                {"data": "5 anos", "contexto": "Duração benefício"}
            ]
        }
    }
    
    agent = ValidationAgent()
    result = agent.validate(test_state)
    
    print("\n📊 Resultado:")
    print(f"   Status: {result.get('validation_status', {})}")
    print(f"\n   Alíquotas corrigidas:")
    for aliq in result["system_changes"]["aliquotas"]:
        print(f"   - {aliq['tributo']}: {aliq['tipo_mudanca']}")
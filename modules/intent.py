# modules/intent.py
"""
Camada de roteamento de intenção para evitar chamadas de SQL Agent em saudações e papo-furado.
"""

def detectar_intencao(texto: str) -> str:
    texto = texto.lower().strip()

    # Saudações simples
    if texto in ["oi", "olá", "ola", "bom dia", "boa tarde", "boa noite", "e aí", "e ai"]:
        return "saudacao"

    # Perguntas simples/conversacionais ou suporte
    if any(p in texto for p in ["quem é você", "o que você faz", "ajuda", "como funciona", "obrigado", "valeu", "show"]):
        return "conversa"

    # Consulta de negócio (Winthor)
    if any(p in texto for p in ["preço", "valor", "estoque", "pedido", "produto", "cliente", "venda", "quanto", "tem", "qual"]):
        return "consulta"

    # Padrão é tratar como conversa se não houver palavras-chave de negócio
    return "conversa"

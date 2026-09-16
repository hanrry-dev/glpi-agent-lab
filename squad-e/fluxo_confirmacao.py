def preparar_rascunho_chamado(intencao_usuario):
   
    print(f" [Agente IA] Entendi sua intenção: '{intencao_usuario}'")
    print(" [Agente IA] Preparando o rascunho do chamado...\n")
    
   
    rascunho = {
        "name": "Solicitação de licença do software SaaS",
        "content": "Preciso da licença para a nova estagiária do setor de Marketing.",
        "type": 2,         
        "urgency": 3,       
        "itilcategories_id": 15 
    }
    
    return rascunho

def confirmar_e_gravar(payload):
    

    print("===  RESUMO DO CHAMADO PARA CONFIRMAÇÃO ===")
    print(f"Título:    {payload['name']}")
    print(f"Descrição: {payload['content']}")
    print("=============================================\n")
    
    
    confirmacao = input("Você confirma a gravação deste chamado no GLPI? (S/N): ")
    
    if confirmacao.upper() == 'S':
        
        print("\n [SUCESSO] Autorização recebida!")
        print("  Enviando POST para /Ticket na API do GLPI... (Simulado)")
       
    else:
        print("\n❌ [CANCELADO] Ação bloqueada. O chamado foi descartado pelo usuário.")


if __name__ == "__main__":
  
    texto_usuario = "Preciso de uma licença nova para o estagiário"
   
    payload_gerado = preparar_rascunho_chamado(texto_usuario)
    
   
    confirmar_e_gravar(payload_gerado)
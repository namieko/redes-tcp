import socket
import threading
import sys
import hashlib

HOST = '127.0.0.1'  # Deve ser o mesmo do servidor
PORT = 65432        # Deve ser a mesma do servidor

# PROTOCOLO (O mesmo do Servidor)
def enviar_mensagem(conexao, comando, payload):
    if isinstance(payload, str):
        payload = payload.encode('utf-8')
    tamanho = len(payload)
    cabecalho = f"{comando}{tamanho:010d}".encode('utf-8')
    conexao.sendall(cabecalho + payload)

def receber_mensagem(conexao):
    try:
        cabecalho = conexao.recv(11)
        if not cabecalho:
            return None, None
            
        comando = cabecalho[0:1].decode('utf-8')
        tamanho = int(cabecalho[1:11].decode('utf-8'))
        
        payload = b""
        while len(payload) < tamanho:
            bytes_restantes = tamanho - len(payload)
            pedaco = conexao.recv(bytes_restantes)
            if not pedaco:
                break
            payload += pedaco
            
        return comando, payload
    except Exception:
        return None, None


# THREAD DE RECEPÇÃO (Escuta o servidor o tempo todo)
def escutar_servidor(conexao):
    while True:
        comando, payload = receber_mensagem(conexao)
        
        if not comando:
            print("\n[DESCONECTADO] O servidor encerrou a conexão.")
            import os
            os._exit(0) 
            
        if comando == 'C':
            print(f"\r[Mensagem recebida]: {payload.decode('utf-8')}\n> ", end="")
            
        elif comando == 'E':
            print(f"\r[ERRO DO SERVIDOR]: {payload.decode('utf-8')}\n> ", end="")
            
        elif comando == 'M':
            # Recebeu metadados, vamos preparar o download!
            dados = payload.decode('utf-8').split('|')
            nome_arquivo = dados[0]
            tamanho_esperado = int(dados[1])
            hash_esperado = dados[2]
            
            print(f"\r[DOWNLOAD] Iniciando '{nome_arquivo}' ({tamanho_esperado} bytes)...")
            
            bytes_recebidos = 0
            sha256_local = hashlib.sha256()
            
            # Abre um arquivo local para salvar os dados
            with open(f"baixado_{nome_arquivo}", 'wb') as f:
                # Fica num loop até receber todos os bytes prometidos
                while bytes_recebidos < tamanho_esperado:
                    cmd_down, pedaco_down = receber_mensagem(conexao)
                    
                    if cmd_down == 'F':
                        f.write(pedaco_down)
                        sha256_local.update(pedaco_down) # Calcula o hash localmente
                        bytes_recebidos += len(pedaco_down)
                        
                    elif cmd_down == 'C':
                        # Se alguém mandar mensagem no chat DURANTE o download, ele não trava!
                        print(f"\r[Chat durante o download]: {pedaco_down.decode('utf-8')}")
            
            # Validação Final
            if sha256_local.hexdigest() == hash_esperado:
                print(f"\r[SUCESSO] Download concluído! Integridade validada (SHA-256 OK).\n> ", end="")
            else:
                print(f"\r[FALHA DE SEGURANÇA] Arquivo corrompido! Hashes não batem.\n> ", end="")


# FLUXO PRINCIPAL (Menu Interativo e Teclado)
def iniciar_cliente():
    cliente = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        cliente.connect((HOST, PORT))
        print("[CONECTADO] Conexão estabelecida com o servidor!")
    except Exception as e:
        print(f"[ERRO] Não foi possível conectar: {e}")
        return

    # Inicia a Thread para ficar escutando o servidor
    thread_escuta = threading.Thread(target=escutar_servidor, args=(cliente,))
    thread_escuta.daemon = True # Faz a thread morrer automaticamente se o programa principal fechar
    thread_escuta.start()

    # Loop do Menu (Roda na linha de execução principal)
    try:
        while True:
            print("\n=== MENU ===")
            print("1. Enviar mensagem no Chat")
            print("2. Baixar Arquivo")
            print("3. Sair")
            escolha = input("> ")

            if escolha == '1':
                texto = input("Digite sua mensagem: ")
                # Envia usando o comando 'C' (Chat)
                enviar_mensagem(cliente, 'C', texto)
                
            elif escolha == '2':
                nome_arquivo = input("Digite o nome do arquivo que deseja baixar: ")
                enviar_mensagem(cliente, 'D', nome_arquivo)
                
            elif escolha == '3':
                print("Saindo...")
                break
            else:
                print("Opção inválida.")
    except KeyboardInterrupt:
        print("\nSaindo...")
    finally:
        cliente.close()

if __name__ == "__main__":
    iniciar_cliente()
import socket
import threading
import os
import hashlib

HOST = '127.0.0.1'  # Endereço local (localhost)
PORT = 65432        # Porta para o servidor escutar
DIRETORIO_BASE = os.path.abspath('./arquivos') # Pasta padrão de arquivos

clientes_conectados = [] # Lista para controlar os clientes no chat


# Esta função garante que o cliente só acesse arquivos dentro da pasta '/arquivos'
def caminho_seguro(nome_arquivo):
    # Junta o caminho da pasta base com o nome do arquivo solicitado
    caminho_solicitado = os.path.abspath(os.path.join(DIRETORIO_BASE, nome_arquivo))
    
    # Valida se o caminho final ainda começa com a nossa pasta permitida
    if caminho_solicitado.startswith(DIRETORIO_BASE):
        return caminho_solicitado
    else:
        return None # Se o usuário tentou usar "../../", retorna None (Bloqueado!)


# PASSO 2: FUNÇÕES DO PROTOCOLO (EMPACOTAMENTO DE MENSAGENS)
# O TCP entrega bytes contínuos. Estas funções garantem que as mensagens 
# não cheguem coladas ou cortadas.
def enviar_mensagem(conexao, comando, payload):
    """
    Formata a mensagem antes de enviar.
    Estrutura: [1 byte Comando] + [10 bytes Tamanho] + [Dados]
    """
    if isinstance(payload, str):
        payload = payload.encode('utf-8')
        
    tamanho = len(payload)
    # Cria o cabeçalho de tamanho fixo (11 bytes no total)
    # :010d garante que o número tenha sempre 10 dígitos (ex: 0000000025)
    cabecalho = f"{comando}{tamanho:010d}".encode('utf-8')
    
    # Envia o cabeçalho grudado com os dados brutos
    conexao.sendall(cabecalho + payload)

def receber_mensagem(conexao):
    """
    Lê a mensagem seguindo estritamente a regra do cabeçalho.
    """
    try:
        # 1. Lê primeiro os 11 bytes fixos do cabeçalho
        cabecalho = conexao.recv(11)
        if not cabecalho:
            return None, None
            
        # Separando as informações do cabeçalho
        comando = cabecalho[0:1].decode('utf-8')
        tamanho = int(cabecalho[1:11].decode('utf-8'))
        
        # 2. Loop para ler exatamente a quantidade de bytes que o cabeçalho anunciou
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

def enviar_broadcast(remetente_conexao, mensagem_texto):
    """
    Envia a mensagem para todos os clientes, exceto para quem enviou.
    """
    # Varre a nossa lista de conexões ativas
    for cliente_destino in clientes_conectados:
        # Só envia se o destino for diferente de quem mandou a mensagem original
        if cliente_destino != remetente_conexao:
            try:
                # Usamos o comando 'C' e a nossa função de empacotamento segura
                enviar_mensagem(cliente_destino, 'C', mensagem_texto)
            except Exception as e:
                print(f"[ERRO BROADCAST] Falha ao enviar para um cliente: {e}")

# GERENCIAMENTO DE CLIENTES (MULTITHREADING)
def lidar_com_cliente(conexao, endereco):
    print(f"[NOVA CONEXÃO] Cliente {endereco} conectado.")
    clientes_conectados.append(conexao)
    
    try:
        while True:
            comando, payload = receber_mensagem(conexao)
            
            if not comando:
                break # Cliente desconectou
                
            if comando == 'C':
                mensagem_original = payload.decode('utf-8')
                
                # Monta a mensagem bonita com o "nome" (IP/Porta) de quem enviou
                mensagem_formatada = f"[{endereco[1]}] diz: {mensagem_original}"
                print(f"[CHAT SERVER] {mensagem_formatada}")
                
                # Espalha para todos os outros clientes
                enviar_broadcast(conexao, mensagem_formatada)
           
            elif comando == 'D':
                nome_arquivo = payload.decode('utf-8')
                print(f"[{endereco[1]}] Solicitou o arquivo: {nome_arquivo}")
                
                # VERIFICAÇÃO DE SEGURANÇA 
                caminho = caminho_seguro(nome_arquivo)
                if not caminho or not os.path.exists(caminho):
                    enviar_mensagem(conexao, 'E', "ERRO: Arquivo inexistente ou acesso negado (Path Traversal bloqueado).")
                    continue # Volta para o início do loop
                    
                # CÁLCULO DO SHA-256 EM CHUNKS
                tamanho_total = os.path.getsize(caminho)
                sha256 = hashlib.sha256()
                
                # Abre o arquivo em modo leitura binária ('rb')
                with open(caminho, 'rb') as f:
                    while True:
                        pedaco = f.read(4096) # Lê blocos de 4KB
                        if not pedaco: 
                            break # Fim do arquivo
                        sha256.update(pedaco) # Alimenta o algoritmo
                        
                hash_arquivo = sha256.hexdigest()
                
                # ENVIO DOS METADADOS (Nome | Tamanho | Hash)
                metadados = f"{nome_arquivo}|{tamanho_total}|{hash_arquivo}"
                enviar_mensagem(conexao, 'M', metadados)
                
                # ENVIO DO ARQUIVO EM CHUNKS
                print(f"[SERVIDOR] Enviando arquivo {nome_arquivo} para {endereco[1]}...")
                with open(caminho, 'rb') as f:
                    while True:
                        pedaco = f.read(4096)
                        if not pedaco: 
                            break
                        # Envia o pedaço bruto com o comando 'F' (File)
                        enviar_mensagem(conexao, 'F', pedaco)
                
                print(f"[SERVIDOR] Envio concluído para {endereco[1]}.")
            
    except Exception as e:
        print(f"[ERRO] Problema com o cliente {endereco}: {e}")
    finally:
        print(f"[DESCONEXÃO] Cliente {endereco} saiu.")
        if conexao in clientes_conectados:
            clientes_conectados.remove(conexao)
        conexao.close()

def iniciar_servidor():
    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    servidor.bind((HOST, PORT))
    servidor.listen()
    print(f"[ESCUTANDO] Servidor aguardando conexões em {HOST}:{PORT}...")

    while True:
        conexao, endereco = servidor.accept()
        thread_cliente = threading.Thread(target=lidar_com_cliente, args=(conexao, endereco))
        thread_cliente.start()
        print(f"[THREADS ATIVAS] {threading.active_count() - 1}")

if __name__ == "__main__":
    iniciar_servidor()
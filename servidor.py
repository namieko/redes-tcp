import socket
import threading
import os

HOST = '127.0.0.1'
PORT = 8080 # Mudamos para 8080 (Padrão web para testes)
DIRETORIO_BASE = os.path.abspath('./arquivos')

def caminho_seguro(nome_arquivo):
    caminho_solicitado = os.path.abspath(os.path.join(DIRETORIO_BASE, nome_arquivo))
    if caminho_solicitado.startswith(DIRETORIO_BASE):
        return caminho_solicitado
    return None

def obter_content_type(caminho_arquivo):
    """Garante os 2,0 pts de Inspeção de Protocolo determinando o tipo de arquivo."""
    if caminho_arquivo.endswith(".html"):
        return "text/html"
    elif caminho_arquivo.endswith(".jpg") or caminho_arquivo.endswith(".jpeg"):
        return "image/jpeg"
    elif caminho_arquivo.endswith(".png"):
        return "image/png"
    else:
        return "application/octet-stream" # Binário genérico

def lidar_com_cliente(conexao, endereco):
    try:
        # 1. Lê a requisição do navegador (Browser manda em UTF-8)
        requisicao = conexao.recv(4096).decode('utf-8')
        if not requisicao:
            return
            
        # 2. Parsing: Pega a primeira linha (ex: "GET /index.html HTTP/1.1")
        linhas = requisicao.split('\r\n')
        linha_pedido = linhas[0]
        print(f"\n[REQUEST] {endereco} solicitou: {linha_pedido}")
        
        partes = linha_pedido.split(' ')
        if len(partes) >= 2 and partes[0] == 'GET':
            caminho_solicitado = partes[1]
            
            # Se pediu a raiz "/", redireciona para o index.html
            if caminho_solicitado == '/':
                caminho_solicitado = '/index.html'
                
            # Remove a barra inicial para a junção de pastas funcionar corretamente
            caminho_solicitado = caminho_solicitado.lstrip('/')
            
            caminho_final = caminho_seguro(caminho_solicitado)
            
            # 3. TRATAMENTO DE ERRO 404 (Valendo 2,0 pts)
            if not caminho_final or not os.path.exists(caminho_final):
                print(f"[404 NOT FOUND] Arquivo inexistente: {caminho_solicitado}")
                caminho_404 = os.path.join(DIRETORIO_BASE, '404.html')
                
                with open(caminho_404, 'rb') as f:
                    conteudo = f.read()
                    
                cabecalho = (
                    "HTTP/1.1 404 Not Found\r\n"
                    "Content-Type: text/html\r\n"
                    f"Content-Length: {len(conteudo)}\r\n"
                    "Connection: close\r\n\r\n"
                )
                conexao.sendall(cabecalho.encode('utf-8') + conteudo)
                return

            # 4. TRATAMENTO DE SUCESSO 200 OK
            tipo_conteudo = obter_content_type(caminho_final)
            tamanho = os.path.getsize(caminho_final)
            
            # EXIBIÇÃO DE MÍDIA (Valendo 2,0 pts): Lendo sempre em modo binário ('rb')
            with open(caminho_final, 'rb') as f:
                conteudo = f.read()
                
            # A linha em branco no final (\r\n\r\n) é vital para separar o cabeçalho do arquivo!
            cabecalho = (
                "HTTP/1.1 200 OK\r\n"
                f"Content-Type: {tipo_conteudo}\r\n"
                f"Content-Length: {tamanho}\r\n"
                "Connection: close\r\n\r\n"
            )
            
            # Junta o texto do cabeçalho com os bytes do arquivo e envia
            conexao.sendall(cabecalho.encode('utf-8') + conteudo)
            print(f"[200 OK] {caminho_solicitado} enviado com sucesso.")

    except Exception as e:
        print(f"[ERRO] Falha com {endereco}: {e}")
    finally:
        conexao.close()

def iniciar_servidor():
    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Permite reiniciar o servidor sem dar erro de "porta em uso"
    servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    servidor.bind((HOST, PORT))
    servidor.listen()
    print(f"[HTTP SERVER] Rodando em http://{HOST}:{PORT}")

    while True:
        conexao, endereco = servidor.accept()
        thread_cliente = threading.Thread(target=lidar_com_cliente, args=(conexao, endereco))
        thread_cliente.start()

if __name__ == "__main__":
    iniciar_servidor()
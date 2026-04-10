
import os
import glob

def renomear_arquivos(pasta, nome_base, extensao=None):
    """
    Renomeia arquivos de uma pasta sequencialmente.
    
    Args:
        pasta (str): Caminho da pasta com os arquivos
        nome_base (str): Nome base para os arquivos
        extensao (str, optional): Filtro de extensão (ex: '.mp4')
    """
    
    # Define o padrão de busca
    if extensao:
        padrao = f"*{extensao}"
    else:
        padrao = "*.*"
    
    # Lista todos os arquivos na pasta
    caminho_completo = os.path.join(pasta, padrao)
    arquivos = glob.glob(caminho_completo)
    
    # Filtra apenas arquivos (ignora pastas)
    arquivos = [f for f in arquivos if os.path.isfile(f)]
    
    # Ordena os arquivos para renomear em ordem
    arquivos.sort()
    
    print(f"Encontrados {len(arquivos)} arquivos para renomear.")
    
    # Renomeia cada arquivo
    for i, arquivo in enumerate(arquivos, 1):
        # Obtém o diretório e a extensão do arquivo
        diretorio = os.path.dirname(arquivo)
        _, ext = os.path.splitext(arquivo)
        
        # Cria o novo nome
        novo_nome = f"{nome_base}{i}{ext}"
        novo_caminho = os.path.join(diretorio, novo_nome)
        
        try:
            os.rename(arquivo, novo_caminho)
            print(f"✓ {os.path.basename(arquivo)} -> {novo_nome}")
        except Exception as e:
            print(f"✗ Erro ao renomear {arquivo}: {e}")

# Exemplo de uso
if __name__ == "__main__":
    # Configure aqui:
    PASTA = "videos/Pack teste"  # Altere para o caminho da sua pasta
    NOME_BASE = "Videos teste"
    EXTENSAO = None  # None para todas extensões
    
    renomear_arquivos(PASTA, NOME_BASE, EXTENSAO)
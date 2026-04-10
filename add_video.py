import os
import uuid
from video_manager import VideoManager
from video_processor import VideoProcessor
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def ensure_directories():
    """Garante que diretórios existem."""
    directories = ['previews', 'videos', 'thumbnails']
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"✅ Diretório criado: {directory}/")

def add_video_interactive():
    """Adiciona vídeo interativamente."""
    ensure_directories()
    
    manager = VideoManager()
    processor = VideoProcessor()
    
    print("\n" + "="*50)
    print("📹 ADICIONAR NOVO VÍDEO PARA VENDA")
    print("="*50 + "\n")
    
    # Gerar ID único
    video_id = f"video_{uuid.uuid4().hex[:8]}"
    print(f"📋 ID do vídeo: {video_id}")
    
    # Informações básicas
    title = input("🎬 Título do vídeo: ").strip()
    while not title:
        print("❌ Título é obrigatório!")
        title = input("🎬 Título do vídeo: ").strip()
    
    description = input("📝 Descrição: ").strip()
    
    # Preço
    while True:
        try:
            price = float(input("💰 Preço (R$): ").strip())
            if price <= 0:
                print("❌ Preço deve ser maior que zero!")
                continue
            break
        except ValueError:
            print("❌ Preço inválido. Use números (ex: 9.99)")
    
    # Vídeo completo
    print("\n📁 PASTA DE VÍDEOS COMPLETOS:")
    print("Arquivos disponíveis em 'videos/'")
    complete_files = [f for f in os.listdir('videos') if f.lower().endswith(('.mp4', '.mov', '.avi', '.mkv'))]
    
    if complete_files:
        print(f"Vídeos encontrados: {complete_files}")
        video_filename = input("Nome do arquivo do vídeo completo (ou caminho completo): ").strip()
        
        if '/' not in video_filename and '\\' not in video_filename:
            video_path = os.path.join('videos', video_filename)
        else:
            video_path = video_filename
        
        if not os.path.exists(video_path):
            print(f"❌ Arquivo não encontrado: {video_path}")
            return
    else:
        video_path = input("📂 Caminho completo do vídeo: ").strip()
        if not os.path.exists(video_path):
            print(f"❌ Arquivo não encontrado: {video_path}")
            return
    
    # Criar prévia borrada
    print("\n🔄 Criando prévia borrada...")
    preview_path = os.path.join('previews', f"{video_id}_preview.mp4")
    
    # Verifica se já existe prévia com mesmo nome
    if os.path.exists(preview_path):
        overwrite = input(f"⚠️  Prévia já existe. Sobrescrever? (s/n): ").lower()
        if overwrite != 's':
            preview_path = os.path.join('previews', f"{video_id}_preview_{uuid.uuid4().hex[:4]}.mp4")
    
    # Cria prévia borrada
    success = processor.create_blurred_preview(
        input_path=video_path,
        output_path=preview_path,
        blur_strength=15,  # Ajuste a intensidade do blur
        preview_duration=10  # 10 segundos de prévia
    )
    
    if not success:
        print("❌ Erro ao criar prévia borrada. Tentando método alternativo...")
        success = processor.create_preview_with_watermark(
            video_path=video_path,
            output_path=preview_path,
            watermark_text="PRÉVIA BORRADA"
        )
    
    if not success:
        print("❌ Falha ao criar prévia. Continuando sem prévia...")
        preview_path = ""  # Será usada uma imagem estática como fallback
    
    # Criar thumbnail
    print("\n🖼️ Criando thumbnail...")
    thumbnail_path = os.path.join('thumbnails', f"{video_id}_thumb.jpg")
    if os.path.exists(video_path) and processor.extract_thumbnail(video_path, thumbnail_path):
        print(f"✅ Thumbnail criada: {thumbnail_path}")
    else:
        print("⚠️  Thumbnail não criada")
        thumbnail_path = ""
    
    # Calcular duração e tamanho
    duration = processor.get_video_duration(video_path)
    file_size = os.path.getsize(video_path) / (1024 * 1024)  # MB
    
    # Preparar dados
    video_data = {
        'video_id': video_id,
        'title': title,
        'description': description,
        'price_brl': price,
        'preview_path': preview_path,
        'video_path': video_path,
        'duration_seconds': int(duration),
        'file_size_mb': round(file_size, 2),
        'thumbnail_path': thumbnail_path,
        'telegram_file_id': '',
        'telegram_preview_id': ''
    }
    
    # Salvar no banco
    if manager.add_video(video_data):
        print(f"\n✅ VÍDEO ADICIONADO COM SUCESSO!")
        print(f"ID: {video_id}")
        print(f"Título: {title}")
        print(f"Preço: R$ {price:.2f}")
        print(f"Duração: {int(duration//60)}:{int(duration%60):02d}")
        print(f"Tamanho: {file_size:.1f} MB")
        print(f"Vídeo completo: {video_path}")
        if preview_path:
            print(f"Prévia borrada: {preview_path}")
        if thumbnail_path:
            print(f"Thumbnail: {thumbnail_path}")
    else:
        print("❌ Erro ao salvar vídeo no banco de dados.")
    
    # Perguntar se quer adicionar mais
    print("\n" + "="*50)
    more = input("\n➕ Adicionar outro vídeo? (s/n): ").lower()
    if more == 's':
        add_video_interactive()

def list_videos():
    """Lista todos os vídeos cadastrados."""
    manager = VideoManager()
    videos = manager.get_all_videos()
    
    print("\n" + "="*50)
    print("📋 VÍDEOS CADASTRADOS")
    print("="*50)
    
    if not videos:
        print("Nenhum vídeo cadastrado.")
        return
    
    for i, video in enumerate(videos, 1):
        print(f"\n{i}. {video['title']}")
        print(f"ID: {video['video_id']}")
        print(f"Preço: R$ {video['price_brl']:.2f}")
        print(f"Status: {'✅ Ativo' if video['is_active'] else '❌ Inativo'}")
        print(f"Prévia: {'✅ Existe' if video['preview_exists'] else '❌ Falta'}")
        print(f"Vídeo: {'✅ Existe' if video['video_exists'] else '❌ Falta'}")

def main():
    """Menu principal."""
    while True:
        print("\n" + "="*50)
        print("🎬 GERENCIADOR DE VÍDEOS")
        print("="*50)
        print("1. ➕ Adicionar novo vídeo")
        print("2. 📋 Listar vídeos cadastrados")
        print("3. 🚪 Sair")
        print("="*50)
        
        choice = input("\nEscolha uma opção: ").strip()
        
        if choice == '1':
            add_video_interactive()
        elif choice == '2':
            list_videos()
        elif choice == '3':
            print("👋 Até logo!")
            break
        else:
            print("❌ Opção inválida!")

if __name__ == '__main__':
    ensure_directories()
    main()
#!/usr/bin/env python3
"""
CRIADOR DE PACKS DIRETO
"""

import os
import uuid
from pathlib import Path
from video_processor import VideoProcessor
from video_manager import VideoManager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configurações
VIDEOS_DIR = "videos"
PREVIEWS_DIR = "previews"
THUMBNAILS_DIR = "thumbnails"

def ensure_dirs():
    """Cria diretórios se não existirem."""
    for d in [PREVIEWS_DIR, THUMBNAILS_DIR]:
        Path(d).mkdir(exist_ok=True)

def scan_subfolders():
    """Retorna todas as subpastas dentro de videos/."""
    subpastas = []
    
    if not os.path.exists(VIDEOS_DIR):
        print(f"❌ Pasta '{VIDEOS_DIR}' não existe!")
        return subpastas
    
    for item in os.listdir(VIDEOS_DIR):
        item_path = os.path.join(VIDEOS_DIR, item)
        if os.path.isdir(item_path):
            # Lista vídeos na pasta
            videos = []
            exts = {'.mp4', '.mov', '.avi', '.mkv', '.flv', '.wmv'}
            
            for file in os.listdir(item_path):
                file_path = os.path.join(item_path, file)
                if os.path.isfile(file_path) and os.path.splitext(file)[1].lower() in exts:
                    videos.append({
                        'path': file_path,
                        'name': file,
                        'title': os.path.splitext(file)[0].replace('_', ' ').replace('-', ' ').title()
                    })
            
            if len(videos) >= 2:
                subpastas.append({
                    'path': item_path,
                    'name': item,
                    'clean_name': item.replace('_', ' ').replace('-', ' ').title(),
                    'videos': videos,
                    'video_count': len(videos)
                })
            else:
                print(f"⏭️ Pasta ignorada ({len(videos)} vídeo(s)): {item}")
    
    return subpastas

def process_video_for_pack(video_data, pack_id, video_index, processor, preco_pack, pack_title):
    """
    Processa um vídeo para o pack.
    """
    video_id = f"pkv_{pack_id}_{video_index}"  # Prefixo mais curto
    
    print(f"📹 {video_data['name']}")
    
    # CRIA PRÉVIA BORRADA
    preview_filename = f"{video_id}_preview.mp4"
    preview_path = os.path.join(PREVIEWS_DIR, preview_filename)
    
    print("🎬 Criando prévia...", end="", flush=True)
    
    # IMPORTANTE: Passar o caminho do ARQUIVO, não da pasta!
    success = processor.create_blurred_preview(
        input_path=video_data['path'],  # ← caminho completo do arquivo
        output_path=preview_path,
        blur_strength=15,
        preview_duration=10
    )
    
    if not success:
        print("❌")
        preview_path = ""
    else:
        print("✅")
    
    # CRIA THUMBNAIL
    thumb_filename = f"{video_id}_thumb.jpg"
    thumb_path = os.path.join(THUMBNAILS_DIR, thumb_filename)
    
    print("🖼️ Criando thumbnail...", end="", flush=True)
    if processor.extract_thumbnail(video_data['path'], thumb_path):
        print("✅")
    else:
        print("❌")
        thumb_path = ""
    
    # Obtém informações do vídeo
    duration = processor.get_video_duration(video_data['path']) or 0
    file_size = os.path.getsize(video_data['path']) / (1024 * 1024)
    
    return {
        'video_id': video_id,
        'title': video_data['title'],  # Título individual
        'description': f"Vídeo do pack: {pack_title}",
        'price_brl': preco_pack,  # Mesmo preço do pack (não vende individual)
        'preview_path': preview_path,
        'video_path': video_data['path'],
        'duration_seconds': int(duration),
        'file_size_mb': round(file_size, 2),
        'thumbnail_path': thumb_path,
        'telegram_file_id': '',
        'telegram_preview_id': '',
        'pack_id': pack_id,
        'pack_only': 1
    }

def criar_pack_direto():
    """CRIA UM PACK DIRETAMENTE"""
    ensure_dirs()
    manager = VideoManager()
    processor = VideoProcessor()

    print("\n" + "="*50)
    print("📦 ADICIONAR NOVO PACK PARA VENDA")
    print("="*50 + "\n")

    # GERAR IDs
    pack_id = f"pack_{uuid.uuid4().hex[:8]}"
    print(f"📋 ID do Pack: {pack_id}")

    # Informações básicas
    title = input("📦 Título do Pack: ").strip()
    while not title:
        print("❌ Título é obrigatório!")
        title = input("📦 Título do Pack: ").strip()
    
    description = input("📝 Descrição: ").strip()
    if not description:
        description = f"Pack com vídeos exclusivos!"

    # PREÇO DO PACK
    print(f"\n💰 Defina o PREÇO DO PACK COMPLETO:")
    while True:
        try:
            pack_price = float(input(f"Preço (R$): R$ ").strip())
            if pack_price <= 0:
                print("❌ Preço deve ser maior que zero!")
                continue
            break
        except ValueError:
            print("❌ Preço inválido! Use números (ex: 29.90)")

    # Escaneia subpastas
    print("\n🔍 Escaneando subpastas...")
    subpastas = scan_subfolders()
    
    if not subpastas:
        print("❌ Nenhuma subpasta com 2+ vídeos encontrada!")
        return
    
    print(f"\n📋 PASTAS ENCONTRADAS ({len(subpastas)}):")
    for i, pasta in enumerate(subpastas, 1):
        print(f"   {i}. {pasta['clean_name']} - {pasta['video_count']} vídeos")

    # Confirmação
    print(f"\n⚠️  Você está prestes a CRIAR {len(subpastas)} PACK(S)!")
    resp = input("❓ Continuar? (s/n): ").strip().lower()
    if resp != 's':
        print("🚫 Cancelado.")
        return
    
    print("\n" + "="*70)
    print("🚀 CRIANDO PACKS...")
    print("="*70)

    # Processar TODOS os packs
    todos_videos = []
    
    for i, pasta in enumerate(subpastas, 1):
        print(f"\n[{i}/{len(subpastas)}] 📦 {pasta['clean_name']}")
        
        # Processa TODOS os vídeos da pasta
        videos_processados = []
        for j, video_data in enumerate(pasta['videos'], 1):
            print(f"\n  [{j}/{pasta['video_count']}] ", end="")
            video_info = process_video_for_pack(
                video_data, pack_id, f"{i}_{j}", 
                processor, pack_price, title
            )
            if video_info:
                videos_processados.append(video_info)
        
        if videos_processados:
            todos_videos.extend(videos_processados)
    
    if not todos_videos:
        print("❌ Nenhum vídeo processado com sucesso!")
        return None

    # THUMBNAIL DO PACK
    thumbnail_path = ""
    add_thumb = input(f"\n🖼️ Adicionar thumbnail para o pack? (s/n): ").strip().lower()
    if add_thumb == 's':
        thumb_path = input(f"Caminho da imagem: ").strip()
        if os.path.exists(thumb_path):
            thumbnail_path = thumb_path
        else:
            print("⚠️ Arquivo não encontrado, continuando sem thumbnail")

    # CONFIRMAÇÃO FINAL
    confirm = input("\n✅ Confirmar criação do pack? (s/n): ").lower()
    if confirm != 's':
        print("❌ Operação cancelada.")
        return
    
    # ===== 1. PRIMEIRO: Salvar TODOS os vídeos na tabela pack_videos =====
    videos_salvos = []
    for video_data in todos_videos:
        try:
            # Insere na tabela pack_videos
            cursor = manager.conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO pack_videos 
                (video_id, title, description, price_brl, preview_path, 
                 video_path, duration_seconds, file_size_mb, thumbnail_path,
                 telegram_file_id, telegram_preview_id, pack_id, pack_only)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                video_data['video_id'],
                video_data['title'],
                video_data['description'],
                video_data['price_brl'],
                video_data['preview_path'],
                video_data['video_path'],
                video_data['duration_seconds'],
                video_data['file_size_mb'],
                video_data['thumbnail_path'],
                video_data.get('telegram_file_id', ''),
                video_data.get('telegram_preview_id', ''),
                video_data['pack_id'],
                video_data['pack_only']
            ))
            manager.conn.commit()
            videos_salvos.append(video_data['video_id'])
            print(f"✅ Vídeo salvo: {video_data['title']}")
        except Exception as e:
            print(f"❌ Erro ao salvar vídeo {video_data['video_id']}: {e}")
    
    # ===== 2. DEPOIS: Salvar o PACK na tabela video_packs =====
    if videos_salvos:
        try:
            cursor = manager.conn.cursor()
            cursor.execute('''
                INSERT INTO video_packs 
                (pack_id, title, description, price_brl, thumbnail_path, video_ids)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                pack_id,
                title,
                description,
                pack_price,
                thumbnail_path,
                ','.join(videos_salvos)  # Lista de IDs como string
            ))
            manager.conn.commit()
            
            print(f"\n✅ PACK CRIADO COM SUCESSO!")
            print(f"ID: {pack_id}")
            print(f"Título: {title}")
            print(f"Preço: R$ {pack_price:.2f}")
            print(f"Vídeos: {len(videos_salvos)}")
            
        except Exception as e:
            print(f"❌ Erro ao salvar pack: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("❌ Nenhum vídeo foi salvo, pack não criado.")

def main():
    """Função principal."""
    print("\n" + "="*70)
    print("📦 CRIADOR DE PACKS DIRETO")
    print("="*70)
    print("📌 COMO FUNCIONA:")
    print("1. 🔍 Escaneia TODAS as subpastas dentro de 'videos/'")
    print("2. 📦 CRIA 1 PACK para CADA subpasta")
    print("3. 🎬 Processa TODOS os vídeos da pasta")
    print("4. 💰 Pergunta o PREÇO DO PACK")
    print("5. ✅ Salva PACK + VÍDEOS no banco")
    print("="*70)
    
    resp = input("\n❓ Continuar? (s/n): ").strip().lower()
    if resp != 's':
        print("🚫 Cancelado.")
        return
    
    criar_pack_direto()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n🚫 Interrompido pelo usuário")
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()
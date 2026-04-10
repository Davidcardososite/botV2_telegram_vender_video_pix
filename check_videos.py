import sqlite3

def check_videos():
    conn = sqlite3.connect('videos.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print("📊 VERIFICANDO VÍDEOS NO BANCO DE DADOS")
    print("="*50)
    
    cursor.execute("SELECT * FROM videos")
    videos = cursor.fetchall()
    
    if not videos:
        print("❌ Nenhum vídeo encontrado no banco!")
        return
    
    for i, video in enumerate(videos, 1):
        print(f"\n{i}. {video['title']}")
        print(f"ID: {video['video_id']}")
        print(f"Ativo: {'✅' if video['is_active'] else '❌'}")
        print(f"Caminho: {video['video_path']}")
        print(f"Prévia: {video['preview_path']}")
    
    print(f"\nTotal: {len(videos)} vídeo(s)")
    conn.close()

if __name__ == '__main__':
    check_videos()
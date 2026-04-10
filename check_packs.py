import sqlite3

def check_packs():
    conn = sqlite3.connect('videos.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print("📊 VERIFICANDO PACKS NO BANCO DE DADOS")
    print("="*50)
    
    cursor.execute("SELECT * FROM video_packs")
    packs = cursor.fetchall()
    
    if not packs:
        print("❌ Nenhum pack encontrado no banco!")
        return
    
    for i, pack in enumerate(packs, 1):
        print(f"\n{i}. {pack['title']}")
        print(f"ID: {pack['pack_id']}")
        print(f"Ativo: {'✅' if pack['is_active'] else '❌'}")
        print(f"Descrição: {pack['description']}")
    
    print(f"\nTotal: {len(packs)} packs (s)")
    conn.close()

if __name__ == '__main__':
    check_packs()
import sqlite3
import os
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class VideoManager:
    """Gerencia vídeos disponíveis para venda."""
    
    def __init__(self, db_path: str = 'videos.db'):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_database()
    
    def _init_database(self):
        """Cria as tabelas para vídeos."""
        cursor = self.conn.cursor()

        # TABELA DE PACKS 
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS video_packs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pack_id TEXT UNIQUE,
                title TEXT NOT NULL,
                description TEXT,
                price_brl REAL NOT NULL,
                thumbnail_path TEXT,
                video_ids TEXT,  -- IDs separados por vírgula
                discount_percent INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # TABELA DE VÍDEOS DE PACK
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pack_videos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                video_id TEXT UNIQUE,
                title TEXT NOT NULL,
                description TEXT,
                price_brl REAL NOT NULL,
                preview_path TEXT NOT NULL, 
                video_path TEXT NOT NULL,    
                duration_seconds INTEGER,    
                file_size_mb REAL,           
                thumbnail_path TEXT,         
                telegram_file_id TEXT,       
                telegram_preview_id TEXT,    
                pack_id TEXT NOT NULL,
                pack_only INTEGER DEFAULT 1,  -- 1 = exclusivo de pack       
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # TABELA DE PACKS COMPRADOS
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS purchased_packs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                pack_id TEXT NOT NULL,
                order_id TEXT,
                payment_id TEXT,
                purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (pack_id) REFERENCES video_packs (pack_id),
                UNIQUE(user_id, pack_id)
            )
        ''')
        
        # Tabela de vídeos disponíveis
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS videos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                video_id TEXT UNIQUE,
                title TEXT NOT NULL,
                description TEXT,
                price_brl REAL NOT NULL,
                preview_path TEXT NOT NULL, 
                video_path TEXT NOT NULL,    
                duration_seconds INTEGER,    
                file_size_mb REAL,           
                thumbnail_path TEXT,         
                telegram_file_id TEXT,       
                telegram_preview_id TEXT,    
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabela de vídeos comprados
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS purchased_videos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                video_id TEXT NOT NULL,
                order_id TEXT,
                payment_id TEXT,
                purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (video_id) REFERENCES videos (video_id),
                UNIQUE(user_id, video_id)
            )
        ''')
        
        # Tabela de pagamentos
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                video_id TEXT,
                pack_id TEXT,
                amount_brl REAL,
                payment_method TEXT,
                payment_status TEXT,
                order_id TEXT,
                pix_code TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (video_id) REFERENCES videos (video_id),
                FOREIGN KEY (pack_id) REFERENCES video_packs (pack_id)
            )
        ''')
        
        self.conn.commit()

    # MÉTODOS PARA PACKS
    def has_purchased_pack(self, user_id: str, pack_id: str) -> bool:
        """Verifica se usuário já comprou o pack."""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT 1 FROM purchased_packs 
                WHERE user_id = ? AND pack_id = ?
            ''', (user_id, pack_id))
            
            return cursor.fetchone() is not None
        except Exception as e:
            logger.error(f"Erro ao verificar compra de pack: {e}")
            return False

    def get_pack_video(self, video_id: str) -> Optional[Dict]:
        """Obtém informações de um vídeo de pack (da tabela pack_videos)."""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT * FROM pack_videos 
                WHERE video_id = ? AND is_active = 1
            ''', (video_id,))
            
            result = cursor.fetchone()
            if result:
                return dict(result)
            return None
        except Exception as e:
            logger.error(f"Erro ao buscar pack video: {e}")
            return None
    
    def get_pack_videos_by_pack_id(self, pack_id: str) -> List[Dict]:
        """Obtém todos os vídeos de um pack específico."""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM pack_videos 
            WHERE pack_id = ? AND is_active = 1
            ORDER BY video_id
        ''', (pack_id,))
        return [dict(row) for row in cursor.fetchall()]
    
    def update_pack_video_file_id(self, video_id: str, file_id: str, is_preview: bool = False):
        """Atualiza file_id do Telegram para vídeo de pack."""
        try:
            cursor = self.conn.cursor()
            if is_preview:
                cursor.execute('''
                    UPDATE pack_videos SET telegram_preview_id = ?
                    WHERE video_id = ?
                ''', (file_id, video_id))
            else:
                cursor.execute('''
                    UPDATE pack_videos SET telegram_file_id = ?
                    WHERE video_id = ?
                ''', (file_id, video_id))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Erro ao atualizar file_id de pack video: {e}")
            return False
    
    def add_pack(self, pack_data: Dict) -> bool:
        """Adiciona um novo pack de vídeos."""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO video_packs 
                (pack_id, title, description, price_brl, 
                 thumbnail_path, video_ids, discount_percent)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                pack_data['pack_id'],
                pack_data['title'],
                pack_data.get('description', ''),
                pack_data['price_brl'],
                pack_data.get('thumbnail_path', ''),
                ','.join(pack_data['video_ids']),  # IDs como string separada por vírgula
                pack_data.get('discount_percent', 0)
            ))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Erro ao adicionar pack: {e}")
            return False
        
    def get_pack(self, pack_id: str) -> Optional[Dict]:
        """Obtém informações de um pack"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM video_packs 
            WHERE pack_id = ? AND is_active = 1
        ''', (pack_id,))
        
        result = cursor.fetchone()
        if result:
            pack_dict = dict(result)
            # Converte string de vídeos para lista
            pack_dict['video_ids'] = pack_dict['video_ids'].split(',') if pack_dict['video_ids'] else []
            
            # Busca os vídeos DA TABELA PACK_VIDEOS, NÃO da tabela videos
            pack_dict['videos'] = self.get_pack_videos_by_pack_id(pack_id)
            
            # Calcula o valor total INDIVIDUAL (preço de cada vídeo)
            total_individual = 0
            for video in pack_dict['videos']:
                total_individual += video['price_brl']
            
            # Se não encontrou vídeos na tabela pack_videos, tenta calcular dos video_ids (fallback)
            if total_individual == 0 and pack_dict['video_ids']:
                for video_id in pack_dict['video_ids']:
                    video = self.get_video(video_id.strip())  # Fallback para tabela antiga
                    if video:
                        total_individual += video['price_brl']
            
            pack_dict['total_individual'] = total_individual
            
            # Calcula economia
            if total_individual > 0:
                savings = total_individual - pack_dict['price_brl']
                savings_percent = (savings / total_individual) * 100
                pack_dict['savings'] = round(savings_percent, 1)
                pack_dict['savings_amount'] = round(savings, 2)
            else:
                pack_dict['savings'] = 0
                pack_dict['savings_amount'] = 0
            
            pack_dict['video_count'] = len(pack_dict['video_ids'])
            return pack_dict
        return None
    
    def get_all_packs(self) -> List[Dict]:
        """Obtém todos os packs ativos."""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM video_packs 
            WHERE is_active = 1
            ORDER BY created_at DESC
        ''')
        
        packs = []
        for row in cursor.fetchall():
            pack_dict = dict(row)
            pack_dict['video_ids'] = pack_dict['video_ids'].split(',') if pack_dict['video_ids'] else []
            
            # REUTILIZA O MESMO MÉTODO get_pack() para cada pack
            pack_completo = self.get_pack(pack_dict['pack_id'])
            if pack_completo:
                pack_dict['total_individual'] = pack_completo.get('total_individual', 0)
                pack_dict['savings'] = pack_completo.get('savings', 0)
                pack_dict['savings_amount'] = pack_completo.get('savings_amount', 0)
                pack_dict['video_count'] = pack_completo.get('video_count', 0)
            else:
                pack_dict['total_individual'] = 0
                pack_dict['savings'] = 0
                pack_dict['savings_amount'] = 0
                pack_dict['video_count'] = len(pack_dict['video_ids'])
            
            packs.append(pack_dict)
        
        return packs
    
    def record_pack_purchase(self, user_id: str, pack_id: str, order_id: str = None) -> bool:
        """Registra compra de um pack"""
        try:
            cursor = self.conn.cursor()
            
            # 1. Registra a compra do pack
            cursor.execute('''
                INSERT OR REPLACE INTO purchased_packs 
                (user_id, pack_id, order_id)
                VALUES (?, ?, ?)
            ''', (user_id, pack_id, order_id))
            
            # 2. Busca os vídeos do pack NA TABELA CORRETA (pack_videos)
            pack = self.get_pack(pack_id)
            if pack and pack.get('video_ids'):
                for video_id in pack['video_ids']:
                    # Verifica se o vídeo existe na tabela pack_videos
                    cursor.execute('''
                        SELECT 1 FROM pack_videos WHERE video_id = ? AND is_active = 1
                    ''', (video_id.strip(),))
                    
                    if cursor.fetchone():
                        # Registra a compra do vídeo do pack
                        cursor.execute('''
                            INSERT OR REPLACE INTO purchased_videos 
                            (user_id, video_id, order_id)
                            VALUES (?, ?, ?)
                        ''', (user_id, video_id.strip(), order_id))
                        print(f"✅ Vídeo do pack registrado: {video_id}")
            
            self.conn.commit()
            print(f"✅ Pack purchase recorded for user {user_id}, pack {pack_id}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao registrar compra de pack: {e}")
            import traceback
            traceback.print_exc()
            return False
    



    # MÉTODOS PARA VIDEOS INDIVIDUAIS
    def has_purchased(self, user_id: str, video_id: str) -> bool:
        """Verifica se usuário já comprou o vídeo"""
        cursor = self.conn.cursor()
        
        # Verifica se é vídeo de pack
        if video_id.startswith('pack_video_') or video_id.startswith('pkv_'):
            # Vídeo de pack - verifica se comprou o pack
            cursor.execute('''
                SELECT 1 FROM pack_videos pv
                JOIN purchased_packs pp ON pv.pack_id = pp.pack_id
                WHERE pv.video_id = ? AND pp.user_id = ?
            ''', (video_id, user_id))
        else:
            # Vídeo individual
            cursor.execute('''
                SELECT 1 FROM purchased_videos 
                WHERE user_id = ? AND video_id = ?
            ''', (user_id, video_id))
        
        return cursor.fetchone() is not None
    
    def add_video(self, video_data: Dict) -> bool:
        """Adiciona um novo vídeo para venda."""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO videos 
                (video_id, title, description, price_brl, 
                 preview_path, video_path, duration_seconds,
                 file_size_mb, thumbnail_path, telegram_file_id,
                 telegram_preview_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                video_data['video_id'],
                video_data['title'],
                video_data.get('description', ''),
                video_data['price_brl'],
                video_data['preview_path'],
                video_data['video_path'],
                video_data.get('duration_seconds', 0),
                video_data.get('file_size_mb', 0),
                video_data.get('thumbnail_path', ''),
                video_data.get('telegram_file_id', ''),
                video_data.get('telegram_preview_id', '')
            ))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Erro ao adicionar vídeo: {e}")
            return False
    
    def get_video(self, video_id: str) -> Optional[Dict]:
        """Obtém informações de um vídeo."""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM videos 
            WHERE video_id = ? AND is_active = 1
        ''', (video_id,))
        
        result = cursor.fetchone()
        if result:
            video_dict = dict(result)
            # Verifica se arquivos existem
            video_dict['preview_exists'] = os.path.exists(video_dict['preview_path'])
            video_dict['video_exists'] = os.path.exists(video_dict['video_path'])
            return video_dict
        return None
    
    def get_all_videos(self) -> List[Dict]:
        """Obtém APENAS vídeos INDIVIDUAIS (NÃO vídeos de pack)."""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM videos 
            WHERE is_active = 1
            ORDER BY created_at DESC
        ''')
        
        videos = []
        for row in cursor.fetchall():
            video_dict = dict(row)
            video_dict['preview_exists'] = os.path.exists(video_dict['preview_path'])
            video_dict['video_exists'] = os.path.exists(video_dict['video_path'])
            videos.append(video_dict)
        
        return videos
    
    def record_purchase(self, user_id: str, video_id: str, order_id: str = None) -> bool:
        """Registra uma compra de vídeo."""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO purchased_videos 
                (user_id, video_id, order_id)
                VALUES (?, ?, ?)
            ''', (user_id, video_id, order_id))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Erro ao registrar compra: {e}")
            return False

    def get_user_purchases(self, user_id: str) -> List[Dict]:
        """Obtém todos os vídeos comprados pelo usuário"""
        cursor = self.conn.cursor()
        
        # Busca vídeos individuais (da tabela videos)
        cursor.execute('''
            SELECT v.*, p.purchased_at 
            FROM videos v
            JOIN purchased_videos p ON v.video_id = p.video_id
            WHERE p.user_id = ? AND v.is_active = 1
            ORDER BY p.purchased_at DESC
        ''', (user_id,))
        
        purchases = [dict(row) for row in cursor.fetchall()]
        
        # Se quiser mostrar também os vídeos de pack comprados (opcional)
        # Descomente se quiser que apareçam em "Meus Vídeos"
        
        cursor.execute('''
            SELECT pv.*, pp.purchased_at 
            FROM pack_videos pv
            JOIN purchased_packs pp ON pv.pack_id = pp.pack_id
            WHERE pp.user_id = ?
            ORDER BY pp.purchased_at DESC
        ''', (user_id,))
        
        pack_videos = [dict(row) for row in cursor.fetchall()]
        purchases.extend(pack_videos)
       
        return purchases
    
    def update_telegram_file_id(self, video_id: str, file_id: str, is_preview: bool = False):
        """Atualiza file_id do Telegram para vídeo ou prévia."""
        try:
            cursor = self.conn.cursor()
            if is_preview:
                cursor.execute('''
                    UPDATE videos SET telegram_preview_id = ?
                    WHERE video_id = ?
                ''', (file_id, video_id))
            else:
                cursor.execute('''
                    UPDATE videos SET telegram_file_id = ?
                    WHERE video_id = ?
                ''', (file_id, video_id))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Erro ao atualizar file_id: {e}")
            return False

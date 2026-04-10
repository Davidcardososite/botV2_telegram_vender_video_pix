
import os
import subprocess
import logging

logger = logging.getLogger(__name__)

class VideoProcessor:
    """Processa vídeos para criar prévias borradas."""
    
    @staticmethod
    def create_blurred_preview(input_path: str, output_path: str, 
                               blur_strength: int = 15, 
                               preview_duration: int = 10) -> bool:
        """
        Cria uma prévia borrada do vídeo.
        
        Args:
            input_path: Caminho do vídeo original
            output_path: Caminho para salvar prévia
            blur_strength: Intensidade do blur (1-30)
            preview_duration: Duração da prévia em segundos
        
        Returns:
            True se sucesso, False se erro
        """
        try:
            # Verifica se arquivo existe
            if not os.path.exists(input_path):
                logger.error(f"Arquivo não encontrado: {input_path}")
                return False
            
            # Usa ffmpeg para criar prévia borrada
            cmd = [
                'ffmpeg',
                '-i', input_path,
                '-t', str(preview_duration),  # Duração da prévia
                '-vf', f'boxblur={blur_strength}:1',  # Aplicar blur
                '-c:v', 'libx264',
                '-preset', 'fast',
                '-crf', '28',  # Qualidade reduzida
                '-c:a', 'aac',
                '-b:a', '64k',
                '-y',  # Sobrescrever se existir
                output_path
            ]
            
            logger.info(f"Criando prévia borrada: {input_path} -> {output_path}")
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"Erro ffmpeg: {result.stderr}")
                return False
            
            # Verifica se arquivo foi criado
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                logger.info(f"Prévia criada com sucesso: {output_path}")
                return True
            else:
                logger.error("Arquivo de saída vazio ou não criado")
                return False
                
        except Exception as e:
            logger.error(f"Erro ao criar prévia: {e}")
            return False
    
    @staticmethod
    def extract_thumbnail(video_path: str, output_path: str, 
                         time_sec: float = 5) -> bool:
        """
        Extrai uma thumbnail do vídeo.
        
        Args:
            video_path: Caminho do vídeo
            output_path: Caminho para salvar thumbnail
            time_sec: Tempo em segundos para extrair frame
        
        Returns:
            True se sucesso, False se erro
        """
        try:
            cmd = [
                'ffmpeg',
                '-ss', str(time_sec),
                '-i', video_path,
                '-vframes', '1',
                '-vf', 'scale=320:-1',  # Redimensiona para largura 320px
                '-y',
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.returncode == 0
            
        except Exception as e:
            logger.error(f"Erro ao extrair thumbnail: {e}")
            return False
    
    @staticmethod
    def get_video_duration(video_path: str) -> float:
        """Obtém duração do vídeo em segundos."""
        try:
            cmd = [
                'ffprobe',
                '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                video_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            return float(result.stdout.strip())
        except:
            return 0
    
    @staticmethod
    def create_preview_with_watermark(video_path: str, output_path: str,
                                     watermark_text: str = "PRÉVIA") -> bool:
        """
        Cria prévia com marca d'água.
        """
        try:
            # Cria prévia de 15 segundos com marca d'água
            cmd = [
                'ffmpeg',
                '-i', video_path,
                '-t', '15',  # 15 segundos
                '-vf', f"drawtext=text='{watermark_text}':"
                       "fontcolor=white:fontsize=24:"
                       "box=1:boxcolor=black@0.5:"
                       "boxborderw=5:"
                       "x=(w-text_w)/2:y=(h-text_h)/2,"
                       f"boxblur=10:1",
                '-c:v', 'libx264',
                '-preset', 'fast',
                '-crf', '28',
                '-c:a', 'aac',
                '-b:a', '64k',
                '-y',
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.returncode == 0
            
        except Exception as e:
            logger.error(f"Erro ao criar prévia com watermark: {e}")
            return False
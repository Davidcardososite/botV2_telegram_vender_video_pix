
import os
import subprocess
from pathlib import Path

def otimizar_video(input_path, output_path=None, crf=23):
    """
    Otimiza vídeo para Telegram/WhatsApp
    """
    if output_path is None:
        output_path = input_path.replace('.mp4', '_otimizado.mp4')
    
    cmd = [
        'ffmpeg',
        '-i', input_path,
        '-vf', 'unsharp=5:5:0.8,eq=saturation=1.2',
        '-c:v', 'libx264',
        '-crf', str(crf),
        '-preset', 'medium',
        '-c:a', 'aac',
        '-b:a', '128k',
        '-movflags', '+faststart',
        '-y',
        output_path
    ]

    
    print(f"Processando: {os.path.basename(input_path)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        # Calcular redução de tamanho
        tamanho_original = os.path.getsize(input_path) / (1024 * 1024)
        tamanho_novo = os.path.getsize(output_path) / (1024 * 1024)
        reducao = ((tamanho_original - tamanho_novo) / tamanho_original) * 100
        
        print(f"✅ Concluído: {os.path.basename(output_path)}")
        print(f"   Original: {tamanho_original:.1f}MB")
        print(f"   Otimizado: {tamanho_novo:.1f}MB")
        print(f"   Redução: {reducao:.1f}%")
        return True
    else:
        print(f"❌ Erro: {result.stderr}")
        return False

# Processar todos vídeos MP4 da pasta atual
pasta_atual = Path("videos/Belle belinha")
arquivos_mp4 = list(pasta_atual.glob("*.mp4"))

print(f"Encontrados {len(arquivos_mp4)} arquivos MP4")

for arquivo in arquivos_mp4:
    if "_otimizado" not in arquivo.name:  # Evitar reprocessar
        otimizar_video(str(arquivo))

print("🎯 Processamento concluído!")
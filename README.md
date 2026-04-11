![Logo](images/bot.png)

<div align="center">
  
  ![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
  ![Telegram](https://img.shields.io/badge/Telegram-Bot-26A5E4.svg)
  ![FFmpeg](https://img.shields.io/badge/FFmpeg-blue.svg)
  ![Mercadopago](https://img.shields.io/badge/Mercadopago-yellow.svg)

  
</div>


```markdown
# 🤖 Bot Telegram para vender vídeos via PIX

Um bot simples do Telegram que permite vender vídeos individualmente e packs de vários vídeos via PIX.

## ✨ Funcionalidades

✅ Catálogo de vídeos - Lista organizada com paginação
✅ Sistema PIX completo - Usa Mercado Pago QR Code
✅ Entrega automática - Vídeo enviado após confirmação de pagamento
- 🎥 gerenciar vídeos
- ➕ adicionar vídeos
- ➕ adicionar pack de videos automaticamente
```


## 📋 Pré-requisitos

- Python 3.8 ou superior
- pip (gerenciador de pacotes)
- Token de Bot do Telegram ([@BotFather](https://t.me/BotFather))
- Token Mercado Pago https://www.mercadopago.com.br/developers/
- FFmpeg (para conversão de vídeos)

## 🔧 Instalação

### 1. Clone o repositório
```bash
git clone https://github.com/Davidcardososite/botV2_telegram_vender_video_pix.git
cd botV2_telegram_vender_video_pix
```

### 2. Crie um ambiente virtual (recomendado)
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows
```

### 3. Instale as dependências
```bash
pip install -r requirements.txt
pip install opencv-python pillow numpy
pip install python-telegram-bot mercadopago python-dotenv
```

### 4. Instale o FFmpeg

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install ffmpeg
```

**MacOS:**
```bash
brew install ffmpeg
```
**Termux:**
```bash
pkg install ffmpeg
```

**Windows:**
- Baixe do [site oficial do FFmpeg](https://ffmpeg.org/download.html)
- Adicione ao PATH do sistema

### 5. Configure o token do bot

**Opção 1: Variável de ambiente**
```bash
export TELEGRAM_BOT_TOKEN='seu_token_aqui'
export MERCADO_PAGO_TOKEN='seu_token_aqui'
```

**Opção 2: Arquivo .env** (recomendado)
```bash
echo "TELEGRAM_BOT_TOKEN=seu_token_aqui" > .env
echo "MERCADO_PAGO_TOKEN=seu_token_aqui" > .env
```


## 📁 Estrutura do Projeto
```
botV2_telegram_vender_video_pix/
├── .env
├── bot_videos.py             # Bot principal
├── renomear_arquivos.py      # renomeia todos os arquivos dentro de uma pasta
├── otimizar_videos.py        # Aumenta suavimente a nitidez e a saturação de videos(opcional)
├── mercado_pago_handler.py   # Pagamentos
├── video_manager.py          # Gerenciador de vídeos e packs
├── video_processor.py        # Processa vídeos
├── add_video.py              # Adiciona vídeos individuais
├── add_pack_auto.py          # Adiciona packs dentro de 'videos/'
├── README.md
├── requirements.txt
├── check_videos.py
├── previews/                 # Pré-vias borradas
├── videos/                   # Vídeos completos e sub pastas
    ├── video.mp4             # Vídeos individuais
    ├── pack/
        ├── video1.mp4
        ├── video2.mp4            
├── thumbnails/               # Thumbnails
└── pack_thumbs/              # Thumbnails de packs
```


**Observação importante: O opencv-python pode exigir dependências do sistema. No Ubuntu/Debian, você pode precisar instalar:**

```bash
sudo apt-get update
sudo apt-get install -y python3-opencv
Ou para instalação via pip apenas:
```

```bash
pip install opencv-python-headless  # Versão mais leve sem suporte a GUI
```

## Copie seus vídeos completos para a pasta videos/
```bash
cp /caminho/do/seu/video.mp4 botV2_telegram_vender_video_pix/videos/
```

## 🚀 Como usar # Siga as instruções interativas
```bash
cd botV2_telegram_vender_video_pix
```
```bash
python add_video.py
```
```bash
python add_pack_auto.py
 ```
**Executar o bot**
```bash
python bot_videos.py
```

```bash
`/start` para iniciar o bot no telegram
```

## Fluxo completo:
Usuário acessa /start → Vê menu com opção de ver prévias, Packs com desconto, Vídeos comprados

Clica em "Ver Prévia" → Recebe vídeo borrado de 10 segundos

Gostou do conteúdo? → Clica em "Comprar Vídeo Completo"

Paga via PIX QR Code → Bot verifica pagamento

Pagamento confirmado → Recebe vídeo completo sem borrão

Pode reassistir quando quiser → Acessa "Meus Vídeos"

## Recursos implementados:
```markdown
✅ Prévias borradas automáticas - Cria automaticamente do vídeo original
✅ Cache de file_id - Vídeos enviados rapidamente após primeira vez
✅ Thumbnails automáticas - Gera capa do vídeo
✅ Informações detalhadas - Duração, tamanho, descrição
✅ Sistema de pagamento - PIX com Mercado Pago
```

## 📞 Suporte e Contato

- 📧 Email: devdavid1998@gmail.com
- 💬 Telegram: [@david_cardoso01](https://t.me/david_cardoso01)

## 🙏 Agradecimentos

- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) - Framework PTB
- [FFmpeg](https://ffmpeg.org/) - Processamento de vídeo
- [@BotFather](https://t.me/BotFather) - Criação do bot
- [Mercado Pago developers](https://www.mercadopago.com.br/developers/)



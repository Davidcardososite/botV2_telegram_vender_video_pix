import os
from typing import Dict
import asyncio
import time
import logging
import traceback
from telegram.error import NetworkError, TimedOut
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes
)
from telegram.constants import ParseMode
from mercado_pago_handler import MercadoPagoPIX
from video_manager import VideoManager
from io import BytesIO
from datetime import datetime
import base64

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class VideoSalesBot:
    def __init__(self, telegram_token: str, mercado_pago_token: str):
        self.telegram_token = telegram_token
        self.mp_pix = MercadoPagoPIX(mercado_pago_token)
        self.video_manager = VideoManager()
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Menu principal."""
        user = update.effective_user
        
        welcome_text = """
🎬 *BOT DE VENDAS DE VÍDEOS EXCLUSIVOS*

📹 *Como funciona:*
1. 👁️ Veja a **PRÉVIA BORRADA** dos vídeos
2. 💰 Escolha o que quer comprar
3. 📱 Pague via PIX
4. ▶️ Receba o **VÍDEO COMPLETO** instantaneamente

🔥 *OFERTAS ESPECIAIS:*
• 📦 **Packs com até 50% de desconto!**
• 🎯 Compre vários vídeos de uma vez
• 💸 Economize bastante!

🔒 *Garantia:* Após o pagamento, os vídeos são seus para sempre!
"""
        
        keyboard = [
            [InlineKeyboardButton("👁️ Ver Prévia dos Vídeos", callback_data="catalog")],
            [InlineKeyboardButton("📦 Ver Packs com Desconto", callback_data="packs")],
            [InlineKeyboardButton("📦 Meus Vídeos Comprados", callback_data="my_videos")],
            [InlineKeyboardButton("💬 Suporte", url="https://t.me/PythonVideosExclusivos")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            welcome_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )

    async def show_packs(self, query):
        """Mostra packs de vídeos disponíveis"""
        packs = self.video_manager.get_all_packs()
        
        if not packs:
            await query.message.reply_text(
                "📭 *Nenhum pack disponível no momento.*\n\nVolte em breve para novas ofertas!",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        packs_text = "🔥 *PACKS COM DESCONTO* 🔥\n\n"
        packs_text += "*Compre vários vídeos e economize muito!*\n\n"
        
        keyboard = []
        for pack in packs:
            savings = pack.get('savings', 0)
            video_count = pack.get('video_count', 0)
            total_individual = pack.get('total_individual', 0)
            
            packs_text += f"📦 *{pack['title']}*\n"
            packs_text += f"💰 De: R$ {total_individual:.2f} **Por: R$ {pack['price_brl']:.2f}**\n"
            packs_text += f"🎬 {video_count} vídeos • 💰 Economize {savings:.1f}%\n\n"
            
            keyboard.append([
                InlineKeyboardButton(
                    f"📦 Ver Pack: {pack['title']}",
                    callback_data=f"pack_preview_{pack['pack_id']}"
                )
            ])
        
        keyboard.append([
            InlineKeyboardButton("👁️ Ver Vídeos Individuais", callback_data="catalog"),
            InlineKeyboardButton("🏠 Menu", callback_data="menu_main")
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # SIMPLES: Sempre envia nova mensagem, nunca tenta editar
        await query.message.reply_text(
            packs_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )

    async def _safe_edit_or_reply(self, query, text: str, parse_mode=None, reply_markup=None):
        """
        Tenta editar a mensagem, mas se falhar (por ser foto), envia nova mensagem.
        """
        try:
            # Tenta editar
            await query.edit_message_text(
                text=text,
                parse_mode=parse_mode,
                reply_markup=reply_markup
            )
            return True
        except Exception as e:
            logger.warning(f"Não pôde editar mensagem, enviando nova: {e}")
            try:
                # Envia nova mensagem
                await query.message.reply_text(
                    text=text,
                    parse_mode=parse_mode,
                    reply_markup=reply_markup
                )
                return False
            except Exception as e2:
                logger.error(f"Erro ao enviar nova mensagem: {e2}")
                return False

    def _calculate_original_price(self, pack: Dict) -> float:
        """Calcula preço total dos vídeos individualmente."""
        total = 0
        for video_id in pack.get('video_ids', []):
            video = self.video_manager.get_video(video_id.strip())
            if video:
                total += video['price_brl']
        return total
    
    async def show_pack_preview(self, query, pack_id: str):
        """Mostra detalhes de um pack"""
        pack = self.video_manager.get_pack(pack_id)
        
        if not pack:
            await query.message.reply_text(
                "❌ *Pack não encontrado.*",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # ============ BUSCA OS DADOS DO PACK ============
        video_count = pack.get('video_count', 0)
        total_individual = pack.get('total_individual', 0)
        savings_percent = pack.get('savings', 0)
        savings_amount = pack.get('savings_amount', 0)
        description = pack.get('description', '')
        
        # ============ CONSTRÓI O TEXTO ============
        pack_text = f"📦 *PACK: {pack['title']}*\n\n"
        
        # Descrição
        if description:
            if len(description) > 100:
                description = description[:97] + "..."
            pack_text += f"{description}\n\n"
        
        # Informações do pack
        pack_text += f"🎬 *VÍDEOS INCLUSOS:* {video_count} vídeos\n\n"
        pack_text += f"💰 *VALOR INDIVIDUAL:* R$ {total_individual:.2f}\n"
        pack_text += f"🔥 *VALOR DO PACK:* R$ {pack['price_brl']:.2f}\n"
        
        if savings_amount > 0:
            pack_text += f"💸 *ECONOMIA:* R$ {savings_amount:.2f} ({savings_percent:.1f}%)\n\n"
        else:
            pack_text += f"💸 *ECONOMIA:* {savings_percent:.1f}%\n\n"
        
        # Vantagens
        pack_text += "✅ *Vantagens:*\n"
        pack_text += "• Todos de uma vez • Economia • Download imediato"
        
        # ============ BOTÕES ============
        keyboard = [
            [InlineKeyboardButton(
                f"💰 COMPRAR PACK - R$ {pack['price_brl']:.2f}",
                callback_data=f"buy_pack_{pack_id}"
            )],
            [
                InlineKeyboardButton("📦 Ver Outros Packs", callback_data="packs"),
                InlineKeyboardButton("👁️ Ver Vídeos", callback_data="catalog"),
                InlineKeyboardButton("🏠 Menu", callback_data="menu_main")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # ============ ENVIA COM THUMBNAIL ============
        if pack.get('thumbnail_path') and os.path.exists(pack['thumbnail_path']):
            try:
                with open(pack['thumbnail_path'], 'rb') as thumb_file:
                    await query.message.reply_photo(
                        photo=thumb_file,
                        caption=pack_text[:1024],  # Limite do Telegram
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=reply_markup
                    )
                    
                    # Envia lista de vídeos separadamente
                    await self._send_pack_video_list(query, pack)
                    return
                    
            except Exception as e:
                print(f"⚠️ Erro ao enviar thumbnail: {e}")
        
        # ============ FALLBACK: SÓ TEXTO ============
        await query.message.reply_text(
            pack_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
        
        # Envia lista de vídeos separadamente
        await self._send_pack_video_list(query, pack)
        
    async def _send_pack_video_list(self, query, pack):
        """Envia lista de vídeos do pack - USANDO pack_videos."""
        if not pack or not pack.get('video_ids'):
            return
        
        # Busca os vídeos da tabela pack_videos
        videos_text = "🎬 *LISTA DE VÍDEOS INCLUSOS:*\n\n"
        videos_encontrados = 0
        
        for i, video_id in enumerate(pack.get('video_ids', []), 1):
            # USA o novo método get_pack_video()
            video = self.video_manager.get_pack_video(video_id.strip())
            if video:
                minutes = video['duration_seconds'] // 60
                seconds = video['duration_seconds'] % 60
                videos_text += f"{i}. {video['title']} ({minutes}:{seconds:02d})\n"
                videos_encontrados += 1
        
        if videos_encontrados == 0:
            videos_text = "📹 *Os vídeos deste pack estão sendo processados...*"
        
        # Se lista muito longa, divide
        if len(videos_text) > 4000:
            parts = [videos_text[i:i+4000] for i in range(0, len(videos_text), 4000)]
            for part in parts:
                await query.message.reply_text(
                    part,
                    parse_mode=ParseMode.MARKDOWN
                )
        else:
            await query.message.reply_text(
                videos_text,
                parse_mode=ParseMode.MARKDOWN
            )

    async def initiate_pack_purchase(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Inicia processo de compra de pack."""
        query = update.callback_query
        
        # IMPORTANTE: NUNCA tente editar a mensagem aqui
        # Sempre envie uma nova mensagem
        await query.answer()
        
        data = query.data
        pack_id = data.replace("buy_pack_", "")
        user_id = str(query.from_user.id)
        
        print(f"🚀 Iniciando compra do pack: {pack_id}")
        print(f"👤 Usuário: {user_id}")
        
        pack = self.video_manager.get_pack(pack_id)
        if not pack:
            print(f"❌ Pack não encontrado: {pack_id}")
            await query.message.reply_text(
                "❌ *Pack não encontrado.*",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # Verificar se já comprou
        if self.video_manager.has_purchased_pack(user_id, pack_id):
            print(f"✅ Usuário já possui este pack")
            keyboard = [[
                InlineKeyboardButton("📦 Ver Meus Vídeos", callback_data="my_videos"),
                InlineKeyboardButton("📦 Ver Outros Packs", callback_data="packs")
            ]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # SEMPRE envie nova mensagem
            await query.message.reply_text(
                f"✅ *Você já possui este pack!*\n\n"
                f"📦 *{pack['title']}*\n\n"
                f"Todos os vídeos já estão disponíveis na sua biblioteca.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
            return
        
        print(f"💰 Criando pagamento para pack: {pack['title']}")
        print(f"💵 Valor: R$ {pack['price_brl']:.2f}")
        
        # Criar pagamento
        amount = pack['price_brl']
        
        try:
            # Cria pagamento PIX
            result = self.mp_pix.create_pix_payment(
                user_id=user_id,
                video_price=amount
            )
            
            if not result['success']:
                error_msg = result.get('error', 'Erro desconhecido')
                print(f"❌ Erro no pagamento: {error_msg}")
                
                # SEMPRE envie nova mensagem
                await query.message.reply_text(
                    f"❌ *Erro no pagamento:*\n\n`{error_msg}`",
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            
            pix_data = result['data']
            print(f"✅ pix_data: {pix_data}")
            print(f"📅 data_criada: {pix_data['last_updated_date']}")
            print(f"📅 data_da_última_atualização: {pix_data['created_date']}")
            print(f"📅 data_de_expiração: {pix_data['date_of_expiration']}")
            print(f"📦 Order ID: {pix_data['order_id']}")
            print(f"🕣 Status: {pix_data['status']}")
            print(f"📊 status_detalhe: {pix_data['status_detail']}")
            print(f"🔐 pix_code: {pix_data['pix_code']}")
            print(f"💰 Metodo de pagamento: {pix_data.get('payment_method', '')}")


            # Salva no banco
            cursor = self.video_manager.conn.cursor()
            cursor.execute('''
                INSERT INTO payments 
                (user_id, pack_id, amount_brl, payment_method, payment_status, 
                order_id, pix_code)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_id, pack_id, amount, pix_data['payment_method'],
                pix_data['status'], pix_data['order_id'], pix_data['pix_code']
            ))
            self.video_manager.conn.commit()
            print("💾 Pagamento salvo no banco")
            
            # Mensagem de pagamento
            mode_note = f"💰 *Valor:* R$ {amount:.2f}\n"
            instruction = "📱 *Pague via PIX e clique em '✅ Já Paguei'*"
            data_formatada = self.format_expiration_with_remaining(pix_data['date_of_expiration'])
            
            payment_message = (
                f"{mode_note}"
                f"📦 *PACK:* {pack['title']}\n\n"
                f"*ID do Pedido:* `{pix_data['order_id']}`\n\n"
                f"{instruction}\n\n"
                f"📋 *Código PIX:*\n"
                f"```\n{pix_data.get('pix_code', '')}\n```"
                f"📅 *Expira em:* `{data_formatada}`\n"
            )
            
            # Botões
            keyboard = [
                [
                    InlineKeyboardButton("✅ Já Paguei", 
                                    callback_data=f"confirm_pack_payment_{pix_data['order_id']}"),
                    InlineKeyboardButton("❌ Cancelar", 
                                    callback_data=f"cancel_pack_payment_{pix_data['order_id']}")
                ]
            ]

            
            keyboard.append([
                InlineKeyboardButton("🔗 Abrir Link PIX", url=pix_data.get('ticket_url', '#')),
                InlineKeyboardButton("💬 Ajuda", url="https://t.me/UserDavidCardoso")
            ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Enviar QR code se disponível
            if pix_data.get('pix_qr_code_base64'):
                try:
                    qr_data = pix_data['pix_qr_code_base64']
                    if qr_data.startswith('data:image'):
                        qr_data = qr_data.split(',')[1]
                    
                    qr_bytes = base64.b64decode(qr_data)
                    
                    print(f"🖼 Enviando QR code para pack")
                    await query.message.reply_photo(
                        photo=BytesIO(qr_bytes),
                        caption=payment_message[:1024],
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=reply_markup
                    )
                    return
                except Exception as e:
                    print(f"⚠️ QR code falhou: {e}")
            
            # SEMPRE envie nova mensagem (não edite)
            print(f"📤 Enviando mensagem de pagamento do pack")
            await query.message.reply_text(
                payment_message,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
            
        except Exception as e:
            print(f"❌ Exceção ao processar pagamento do pack: {e}")
            import traceback
            traceback.print_exc()
            
            # SEMPRE envie nova mensagem em caso de erro
            await query.message.reply_text(
                "❌ *Erro ao processar pagamento.*\n\n"
                "Tente novamente ou entre em contato com o suporte.",
                parse_mode=ParseMode.MARKDOWN
            )

    async def confirm_pack_payment(self, update: Update, context: ContextTypes.DEFAULT_TYPE, order_id: str):
        """Verifica e confirma pagamento de pack."""
        query = update.callback_query
        await query.answer("🔍 Verificando pagamento do pack...")
        user_id = str(query.from_user.id)
        print(f"✅ Order ID:{order_id}")
        
        # Verifica pagamento
        result = self.mp_pix.check_payment_status(order_id)
        
        print(f"🔍 Status do pagamento do pack: {result}")
        
        if not result.get('success'):
            error_msg = result.get('error', 'Erro desconhecido')
            try:
                await query.edit_message_text(
                    f"❌ *Erro ao verificar pagamento:*\n\n`{error_msg}`",
                    parse_mode=ParseMode.MARKDOWN
                )
            except:
                await query.message.reply_text(
                    f"❌ *Erro ao verificar pagamento:*\n\n`{error_msg}`",
                    parse_mode=ParseMode.MARKDOWN
                )
            return
        
        pagamento_data = result['data']
        print(f"✅ pagamento_data: {pagamento_data}")
        print(f"📦 Order ID: {pagamento_data['order_id']}")
        print(f"📊 Status encontrado: {pagamento_data['status']}")
        print(f"📊 status_detalhe: {pagamento_data['status_detail']}")
        print(f"📅 data_criada: {pagamento_data['last_updated_date']}")
        print(f"📅 data_da_última_atualização: {pagamento_data['created_date']}")
        print(f"📅 data_de_expiração: {pagamento_data['date_of_expiration']}")
        print(f"💰 Valor pago: {pagamento_data.get('paid_amount')}")
        
        payment_status = pagamento_data['status']
        payment_status_detail = pagamento_data['status_detail']
        
        # Status que indicam aprovação
        approved_statuses = ['processed']

        if payment_status in approved_statuses:
            # Pagamento aprovado!
            friendly_status = self.get_payment_status_message(payment_status, payment_status_detail)
            await self._process_pack_payment_approved(query, user_id, order_id, friendly_status["status_messages"],  
                friendly_status["status_detail_menssages"])
            

        elif payment_status == 'action_required':
            # O usuário precisa abrir o app do banco
            friendly_status = self.get_payment_status_message(payment_status, payment_status_detail)
            await self._show_pack_waiting_message(
                query, 
                order_id, 
                friendly_status["status_messages"],  
                friendly_status["status_detail_menssages"]
            )
            
        else:
            # Ainda não confirmado
            friendly_status = self.get_payment_status_message(payment_status_detail, payment_status_detail)
            await self._show_pack_waiting_message(
                query, 
                order_id, 
                friendly_status["status_messages"],  
                friendly_status["status_detail_menssages"]
            )

    async def _process_pack_payment_approved(self, query, user_id: str, order_id: str, status: str, status_detail: str):
        """Processa pagamento de pack aprovado."""
        # Obtém dados do pagamento
        cursor = self.video_manager.conn.cursor()
        cursor.execute('''
            SELECT pack_id FROM payments 
            WHERE order_id = ? AND user_id = ?
        ''', (order_id, user_id))
        
        payment = cursor.fetchone()
        if not payment:
            try:
                await query.edit_message_text(
                    "❌ *Pagamento não encontrado.*",
                    parse_mode=ParseMode.MARKDOWN
                )
            except:
                await query.message.reply_text(
                    "❌ *Pagamento não encontrado.*",
                    parse_mode=ParseMode.MARKDOWN
                )
            return
        
        pack_id = payment['pack_id']

        # Atualiza status do pagamento
        cursor.execute('''
            UPDATE payments 
            SET payment_status = 'processed'
            WHERE order_id = ?
        ''', (order_id,))

        
        # Registra a compra do pack
        self.video_manager.record_pack_purchase(user_id, pack_id, order_id)
        self.video_manager.conn.commit()
        

        # Mensagem de sucesso
        success_msg = (
            f"🎉 *🎉 *PAGAMENTO DO PACK CONFIRMADO!*\n\n"
            f"🎬 *Seu pack de videos será enviado agora...*\n\n"
            f"{status}\n"
            f"{status_detail}\n"
        )
        
        try:
            await query.edit_message_text(
                success_msg,
                parse_mode=ParseMode.MARKDOWN
            )
        except:
            await query.message.reply_text(
                success_msg,
                parse_mode=ParseMode.MARKDOWN
            )
        
        # Entrega o pack
        await self.deliver_pack(query, user_id, pack_id)

    async def _show_pack_waiting_message(self, query, order_id: str, status: str, status_detail: str):
        """Mostra mensagem de aguardando confirmação para pack."""
        
        keyboard = [
            [
                InlineKeyboardButton("🔄 Verificar Novamente", 
                                callback_data=f"confirm_pack_payment_{order_id}"),
                InlineKeyboardButton("❌ Cancelar", 
                                callback_data=f"cancel_pack_payment_{order_id}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # TIMESTAMP para garantir que o texto seja DIFERENTE
        timestamp = int(time.time())
        data_hora = datetime.fromtimestamp(timestamp).strftime('%d/%m/%Y %H:%M:%S')
        
        message = (
            f"⏳ *Aguardando confirmação...*\n\n"
            f"*Status:* {status}\n"
            f"*Detalhe:* {status_detail}\n"
            f"*Última verificação:* `{data_hora}`\n\n"
            f"💡 *O que fazer:*\n"
            f"• Aguarde processamento do banco\n"
            f"• Pode levar alguns minutos\n"
            f"• Clique em 'Verificar Novamente'"
        )
        
        try:
            await query.edit_message_text(
                message,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
        except Exception as e:
            logger.warning(f"Não pôde editar mensagem, enviando nova: {e}")
            await query.message.reply_text(
                message,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )

    async def cancel_pack_payment(self, query, order_id: str):
        """Cancela pagamento de pack."""
        print(f"🔄 PROCESSANDO CANCELAMENTO DE PACK - Order: {order_id}")
        print(f"👤 Usuário: {query.from_user.id}")
        user_id = str(query.from_user.id)
        print(f"DEBUG: User ID: {user_id}")
        
        # Atualiza status no banco
        cursor = self.video_manager.conn.cursor()
        cursor.execute('''
            UPDATE payments 
            SET payment_status = 'cancelled'
            WHERE order_id = ? AND user_id = ?
        ''', (order_id, user_id))
        self.video_manager.conn.commit()
        
        keyboard = [
            [
                InlineKeyboardButton("📦 Ver Packs", callback_data="packs"),
                InlineKeyboardButton("👁️ Ver Vídeos", callback_data="catalog"),
                InlineKeyboardButton("🏠 Menu", callback_data="menu_main")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        try:
            await query.edit_message_text(
                "❌ *Pagamento do pack cancelado.*\n\n"
                "Você pode tentar novamente quando quiser!",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
        except Exception as e:
            await query.message.reply_text(
                "❌ *Pagamento do pack cancelado.*\n\n"
                "Você pode tentar novamente quando quiser!",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )

    def _get_featured_pack(self):
        """Retorna um pack para destaque (ex: maior desconto)."""
        packs = self.video_manager.get_all_packs()
        if packs:
            # Retorna o pack com maior economia
            return max(packs, key=lambda x: x.get('savings', 0))
        return None

    async def deliver_pack(self, query, user_id: str, pack_id: str):
        """Entrega todos os vídeos do pack após pagamento"""
        pack = self.video_manager.get_pack(pack_id)
        
        if not pack:
            await query.message.reply_text(
                "❌ *Erro:* Pack não encontrado no sistema.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # Mensagem inicial
        delivery_text = (
            f"🎉 *PACK CONFIRMADO!*\n\n"
            f"📦 *{pack['title']}*\n\n"
            f"✅ Enviando {len(pack.get('video_ids', []))} vídeos...\n\n"
            f"⏳ Isso pode levar vários minutos para vídeos grandes.\n"
            f"💡 *Dica:* Aguarde o envio de todos os vídeos.\n"
            f"‼️*Atenção:* Baixe os vídeos para assistir offline!"
        )
        
        await query.message.reply_text(
            delivery_text,
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Busca os vídeos da tabela pack_videos
        video_count = 0
        failed_videos = []
        
        for video_id in pack.get('video_ids', []):
            # AGORA usa get_pack_video() em vez de get_video()
            video = self.video_manager.get_pack_video(video_id.strip())
            if video:
                try:
                    await asyncio.wait_for(
                        self.deliver_single_pack_video(query, video),
                        timeout=300
                    )
                    video_count += 1
                    await asyncio.sleep(3)
                    
                except asyncio.TimeoutError:
                    print(f"⏰ Timeout no vídeo: {video['title']}")
                    failed_videos.append(video['title'])
                    await query.message.reply_text(
                        f"⚠️ *Timeout no vídeo:* {video['title']}\n"
                        f"Este vídeo será enviado posteriormente.",
                        parse_mode=ParseMode.MARKDOWN
                    )
        
        # Confirmação final
        success_msg = (
            f"✅ *Entrega concluída!*\n\n"
            f"📦 {video_count} vídeos do pack *{pack['title']}* foram enviados.\n"
        )
        
        if failed_videos:
            success_msg += f"\n⚠️ *Vídeos com problemas:*\n"
            for v in failed_videos:
                success_msg += f"• {v}\n"
            success_msg += f"\nEntre em contato com o suporte para recebê-los."
        
        success_msg += (
            f"\n🎬 *Seus vídeos:* /myvideos\n"
            f"🔄 *Comprar mais:* /start\n\n"
            f"Aproveite! 🎬"
        )
        
        await query.message.reply_text(
            success_msg,
            parse_mode=ParseMode.MARKDOWN
        )

    async def deliver_single_pack_video(self, query, video: Dict):
        """Envia um único vídeo de pack"""
        try:
            if video.get('video_path') and os.path.exists(video['video_path']):
                file_size_mb = os.path.getsize(video['video_path']) / (1024 * 1024)
                
                print(f"📦 Enviando vídeo do pack: {video['title']}")
                print(f"📊 Tamanho: {file_size_mb:.1f} MB")
                
                if file_size_mb > 50:
                    print(f"⚠️ Vídeo muito grande: {file_size_mb:.1f} MB")
                    await query.message.reply_text(
                        f"⚠️ *Vídeo muito grande:* {video['title']}\n"
                        f"Entre em contato com o suporte.",
                        parse_mode=ParseMode.MARKDOWN
                    )
                    return
                
                # Tenta usar file_id salvo
                if video.get('telegram_file_id'):
                    await query.message.reply_video(
                        video=video['telegram_file_id'],
                        caption=f"🎬 {video['title']}",
                        supports_streaming=True
                    )
                else:
                    with open(video['video_path'], 'rb') as video_file:
                        sent_message = await query.message.reply_video(
                            video=video_file,
                            caption=f"🎬 {video['title']}",
                            supports_streaming=True,
                            duration=video.get('duration_seconds', 0)
                        )
                        
                        if sent_message.video:
                            self.video_manager.update_pack_video_file_id(
                                video['video_id'], 
                                sent_message.video.file_id, 
                                is_preview=False
                            )
        except Exception as e:
            print(f"⚠️ Erro ao enviar vídeo do pack: {e}")
            await query.message.reply_text(
                f"⚠️ *Erro ao enviar vídeo:* {video['title']}",
                parse_mode=ParseMode.MARKDOWN
            )
    
    async def show_catalog(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Mostra catálogo com prévias."""
        query = update.callback_query
        
        # Verifica se é uma callback query ou comando direto
        if query:
            await query.answer()
        
        videos = self.video_manager.get_all_videos()
        
        if not videos:
            message_text = "📭 *Nenhum vídeo disponível no momento.*\n\nVolte em breve para novas atualizações!"
            
            if query:
                try:
                    await query.edit_message_text(
                        message_text,
                        parse_mode=ParseMode.MARKDOWN
                    )
                except Exception as e:
                    # Se não conseguir editar, envia nova mensagem
                    await query.message.reply_text(
                        message_text,
                        parse_mode=ParseMode.MARKDOWN
                    )
            else:
                await update.message.reply_text(
                    message_text,
                    parse_mode=ParseMode.MARKDOWN
                )
            return
        
        # Divide os vídeos em páginas (ex: 10 vídeos por página)
        videos_per_page = 10
        total_pages = (len(videos) + videos_per_page - 1) // videos_per_page
        
        # Verifica se tem argumento de página
        page = 0
        if context.args:
            try:
                page = int(context.args[0]) - 1
                page = max(0, min(page, total_pages - 1))
            except:
                page = 0
        
        # Pega vídeos da página atual
        start_idx = page * videos_per_page
        end_idx = min(start_idx + videos_per_page, len(videos))
        page_videos = videos[start_idx:end_idx]
        
        # Constrói texto da página
        catalog_text = f"👁️ *PRÉVIAS DISPONÍVEIS* (Página {page + 1}/{total_pages})\n\n"
        catalog_text += "*Assista a prévia borrada e compre para ver o vídeo completo!*\n\n"
        
        # Contador global
        for i, video in enumerate(page_videos, start=start_idx + 1):
            minutes = video['duration_seconds'] // 60
            seconds = video['duration_seconds'] % 60
            
            catalog_text += f"{i}. *{video['title']}*\n"
            catalog_text += f"   💰 R$ {video['price_brl']:.2f} • ⏱️ {minutes}:{seconds:02d}\n\n"
        
        catalog_text += f"📊 *Total de vídeos:* {len(videos)}\n"
        catalog_text += f"📄 *Página:* {page + 1} de {total_pages}"
        
        # Botões de navegação
        keyboard = []
        
        # Botões para cada vídeo na página
        for video in page_videos:
            keyboard.append([
                InlineKeyboardButton(
                    f"👁️ Ver Prévia: {video['title']}",
                    callback_data=f"preview_{video['video_id']}"
                )
            ])
        
        # Botões de navegação entre páginas
        nav_buttons = []
        
        if page > 0:
            nav_buttons.append(InlineKeyboardButton(
                "⬅️ Página Anterior",
                callback_data=f"catalog_page_{page}"  # página anterior (0-based)
            ))
        
        if page < total_pages - 1:
            nav_buttons.append(InlineKeyboardButton(
                "Próxima Página ➡️",
                callback_data=f"catalog_page_{page + 2}"  # próxima página (1-based para usuário)
            ))
        
        if nav_buttons:
            keyboard.append(nav_buttons)
        
        keyboard.append([
            InlineKeyboardButton("🏠 Menu Principal", callback_data="menu_main"),
            InlineKeyboardButton("📦 Ver Packs", callback_data="packs")
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Envia ou edita a mensagem
        if query:
            try:
                await query.edit_message_text(
                    catalog_text,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=reply_markup
                )
            except Exception as e:
                # Se falhar ao editar, envia nova mensagem
                logger.warning(f"Não pôde editar mensagem, enviando nova: {e}")
                await query.message.reply_text(
                    catalog_text,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=reply_markup
                )
        else:
            await update.message.reply_text(
                catalog_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
    
    async def show_preview(self, query, video_id):
        """Mostra prévia borrada do vídeo."""
        print(f"DEBUG: Buscando vídeo com ID: {video_id}")
        
        video = self.video_manager.get_video(video_id)
        
        if not video:
            print(f"DEBUG: Vídeo NÃO encontrado no banco: {video_id}")
            try:
                await query.edit_message_text(
                    "❌ *Vídeo não encontrado.*\n\n"
                    "O vídeo pode ter sido removido ou estar temporariamente indisponível.",
                    parse_mode=ParseMode.MARKDOWN
                )
            except:
                await query.message.reply_text(
                    "❌ *Vídeo não encontrado.*\n\n"
                    "O vídeo pode ter sido removido ou estar temporariamente indisponível.",
                    parse_mode=ParseMode.MARKDOWN
                )
            return
        
        print(f"DEBUG: Vídeo encontrado: {video['title']}")
        
        # Mensagem informativa sobre a prévia
        preview_text = (
            f"👁️ *PRÉVIA BORRADA*\n\n"
            f"🎬 *{video['title']}*\n\n"
            f"📝 *Descrição:*\n{video['description']}\n\n"
            f"⏱️ *Duração total:* {video['duration_seconds']//60}:{video['duration_seconds']%60:02d}\n"
            f"📊 *Tamanho:* {video['file_size_mb']:.1f} MB\n\n"
            f"💰 *Preço do vídeo completo:* R$ {video['price_brl']:.2f}\n\n"
            f"⚠️ *Esta é apenas uma prévia borrada.*\n"
            f"Para ver o vídeo completo em alta qualidade, compre-o abaixo.\n"
        )
        
        keyboard = [
            [InlineKeyboardButton(
                f"💰 COMPRAR VÍDEO COMPLETO - R$ {video['price_brl']:.2f}",
                callback_data=f"buy_{video_id}"
            )],
            [
                InlineKeyboardButton("📺 Ver Mais Prévias", callback_data="catalog"),
                InlineKeyboardButton("🏠 Menu", callback_data="menu_main")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Tenta enviar a prévia borrada
        preview_sent = False
        
        # Primeiro, tenta usar file_id salvo
        if video.get('telegram_preview_id'):
            try:
                await query.message.reply_video(
                    video=video['telegram_preview_id'],
                    caption=preview_text,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=reply_markup
                )
                preview_sent = True
            except Exception as e:
                logger.warning(f"Não pôde usar file_id da prévia: {e}")
        
        # Se não conseguiu com file_id, tenta enviar arquivo local
        if not preview_sent and video.get('preview_path') and os.path.exists(video['preview_path']):
            try:
                with open(video['preview_path'], 'rb') as preview_file:
                    sent_message = await query.message.reply_video(
                        video=preview_file,
                        caption=preview_text,
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=reply_markup,
                        supports_streaming=True
                    )
                    
                    # Salva file_id para uso futuro
                    if sent_message.video:
                        self.video_manager.update_telegram_file_id(
                            video_id, 
                            sent_message.video.file_id, 
                            is_preview=True
                        )
                
                preview_sent = True
                
            except Exception as e:
                logger.error(f"Erro ao enviar prévia: {e}")
                # Fallback para texto
                try:
                    await query.edit_message_text(
                        f"{preview_text}\n\n"
                        f"⚠️ *Erro ao carregar prévia*\n"
                        f"Tente novamente ou entre em contato com o suporte.",
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=reply_markup
                    )
                except:
                    await query.message.reply_text(
                        f"{preview_text}\n\n"
                        f"⚠️ *Erro ao carregar prévia*\n"
                        f"Tente novamente ou entre em contato com o suporte.",
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=reply_markup
                    )
        
        # Fallback: se não tem prévia, mostra apenas informações
        if not preview_sent:
            try:
                await query.edit_message_text(
                    f"{preview_text}\n\n"
                    f"⚠️ *Prévia temporariamente indisponível*\n"
                    f"Você pode comprar o vídeo para ver o conteúdo completo.",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=reply_markup
                )
            except:
                await query.message.reply_text(
                    f"{preview_text}\n\n"
                    f"⚠️ *Prévia temporariamente indisponível*\n"
                    f"Você pode comprar o vídeo para ver o conteúdo completo.",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=reply_markup
                )

    def format_expiration_with_remaining(self, iso_string):
        """Formata data de expiração com tempo restante"""
        try:
            # Converte string ISO para datetime
            if iso_string.endswith('Z'):
                iso_string = iso_string.replace('Z', '+00:00')
            
            expiracao = datetime.fromisoformat(iso_string)
            agora = datetime.now(expiracao.tzinfo)  # Usa mesmo timezone
            
            # Formata data
            data_formatada = expiracao.strftime('%d/%m/%Y %H:%M:%S')
            
            # Calcula tempo restante
            tempo_restante = expiracao - agora
            horas = int(tempo_restante.total_seconds() // 3600)
            minutos = int((tempo_restante.total_seconds() % 3600) // 60)
            
            if horas > 0:
                tempo_msg = f"⏰ Expira em {horas}h {minutos}min"
            elif minutos > 0:
                tempo_msg = f"⏰ Expira em {minutos}min"
            else:
                tempo_msg = f"⏰ Expira em segundos"
            
            return f"{data_formatada} ({tempo_msg})"
            
        except Exception as e:
            logging.error(f"Erro ao formatar data: {e}")
            return str(iso_string)
    
    async def initiate_purchase(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Inicia processo de compra."""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        video_id = data.replace("buy_", "")
        user_id = str(query.from_user.id)
        
        video = self.video_manager.get_video(video_id)
        if not video:
            await query.edit_message_text(
                "❌ *Vídeo não encontrado.*",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # Verificar se já comprou
        if self.video_manager.has_purchased(user_id, video_id):
            # NÃO tenta editar - sempre envia nova mensagem
            keyboard = [[
                InlineKeyboardButton(
                    f"▶️ Assistir Vídeo",
                    callback_data=f"watch_{video_id}"
                )],
                [
                    InlineKeyboardButton("📺 Ver Catálogo", callback_data="catalog"),
                    InlineKeyboardButton("🏠 Menu", callback_data="menu_main")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.message.reply_text(
                f"✅ *Você já possui este vídeo!*\n\n"
                f"🎬 *{video['title']}*\n\n"
                f"Clique no botão abaixo para assistir novamente.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
            return
        
        amount = video['price_brl']
        
        try:
            # Cria pagamento PIX
            result = self.mp_pix.create_pix_payment(
                user_id=user_id,
                video_price=amount
            )
            
            if not result['success']:
                error_msg = result.get('error', 'Erro desconhecido')
                
                # Envia nova mensagem em vez de editar
                await query.message.reply_text(
                    f"❌ *Erro no pagamento:*\n\n`{error_msg}`\n\n"
                    f"Tente novamente ou entre em contato com o suporte.",
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            
            pix_data = result['data']
            print(f"✅ pix_data: {pix_data}")
            print(f"📅 data_criada: {pix_data['last_updated_date']}")
            print(f"📅 data_da_última_atualização: {pix_data['created_date']}")
            print(f"📅 data_de_expiração: {pix_data['date_of_expiration']}")
            print(f"📦 Order ID: {pix_data['order_id']}")
            print(f"🕣 Status: {pix_data['status']}")
            print(f"📊 status_detalhe: {pix_data['status_detail']}")
            print(f"🔐 pix_code: {pix_data['pix_code']}")
            print(f"💰 Metodo de pagamento: {pix_data.get('payment_method', '')}")
            
            # Salva no banco
            cursor = self.video_manager.conn.cursor()
            cursor.execute('''
                INSERT INTO payments 
                (user_id, video_id, amount_brl, payment_method, payment_status, 
                order_id, pix_code)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_id, video_id, amount, pix_data['payment_method'],
                pix_data['status'], pix_data['order_id'], pix_data['pix_code']
            ))
            self.video_manager.conn.commit()
            print("💾 Pagamento salvo no banco")
            
            # Mensagem de pagamento
            mode_note = f"💰 *Valor:* R$ {amount:.2f}\n"
            instruction = "📱 *Pague via PIX e clique em '✅ Já Paguei'*"
            data_formatada = self.format_expiration_with_remaining(pix_data['date_of_expiration'])
            
            payment_message = (
                f"{mode_note}"
                f"🎬 *VÍDEO:* {video['title']}\n\n"
                f"*ID do Pedido:* `{pix_data['order_id']}`\n\n"
                f"{instruction}\n\n"
                f"📋 *Código PIX:*\n"
                f"```\n{pix_data.get('pix_code', '')}\n```"
                f"📅 *Expira em:* `{data_formatada}`\n"
            )
            
            # Botões
            keyboard = [
                [
                    InlineKeyboardButton("✅ Já Paguei", 
                                    callback_data=f"confirm_payment_{pix_data['order_id']}"),
                    InlineKeyboardButton("❌ Cancelar", 
                                    callback_data=f"cancel_payment_{pix_data['order_id']}")
                ]
            ]
            
            
            keyboard.append([
                InlineKeyboardButton("🔗 Abrir Link PIX", url=pix_data.get('ticket_url', '#')),
                InlineKeyboardButton("💬 Ajuda", url="https://t.me/PythonVideosExclusivos")
            ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)

            # Tenta enviar QR code
            if pix_data.get('pix_qr_code_base64'):
                try:
                    qr_data = pix_data['pix_qr_code_base64']
                    
                    if qr_data.startswith('data:image'):
                        qr_data = qr_data.split(',')[1]
                    
                    qr_bytes = base64.b64decode(qr_data)
                    
                    await query.message.reply_photo(
                        photo=BytesIO(qr_bytes),
                        caption=payment_message[:1024],
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=reply_markup
                    )
                    return
                    
                except Exception as e:
                    print(f"⚠️ QR code falhou: {e}")
            
            # Envia nova mensagem em vez de editar
            await query.message.reply_text(
                payment_message,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )

        except Exception as e:
            print(f"❌ Exceção: {e}")
            import traceback
            traceback.print_exc()
            
            await query.edit_message_text(
                "❌ *Erro ao processar pagamento.*",
                parse_mode=ParseMode.MARKDOWN
            )
    
    async def confirm_payment(self, update: Update, context: ContextTypes.DEFAULT_TYPE, order_id):
        """Verifica e confirma pagamento."""
        query = update.callback_query
        await query.answer("🔍 Verificando pagamento...")
        
        data = query.data
        order_id = data.replace("confirm_payment_", "")
        print(f"✅ Order ID:{order_id}")
        user_id = str(query.from_user.id)
        
        # Verifica pagamento
        result = self.mp_pix.check_payment_status(order_id)
        print(f"🔍 Status do pagamento: {result}")
        
        if not result.get('success'):
            # Erro na verificação
            error_msg = result.get('error', 'Erro desconhecido')
            try:
                await query.edit_message_text(
                    f"❌ *Erro ao verificar pagamento:*\n\n`{error_msg}`",
                    parse_mode=ParseMode.MARKDOWN
                )
            except:
                await query.message.reply_text(
                    f"❌ *Erro ao verificar pagamento:*\n\n`{error_msg}`",
                    parse_mode=ParseMode.MARKDOWN
                )
            return
        
        pagamento_data = result['data']
        print(f"✅ pagamento_data: {pagamento_data}")
        print(f"📦 Order ID: {pagamento_data['order_id']}")
        print(f"📊 Status encontrado: {pagamento_data['status']}")
        print(f"📊 status_detalhe: {pagamento_data['status_detail']}")
        print(f"📅 data_criada: {pagamento_data['last_updated_date']}")
        print(f"📅 data_da_última_atualização: {pagamento_data['created_date']}")
        print(f"📅 data_de_expiração: {pagamento_data['date_of_expiration']}")
        print(f"💰 Valor pago: {pagamento_data.get('paid_amount')}")
        
        payment_status = pagamento_data['status']
        payment_status_detail = pagamento_data['status_detail']

        
        # Status que indicam aprovação
        approved_statuses = ['processed']
        
        if payment_status in approved_statuses:
            # Pagamento aprovado!
            friendly_status = self.get_payment_status_message(payment_status, payment_status_detail)
            await self._process_payment_approved(query, user_id, order_id, friendly_status["status_messages"],  
                friendly_status["status_detail_menssages"])
            
        elif payment_status == 'action_required':
            # O usuário precisa abrir o app do banco
            friendly_status = self.get_payment_status_message(payment_status, payment_status_detail)
            await self._show_waiting_message(
                query, 
                order_id, 
                friendly_status["status_messages"],  
                friendly_status["status_detail_menssages"]
            )
        else:
            # Ainda não confirmado
            friendly_status = self.get_payment_status_message(payment_status_detail, payment_status_detail)
            await self._show_waiting_message(
                query, 
                order_id, 
                friendly_status["status_messages"],  
                friendly_status["status_detail_menssages"]
            )

    def get_payment_status_message(self, status: str, status_detail: str) -> dict:
        """Retorna mensagem amigável para cada status."""
        status_detail_messages = {
            'waiting_transfer': "⏳ Aguardando transferência",
            'accredited': "✅ A transação foi processada com sucesso e o valor foi creditado efetivamente",
            'partially_refunded': "↩️ A transação foi processada com sucesso e parte do valor foi reembolsada",
            'created': "🔄 A transação foi criada com sucesso, mas ainda não foi processada",
            'in_process' : "🔄 Isso significa que a transação está em andamento e ainda não foi concluída",
            'pending_review_manual': "📲 aguardando revisão manual.",
        }
        
        status_messages = {
            'processing': "🔄 A transação está em andamento",
            'cancelled': "🚫 Pagamento cancelado",
            'refunded': "💸 Pagamento reembolsado",
            'charged_back': "↩️ Estorno realizado",
            'action_required': "📱 Ação necessária no app do banco",
            'rejected': "❌ Pagamento rejeitado",
            'processed': "✅ Pagamento processado com sucesso",
            'approved': "✅ Pagamento aprovado com sucesso",
            'authorized': "✅ Pagamento autorizado com sucesso"
        }
        
        return {
            "status_messages": status_messages.get(status, f"Status: {status}"),
            "status_detail_menssages": status_detail_messages.get(status_detail, f"Detalhe: {status_detail}"),
        }
    
    async def _show_waiting_message(self, query, order_id: str, status: str, status_detail: str):
        """Mostra mensagem de aguardando confirmação."""
        
        keyboard = [
            [
                InlineKeyboardButton("🔄 Verificar Novamente", 
                                callback_data=f"confirm_payment_{order_id}"),
                InlineKeyboardButton("❌ Cancelar", 
                                callback_data=f"cancel_payment_{order_id}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        timestamp = int(time.time())
        data_hora = datetime.fromtimestamp(timestamp).strftime('%d/%m/%Y %H:%M:%S')

        message = (
            f"⏳ *Aguardando confirmação...*\n\n"
            f"*Status:* {status}\n"
            f"*Detalhe:* {status_detail}\n"
            f"*Última verificação:* `{data_hora}`\n\n"
            f"💡 *O que fazer:*\n"
            f"• Aguarde processamento do banco\n"
            f"• Pode levar alguns minutos\n"
            f"• Clique em 'Verificar Novamente'"
        )
        
        try:
            await query.edit_message_text(
                message,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
        except Exception as e:
            logger.warning(f"Não pôde editar mensagem, enviando nova: {e}")
            await query.message.reply_text(
                message,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
    
    async def cancel_payment(self, query):
        """Cancela pagamento."""
        order_id = query.data.replace("cancel_payment_", "")
        user_id = str(query.from_user.id)
        
        # Atualiza status no banco
        cursor = self.video_manager.conn.cursor()
        cursor.execute('''
            UPDATE payments 
            SET payment_status = 'cancelled'
            WHERE order_id = ? AND user_id = ?
        ''', (order_id, user_id))
        self.video_manager.conn.commit()
        
        keyboard = [
            [
                InlineKeyboardButton("📺 Ver Catálogo", callback_data="catalog"),
                InlineKeyboardButton("🏠 Menu", callback_data="menu_main")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        try:
            await query.edit_message_text(
                "❌ *Pagamento cancelado.*\n\n"
                "Você pode tentar novamente quando quiser!",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
        except Exception as e:
            await query.message.reply_text(
                "❌ *Pagamento cancelado.*\n\n"
                "Você pode tentar novamente quando quiser!",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )

    async def _process_payment_approved(self, query, user_id: str, order_id: str, status: str, status_detail: str):
        """Processa pagamento aprovado."""
        # Obtém dados do pagamento
        cursor = self.video_manager.conn.cursor()
        cursor.execute('''
            SELECT video_id FROM payments 
            WHERE order_id = ? AND user_id = ?
        ''', (order_id, user_id))
        
        payment = cursor.fetchone()
        if not payment:
            try:
                await query.edit_message_text(
                    "❌ *Pagamento não encontrado.*",
                    parse_mode=ParseMode.MARKDOWN
                )
            except:
                await query.message.reply_text(
                    "❌ *Pagamento não encontrado.*",
                    parse_mode=ParseMode.MARKDOWN
                )
            return
        
        video_id = payment['video_id']
        
        # Atualiza status do pagamento
        cursor.execute('''
            UPDATE payments 
            SET payment_status = 'processed'
            WHERE order_id = ?
        ''', (order_id,))
        
        # Registra a compra
        self.video_manager.record_purchase(user_id, video_id, order_id)
        self.video_manager.conn.commit()
        
        # Mensagem de sucesso
        success_msg = (
            f"🎉 *PAGAMENTO CONFIRMADO!*\n\n"
            f"🎬 *Seu vídeo será enviado agora...*\n\n"
            f"{status}\n"
            f"{status_detail}\n"
        )
        
        try:
            await query.edit_message_text(
                success_msg,
                parse_mode=ParseMode.MARKDOWN
            )
        except:
            await query.message.reply_text(
                success_msg,
                parse_mode=ParseMode.MARKDOWN
            )
        
        # Entrega o vídeo
        await self.deliver_complete_video(query, user_id, video_id)

    async def show_my_videos_from_callback(self, query, context):
        """Mostra vídeos comprados via callback."""
        user_id = str(query.from_user.id)
        purchases = self.video_manager.get_user_purchases(user_id)
        
        if not purchases:
            try:
                await query.edit_message_text(
                    "📭 *Você ainda não comprou nenhum vídeo.*\n\n"
                    "Explore nosso catálogo para ver as opções disponíveis!",
                    parse_mode=ParseMode.MARKDOWN
                )
            except:
                await query.message.reply_text(
                    "📭 *Você ainda não comprou nenhum vídeo.*\n\n"
                    "Explore nosso catálogo para ver as opções disponíveis!",
                    parse_mode=ParseMode.MARKDOWN
                )
            return
        
        videos_text = "📦 *Meus Vídeos Comprados*\n\n"
        
        keyboard = []
        for video in purchases:
            purchase_date = datetime.fromisoformat(video['purchased_at'])
            formatted_date = purchase_date.strftime("%d/%m/%Y")
            
            videos_text += f"🎬 *{video['title']}*\n"
            videos_text += f"📅 Comprado em: {formatted_date}\n\n"
            
            keyboard.append([
                InlineKeyboardButton(
                    f"▶️ Assistir: {video['title'][:20]}...",
                    callback_data=f"watch_{video['video_id']}"
                )
            ])
        
        keyboard.append([
            InlineKeyboardButton("📺 Ver Catálogo", callback_data="catalog"),
            InlineKeyboardButton("🏠 Menu", callback_data="menu_main")
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        try:
            await query.edit_message_text(
                videos_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
        except:
            await query.message.reply_text(
                videos_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
                
    async def deliver_complete_video(self, query, user_id: str, video_id: str):
        """Entrega o vídeo completo após pagamento."""
        video = self.video_manager.get_video(video_id)
        
        if not video:
            await query.message.reply_text(
                "❌ *Erro:* Vídeo não encontrado no sistema.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # Mensagem de entrega
        delivery_text = (
            f"🎉 *COMPRA CONFIRMADA!*\n\n"
            f"⏱️ *Duração:* {video['duration_seconds']//60}:{video['duration_seconds']%60:02d}\n"
            f"📊 *Tamanho:* {video['file_size_mb']:.1f} MB\n\n"
            f"⚠️ *Atenção:* Baixe o vídeo para assistir offline! Você podera perder o video se o banco de dados de videos for atualizado"
        )
        
        # Envia mensagem informativa primeiro
        await query.message.reply_text(
            delivery_text,
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Envia o vídeo completo
        video_sent = False
        
        # Tenta usar file_id salvo
        if video.get('telegram_file_id'):
            try:
                await query.message.reply_video(
                    video=video['telegram_file_id'],
                    caption=f"🎬 {video['title']} - Vídeo Completo",
                    supports_streaming=True
                )
                video_sent = True
            except Exception as e:
                logger.warning(f"Não pôde usar file_id do vídeo: {e}")
        
        # Se não conseguiu com file_id, envia arquivo local
        if not video_sent and video.get('video_path') and os.path.exists(video['video_path']):
            try:
                # Envia vídeo completo
                with open(video['video_path'], 'rb') as video_file:
                    sent_message = await query.message.reply_video(
                        video=video_file,
                        caption=f"🎬 {video['title']} - Vídeo Completo",
                        supports_streaming=True,
                        width=1280,
                        height=720,
                        duration=video['duration_seconds']
                    )
                    
                    # Salva file_id para uso futuro
                    if sent_message.video:
                        self.video_manager.update_telegram_file_id(
                            video_id, 
                            sent_message.video.file_id, 
                            is_preview=False
                        )
                
                video_sent = True
                
            except Exception as e:
                logger.error(f"Erro ao enviar vídeo completo: {e}")
                await query.message.reply_text(
                    f"❌ *Erro ao enviar vídeo:*\n\n{e}\n\n"
                    f"Entre em contato com o suporte: @PythonVideosExclusivos. Ou clique em ✅ Já Paguei,🔄 Verificar Novamente",
                    parse_mode=ParseMode.MARKDOWN
                )
                return
        
        if video_sent:
            # Confirmação final
            await query.message.reply_text(
                f"✅ *Entrega concluída!*\n\n"
                f"O vídeo *{video['title']}* foi enviado com sucesso.\n\n"
                f"📦 *Seus vídeos:* /myvideos\n"
                f"🔄 *Comprar mais:* /start\n\n"
                f"Aproveite! 🎬",
                parse_mode=ParseMode.MARKDOWN
            )
    
    async def show_my_videos(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Mostra vídeos comprados pelo usuário."""
        user_id = str(update.effective_user.id)
        purchases = self.video_manager.get_user_purchases(user_id)
        
        if not purchases:
            await update.message.reply_text(
                "📭 *Você ainda não comprou nenhum vídeo.*\n\n"
                "Explore nosso catálogo para ver as opções disponíveis!",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        videos_text = "📦 *Meus Vídeos Comprados*\n\n"
        
        keyboard = []
        for video in purchases:
            # Formata data
            purchase_date = datetime.fromisoformat(video['purchased_at'])
            formatted_date = purchase_date.strftime("%d/%m/%Y")
            
            videos_text += f"🎬 *{video['title']}*\n"
            videos_text += f"📅 Comprado em: {formatted_date}\n\n"
            
            keyboard.append([
                InlineKeyboardButton(
                    f"▶️ Assistir: {video['title'][:20]}...",
                    callback_data=f"watch_{video['video_id']}"
                )
            ])
        
        keyboard.append([
            InlineKeyboardButton("📺 Ver Catálogo", callback_data="catalog"),
            InlineKeyboardButton("🏠 Menu", callback_data="menu_main")
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            videos_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
    
    async def watch_purchased_video(self, query, video_id):
        """Permite assistir vídeo já comprado."""
        user_id = str(query.from_user.id)
        
        if not self.video_manager.has_purchased(user_id, video_id):
            await query.edit_message_text(
                "❌ *Você não possui este vídeo.*\n\n"
                "Compre-o para poder assistir!",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # Reenvia o vídeo completo
        await self.deliver_complete_video(query, user_id, video_id)

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Processa os dados do callback."""
        query = update.callback_query

        try:
            await query.answer()
        except Exception as e:
            logger.warning(f"Erro ao responder callback: {e}")

        data = query.data
        print(f"📋 Processando callback: {data}")
        
        # ORDEM É IMPORTANTE! Verifique os mais específicos primeiro
        if data == "packs":
            await self.show_packs(query)
        elif data.startswith("pack_preview_"): 
            pack_id = data.replace("pack_preview_", "")
            await self.show_pack_preview(query, pack_id)
        elif data.startswith("buy_pack_"):  
            pack_id = data.replace("buy_pack_", "")
            print(f"🛒 Iniciando compra do pack: {pack_id}")
            await self.initiate_pack_purchase(update, context)
        elif data.startswith("confirm_pack_payment_"): 
            order_id = data.replace("confirm_pack_payment_", "")
            print(f"✅ Verificando pagamento do pack: {order_id}")
            await self.confirm_pack_payment(update, context, order_id)
        elif data.startswith("cancel_pack_payment_"):  
            order_id = data.replace("cancel_pack_payment_", "")
            print(f"❌ Cancelando pagamento do pack: {order_id}")
            await self.cancel_pack_payment(query, order_id)
        elif data == "menu_main":
            await self.start_from_callback(query)
        elif data == "catalog":
            # Mostra primeira página do catálogo
            context.args = ["1"]  # Página 1
            await self.show_catalog(update, context)
        elif data.startswith("catalog_page_"):
            # Navegação entre páginas do catálogo
            page_num = data.replace("catalog_page_", "")
            context.args = [page_num]
            await self.show_catalog(update, context)
        elif data.startswith("preview_"):
            video_id = data.replace("preview_", "")
            await self.show_preview(query, video_id)
        elif data.startswith("buy_"):
            video_id = data.replace("buy_", "")
            await self.initiate_purchase(update, context)
        elif data.startswith("confirm_payment_"):
            order_id = data.replace("confirm_payment_", "")
            await self.confirm_payment(update, context, order_id)
        elif data.startswith("cancel_payment_"):
            order_id = data.replace("cancel_payment_", "")
            await self.cancel_payment(query)
        elif data == "my_videos":
            await self.show_my_videos_from_callback(query, context) 
        elif data.startswith("watch_"):
            video_id = data.replace("watch_", "")
            await self.watch_purchased_video(query, video_id)
        else:
            print(f"⚠️ Callback não reconhecido: {data}")
            await query.message.reply_text(
                "❌ *Ação não reconhecida.*\n\nUse /start para voltar ao menu.",
                parse_mode=ParseMode.MARKDOWN
            )
    
    async def start_from_callback(self, query):
        """Menu principal via callback."""
        welcome_text = """
    🎬 *BOT DE VENDAS DE VÍDEOS EXCLUSIVOS*

    📹 *Como funciona:*
    1. 👁️ Veja a **PRÉVIA BORRADA** dos vídeos
    2. 💰 Escolha o que quer comprar
    3. 📱 Pague via PIX
    4. ▶️ Receba o **VÍDEO COMPLETO** instantaneamente

    🔥 *OFERTAS ESPECIAIS:*
    • 📦 **Packs com até 50% de desconto!**
    • 🎯 Compre vários vídeos de uma vez
    • 💸 Economize bastante!

    🔒 *Garantia:* Após o pagamento, os vídeos são seus para sempre!
    """
        
        keyboard = [
            [InlineKeyboardButton("👁️ Ver Prévia dos Vídeos", callback_data="catalog")],
            [InlineKeyboardButton("📦 Ver Packs com Desconto", callback_data="packs")],
            [InlineKeyboardButton("📦 Meus Vídeos Comprados", callback_data="my_videos")],
            [InlineKeyboardButton("💬 Suporte", url="https://t.me/PythonVideosExclusivos")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        try:
            await query.edit_message_text(
                welcome_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
        except Exception as e:
            # Se não conseguir editar, envia nova
            await query.message.reply_text(
                welcome_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )

    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler global de erros."""
        try:
            error = str(context.error)
            
            # Log do erro
            logger.error(f"Exception while handling an update: {context.error}")
            
            # Erros de rede
            if isinstance(context.error, (NetworkError, TimedOut)):
                print(f"🌐 Erro de rede detectado: {error}")
                
                # Se houver um update, tenta responder
                if update and update.effective_message:
                    try:
                        await update.effective_message.reply_text(
                            "⚠️ *Problema de conexão detectado.*\n"
                            "Tente novamente em alguns segundos.",
                            parse_mode=ParseMode.MARKDOWN
                        )
                    except:
                        pass
            
            # Outros erros
            else:
                print(f"❌ Erro não tratado: {error}")
                traceback.print_exc()
                
        except Exception as e:
            print(f"❌ Erro no handler de erros: {e}")
            traceback.print_exc()
    
    def run(self):
        """Inicia o bot."""
        # Configura timeouts muito maiores para conexão inicial
        application = Application.builder() \
            .token(self.telegram_token) \
            .read_timeout(60.0) \
            .write_timeout(60.0) \
            .connect_timeout(60.0) \
            .pool_timeout(60.0) \
            .build()
        
        # Handlers
        application.add_handler(CommandHandler("start", self.start))
        application.add_handler(CommandHandler("myvideos", self.show_my_videos))
        application.add_handler(CallbackQueryHandler(self.handle_callback))
        
        # Handler para mensagens de texto (para email se necessário)
        text_filter = filters.TEXT & ~filters.COMMAND
        application.add_handler(MessageHandler(text_filter, self.handle_text))

        # Handler de erro global
        application.add_error_handler(self.error_handler)
        
        print("🤖 Bot de vendas de vídeos (com prévias borradas) iniciado!")
        # Configura polling com timeouts
        try:
            # Tenta inicializar com retry
            application.run_polling(
                poll_interval=5.0,
                timeout=60,
                drop_pending_updates=True,
                allowed_updates=Update.ALL_TYPES,
                close_loop=False
            )
        except Exception as e:
            print(f"❌ Erro fatal ao iniciar bot: {e}")
            print("📡 Verifique sua conexão com a internet")
            print("🌐 Verifique se a API do Telegram está acessível")
            print("🔧 Tente novamente em alguns minutos")
    
    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Processa mensagens de texto (para coletar email se necessário)."""
        # Implementação básica para coletar email
        # Pode ser expandida conforme necessidade
        user_id = str(update.effective_user.id)
        text = update.message.text.strip()
        
        # Verifica se é um email válido (simplificado)
        if '@' in text and '.' in text:
            # Aqui você pode salvar o email no banco de dados
            await update.message.reply_text(
                f"✅ Email recebido: `{text}`\n\n"
                f"Obrigado! Continue com sua compra.",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await update.message.reply_text(
                "Por favor, use os botões do menu para navegar.\n"
                "Use /start para ver o menu principal."
            )

def main():
    """Função principal."""
    TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    MERCADO_PAGO_TOKEN = os.getenv('MERCADO_PAGO_TOKEN')

    
    if not TELEGRAM_TOKEN:
        print("❌ Configurações faltando no .env!")
        print("Verifique se você tem:")
        print("TELEGRAM_BOT_TOKEN=seu_token_aqui")
        print("export TELEGRAM_BOT_TOKEN='seu_token_aqui'")
        return
    if not MERCADO_PAGO_TOKEN:
        print("❌ Configurações faltando no .env!")
        print("MERCADO_PAGO_TOKEN=seu_token_mercado_pago")
        print("export MERCADO_PAGO_TOKEN='seu_token_aqui'")
        print("⚠️ AVISO: MERCADO_PAGO_TOKEN não encontrado.")
        return
    

    # Teste simples do token
    test_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getMe"
    print(f"🔍 Testando token em: {test_url}")
    
    try:
        import requests
        response = requests.get(test_url, timeout=10)
        if response.status_code == 200:
            print("✅ Token válido!")
            data = response.json()
            print(f"🤖 Bot: @{data['result']['username']}")
            print(f"📛 Nome: {data['result']['first_name']}")
        else:
            print(f"❌ Token inválido! Status: {response.status_code}")
            print(f"Resposta: {response.text}")
            return
    except Exception as e:
        print(f"❌ Erro ao testar token: {e}")
        return
    
    
    bot = VideoSalesBot(telegram_token=TELEGRAM_TOKEN, mercado_pago_token=MERCADO_PAGO_TOKEN)
    bot.run()

if __name__ == '__main__':
    main()
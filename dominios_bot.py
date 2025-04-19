import os
import json
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler, ContextTypes
from datetime import datetime, timedelta
import pandas as pd 
import requests
from bs4 import BeautifulSoup
import tempfile
import whois
from cryptography.fernet import Fernet
import pyfiglet

# Estados para la conversación
FECHA, OPCION, PALABRAS_CLAVE = range(3)

# Configuración de archivos
CREDENTIALS_FILE = "dominioswhoisbot_config.enc"
KEY_FILE = "dominioswhoisbot_key.key"

class DominiosWhoisBot:
    def __init__(self):
        self.token = None
        self.user_id = None
        self.cargar_credenciales()
        self.mostrar_banner()

    def mostrar_banner(self):
        """Muestra el banner ASCII art"""
        os.system('cls' if os.name == 'nt' else 'clear')
        print(pyfiglet.figlet_format("DominiosWhoisBot", font="slant"))
        print("🔍 Bot de búsqueda de dominios recientemente registrados")
        print("👨💻 Creado por @ivancastl | Telegram: t.me/+_g4DIczsuI9hOWZh")
        print("="*50 + "\n")

    def obtener_clave_encriptacion(self):
        """Genera o recupera la clave de encriptación"""
        if not os.path.exists(KEY_FILE):
            with open(KEY_FILE, "wb") as f:
                f.write(Fernet.generate_key())
        with open(KEY_FILE, "rb") as f:
            return f.read()

    def cargar_credenciales(self):
        """Carga las credenciales encriptadas"""
        if os.path.exists(CREDENTIALS_FILE):
            try:
                cipher_suite = Fernet(self.obtener_clave_encriptacion())
                with open(CREDENTIALS_FILE, "rb") as f:
                    encrypted_data = f.read()
                credenciales = json.loads(cipher_suite.decrypt(encrypted_data).decode())
                self.token = credenciales.get('token')
                self.user_id = credenciales.get('user_id')
            except Exception as e:
                print(f"⚠ Error cargando credenciales: {e}")
                self.configurar_credenciales()
        else:
            self.configurar_credenciales()

    def guardar_credenciales(self):
        """Guarda las credenciales encriptadas"""
        try:
            cipher_suite = Fernet(self.obtener_clave_encriptacion())
            datos = {'token': self.token, 'user_id': self.user_id}
            encrypted_data = cipher_suite.encrypt(json.dumps(datos).encode())
            with open(CREDENTIALS_FILE, "wb") as f:
                f.write(encrypted_data)
            return True
        except Exception as e:
            print(f"❌ Error guardando credenciales: {e}")
            return False

    def configurar_credenciales(self):
        """Solicita y guarda las credenciales"""
        self.mostrar_banner()
        print("⚙️ Configuración inicial del bot\n")
        self.token = input("🔑 Introduce el TOKEN del bot de Telegram: ").strip()
        self.user_id = input("👤 Introduce tu ID de usuario de Telegram: ").strip()
        
        if self.guardar_credenciales():
            print("\n✅ Credenciales guardadas de forma segura")
        else:
            print("\n❌ Error al guardar credenciales")
        input("\nPresiona Enter para continuar...")

    def generar_rango_fechas(self, inicio, fin):
        fecha_inicio = datetime.strptime(inicio, '%Y%m%d')
        fecha_fin = datetime.strptime(fin, '%Y%m%d')
        return [(fecha_inicio + timedelta(days=i)).strftime('%Y%m%d') for i in range((fecha_fin - fecha_inicio).days + 1)]

    def generar_urls_por_fecha(self, fecha):
        fecha_str = datetime.strptime(fecha, '%Y%m%d').strftime('%Y-%m-%d')
        base_urls = []
        tlds = ['com', 'shop', 'xyz', 'net']
        for tld in tlds:
            url = f'https://newly-registered-domains.abtdomain.com/{fecha_str}-{tld}-newly-registered-domains-part-'
            filename = f'{fecha}_{tld}.txt'
            base_urls.append((url, filename))
        return base_urls

    def get_domains_from_page(self, url):
        response = requests.get(url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            return [div.text.strip() for div in soup.find_all('div', style=lambda v: v and 'word-wrap: break-word' in v) if div.text.strip()]
        return []

    def buscar_dominios(self, base_url_data, palabras_clave=None):
        all_domains = []
        for base_url, _ in base_url_data:
            part = 1
            while True:
                current_url = f"{base_url}{part}/"
                domains = self.get_domains_from_page(current_url)
                if not domains:
                    break
                all_domains.extend(domains)
                part += 1

        if palabras_clave:
            palabras_clave = [p.strip().lower() for p in palabras_clave.split(',')]
            conteo = {p: 0 for p in palabras_clave}
            filtrados = []
            for dominio in all_domains:
                for palabra in palabras_clave:
                    if palabra in dominio.lower():
                        conteo[palabra] += 1
                        filtrados.append(dominio)
                        break
            return filtrados, conteo
        return all_domains, {}

    def buscar_whois(self, dominio):
        try:
            data = whois.whois(dominio)
            return {
                "nombre_dominio": data.get('domain_name', '').lower(),
                "fecha_creacion": data.get('creation_date', ''),
                "fecha_expiracion": data.get('expiration_date', ''),
                "registrador": data.get('registrar', ''),
                "abuse_contacto": data.get('emails', ''),
                "nameservers": data.get('nameservers', ''),
                "estado": data.get('status', ''),
                "servidor_whois": data.get('whois_server', ''),
                "registrante": data.get('registrant', ''),
                "contacto_administrador": data.get('admin_contact', ''),
                "contacto_tecnico": data.get('tech_contact', '')
            }
        except Exception as e:
            print(f"Error WHOIS para {dominio}: {e}")
            return None

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "👋 ¡Bienvenido al bot de búsqueda de dominios!\n\n"
            "Este bot te permite consultar dominios registrados en una fecha específica o dentro de un rango de fechas. 🌐\n\n"
            "Por favor, ingresa una fecha o un rango de fechas en el siguiente formato:\n\n"
            "📅 Fecha individual: `AAAAMMDD`\n"
            "📅 Rango de fechas: `AAAAMMDD-AAAAMMDD`\n\n"
            "Ejemplos:\n"
            "20240115 → Dominios registrados ese día\n"
            "20240101-20240131 → Dominios registrados durante enero 2024\n\n"
            "⌛ Esperando tu entrada..."
        )
        return FECHA

    async def obtener_fecha(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        fecha = update.message.text.strip()
        try:
            if '-' in fecha:
                inicio, fin = fecha.split('-')
                datetime.strptime(inicio, '%Y%m%d')
                datetime.strptime(fin, '%Y%m%d')
                context.user_data['rango_fechas'] = self.generar_rango_fechas(inicio, fin)
            else:
                datetime.strptime(fecha, '%Y%m%d')
                context.user_data['rango_fechas'] = [fecha]
            await update.message.reply_text("¿Quieres 'TODOS' los dominios o usar 'PALABRAS' clave?")
            return OPCION
        except ValueError:
            await update.message.reply_text("Formato inválido. Intenta otra vez.")
            return FECHA

    async def obtener_opcion(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        opcion = update.message.text.strip().lower()
        if opcion == 'todos':
            context.user_data['opcion'] = 'todos'
            await update.message.reply_text("Buscando todos los dominios. Espera un momento...")
            dominios = []
            for fecha in context.user_data['rango_fechas']:
                urls = self.generar_urls_por_fecha(fecha)
                encontrados, _ = self.buscar_dominios(urls)
                dominios.extend(encontrados)
            await self.procesar_whois_y_enviar(update, dominios)
            return ConversationHandler.END
        elif opcion == 'palabras':
            context.user_data['opcion'] = 'palabras'
            await update.message.reply_text("Dime las palabras clave separadas por comas.")
            return PALABRAS_CLAVE
        else:
            await update.message.reply_text("Responde con 'TODOS' o 'PALABRAS'.")
            return OPCION

    async def obtener_palabras_clave(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        palabras = update.message.text.strip()
        context.user_data['palabras_clave'] = palabras
        await update.message.reply_text(f"Buscando dominios con: {palabras}")
        total_conteo = {p: 0 for p in palabras.split(',')}
        dominios = []
        for fecha in context.user_data['rango_fechas']:
            urls = self.generar_urls_por_fecha(fecha)
            encontrados, conteo = self.buscar_dominios(urls, palabras)
            dominios.extend(encontrados)
            for palabra, c in conteo.items():
                total_conteo[palabra] += c
        await self.procesar_whois_y_enviar(update, dominios)
        resumen = "\n".join([f"- {k.strip()}: {v}" for k, v in total_conteo.items()])
        await update.message.reply_text(f"Resumen de coincidencias:\n{resumen}")
        return ConversationHandler.END

    async def procesar_whois_y_enviar(self, update: Update, dominios):
        if dominios:
            whois_data = [self.buscar_whois(d) for d in dominios if self.buscar_whois(d)]
            df = pd.DataFrame(whois_data)
            with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp:
                df.to_excel(tmp.name, index=False, engine='openpyxl')
                tmp.close()
                with open(tmp.name, 'rb') as f:
                    await update.message.reply_document(f, filename='dominios_whois.xlsx')
            os.unlink(tmp.name)
        else:
            await update.message.reply_text("❌ No se encontraron dominios con los criterios especificados.")

    def run(self):
        """Inicia el bot"""
        if not self.token or not self.user_id:
            print("❌ No se pudieron cargar las credenciales necesarias")
            return

        application = Application.builder().token(self.token).build()

        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', self.start)],
            states={
                FECHA: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.obtener_fecha)],
                OPCION: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.obtener_opcion)],
                PALABRAS_CLAVE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.obtener_palabras_clave)],
            },
            fallbacks=[],
        )

        application.add_handler(conv_handler)
        print("\n🤖 Bot iniciado correctamente")
        application.run_polling()

if __name__ == '__main__':
    try:
        bot = DominiosWhoisBot()
        bot.run()
    except KeyboardInterrupt:
        print("\n👋 Bot detenido por el usuario")
    except Exception as e:
        print(f"\n❌ Error fatal: {str(e)}")
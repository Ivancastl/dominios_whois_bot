import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler, ContextTypes
from datetime import datetime, timedelta
import pandas as pd 
import requests
from bs4 import BeautifulSoup
import tempfile
import whois

# Definir estados para la conversación
FECHA, OPCION, PALABRAS_CLAVE = range(3)

# Cargar o pedir credenciales
def cargar_credenciales():
    archivo_credenciales = 'credenciales.txt'
    if os.path.exists(archivo_credenciales):
        with open(archivo_credenciales, 'r') as f:
            lineas = f.readlines()
            token = lineas[0].strip()
            user_id = lineas[1].strip()
            return token, user_id
    else:
        token = input("Introduce el TOKEN del bot de Telegram: ").strip()
        user_id = input("Introduce tu ID de usuario de Telegram: ").strip()
        with open(archivo_credenciales, 'w') as f:
            f.write(f"{token}\n{user_id}")
        return token, user_id

# Funciones auxiliares
def generar_rango_fechas(inicio, fin):
    fecha_inicio = datetime.strptime(inicio, '%Y%m%d')
    fecha_fin = datetime.strptime(fin, '%Y%m%d')
    return [(fecha_inicio + timedelta(days=i)).strftime('%Y%m%d') for i in range((fecha_fin - fecha_inicio).days + 1)]

def generar_urls_por_fecha(fecha):
    fecha_str = datetime.strptime(fecha, '%Y%m%d').strftime('%Y-%m-%d')
    base_urls = []
    tlds = ['com', 'shop', 'xyz', 'net']
    for tld in tlds:
        url = f'https://newly-registered-domains.abtdomain.com/{fecha_str}-{tld}-newly-registered-domains-part-'
        filename = f'{fecha}_{tld}.txt'
        base_urls.append((url, filename))
    return base_urls

def get_domains_from_page(url):
    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        return [div.text.strip() for div in soup.find_all('div', style=lambda v: v and 'word-wrap: break-word' in v) if div.text.strip()]
    return []

def buscar_dominios(base_url_data, palabras_clave=None):
    all_domains = []
    for base_url, _ in base_url_data:
        part = 1
        while True:
            current_url = f"{base_url}{part}/"
            domains = get_domains_from_page(current_url)
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

def buscar_whois(dominio):
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

# Conversaciones
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 ¡Bienvenido al bot de búsqueda de dominios!\n\n"
        "Este bot te permite consultar **dominios registrados** en una fecha específica o dentro de un rango de fechas. 🌐\n\n"
        "Por favor, ingresa una fecha o un rango de fechas en el siguiente formato:\n\n"
        "📅 **Fecha individual:** `AAAAMMDD`\n"
        "📅 **Rango de fechas:** `AAAAMMDD-AAAAMMDD`\n\n"
        "Ejemplos:\n"
        "`20240115` → Dominios registrados ese día\n"
        "`20240101-20240131` → Dominios registrados durante enero 2024\n\n"
        "⌛ Esperando tu entrada..."
    )
    return FECHA


async def obtener_fecha(update: Update, context: ContextTypes.DEFAULT_TYPE):
    fecha = update.message.text.strip()
    try:
        if '-' in fecha:
            inicio, fin = fecha.split('-')
            datetime.strptime(inicio, '%Y%m%d')
            datetime.strptime(fin, '%Y%m%d')
            context.user_data['rango_fechas'] = generar_rango_fechas(inicio, fin)
        else:
            datetime.strptime(fecha, '%Y%m%d')
            context.user_data['rango_fechas'] = [fecha]
        await update.message.reply_text("¿Quieres 'TODOS' los dominios o usar 'PALABRAS' clave?")
        return OPCION
    except ValueError:
        await update.message.reply_text("Formato inválido. Intenta otra vez.")
        return FECHA

async def obtener_opcion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    opcion = update.message.text.strip().lower()
    if opcion == 'todos':
        context.user_data['opcion'] = 'todos'
        await update.message.reply_text("Buscando todos los dominios. Espera un momento...")
        dominios = []
        for fecha in context.user_data['rango_fechas']:
            urls = generar_urls_por_fecha(fecha)
            encontrados, _ = buscar_dominios(urls)
            dominios.extend(encontrados)
        await procesar_whois_y_enviar(update, dominios)
        return ConversationHandler.END
    elif opcion == 'palabras':
        context.user_data['opcion'] = 'palabras'
        await update.message.reply_text("Dime las palabras clave separadas por comas.")
        return PALABRAS_CLAVE
    else:
        await update.message.reply_text("Responde con 'TODOS' o 'PALABRAS'.")
        return OPCION

async def obtener_palabras_clave(update: Update, context: ContextTypes.DEFAULT_TYPE):
    palabras = update.message.text.strip()
    context.user_data['palabras_clave'] = palabras
    await update.message.reply_text(f"Buscando dominios con: {palabras}")
    total_conteo = {p: 0 for p in palabras.split(',')}
    dominios = []
    for fecha in context.user_data['rango_fechas']:
        urls = generar_urls_por_fecha(fecha)
        encontrados, conteo = buscar_dominios(urls, palabras)
        dominios.extend(encontrados)
        for palabra, c in conteo.items():
            total_conteo[palabra] += c
    await procesar_whois_y_enviar(update, dominios)
    resumen = "\n".join([f"- {k.strip()}: {v}" for k, v in total_conteo.items()])
    await update.message.reply_text(f"Resumen de coincidencias:\n{resumen}")
    return ConversationHandler.END

async def procesar_whois_y_enviar(update: Update, dominios):
    if dominios:
        whois_data = [buscar_whois(d) for d in dominios if buscar_whois(d)]
        df = pd.DataFrame(whois_data)
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp:
            df.to_excel(tmp.name, index=False, engine='openpyxl')
            tmp.close()
            with open(tmp.name, 'rb') as f:
                await update.message.reply_document(f, filename='dominios_whois.xlsx')

# MAIN
if __name__ == '__main__':
    token, user_id = cargar_credenciales()
    application = Application.builder().token(token).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            FECHA: [MessageHandler(filters.TEXT & ~filters.COMMAND, obtener_fecha)],
            OPCION: [MessageHandler(filters.TEXT & ~filters.COMMAND, obtener_opcion)],
            PALABRAS_CLAVE: [MessageHandler(filters.TEXT & ~filters.COMMAND, obtener_palabras_clave)],
        },
        fallbacks=[],
    )

    application.add_handler(conv_handler)
    application.run_polling()

# Bot de Búsqueda de Dominios por Fecha 📆🌐

Este bot de Telegram permite consultar dominios registrados en una fecha específica o dentro de un rango de fechas. Ideal para tareas de OSINT y análisis de tendencias de registro.

## 🚀 ¿Qué hace?

- Permite al usuario ingresar una fecha o rango de fechas en formato `AAAAMMDD` o `AAAAMMDD-AAAAMMDD`.
- Devuelve una lista de dominios registrados en esa fecha o período.
- Simple, interactivo y útil para investigadores digitales.

## 🛠️ Uso

1. Inicia el bot con `/start`.
2. Ingresa una fecha o rango en el formato indicado.
3. Recibe una lista de dominios registrados.

## Instalación

### **Paso 1:**
# Clona este repositorio 
```bash
git clone https://github.com/Ivancastl/dominios_whois_bot
```

### **Paso 2:**
# Accede al directorio del proyecto.
```bash
cd dominios_whois_bot
```

### **Paso 3:**
# Instala las dependencias necesarias.
```bash
pip install -r requirements.txt
```

### **Paso 4:**
# Ejecuta el script principal
```bash
python dominios_bot.py
```

##  
Token y ID
Al ejecutar el script por primera vez, se te solicitará ingresar tu token y ID para guardar la sesión. Esta información se almacenará en un archivo .txt, por lo que no tendrás que ingresarla nuevamente en futuras ejecuciones.

Si deseas cambiar el token o el ID, simplemente elimina el archivo .txt correspondiente y el script volverá a pedirte los datos al iniciarse.

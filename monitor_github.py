#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Monitor para GitHub Actions - Búsqueda de Anubis Octavio Clavijo Valencia
Corre automáticamente cada 24 horas en GitHub
"""

import requests
import json
import os
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ==========================================
# CONFIGURACIÓN
# ==========================================

NOMBRES_BUSCAR = [
    "Clavijo",
    "Klavijo",
    "Клавихо",
    "Anubis",
    "Анубис",
    "Valencia",
    "Валенсия",
    "Alkons",
    "Анубис Октавио",
    "Anubis Octavio"
]

URLS_MONITOREAR = [
    {
        "url": "https://200.zona.media",
        "nombre": "Mediazona Base de Datos"
    },
    {
        "url": "https://zona.media/article/2026/03/27/perdidas",
        "nombre": "Mediazona Estadísticas"
    }
]

# Email de destino (desde secrets de GitHub)
EMAIL_DESTINO = os.environ.get('EMAIL_DESTINO', 'spikeblade@gmail.com')

# ==========================================
# FUNCIONES
# ==========================================

def buscar_en_url(url_info):
    """
    Busca términos en una URL específica
    """
    url = url_info["url"]
    nombre = url_info["nombre"]
    
    print(f"📡 Revisando: {nombre}")
    print(f"   URL: {url}")
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code != 200:
            print(f"   ⚠️  Status code: {response.status_code}")
            return {
                "sitio": nombre,
                "url": url,
                "encontrado": False,
                "terminos": [],
                "error": f"Status code {response.status_code}"
            }
        
        contenido = response.text.lower()
        encontrados = []
        
        for termino in NOMBRES_BUSCAR:
            if termino.lower() in contenido:
                encontrados.append(termino)
                print(f"   ✅ ENCONTRADO: {termino}")
        
        if not encontrados:
            print(f"   ❌ No se encontraron términos")
        
        return {
            "sitio": nombre,
            "url": url,
            "encontrado": len(encontrados) > 0,
            "terminos": encontrados,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"   ⚠️  Error: {str(e)}")
        return {
            "sitio": nombre,
            "url": url,
            "encontrado": False,
            "terminos": [],
            "error": str(e)
        }

def enviar_email_alerta(resultados_positivos):
    """
    Envía email si hay resultados positivos
    Requiere configurar secrets en GitHub
    """
    try:
        smtp_server = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
        smtp_port = int(os.environ.get('SMTP_PORT', '587'))
        smtp_user = os.environ.get('SMTP_USER', '')
        smtp_password = os.environ.get('SMTP_PASSWORD', '')
        
        if not smtp_user or not smtp_password:
            print("⚠️  Configuración de email no disponible")
            print("   Configura SMTP_USER y SMTP_PASSWORD en GitHub Secrets")
            return False
        
        mensaje = MIMEMultipart()
        mensaje['From'] = smtp_user
        mensaje['To'] = EMAIL_DESTINO
        mensaje['Subject'] = '🚨 ALERTA - Posible información de Anubis encontrada'
        
        cuerpo = "🚨 ALERTA AUTOMÁTICA - Monitor GitHub Actions\n\n"
        cuerpo += "Se encontraron términos relacionados con Anubis Octavio Clavijo Valencia:\n\n"
        
        for resultado in resultados_positivos:
            cuerpo += f"Sitio: {resultado['sitio']}\n"
            cuerpo += f"URL: {resultado['url']}\n"
            cuerpo += f"Términos encontrados: {', '.join(resultado['terminos'])}\n"
            cuerpo += f"Fecha: {resultado['timestamp']}\n"
            cuerpo += "-" * 60 + "\n\n"
        
        cuerpo += "\n⚠️  IMPORTANTE: Revisa manualmente los sitios para confirmar la información.\n"
        cuerpo += f"\nEsta alerta fue generada automáticamente el {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}"
        
        mensaje.attach(MIMEText(cuerpo, 'plain', 'utf-8'))
        
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(mensaje)
        
        print(f"✅ Email enviado a {EMAIL_DESTINO}")
        return True
        
    except Exception as e:
        print(f"⚠️  Error enviando email: {e}")
        return False

def guardar_resultados(todos_resultados):
    """
    Guarda resultados en archivo para histórico
    """
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')
    
    with open('resultados.txt', 'w', encoding='utf-8') as f:
        f.write("="*70 + "\n")
        f.write("MONITOR AUTOMÁTICO - BÚSQUEDA DE ANUBIS OCTAVIO CLAVIJO VALENCIA\n")
        f.write("="*70 + "\n")
        f.write(f"Fecha ejecución: {timestamp}\n")
        f.write(f"Email alertas: {EMAIL_DESTINO}\n")
        f.write("="*70 + "\n\n")
        
        for resultado in todos_resultados:
            f.write(f"Sitio: {resultado['sitio']}\n")
            f.write(f"URL: {resultado['url']}\n")
            
            if 'error' in resultado:
                f.write(f"⚠️  ERROR: {resultado['error']}\n")
            elif resultado['encontrado']:
                f.write(f"✅ ENCONTRADO: {', '.join(resultado['terminos'])}\n")
            else:
                f.write(f"❌ No encontrado\n")
            
            f.write("-" * 70 + "\n\n")
        
        # Resumen
        encontrados = [r for r in todos_resultados if r['encontrado']]
        f.write("\n" + "="*70 + "\n")
        f.write("RESUMEN:\n")
        f.write("="*70 + "\n")
        f.write(f"Total sitios revisados: {len(todos_resultados)}\n")
        f.write(f"Sitios con resultados: {len(encontrados)}\n")
        
        if encontrados:
            f.write("\n🚨 SE ENCONTRARON COINCIDENCIAS - REVISAR MANUALMENTE\n")
        else:
            f.write("\n✅ No se encontraron coincidencias en esta ejecución\n")
    
    print(f"\n📄 Resultados guardados en resultados.txt")

def main():
    """
    Función principal
    """
    print("="*70)
    print("🔍 MONITOR AUTOMÁTICO - GITHUB ACTIONS")
    print("="*70)
    print(f"Inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"Términos de búsqueda: {len(NOMBRES_BUSCAR)}")
    print(f"Sitios a revisar: {len(URLS_MONITOREAR)}")
    print(f"Email alertas: {EMAIL_DESTINO}")
    print("="*70 + "\n")
    
    todos_resultados = []
    
    # Revisar cada URL
    for url_info in URLS_MONITOREAR:
        resultado = buscar_en_url(url_info)
        todos_resultados.append(resultado)
        print()  # Línea en blanco entre sitios
    
    # Guardar resultados
    guardar_resultados(todos_resultados)
    
    # Enviar alerta si hay coincidencias
    resultados_positivos = [r for r in todos_resultados if r['encontrado']]
    
    if resultados_positivos:
        print("\n" + "="*70)
        print("🚨 ¡ALERTA! SE ENCONTRARON COINCIDENCIAS")
        print("="*70)
        enviar_email_alerta(resultados_positivos)
    else:
        print("\n" + "="*70)
        print("✅ No se encontraron coincidencias en esta ejecución")
        print("="*70)
    
    print(f"\n✅ Ejecución completada: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")

if __name__ == "__main__":
    main()

import streamlit as st
from fpdf import FPDF
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io
from datetime import datetime

# --- CONFIGURACIÓN DE GOOGLE DRIVE ---
# En Streamlit Cloud, sube tu credentials.json o usa st.secrets
SCOPES = ['https://www.googleapis.com/auth/drive']
SERVICE_ACCOUNT_FILE = 'credentials.json' # Tu archivo descargado
PARENT_FOLDER_ID = 'ID_DE_TU_CARPETA_RAIZ' # El ID del link de tu carpeta en Drive

def get_drive_service():
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    return build('drive', 'v3', credentials=creds)

def obtener_o_crear_carpeta(service, nombre_cliente):
    """Busca la carpeta del cliente, si no existe la crea dentro de la carpeta raíz."""
    query = f"name = '{nombre_cliente}' and mimeType = 'application/vnd.google-apps.folder' and '{PARENT_FOLDER_ID}' in parents and trashed = false"
    results = service.files().list(q=query, spaces='drive').execute()
    items = results.get('files', [])

    if items:
        return items[0]['id']
    else:
        # Crear carpeta nueva
        file_metadata = {
            'name': nombre_cliente,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [PARENT_FOLDER_ID]
        }
        folder = service.files().create(body=file_metadata, fields='id').execute()
        return folder.get('id')

def subir_pdf_a_drive(pdf_content, filename, folder_id):
    """Sube el contenido del PDF a la carpeta específica del cliente."""
    service = get_drive_service()
    file_metadata = {'name': filename, 'parents': [folder_id]}
    media = MediaIoBaseUpload(io.BytesIO(pdf_content), mimetype='application/pdf')
    file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    return file.get('id')

# --- LÓGICA DE GENERACIÓN DE PDF (IGUAL AL ANTERIOR) ---
def crear_pdf_bytes(datos, items):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, f"COTIZACIÓN N° {datos['n_cot']}", 0, 1, 'R')
    pdf.set_font("Arial", '', 12)
    pdf.cell(0, 10, f"Cliente: {datos['cliente']}", 0, 1)
    pdf.cell(0, 10, f"Comuna: {datos['comuna']}", 0, 1)
    # ... (Aquí iría el resto del diseño de la tabla que hicimos antes)
    return pdf.output(dest='S').encode('latin-1')

# --- INTERFAZ STREAMLIT ---
st.title("🚀 Sistema de Cotizaciones Cloud (Drive Sync)")

with st.form("cotizador"):
    cliente = st.text_input("Nombre del Cliente")
    comuna = st.text_input("Comuna")
    n_cot = st.text_input("Número de Cotización")
    
    # Simulación de items (en un caso real usarías st.data_editor)
    descripcion = st.text_area("Descripción de productos (ej: 3 Monitores Samsung)")
    total_neto = st.number_input("Total Neto $", min_value=0)
    
    boton = st.form_submit_button("Generar y Organizar en Drive")

if boton:
    with st.spinner("Generando PDF y organizando en la nube..."):
        try:
            # 1. Crear el PDF en memoria
            datos = {"cliente": cliente, "comuna": comuna, "n_cot": n_cot}
            pdf_bytes = crear_pdf_bytes(datos, [])
            
            # 2. Conectar con Drive
            service = get_drive_service()
            
            # 3. Organizar por cliente (Paso C)
            folder_id = obtener_o_crear_carpeta(service, f"Cotizaciones_{cliente}")
            
            # 4. Subir archivo
            nombre_archivo = f"Cot_{n_cot}_{cliente}_{datetime.now().strftime('%Y%m%d')}.pdf"
            file_id = subir_pdf_a_drive(pdf_bytes, nombre_archivo, folder_id)
            
            st.success(f"✅ ¡Hecho! El archivo se guardó en Google Drive en la carpeta: Cotizaciones_{cliente}")
            st.info(f"ID del archivo en la nube: {file_id}")
            
            # Opción de descarga local también
            st.download_button("Descargar copia local", data=pdf_bytes, file_name=nombre_archivo)
            
        except Exception as e:
            st.error(f"Error de conexión: {e}")
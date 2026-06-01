import streamlit as st
import json
try:
    import google.generativeai as genai
except ModuleNotFoundError:
    genai = None
    st.error("Módulo 'google.generativeai' não encontrado. Instale as dependências com `pip install -r requirements.txt` ou adicione o arquivo requirements.txt no deploy do Streamlit.")
    st.stop()
from PIL import Image
from fpdf import FPDF  # Recomenda-se: pip install fpdf2
import io
from pdf2image import convert_from_bytes
import typing_extensions as typing

# ---- 1. CONFIGURAÇÃO DA PÁGINA ----
st.set_page_config(
    page_title="BRALLI — Multi-Norma Batch Analysis",
    page_icon="logo.png", 
    layout="wide"
)

# --- 2. MEMÓRIA DA SESSÃO --- 
if 'uploader_key' not in st.session_state:
    st.session_state['uploader_key'] = 0
if 'batch_results' not in st.session_state:
    st.session_state['batch_results'] = {}

# --- 3. DEFINIÇÃO DO ESQUEMA DE RETORNO DA IA ---
class RequisitoAnalise(typing.TypedDict):
    id: int
    item: str
    status: str
    justificativa: str

# --- 4. FUNÇÕES AUXILIARES ---
def load_requirements(nome_arquivo): 
    try:
        with open(nome_arquivo, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        st.error(f"Arquivo '{nome_arquivo}' não encontrado na pasta do projeto. Certifique-se de que o arquivo JSON está presente.")
        return None

class PDFReport(FPDF):
    def __init__(self, norma_nome):
        super().__init__()
        self.norma_nome = norma_nome

    def header(self):
        self.set_font('Helvetica', 'B', 14)
        self.cell(0, 10, 'Relatorio Consolidado de Auditoria em Lote', 0, 1, 'C')
        self.set_font('Helvetica', 'I', 10)
        self.cell(0, 10, f'Diretriz: {self.norma_nome} / Plataforma BRALLI', 0, 1, 'C')
        self.ln(5)
        
    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.cell(0, 10, f'Pagina {self.page_no()}', 0, 0, 'C')

def generate_batch_pdf(batch_results, norma_nome):
    pdf = PDFReport(norma_nome)
    
    for filename, results in batch_results.items():
        pdf.add_page()
        
        # Título do Projeto/Arquivo
        pdf.set_font("Helvetica", 'B', 14)
        pdf.set_text_color(74, 144, 226) # Azul BRALLI
        titulo_projeto = f"Projeto: {filename}".encode('windows-1252', errors='ignore').decode('windows-1252')
        pdf.cell(0, 12, titulo_projeto, 0, 1)
        pdf.set_text_color(0, 0, 0) # Reset para preto
        pdf.ln(2)
        
        for item in results:
            pdf.set_font("Helvetica", 'B', 11)
            id_item = item.get('id', '-')
            nome_item = item.get('item', 'Item nao especificado')
            status_item = item.get('status', 'Nao avaliado')
            
            texto_justificativa = item.get('justificativa') or item.get('justificativa_tecnica') or item.get('Justificativa') or 'Sem justificativa disponivel.'
            
            titulo = f"{id_item}. {nome_item}".encode('windows-1252', errors='ignore').decode('windows-1252')
            pdf.cell(0, 8, titulo, 0, 1)
            
            pdf.set_font("Helvetica", 'I', 10)
            status = f"Status: {status_item}".encode('windows-1252', errors='ignore').decode('windows-1252')
            pdf.cell(0, 6, status, 0, 1)
            
            pdf.set_font("Helvetica", size=10)
            justificativa = f"Justificativa: {texto_justificativa}".encode('windows-1252', errors='ignore').decode('windows-1252')
            pdf.multi_cell(0, 5, justificativa)
            pdf.ln(4)
            
    pdf_raw = pdf.output()
    return bytes(pdf_raw)

def nova_analise_lote():
    st.session_state.uploader_key += 1
    st.session_state.batch_results = {}

# --- 5. INTERFACE DO USUÁRIO ---
st.markdown(
    """
    <div style="display: flex; justify-content: center; margin-bottom: 20px;">
        <h1 style="font-family: sans-serif; color: #4A90E2; letter-spacing: 2px;">BRALLI</h1>
    </div>
    """,
    unsafe_allow_html=True
)

st.title("🗂️ Auditoria de Projetos Multi-Normas")
st.write("Selecione o tipo de análise técnica, carregue os arquivos e execute a auditoria por IA.")

# --- 6. SIDEBAR: CONFIGURAÇÕES E SELEÇÃO DE ANÁLISE --- 
with st.sidebar:
    st.header("⚙️ Configurações do Sistema")
    
    api_key_input = st.text_input(
        "Chave API do Gemini", 
        type="password", 
        help="Insira sua chave gerada no Google AI Studio."
    )
    
    temp_input = st.slider(
        "Criatividade da IA (Temperature)", 
        min_value=0.0, max_value=1.0, value=0.0, step=0.1,
        help="Mantenha em 0.0 para garantir precisão normativa factual."
    )
    
    modelos_disponiveis = ["gemini-1.5-flash", "gemini-2.0-flash"]
    
    if api_key_input:
        genai.configure(api_key=api_key_input)
        try:
            modelos_dinamicos = []
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    nome_limpo = m.name.replace('models/', '')
                    if 'flash' in nome_limpo:
                        modelos_dinamicos.append(nome_limpo)
            if modelos_dinamicos:
                modelos_disponiveis = sorted(list(set(modelos_dinamicos)))
        except Exception:
            st.error("⚠️ Erro: Verifique sua Chave API.")

    model_choice = st.selectbox("Modelo LLM", modelos_disponiveis)
    
    st.divider()
    
    # MAPEAMENTO DAS TRÊS DIRETRIZES DE ANÁLISE
    st.header("📚 Tipo de Análise")
    opcao_norma = st.selectbox(
        "Escolha o escopo de auditoria:",
        [
            "Análise Técnica Original", 
            "Acessibilidade (NBR 9050)", 
            "Conforto Acústico (NBR 15575)"
        ]
    )
    
    # Configuração dinâmica baseada na seleção
    if opcao_norma == "Análise Técnica Original":
        arquivo_norma = "requisitos_normativos.json"
        persona_prompt = "Você é um auditor especialista em engenharia e arquitetura executiva."
    elif opcao_norma == "Acessibilidade (NBR 9050)":
        arquivo_norma = "requisitos_acessibilidade.json"
        persona_prompt = "Você é um auditor especialista em acessibilidade e arquitetura inclusiva."
    else:
        arquivo_norma = "requisitos_acustica.json"
        persona_prompt = "Você é um engenheiro especialista em desempenho térmico e acústico de edificações."

# --- 7. FLUXO DE UPLOAD (MÚLTIPLOS ARQUIVOS) ---
if not api_key_input:
    st.warning("👈 Por favor, insira sua Chave API do Gemini na barra lateral para iniciar a aplicação.")
else:
    uploaded_files = st.file_uploader(
        "Arraste as pranchas ou arquivos dos projetos (.jpeg, .png, .pdf)", 
        type=["jpg", "jpeg", "png", "pdf"],
        accept_multiple_files=True,
        key=f"uploader_{st.session_state.uploader_key}"
    )

    CAMINHO_POPPLER = r'H:\Meu Drive\PROFISSIONAL\CURSOS\Master IA Zigurat\M7T1 -\02. Código\poppler-26.02.0\Library\bin' 

    if uploaded_files and not st.session_state.batch_results:
        st.info(f"📁 {len(uploaded_files)} arquivo(s) carregado(s) pronto(s) para: **{opcao_norma}**.")
        
        if st.button(f"🚀 Executar Auditoria — {opcao_norma}", type="primary", use_container_width=True):
            data = load_requirements(arquivo_norma)
            
            if data:
                contexto_normativo = json.dumps(data['requisitos'], ensure_ascii=False)
                
                model = genai.GenerativeModel(
                    model_name=model_choice,
                    generation_config={
                        "response_mime_type": "application/json",
                        "response_schema": list[RequisitoAnalise],
                        "temperature": temp_input
                    }
                )
                
                prompt = f"""
                {persona_prompt}
                Analise minuciosamente a imagem do projeto técnico fornecida.
                Sua tarefa é avaliar o projeto com base nos seguintes critérios normativos:
                {contexto_normativo}
                
                Determine o status ("Atendido", "Não Atendido" ou "Parcialmente Atendido") e forneça uma justificativa técnica detalhada.
                """
                
                progresso_bar = st.progress(0)
                status_texto = st.empty()
                resultados_temporarios = {}
                
                for idx, file in enumerate(uploaded_files):
                    status_texto.markdown(f"🔄 **Processando ({idx+1}/{len(uploaded_files)}):** {file.name}...")
                    images_to_analyze = []
                    
                    if file.type == "application/pdf":
                        try:
                            file_bytes = file.getvalue()
                            try:
                                decoded_images = convert_from_bytes(file_bytes, dpi=150, poppler_path=CAMINHO_POPPLER)
                            except Exception:
                                decoded_images = convert_from_bytes(file_bytes, dpi=150)
                            
                            images_to_analyze = decoded_images[:3]
                        except Exception as e:
                            st.error(f"Erro ao abrir as páginas do PDF {file.name}: {e}")
                            continue
                    else:
                        images_to_analyze = [Image.open(file)]
                    
                    if images_to_analyze:
                        try:
                            conteudo_requisicao = [prompt] + images_to_analyze
                            response = model.generate_content(conteudo_requisicao)
                            resultados_temporarios[file.name] = json.loads(response.text.strip())
                        except Exception as e:
                            st.error(f"Erro na análise de IA do arquivo {file.name}: {e}")
                    
                    progresso_bar.progress((idx + 1) / len(uploaded_files))
                
                status_texto.empty()
                progresso_bar.empty()
                
                st.session_state.batch_results = resultados_temporarios
                st.rerun()

    # --- 8. EXIBIÇÃO DOS RESULTADOS CONSOLIDADOS ---
    if st.session_state.batch_results:
        st.success(f"✅ Auditoria Concluída! {len(st.session_state.batch_results)} projetos analisados sob o escopo de: **{opcao_norma}**.")
        
        abas = st.tabs(list(st.session_state.batch_results.keys()))
        
        for idx, (filename, resultados) in enumerate(st.session_state.batch_results.items()):
            with abas[idx]:
                st.subheader(f"Análise Técnica: {filename}")
                
                for res in resultados:
                    status_atual = res.get('status', 'Não avaliado')
                    status_lower = status_atual.lower()
                    
                    if "não" in status_lower:
                        cor_status = "🔴"
                    elif "parcial" in status_lower:
                        cor_status = "🟡"
                    else:
                        cor_status = "🟢"
                    
                    with st.expander(f"{res.get('id', '-')}. {res.get('item', 'Item')} — {cor_status} {status_atual}"):
                        texto_just_tela = res.get('justificativa') or res.get('justificativa_tecnica') or res.get('Justificativa') or 'Sem justificativa disponível.'
                        st.write(texto_just_tela)
                        
        st.divider()
      
        col1, col2 = st.columns(2)
        with col1:
            try:
                pdf_data = generate_batch_pdf(st.session_state.batch_results, opcao_norma)
                st.download_button(
                    label="📥 Baixar Relatório Unificado (PDF)",
                    data=pdf_data,
                    file_name=f"Relatorio_{opcao_norma.replace(' ', '_')}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
            except Exception as pdf_err:
                st.error(f"Erro ao gerar o PDF consolidado: {pdf_err}")
            
        with col2:
            if st.button("🔄 Iniciar Nova Análise / Mudar Escopo", use_container_width=True):
                nova_analise_lote()
                st.rerun()

st.divider()
st.caption("Master em Inteligência Artificial para Arquitetura - ZIGURAT Institute of Technology")
import streamlit as st
import pandas as pd
import pdfplumber  # Para ler o PDF
import re
import io          # Para trabalhar com bytes em memória (para download)
# Não precisamos mais de 'sys' ou 'os' na versão Streamlit

# --- Função Principal de Processamento (Adaptada) ---
# Retorna uma tupla: (sucesso_boolean, dados_ou_erro, lista_mensagens_info)
def processar_pdf_para_streamlit(pdf_file_object):
    """
    Lê um objeto de arquivo PDF do Streamlit, extrai texto, processa dados
    no formato SIAPE e retorna bytes do Excel ou mensagem de erro.
    (Versão SEM a separação de CODIGO_RUBRICA)
    """
    extracted_text_lines = []
    info_messages = ["--- Iniciando processamento do PDF ---"]

    info_messages.append("--- Extraindo texto do PDF (pode levar um momento) ---")
    try:
        with pdfplumber.open(pdf_file_object) as pdf:
            num_pages = len(pdf.pages)
            info_messages.append(f"PDF contém {num_pages} página(s).")
            for i, page in enumerate(pdf.pages):
                info_messages.append(f"Processando página {i+1}/{num_pages}...")
                text = page.extract_text(x_tolerance=2, y_tolerance=2)
                if text:
                    extracted_text_lines.extend(text.split('\n'))
                else:
                    info_messages.append(f"Aviso: Nenhum texto extraído da página {i+1}.")
    except Exception as e:
        error_msg = f"Erro ao abrir ou extrair texto do PDF: {e}. Verifique se o arquivo não está corrompido ou protegido por senha."
        info_messages.append(error_msg)
        return False, error_msg, info_messages

    if not extracted_text_lines:
        error_msg = "Erro: Nenhum texto foi extraído do PDF."
        info_messages.append(error_msg)
        return False, error_msg, info_messages

    # --- Processamento do Texto Extraído ---
    extracted_data = []
    in_data_section = False
    data_pattern = re.compile(r'^(\S+)\s+(.*?)\s+(\d{1,3}(?:\.\d{3})*,\d{2})$')

    info_messages.append("--- Processando linhas do texto extraído ---")
    line_number = 0
    for line in extracted_text_lines:
        line_number += 1
        cleaned_line = line.strip()

        if 'CLSF.CONTABIL' in cleaned_line and 'DENOMINACAO / RUBRICA' in cleaned_line:
            in_data_section = True
            info_messages.append(f"Info Linha {line_number}: Seção de dados iniciada.")
            continue

        if not in_data_section or not cleaned_line or '---' in cleaned_line or cleaned_line.startswith('***') or 'SIAPE, GERENCIAL' in cleaned_line or cleaned_line.startswith('DATA:'):
            continue

        match = data_pattern.match(cleaned_line)
        if match:
            classificacao = match.group(1)
            denominacao = match.group(2).strip()
            valor_str = match.group(3)
            try:
                valor_float = float(valor_str.replace('.', '').replace(',', '.'))
                extracted_data.append([classificacao, denominacao, valor_float])
            except ValueError:
                info_messages.append(f"Aviso Linha {line_number}: Valor '{valor_str}' inválido na linha: {cleaned_line}")

    if not extracted_data:
        error_msg = "Atenção: Nenhum dado no formato esperado foi extraído após processar o texto do PDF."
        info_messages.append(error_msg)
        return False, error_msg, info_messages

    info_messages.append(f"--- Processamento de texto concluído. {len(extracted_data)} linhas de dados encontradas. ---")

    # --- Criação do DataFrame (SEM a reorganização) ---
    try:
        # Cria o DataFrame diretamente com as colunas extraídas
        df = pd.DataFrame(extracted_data, columns=['CLSF.CONTABIL', 'DENOMINACAO / RUBRICA', 'VALOR / TOTAL'])
        info_messages.append("--- DataFrame criado com os dados extraídos ---")

        # >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
        # Bloco de código de reorganização que foi REMOVIDO:
        # info_messages.append("--- Reorganizando códigos específicos ---")
        # df['CODIGO_RUBRICA'] = pd.NA
        # mask_rubricas = ~df['CLSF.CONTABIL'].astype(str).str.contains('.', regex=False, na=False)
        # df.loc[mask_rubricas, 'CODIGO_RUBRICA'] = df.loc[mask_rubricas, 'CLSF.CONTABIL']
        # df.loc[mask_rubricas, 'CLSF.CONTABIL'] = pd.NA
        # df = df[['CLSF.CONTABIL', 'CODIGO_RUBRICA', 'DENOMINACAO / RUBRICA', 'VALOR / TOTAL']]
        # info_messages.append("--- Reorganização concluída ---")
        # <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<

    except Exception as e:
        error_msg = f"Erro durante a criação do DataFrame: {e}"
        info_messages.append(error_msg)
        return False, error_msg, info_messages

    # --- Salvar no Excel (em memória) ---
    info_messages.append(f"--- Gerando arquivo Excel em memória ---")
    try:
        output_buffer = io.BytesIO()
        with pd.ExcelWriter(output_buffer, engine='openpyxl') as writer:
             # Salva o DataFrame com 3 colunas
             df.to_excel(writer, index=False, sheet_name='Dados_Extraidos', na_rep='')
        excel_bytes = output_buffer.getvalue()
        info_messages.append("\nArquivo Excel gerado com sucesso!")
        return True, excel_bytes, info_messages
    except Exception as e:
        error_msg = f"\nErro ao gerar o arquivo Excel: {e}"
        info_messages.append(error_msg)
        return False, error_msg, info_messages


# --- Interface Streamlit ---
st.set_page_config(page_title="PDF para Excel (SIAPE)", layout="wide") # Configura título da aba e layout

# Adiciona uma nota no rodapé ou barra lateral
with st.sidebar:
    st.header("Desenvolvido por Tiago Gandra :) - Adaptado para Streamlit")
    # Área de Upload
    uploaded_file = st.file_uploader("Escolha um arquivo PDF", type="pdf")

st.title("⚙️ Conversor de PDF da folha de pagamento ICMBio")
st.write("""
Esta ferramenta extrai dados da tabela da folha de pagamento do ICMBio
dentro de arquivos PDF e os converte para o formato Excel (.xlsx).
Faça o upload do seu arquivo PDF abaixo.
""")
st.markdown("---")


if uploaded_file is not None:
    st.info(f"Arquivo '{uploaded_file.name}' carregado. Iniciando processamento...")

    # Usar st.spinner para feedback visual durante o processamento
    with st.spinner("Extraindo dados do PDF e convertendo... Isso pode levar alguns segundos...⏳"):
        # Chama a função de processamento adaptada
        success, result_data, info_msgs = processar_pdf_para_streamlit(uploaded_file)

    # Exibe as mensagens de log/info coletadas em um expansor
    if info_msgs:
         with st.expander("Ver detalhes do processamento"):
              # Usar st.text para preservar a formatação ou st.write
              st.text("\n".join(info_msgs))

    st.markdown("---") # Linha divisória

    # Se o processamento foi bem-sucedido
    if success:
        st.success("✅ Processamento concluído com sucesso!")

        # Gera nome do arquivo para download
        download_filename = uploaded_file.name.replace('.pdf', '_convertido.xlsx').replace('.PDF', '_convertido.xlsx')

        # Botão de Download
        st.download_button(
            label="📥 Baixar Arquivo Excel (.xlsx)",
            data=result_data,  # Aqui 'result_data' contém os bytes do Excel
            file_name=download_filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" # MIME type para .xlsx
        )
    # Se houve erro no processamento
    else:
        # Aqui 'result_data' contém a mensagem de erro principal
        st.error("❌ Falha no Processamento!")
        st.error(f"Erro principal: {result_data}")
        st.warning("Verifique os detalhes do processamento acima. Certifique-se de que o PDF está no formato correto, não está corrompido ou protegido por senha.")

else:
    st.info("⬆️ Aguardando o upload de um arquivo PDF.")

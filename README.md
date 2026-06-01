# M7T1---Requisitos-Normativos

Plataforma para validação de requisitos com base em documento PDF usando Streamlit e Google Gemini.

## Instalação

1. Instale as dependências do projeto:

```bash
python -m pip install -r requirements.txt
```

2. Se você estiver usando o workspace do Codespace, use este Python:

```bash
/home/codespace/.python/current/bin/python -m streamlit run M7T1_PDF_NBR.py
```

3. Se estiver usando outro ambiente Python, selecione o interpretador correto no VS Code e execute:

```bash
streamlit run M7T1_PDF_NBR.py
```

## Observações

- O arquivo `requirements.txt` já inclui `streamlit`.
- Caso o VS Code continue mostrando erro em `import streamlit as st`, selecione o interpretador Python correto em:
  - `Ctrl+Shift+P`
  - `Python: Select Interpreter`

## Deploy

Veja `DEPLOY.md` para instruções de deploy no Streamlit Cloud.

# main.py (COMPLETO E ATUALIZADO)
import os
import sys
import subprocess
import shutil
import uuid
import json
import re
import io
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, Form
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

# Inicializa o FastAPI
app = FastAPI()

# --- CAMINHOS ---
CAMINHO_DO_SCRIPT_ATUAL = os.path.dirname(os.path.abspath(__file__)) # .../backend
CAMINHO_PAI = os.path.dirname(CAMINHO_DO_SCRIPT_ATUAL) # .../projeto-sped-automacao

CAMINHO_WALL_E = os.path.join(CAMINHO_DO_SCRIPT_ATUAL, "wall-e.py")
CAMINHO_LER_PDF = os.path.join(CAMINHO_DO_SCRIPT_ATUAL, "ler_pdf.py")
CAMINHO_ANALISAR_DETALHES = os.path.join(CAMINHO_DO_SCRIPT_ATUAL, "analisar_detalhes.py")
CAMINHO_FRONTEND = os.path.join(CAMINHO_PAI, "frontend") 
PASTA_UPLOADS = os.path.join(CAMINHO_DO_SCRIPT_ATUAL, "temp_uploads")
os.makedirs(PASTA_UPLOADS, exist_ok=True)


# --- FUNÇÃO DE LIMPEZA EM BACKGROUND ---
def _limpar_arquivos(caminhos_dos_arquivos):
    print(f"\nTAREFA DE LIMPEZA: Apagando arquivos: {caminhos_dos_arquivos}", file=sys.stderr)
    for caminho in caminhos_dos_arquivos:
        if caminho and os.path.exists(caminho):
            try:
                os.remove(caminho)
                print(f"Arquivo {os.path.basename(caminho)} apagado.", file=sys.stderr)
            except Exception as e:
                print(f"AVISO: Não foi possível apagar o arquivo {caminho}. Erro: {e}", file=sys.stderr)


# --- FUNÇÃO DE EXTRAÇÃO DO BLOCO E ---
def extrair_bloco_e_do_sped(caminho_txt):
    bloco_e_linhas, codigos_e111 = [], set()
    dentro_do_bloco_e = False
    try:
        with io.open(caminho_txt, 'r', encoding='latin-1') as f:
            for linha in f:
                linha_strip = linha.strip()
                if not linha_strip: continue
                if linha_strip.startswith('|E001|'): dentro_do_bloco_e = True
                if dentro_do_bloco_e:
                    bloco_e_linhas.append(linha_strip)
                    if linha_strip.startswith('|E111|'):
                        try:
                            campos = linha_strip.split('|')
                            if len(campos) > 3: codigos_e111.add(campos[2])
                        except: pass
                if linha_strip.startswith('|E990|'): break
        texto_bloco_e = "\n".join(bloco_e_linhas) if bloco_e_linhas else None
        return texto_bloco_e, list(codigos_e111)
    except Exception as e:
        print(f"ERRO CRÍTICO ao ler o arquivo TXT: {e}", file=sys.stderr)
        return None, []


# --- [FLUXO ROBÔ] ROTA MODIFICADA ---
@app.post("/upload-e-processar/")
async def processar_arquivos_com_robo(
    background_tasks: BackgroundTasks,
    file_sped: UploadFile = File(...), 
    file_livro: UploadFile = File(...),
    advanced_fields_str: str = Form("[]") # <-- [NOVO] Recebe os campos avançados
):
    id_unico = str(uuid.uuid4())
    path_sped_txt = os.path.abspath(os.path.join(PASTA_UPLOADS, f"{id_unico}_sped.txt"))
    path_livro_pdf = os.path.abspath(os.path.join(PASTA_UPLOADS, f"{id_unico}_livro.pdf"))
    
    background_tasks.add_task(_limpar_arquivos, [path_sped_txt, path_livro_pdf])

    try:
        with open(path_sped_txt, "wb") as buffer: shutil.copyfileobj(file_sped.file, buffer)
        with open(path_livro_pdf, "wb") as buffer: shutil.copyfileobj(file_livro.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao salvar arquivos: {e}")

    texto_bloco_e, lista_codigos_e111 = extrair_bloco_e_do_sped(path_sped_txt)
    codigos_e111_str = ",".join(lista_codigos_e111)
    
    try:
        print("Iniciando Robô Wall-E (Isso pode demorar)...", file=sys.stderr)
        python_exe = sys.executable 
        # [MODIFICADO] Passa o novo argumento 4
        command = [python_exe, CAMINHO_WALL_E, path_sped_txt, path_livro_pdf, codigos_e111_str, advanced_fields_str]
        
        resultado = subprocess.run(
            command, capture_output=True, text=True, check=True,
            encoding='cp1252', errors='ignore'
        )
        
        match = re.search(r'\{.*\}', resultado.stdout, re.DOTALL)
        if not match:
            print("ERRO: O script 'wall-e.py' não produziu um JSON válido.", file=sys.stderr)
            print("Saída do Robô:", resultado.stdout, resultado.stderr, file=sys.stderr)
            raise HTTPException(status_code=500, detail="Erro na análise: Nenhum JSON encontrado na saída do robô.")
            
        json_output = json.loads(match.group(0))
        json_output["bloco_e_texto"] = texto_bloco_e or "Bloco E não encontrado ou vazio."
        
        # O script analisar_detalhes.py não é chamado neste fluxo
        # Vamos adicionar o resultado dele (que o app.js espera) como vazio
        json_output["conciliacao_detalhes"] = []
        
        return JSONResponse(content=json_output)
            
    except subprocess.CalledProcessError as e:
        print(f"ERRO: O script 'wall-e.py' falhou:", e.stderr, file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"Erro no Robô (Wall-E): {e.stderr}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro inesperado no servidor: {e}")


# --- [FLUXO MANUAL] ROTA MODIFICADA ---
@app.post("/processar-manual/")
async def processar_arquivos_manual(
    background_tasks: BackgroundTasks,
    file_sped: UploadFile = File(...), 
    file_livro: UploadFile = File(...),
    file_entradas_pdf: UploadFile = File(...),
    file_saidas_pdf: UploadFile = File(...),
    file_apuracao_pdf: UploadFile = File(...),
    advanced_fields_str: str = Form("[]") # <-- [NOVO] Recebe os campos avançados
):
    id_unico = str(uuid.uuid4())
    
    arquivos_info = {
        "sped_txt": {"file": file_sped, "ext": ".txt"},
        "livro_pdf": {"file": file_livro, "ext": ".pdf"},
        "entradas_pdf": {"file": file_entradas_pdf, "ext": ".pdf"},
        "saidas_pdf": {"file": file_saidas_pdf, "ext": ".pdf"},
        "apuracao_pdf": {"file": file_apuracao_pdf, "ext": ".pdf"},
    }
    
    paths_salvos = {}
    try:
        for nome, info in arquivos_info.items():
            path = os.path.abspath(os.path.join(PASTA_UPLOADS, f"{id_unico}_{nome}{info['ext']}"))
            with open(path, "wb") as buffer:
                shutil.copyfileobj(info["file"].file, buffer)
            paths_salvos[nome] = path
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao salvar arquivos: {e}")

    background_tasks.add_task(_limpar_arquivos, list(paths_salvos.values()))
    
    texto_bloco_e, lista_codigos_e111 = extrair_bloco_e_do_sped(paths_salvos["sped_txt"])
    codigos_e111_str = ",".join(lista_codigos_e111)

    try:
        print("Iniciando Análise Manual (sem robô)...", file=sys.stderr)
        python_exe = sys.executable
        
        # 1. Executar ler_pdf.py (com 6 argumentos)
        command_ler_pdf = [
            python_exe, CAMINHO_LER_PDF,
            paths_salvos["livro_pdf"],
            paths_salvos["entradas_pdf"],
            paths_salvos["saidas_pdf"],
            paths_salvos["apuracao_pdf"],
            codigos_e111_str,
            advanced_fields_str # <-- [NOVO] Argumento 6
        ]
        res_ler_pdf = subprocess.run(
            command_ler_pdf, capture_output=True, text=True, check=True,
            encoding='cp1252', errors='ignore'
        )
        json_totais = json.loads(res_ler_pdf.stdout)
        print("--- Log ler_pdf.py (stderr) ---\n", res_ler_pdf.stderr, file=sys.stderr)

        # 2. Executar analisar_detalhes.py (o "HUNT", como estava antes)
        command_detalhes = [
            python_exe, CAMINHO_ANALISAR_DETALHES, 
            paths_salvos["sped_txt"],
            paths_salvos["livro_pdf"]
        ]
        res_detalhes = subprocess.run(
            command_detalhes, capture_output=True, text=True, check=True,
            encoding='cp1252', errors='ignore'
        )
        json_detalhes = json.loads(res_detalhes.stdout)
        print("--- Log analisar_detalhes.py (stderr) ---\n", res_detalhes.stderr, file=sys.stderr)
        
        # 3. Combinar os resultados
        json_totais["bloco_e_texto"] = texto_bloco_e or "Bloco E não encontrado ou vazio."
        json_final_combinado = {**json_totais, **json_detalhes}

        return JSONResponse(content=json_final_combinado)

    except subprocess.CalledProcessError as e:
        print(f"ERRO: Um script de análise falhou:", e.stderr, file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"Erro na execução do script: {e.stderr}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro inesperado no processamento manual: {e}")


# --- Monta o site e a página de progresso ---
@app.get("/progresso", response_class=JSONResponse)
async def get_progresso_page():
    return JSONResponse(content={"message": "Página de progresso. Lógica a ser implementada."})

app.mount("/", StaticFiles(directory=CAMINHO_FRONTEND, html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    if not os.path.exists(CAMINHO_FRONTEND):
        print(f"--- ERRO CRÍTICO ---")
        print(f"A pasta do frontend não foi encontrada em: {CAMINHO_FRONTEND}")
        sys.exit(1)
        
    print(f"Servidor FastAPI rodando em http://127.0.0.1:8000")
    print(f"Frontend sendo servido de: {CAMINHO_FRONTEND}") 
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
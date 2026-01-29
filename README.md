# Projeto SPED: (Versão Legacy V1.0)

> **"A automação onde não havia API."**
> Esta é a primeira versão do sistema de conciliação fiscal, que rodava em nuvem (Azure) interagindo visualmente com o programa PVA do governo.

---

 **Nota Histórica:** Este código representa a **Versão 1.0** (2025/2026), pioneira na automação fiscal do projeto. Embora tenha sido substituída por versões mais modernas feitas por mim baseadas em processamento de dados brutos, esta versão foi crucial para validar a lógica de conciliação.

---

## O Desafio Original
O **SPED (Sistema Público de Escrituração Digital)** e seu validador oficial, o **PVA**, são softwares desktop legados, sem API e extremamente manuais.
O desafio era claro: **Como automatizar a auditoria de arquivos fiscais gigantescos dentro de um software que não permite integração?**

Na época, não podíamos esperar. Precisávamos de uma solução que "operasse" o computador como um humano faria.

---

##  A Solução V1: "Visão Computacional na Nuvem"

Nesta versão, criamos um robô (RPA) hospedado na **Microsoft Azure** que literalmente "enxergava" a tela do PVA.

### A Engenharia por trás (O "Hack"):
1.  **Ambiente Virtualizado:** Uma VM Windows na Azure rodava o software PVA 24/7.
2.  **Operação Visual:** O script Python utilizava reconhecimento de imagem para identificar botões ("Validar", "Gerar Relatório", "Erros") na tela do programa governamental.
3.  **Extração OCR:** Como não tínhamos acesso ao banco de dados do PVA, o robô tirava "prints" dos relatórios de erro e usava OCR para transformar pixels em dados auditáveis.

Foi uma solução de **força bruta inteligente**. Onde não havia porta (API), nós entramos pela janela (Interface Gráfica).

---

## Stack Tecnológica (A Época de Ouro)

* **Infraestrutura:** Microsoft Azure VM (Windows Server)
* **Linguagem:** Python
* **Automação de Interface (RPA):** PyAutoGUI & OpenCV (Para achar os botões na tela)
* **OCR:** Tesseract (Para ler os relatórios do PVA)
* **Alvo:** Programa Validador e Assinador (PVA) - Receita Federal

---

##  Por que ficou obsoleto? (A Evolução)

Apesar de funcional, esta arquitetura tinha seus desafios que nos levaram à V2:
* **Velocidade:** Simular cliques do mouse é mais lento do que processar dados puros.
* **Fragilidade:** Se o governo mudasse a cor de um botão no PVA, o robô precisava ser recalibrado.
* **Custo:** Manter uma VM Windows com interface gráfica na Azure era custoso.

Hoje, o projeto evoluiu para o **ConciliadorSPED V2**, que processa o arquivo `.txt` do SPED diretamente, sem precisar abrir o PVA, ganhando em velocidade e estabilidade. Mas a V1.0 será sempre lembrada como a prova de que **era possível automatizar o impossível**.

---

##  Autor

Desenvolvido por **Nibson Muller**.
*Preservado para fins de portfólio e histórico de evolução técnica.*

---
*© 2026 Nibson Muller. Todos os direitos reservados.*
